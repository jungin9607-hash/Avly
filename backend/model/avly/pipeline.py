"""분석 전체 흐름 (원래 Avly.py 의 맨 아래 실행부).

지금은 터미널 실행을 그대로 옮긴 것이다. API 에서 쓰려면 분석(analyze)과 설문 반영(finalize)을 나누는 작업이 이어서 필요하다.
"""
from .dataio import prompt_text
import contextlib
import csv
import io
import json
import math
from pathlib import Path
from .constants import ACCIDENT_CONFIRMED_INPUT, CODE_VERSION, DETAIL_GATE_VERSION, MATCH_MODEL, OVERVIEW_MAX_IMAGES, REVIEW_IMAGES, STEP_SECONDS, VERBOSE, VERSION, VISION_MODEL
from .tables import SUPPORT_LABELS
from .context import ctx
from .config import configure_local_runtime
from .schemas import Matches, Observation, Scan
from .facts import collect_match_facts, mark_accident_input, parking_environment
from .vision import call, digest_file
from .video import background_cues, display_frames, get_frames, image_content, inspect_video, plan_review, review_high_ids, uniform_pick
from .observation import adaptive_review_prompt, apply_user_road_context, compact_observation, ground_observation, inspect_lane_cause, needs_detail_review, parking_background_review, reconcile_road_context, scan_as_observation, validate, verify_routes
from .matching import compare_all_csv_rows, conditional_candidates, link_match, matching_context, orientation_compatible, pack_catalog, prepare_matches, search_rows
from .adjustments import law_rule_bundle, public_scenarios, reference_scenarios, uncertainty_details
from .timeline import build_timeline, print_timeline, save_timeline_text
from .report import build_user_report, save_user_report
from .survey import supplemental_survey, survey_then_report


def run(settings):
    """영상 하나를 분석하고(3단계) 이어서 터미널 설문과 보고서까지 진행한다. (원래 Avly.py 의 실행부)"""
    # --- 실행 환경 준비 (원래는 모듈 최상단의 전역 문장이었다) ---------------------------------
    # settings: cli.py 가 명령줄 인자로 만든 dict (BACKEND_DIR, VIDEO_FILE, PICK_VIDEO, CSV_FILE, RESULTS_DIR,
    #           SHOW_PROCESS_LOGS, USE_CACHE, no_survey)
    _runtime = configure_local_runtime(settings)
    ctx.USE_CACHE = settings.get('USE_CACHE', True)
    ctx.SHOW_FRAMES = False
    ctx.SHOW_PROCESS_LOGS = settings.get('SHOW_PROCESS_LOGS', False)
    ctx.VIDEO_PATH = Path(_runtime['VIDEO_PATH'])
    CSV_PATH = _runtime['CSV_PATH']
    RESULTS_DIR = _runtime['RESULTS_DIR']

    ctx.csv_path = CSV_PATH
    with ctx.csv_path.open(encoding='utf-8-sig', newline='') as f:
        ctx.table = list(csv.DictReader(f))
    ctx.csv_normalization = []
    for row in ctx.table:
        for field in ('vehicle_a_progress_info_name', 'vehicle_b_progress_info_name'):
            original = row[field]
            normalized = original.replace('출자', '출차') if '주차구역' in original else original
            if normalized != original:
                row['raw_' + field] = original
                row[field] = normalized
                ctx.csv_normalization.append({'accident_type': row['accident_type'], 'field': field, 'original': original, 'normalized': normalized})
        for key in ('accident_type', 'accident_place', 'negligence_a', 'negligence_b'):
            row[key] = int(row[key])
        if not (0 <= row['negligence_a'] <= 100 and 0 <= row['negligence_b'] <= 100 and (row['negligence_a'] + row['negligence_b'] == 100)):
            raise ValueError('CSV 과실 비율 오류')
    if not ctx.table or len({r['accident_type'] for r in ctx.table}) != len(ctx.table):
        raise ValueError('CSV가 비었거나 유형 ID가 중복됩니다.')
    ctx.places = {r['accident_place']: r['accident_place_name'] for r in ctx.table}
    ctx.video_hash = digest_file(ctx.VIDEO_PATH)
    ctx.csv_hash = digest_file(ctx.csv_path)
    ctx.result_dir = RESULTS_DIR
    ctx.cache_dir = ctx.result_dir / 'vision_cache' / VERSION
    ctx.cache_dir.mkdir(parents=True, exist_ok=True)
    ctx.meter = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
    ctx.stages = []
    ctx.client = None
    if ctx.SHOW_PROCESS_LOGS:
        print('버전:', CODE_VERSION, '/ CSV:', len(ctx.table), '개')
    ctx.fps, ctx.frame_count, ctx.video_read_audit = inspect_video(ctx.VIDEO_PATH)
    ctx.last_frame_index = ctx.frame_count - 1
    ctx.duration = ctx.frame_count / ctx.fps
    ctx.cap = None

    _process_log = io.StringIO()
    try:
        with contextlib.nullcontext() if ctx.SHOW_PROCESS_LOGS else contextlib.redirect_stdout(_process_log):
            try:
                match_context = None
                matching_notes = []
                catalog_ids = []
                fallback_used = False
                model_no_match_reason = ''
                raw_model_match = None
                indices = sorted(set([min(round(n * STEP_SECONDS * ctx.fps), ctx.frame_count - 1) for n in range(math.ceil(ctx.duration / STEP_SECONDS))] + [ctx.frame_count - 1]))
                total_sampled = len(indices)
                indices = uniform_pick(indices, OVERVIEW_MAX_IMAGES)
                indices = sorted({int(i) for i in indices if 0 <= int(i) <= ctx.last_frame_index})
                if not indices:
                    raise RuntimeError('분석할 프레임이 없습니다.')
                context_frames = get_frames(indices)
                cues = background_cues(context_frames)
                max_gap = max((b['sec'] - a['sec'] for a, b in zip(context_frames, context_frames[1:])), default=0)
                print(f'1/3 전체 흐름: {ctx.duration:.2f}초 / {len(context_frames)}장 / low / 최대 간격 {max_gap:.2f}초')
                if total_sampled > len(indices):
                    print('[샘플링 한계] 긴 영상의 전체 범위를 압축했습니다. 짧은 충돌 순간이 프레임 사이에 빠질 수 있습니다.')
                prompt = prompt_text('overview_scan') + json.dumps(ctx.places, ensure_ascii=False)
                prompt += '\n배경 변화: ' + json.dumps(cues)
                chosen = call('1/3 전체 흐름 분석', VISION_MODEL, Scan, image_content(prompt, context_frames), 3200, validator=lambda value: validate(value, context_frames))
                overview_results = [(chosen, context_frames)]
                nearby = overview_results
                nearby_frames = context_frames
                scene = scan_as_observation(chosen)
                mark_accident_input(scene)
                review_frames = []
                raw_review_scene = None
                refinement_history = []
                derived_screen_direction = None
                rejected_matches = []
                match = None
                linked = []
                review_required, review_reasons = needs_detail_review(chosen)
                if review_required:
                    print('[상세 검토 진행 이유]', ' / '.join(review_reasons))
                    by_id = {f['id']: f['index'] for f in context_frames}
                    contact_indices = sorted((by_id[i] for i in scene.contact_frame_ids))
                    anchor = by_id.get(scene.impact_anchor_frame_id)
                    if anchor is None and contact_indices:
                        anchor = contact_indices[len(contact_indices) // 2]
                    if anchor is None:
                        lo = context_frames[0]['index']
                        hi = context_frames[-1]['index']
                        anchor = (lo + hi) // 2
                    if not scene.impact_anchor_frame_id and (not contact_indices):
                        review_frames = get_frames(uniform_pick(range(ctx.frame_count), REVIEW_IMAGES))
                        print('[상세 범위] 사건 중심 미확인: 영상 전체 대표 장면을 검토합니다.')
                    else:
                        review_frames = get_frames(plan_review(anchor, min((f['index'] for f in nearby_frames))))
                    high_ids = review_high_ids(review_frames, anchor, chosen.road_shape)
                    print(f'2/3 사고 전후 상세 확인 / 중심 {anchor / ctx.fps:.2f}초 / {len(review_frames)}장 / high {len(high_ids)}장')
                    display_frames(review_frames)
                    review_prompt = adaptive_review_prompt(chosen, nearby, ctx.places)
                    review_cues = background_cues(review_frames)
                    if ACCIDENT_CONFIRMED_INPUT:
                        review_prompt += prompt_text('detail_review_rule_01')
                    review_prompt += prompt_text('detail_review_rule_02')
                    review_prompt += prompt_text('detail_review_rule_03')
                    review_prompt += prompt_text('detail_review_rule_04')
                    review_prompt += prompt_text('detail_review_rule_05')
                    review_prompt += prompt_text('detail_review_rule_06')
                    review_prompt += prompt_text('detail_review_rule_07')
                    review_prompt += prompt_text('detail_review_rule_08')
                    review_prompt += prompt_text('detail_review_rule_09')
                    review_prompt += prompt_text('detail_review_rule_10')
                    review_prompt += prompt_text('detail_review_rule_11')
                    review_prompt += '\n배경 변화: ' + json.dumps(review_cues)
                    scene = call('2/3 사고 전후 상세 확인', VISION_MODEL, Observation, image_content(review_prompt, review_frames, high_ids=high_ids), 5000, validator=lambda s: validate(s, nearby_frames + review_frames))
                    validate(scene, nearby_frames + review_frames)
                    raw_review_scene = scene.model_dump()
                    anchor = {f['id']: f['index'] for f in review_frames}.get(scene.impact_anchor_frame_id, anchor)
                    derived_screen_direction = ground_observation(scene, nearby_frames + review_frames, anchor, review_cues, [f['id'] for f in review_frames])
                    verify_routes(scene, review_frames, anchor)
                    if parking_environment(scene):
                        scene._evidence_audit['parking_static_background'] = parking_background_review(review_frames)
                    collect_match_facts(scene, raw_review_scene)
                    mark_accident_input(scene)
                reconcile_road_context(scene, chosen)
                apply_user_road_context(scene, ctx.video_hash)
                inspect_lane_cause(scene, ctx.video_hash)
                match_context, matching_notes = matching_context(scene)
                rows = search_rows(match_context)
                catalog_ids = [r['accident_type'] for r in rows]
                full_csv_audit = compare_all_csv_rows(rows, match_context)
                print(f'3/3 CSV 전체 유형 비교: {len(rows)}개 / 사전 제외 0개')
                if VERBOSE:
                    print('[CSV 검색] 후보 표', len(rows), '개 / 유형:', catalog_ids)
                    for note in matching_notes:
                        print('[CSV 진행 해석]', note)
                catalog = pack_catalog(rows)
                prompt = prompt_text('csv_match') + json.dumps(compact_observation(match_context), ensure_ascii=False, separators=(',', ':')) + '\nCSV: ' + json.dumps(catalog, ensure_ascii=False, separators=(',', ':'))
                if catalog:
                    match = call('3/3 CSV 연결·과실 시나리오', MATCH_MODEL, Matches, [{'type': 'input_text', 'text': prompt}], 1800)
                else:
                    match = Matches(candidates=[], survey=[], no_match_reason='관찰과 양립 가능한 CSV 표가 없음')
                raw_model_match = match.model_dump()
                rejected_matches.extend(prepare_matches(match, rows, match_context))
                original_ids = {c['accident_type'] for c in raw_model_match['candidates'] if c['accident_type'] in catalog_ids}
                fallback_used = bool(match.candidates) and (not any((c.accident_type in original_ids for c in match.candidates)))
                if not match.candidates:
                    model_no_match_reason = match.no_match_reason
                    match.candidates = conditional_candidates(rows, match_context)
                    fallback_used = bool(match.candidates)
                    if fallback_used:
                        match.no_match_reason = ''
                match.survey = supplemental_survey(match_context)
                by_id = {r['accident_type']: r for r in rows}
                seen = set()
                for candidate in match.candidates:
                    if candidate.accident_type not in by_id or candidate.accident_type in seen:
                        raise ValueError('CSV 유형 ID 오류/중복')
                    seen.add(candidate.accident_type)
                    if not any((orientation_compatible(by_id[candidate.accident_type], match_context, role) for role in ('A', 'B'))):
                        rejected_matches.append({'id': candidate.accident_type, 'reason': '양쪽 역할 모두 사고 직전 행동과 모순'})
                        continue
                    item = link_match(candidate, by_id[candidate.accident_type], match_context)
                    if fallback_used and (not item['ranking_basis']['progress_agreements']) and (not item['ranking_basis']['progress_mismatches']):
                        item['label'] = '진행 미확인 — 장소 기반 조건부 비교 (확신 낮음)'
                    linked.append(item)
                timeline_payload = build_timeline(scene, context_frames + review_frames)
                analysis_bundle = law_rule_bundle(scene, linked)
                user_report = build_user_report(scene, timeline_payload, linked, match.survey if match else [], derived_screen_direction, bundle_override=analysis_bundle)
                if ctx.SHOW_PROCESS_LOGS:
                    print('설문 전 분석 저장 완료')
                if VERBOSE:
                    print('\n[관찰 요약]', scene.summary)
                    for t in scene.tracks:
                        print(f'{t.vehicle_id}: {t.appearance} / {t.first_frame_id}~{t.last_frame_id} / {t.movement}')
                    print('[B: 접촉 상대 후보]', scene.b_vehicle_id or '미확인', '/', scene.b_identity)
                    for phase in scene.a_phases:
                        print('[A 움직임]', phase.first_frame_id, '~', phase.last_frame_id, phase.state, phase.background_evidence)
                    print('[도로]', scene.road_evidence)
                    print('[사고 직전 A 진행]', scene.pre_contact_a_movement)
                    print('[사고 직전 B 진행]', scene.pre_contact_b_movement)
                    print('[좌표로 계산한 B 화면 이동]', derived_screen_direction or '미확인')
                    print('[충돌 정황 근거]', scene.impact_cues)
                    print('[A 상태]', scene.a_state.motion, '/ 교차로 위치:', scene.a_state.roundabout_position, '/ 차로변경:', scene.a_state.lane_change)
                    print('[B 상태]', scene.b_state.motion, '/ 교차로 위치:', scene.b_state.roundabout_position, '/ 차로변경:', scene.b_state.lane_change)
                    for who in ('A', 'B'):
                        route = scene._evidence_audit.get(who, {}).get('roundabout_position', {}).get('geometry_check', {})
                        if route:
                            status = '기존 판단과 일관됨' if route['accepted'] else '확정 보류·도로 위치 가설은 후보 비교에 보존' if route.get('valid') else '근거 부족·판정 보류'
                            print(f'[{who} 도로 위치 검토]', status, '/', route['reason'])
                    for who in ('A', 'B'):
                        support = scene._evidence_audit.get(who, {})
                        print(f'[{who} 근거 수준]', ' / '.join((label + ': ' + SUPPORT_LABELS.get(support.get(field, {}).get('status'), '근거 부족') for field, label in (('motion', '움직임'), ('roundabout_position', '교차로 위치'), ('lane_change', '차로변경')))))
                    if VERBOSE:
                        print('[관찰 검토 항목]', scene.observation_issues)
                    print('[접촉]', scene.contact, scene.contact_evidence)
                    print_timeline(timeline_payload)
                    print('\n[CSV 기반 예상 과실]')
                    for n, item in enumerate(public_scenarios(scene, linked), 1):
                        print(f"후보 {n}: 유형 {item['accident_type']} / {item['place']} / {item['feature']} / {item['label']}")
                        for option in item['ratio_options']:
                            print('[시나리오]', option['scenario_relation'])
                            print(f"A(블랙박스) {option['a_fault']}% / B(접촉 상대) {option['b_fault']}%")
                            print('적용 조건: A', option['a_progress'], '/ B', option['b_progress'])
                            for check in option['actor_conditions']:
                                print(f"  {check['field'][0].upper()} 조건 대응: {check['relation']} / 근거: {SUPPORT_LABELS.get(check['status'], '근거 부족')}")
                            if option['progress_mismatches']:
                                print('현재 진행 추정과의 차이:', ' / '.join(option['progress_mismatches']))
                        visible_conditions = [c for c in item['conditions'] if not any((word in c for word in ('항목 제거', 'ID', 'CSV A/B', '프레임', '표의 A/B 역할')))]
                        print('근거:', item['reason'], '/ 확인할 조건:', visible_conditions[:4])
                        if item['validation_issues'] and VERBOSE:
                            print('[역할 검증]', item['validation_issues'])
                    if not linked:
                        print('유형을 연결하지 못함:', match.no_match_reason if match else '전체 탐색에서 상세 검토 단서를 찾지 못함. 사고가 없다는 확정은 아님')
                    print('\n[추가설문]')
                    for q in match.survey if match else []:
                        print(q.question, '/', ' · '.join(q.options), f'[답변 키: {q.answer_key}]')
                print('[이번 실행 토큰]', ctx.meter)
                print('캐시', sum((s['cached'] for s in ctx.stages)), '회 / 새 호출', sum((not s['cached'] for s in ctx.stages)), '회')
                ctx.output_path = ctx.result_dir / f'analysis_three_stage_{ctx.video_hash[:12]}.json'
                ctx.output_path.write_text(json.dumps({'version': CODE_VERSION, 'video': str(ctx.VIDEO_PATH), 'video_sha256': ctx.video_hash, 'csv_sha256': ctx.csv_hash, 'csv_normalization': ctx.csv_normalization, 'duration': ctx.duration, 'fps': ctx.fps, **timeline_payload, 'user_report': user_report, 'overview': [s.model_dump() for s, _ in overview_results], 'scene': scene.model_dump(), 'raw_review_scene': raw_review_scene, 'derived_screen_direction': derived_screen_direction, 'evidence_audit': scene._evidence_audit, 'catalog_assessments': full_csv_audit, 'csv_comparison': {'scope': 'all_rows', 'total': len(ctx.table), 'compared': len(rows), 'prefiltered': 0, 'passed_to_model_ids': catalog_ids}, 'refinement_history': refinement_history, 'pipeline': {'steps': ['전체 흐름', '사고 전후 상세 확인', 'CSV 연결'], 'overview_image_count': len(context_frames), 'overview_max_gap_seconds': max_gap, 'detail_gate_version': DETAIL_GATE_VERSION, 'detail_review_required': review_required, 'detail_review_reasons': review_reasons, 'review_image_count': len(review_frames), 'extra_review_enabled': False, 'csv_comparison_scope': 'all_rows', 'csv_compared_count': len(rows), 'csv_total_count': len(ctx.table), 'csv_prefiltered_count': 0, 'retry_policy': '출력 잘림 또는 잘못된 프레임 인용에 단계별 합계 최대 1회 재시도; 사용량 합산'}, 'video_read_audit': ctx.video_read_audit, 'overview_frames': [{'id': f['id'], 'sec': f['sec']} for f in context_frames], 'rejected_matches': rejected_matches, 'matching_context': match_context.model_dump() if match_context else None, 'matching_notes': matching_notes, 'catalog_ids': catalog_ids, 'conditional_fallback_used': fallback_used, 'model_no_match_reason': model_no_match_reason, 'raw_model_match': raw_model_match, 'review_frames': [{'id': f['id'], 'sec': f['sec']} for f in review_frames], 'similar_accidents': public_scenarios(scene, linked), 'reference_scenarios': reference_scenarios(scene, linked), 'accident_type_candidates': [{'accident_type_id': i['accident_type'], 'csv_accident_type': i.get('csv_accident_type'), 'status': o.get('display_status')} for i in public_scenarios(scene, linked) for o in i.get('ratio_options', [])], 'internal_candidate_scenarios': linked, 'survey': [q.model_dump() for q in match.survey] if match else [], 'no_match_reason': match.no_match_reason if match else '전체 탐색에서 상세 검토 단서를 찾지 못함. 사고가 없다는 확정은 아님', 'uncertainty_details': uncertainty_details(scene, linked), **analysis_bundle, 'current_run_usage': ctx.meter, 'stages': ctx.stages, 'notice': 'CSV 기본값 기반 조건부 참고 예측. 실제 과실비율과 다를 수 있으며 등록 규칙과 확인된 요소만 가감산하며 법령 조회 상태는 별도 표시.'}, ensure_ascii=False, indent=2), encoding='utf-8')
                print('저장:', ctx.output_path)
                timeline_path = save_timeline_text(ctx.output_path, timeline_payload, ctx.VIDEO_PATH.name)
                print('타임라인 저장:', timeline_path)
                print('보고서 저장:', save_user_report(ctx.output_path, user_report))
            finally:
                if ctx.cap is not None:
                    ctx.cap.release()
    finally:
        if _process_log.getvalue():
            try:
                _log_dir = ctx.result_dir
                _log_dir.mkdir(parents=True, exist_ok=True)
                (_log_dir / 'last_run_log.txt').write_text(_process_log.getvalue(), encoding='utf-8')
            except OSError:
                pass
    if not settings.get('no_survey', False):
        survey_result = survey_then_report(ctx.output_path)
    else:
        print(user_report)
        print('JSON:', ctx.output_path)
        print('보고서:', ctx.output_path.with_name(ctx.output_path.stem + '_report.txt'))
