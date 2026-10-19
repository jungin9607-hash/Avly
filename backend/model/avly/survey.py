"""추가 질문 생성과 답변 반영."""
import html
import json
import re
from pathlib import Path
from .constants import CODE_VERSION, TIMELINE_NOTICE
from .tables import CAUSE_KEYS, CAUSE_QUESTIONS, FACTOR_LABELS, SPECIAL_LABELS, SURVEY_CONTEXT_OPTIONS
from .context import ctx
from .schemas import Candidate, Observation, Question, StraightRelationCheck, Track, unknown_state
from .facts import accident_input_confirmed, action_support, collect_match_facts, mark_accident_input, normalize_tracks, parking_environment, preimpact_ids, reconcile_actions, straight_audit
from .observation import apply_confirmed_video_context
from .matching import compare_all_csv_rows, conditional_candidates, link_match, matching_context, orientation_compatible, search_rows, strict_user_conflicts
from .adjustments import build_rule_input, compact_fault, evaluate_rule_input, law_rule_bundle, public_scenarios, reference_scenarios, uncertainty_details
from .timeline import build_timeline, save_timeline_text
from .report import build_user_report, finish_report, safe_write_result, save_user_report


def supplemental_survey_base(scene):
    questions = []
    if scene.b_vehicle_id is None or scene.b_identity != '구별됨':
        questions.append(Question(answer_key='b_vehicle_id', question='A(블랙박스)와 접촉한 상대 차량은 어느 차량인가요?', options=[f'{t.vehicle_id}: {t.appearance}' for t in scene.tracks][:5] + ['다른 차량', '미확인']))
    if scene.road_shape == '회전교차로':
        for who in ('a', 'b'):
            support = scene._evidence_audit.get(who.upper(), {}).get('roundabout_position', {})
            if getattr(scene, who + '_action') in ('미확인', '기타', '직진') or support.get('status') in ('unknown', 'conflicted'):
                questions.append(Question(answer_key=who + '_route', question=f"사고 직전 {('A(블랙박스)' if who == 'a' else 'B(접촉 상대)')}는 회전교차로에서 어떻게 진행했나요?", options=['진입', '내부 회전', '진출', '진입 전 대기', '미확인']))
        if scene._evidence_audit.get('lane_count', {}).get('status') != 'user':
            questions.append(Question(answer_key='roundabout_lanes', question='사고 지점의 회전차로는 몇 개였나요?', options=['1차로', '2차로 이상', '미확인']))
    else:
        for who in ('a', 'b'):
            support = scene._evidence_audit.get(who.upper(), {}).get('progress', {})
            if support.get('status') != 'user':
                questions.append(Question(answer_key=who + '_action', question=f"사고 직전 {('A(블랙박스)' if who == 'a' else 'B(접촉 상대)')}의 진행은 무엇이었나요?", options=['직진', '후진', '주차 출차', '출발', '좌회전', '우회전', '정지/대기', '주차 중', '진로변경', '기타', '미확인']))
    if scene.road_shape == '교차로':
        sig = scene.signal_check
        if sig.signal_present == '미확인':
            questions.insert(0, Question(answer_key='signal_present', question='사고 교차로에 신호등이 있었나요?', options=['있음', '없음', '미확인']))
        elif sig.signal_present == '있음':
            if sig.signal_operating == '미확인':
                questions.insert(0, Question(answer_key='signal_operating', question='사고 당시 신호등은 어떻게 작동했나요?', options=['정상 작동', '점멸', '꺼짐', '미확인']))
            if sig.signal_operating == '정상 작동':
                for who in ('a', 'b'):
                    if getattr(sig, who + '_signal') == '미확인':
                        questions.insert(0, Question(answer_key=who + '_signal', question=f"사고 당시 {('내 차' if who == 'a' else '상대 차')}의 신호는 무엇이었나요?", options=['녹색', '황색', '적색', '미확인']))
    if not questions:
        questions.append(Question(answer_key='collision_pattern', question='두 차량은 어떤 방식으로 가까워지거나 충돌했나요?', options=['교차 진행/측면 접근', '후행 추돌', '주정차 차량 충돌', '미확인']))

    def priority(q):
        if q.answer_key in ('signal_present', 'signal_operating', 'a_signal', 'b_signal'):
            return -1
        if q.answer_key == 'b_vehicle_id':
            return 0
        if q.answer_key.endswith('_route') and scene._evidence_audit.get(q.answer_key[0].upper(), {}).get('roundabout_position', {}).get('status') == 'conflicted':
            return 1
        return 2 if q.answer_key.endswith(('_route', '_action')) else 3
    return sorted(questions, key=priority)[:2]

def recompute_survey(answers, result_path=None, survey_context=None, baseline_data=None, persist=True):
    answers = {k: '미확인' if v in ('모름', '잘 모르겠어요') else '진로변경' if k in ('a_action', 'b_action') and v == '차로변경' else v for k, v in answers.items()}
    path = Path(result_path or ctx.output_path)
    saved = json.loads(json.dumps(baseline_data)) if baseline_data is not None else json.loads(path.read_text(encoding='utf-8'))
    if saved['csv_sha256'] != ctx.csv_hash:
        raise ValueError('CSV가 바뀌었습니다. 새 CSV로 영상을 분석한 결과를 사용하세요.')
    updated = Observation.model_validate(saved['scene'])
    updated._evidence_audit = json.loads(json.dumps(saved.get('evidence_audit', {})))
    apply_survey_context(updated, saved, survey_context or {})
    original_b = updated.b_vehicle_id
    if 'b_vehicle_id' in answers:
        chosen_b = str(answers['b_vehicle_id']).split(':', 1)[0].strip()
        unresolved_b = chosen_b in ('다른 차량', '미확인', '모름', '잘 모르겠어요')
        if not unresolved_b and chosen_b not in {t.vehicle_id for t in updated.tracks}:
            raise ValueError('영상에서 관찰된 외부 차량 ID만 선택하세요.')
        if unresolved_b or chosen_b != updated.b_vehicle_id:
            updated._evidence_audit.pop('straight_relation', None)
            updated.straight_relation = StraightRelationCheck()
            updated.adjustment_observations = [f for f in updated.adjustment_observations if f.actor != 'B']
            updated._evidence_audit['adjustment_answers'] = {k: v for k, v in updated._evidence_audit.get('adjustment_answers', {}).items() if not k.startswith('b_factor_')}
            updated.parking_motion_phases = [p for p in updated.parking_motion_phases if p.vehicle != 'B']
            updated.parking_route_checks = [p for p in updated.parking_route_checks if p.vehicle != 'B']
            updated.maneuver_checks = [p for p in updated.maneuver_checks if p.vehicle != 'B']
            updated.route_checks = [p for p in updated.route_checks if p.vehicle != 'B']
            updated.contact_frame_ids = []
            updated.impact_anchor_frame_id = None
            updated._evidence_audit.pop('observed_parking_pattern', None)
            updated.b_state = unknown_state()
            updated.b_action = '미확인'
            updated.b_screen_points = []
            updated.b_pre_frame_ids = []
            updated._evidence_audit['B'] = {}
            updated._evidence_audit.pop('collision_pattern', None)
            updated._evidence_audit.pop('contact_user_answer', None)
        updated.b_vehicle_id, updated.b_identity = (None, '판단 불가') if unresolved_b else (chosen_b, '구별됨')
    maps = {'a_route': ('a_state', 'roundabout_position', {'진입', '내부 회전', '진출', '진입 전 대기', '미확인'}), 'b_route': ('b_state', 'roundabout_position', {'진입', '내부 회전', '진출', '진입 전 대기', '미확인'})}
    for who in ('a', 'b'):
        maps[who + '_motion'] = (who + '_state', 'motion', {'이동', '정지', '미확인'})
        maps[who + '_lane_change'] = (who + '_state', 'lane_change', {'있음', '없음', '미확인'})
    for key, value in answers.items():
        if key in maps:
            target, field, allowed = maps[key]
            if value not in allowed:
                raise ValueError(f'{key} 허용 값: {sorted(allowed)}')
            setattr(getattr(updated, target), field, value)
            who = target[0].upper()
            updated._evidence_audit.setdefault(who, {})[field] = {'status': 'user' if value != '미확인' else 'unknown', 'value': value, 'sources': ['사용자 설문 답변 (영상 검증과 별도)'], 'direct_frame_ids': [], 'linked_frame_ids': []}
        elif key == 'roundabout_lanes':
            if value not in ('1차로', '2차로 이상', '미확인'):
                raise ValueError('roundabout_lanes: 1차로/2차로 이상/미확인')
            updated.roundabout_lane_count = value
            updated._evidence_audit['lane_count'] = {'status': 'user' if value != '미확인' else 'unknown', 'value': value}
        elif key in ('signal_present', 'signal_operating', 'a_signal', 'b_signal'):
            allowed = {'signal_present': {'있음', '없음', '미확인'}, 'signal_operating': {'정상 작동', '점멸', '꺼짐', '미확인'}, 'a_signal': {'녹색', '황색', '적색', '미확인'}, 'b_signal': {'녹색', '황색', '적색', '미확인'}}[key]
            if value not in allowed:
                raise ValueError(f'{key}: 허용되지 않은 신호 답변')
            setattr(updated.signal_check, key, value)
            updated._evidence_audit.setdefault('signal_user_answers', {})[key] = value
        elif key == 'b_vehicle_id':
            continue
        elif key in ('a_action', 'b_action'):
            if value not in ('정지/대기', '주차 중', '후진', '주차 출차', '출발', '직진', '교차로 진입', '교차로 내 회전', '진출', '좌회전', '우회전', '진로변경', '기타', '미확인'):
                raise ValueError('허용되지 않은 진행 상태')
            setattr(updated, key, value)
            updated._evidence_audit.setdefault(key[0].upper(), {})['progress'] = {'value': value, 'status': 'user' if value != '미확인' else 'unknown', 'direct_frame_ids': [], 'linked_frame_ids': [], 'sources': ['사용자 답변; 영상 검증과 별도'], 'conflicts': []}
        elif key == 'b_relative_position':
            if value not in ('앞', '뒤', '옆', '미확인'):
                raise ValueError('상대 위치: 앞/뒤/옆/미확인')
            record = updated._evidence_audit.setdefault('straight_relation', {})
            record.update(b_position=value, status='user' if value != '미확인' else 'unknown', source='사용자 확인', explanation='사고 전 앞뒤 위치 사용자 확인')
        elif key == 'collision_pattern':
            if value not in ('교차 진행/측면 접근', '후행 추돌', '주정차 차량 충돌', '미확인'):
                raise ValueError('collision_pattern 선택지와 답변을 확인하세요.')
            updated._evidence_audit['collision_pattern'] = {'value': value, 'status': 'user' if value != '미확인' else 'unknown', 'rear_evidence': value == '후행 추돌', 'parked_evidence': value == '주정차 차량 충돌', 'crossing_evidence': value == '교차 진행/측면 접근', 'prior_accident_evidence': False}
        elif key in ('road_width_relation', 'approach_relation', 'a_approach_side', 'b_approach_side'):
            allowed = {'road_width_relation': {'동일폭', '내 차 도로가 넓음', '상대 차 도로가 넓음', '미확인'}, 'approach_relation': {'마주보며 진행', '교차하는 도로에서 진행', '같은 방향 진행', '미확인'}, 'a_approach_side': {'왼쪽 도로', '오른쪽 도로', '미확인'}, 'b_approach_side': {'왼쪽 도로', '오른쪽 도로', '미확인'}}[key]
            if value not in allowed:
                raise ValueError(f'{key}: 선택지를 확인하세요.')
            updated._evidence_audit.setdefault('context_answers', {})[key] = value
            if key == 'approach_relation':
                for who in ('A', 'B'):
                    updated._evidence_audit.setdefault(who, {})['opposing_travel'] = {'status': 'user' if value != '미확인' else 'unknown', 'value': '있음' if value == '마주보며 진행' else '미확인' if value == '미확인' else '없음'}
        elif key in ('a_parking_route', 'b_parking_route'):
            allowed = {'통로 주행': ('통로', '통로'), '주차구역에서 출차': ('주차구역', '통로'), '통로에서 주차구역 진입': ('통로', '주차구역'), '미확인': ('미확인', '미확인')}
            if value not in allowed:
                raise ValueError(f'{key}: 주차장 경로 선택지를 확인하세요.')
            start_zone, end_zone = allowed[value]
            updated._evidence_audit.setdefault(key[0].upper(), {})['parking_route'] = {'status': 'user' if value != '미확인' else 'unknown', 'start_zone': start_zone, 'end_zone': end_zone, 'frame_ids': [], 'source': '사용자 답변; 영상 검증과 별도'}
        elif key == 'contact_confirmed':
            if value not in ('있음', '없음', '미확인'):
                raise ValueError('contact_confirmed: 있음/없음/미확인')
            updated._evidence_audit['contact_user_answer'] = value
        elif key in {f'{who}_{name}' for who in ('a', 'b') for name in SPECIAL_LABELS}:
            if value not in ('있음', '없음', '미확인'):
                raise ValueError(f'{key}: 있음/없음/미확인')
            who, condition = key.split('_', 1)
            updated._evidence_audit.setdefault(who.upper(), {})[condition] = {'status': 'user' if value != '미확인' else 'unknown', 'value': value, 'frame_ids': [], 'source': '사용자 답변; 영상 검증과 별도'}
        elif key in {f'{who}_factor_{factor}' for who in ('a', 'b') for factor in FACTOR_LABELS}:
            if value not in ('있음', '없음', '미확인'):
                raise ValueError('가감 요소: 있음/없음/미확인')
            updated._evidence_audit.setdefault('adjustment_answers', {})[key] = value
        else:
            raise ValueError(f'알 수 없는 답변 키: {key}')
    for who in ('a', 'b'):
        state = getattr(updated, who + '_state')
        if updated.road_shape == '회전교차로' and (who + '_route' in answers or who + '_lane_change' in answers):
            action = '진로변경' if state.lane_change == '있음' else {'진입': '교차로 진입', '내부 회전': '교차로 내 회전', '진입 전 대기': '정지/대기'}.get(state.roundabout_position, '미확인')
            setattr(updated, who + '_action', action)
    reconcile_actions(updated)
    collect_match_facts(updated)
    mark_accident_input(updated)
    for who in ('a', 'b'):
        key = who + '_action'
        action = answers.get(key)
        if updated.road_shape == '회전교차로' and answers.get(who + '_route'):
            action = {'진입': '교차로 진입', '내부 회전': '교차로 내 회전', '진출': '진출', '진입 전 대기': '정지/대기'}.get(answers[who + '_route'], '미확인')
        if action and action != '미확인':
            setattr(updated, key, action)
            updated._evidence_audit.setdefault(who.upper(), {})['progress'] = {'status': 'user', 'value': action, 'direct_frame_ids': [], 'linked_frame_ids': [], 'sources': ['사용자 설문; 영상 검증과 별도']}
    context, notes = matching_context(updated)
    rows = search_rows(context)
    candidates = survey_candidates(saved, context, rows)
    linked_after_survey = []
    rows_by_id = {r['accident_type']: r for r in rows}
    for candidate in candidates:
        row = rows_by_id[candidate.accident_type]
        roles = [role for role in ('A', 'B') if orientation_compatible(row, context, role)]
        if len(roles) == 1:
            role = roles[0]
            candidate.dashcam_table_role = role
            candidate.mapped_a_progress = row['vehicle_b_progress_info_name' if role == 'B' else 'vehicle_a_progress_info_name']
            candidate.mapped_b_progress = row['vehicle_a_progress_info_name' if role == 'B' else 'vehicle_b_progress_info_name']
            candidate.a_condition_status = candidate.b_condition_status = '가정'
        candidate.reason = '사용자 설문 답변과 영상 관찰을 함께 비교한 CSV 기본값입니다. 답변은 영상 검증 사실과 구분합니다.'
        candidate.assumed_conditions.append('사용자 답변이 실제 사고 상황과 같다는 가정')
        linked_after_survey.append(link_match(candidate, row, context))
    destination = path.with_name(path.stem.removesuffix('_survey') + '_survey.json')
    answer_history = dict(saved.get('survey_answers', {}))
    answer_history.update(answers)
    saved.update({'version': CODE_VERSION, 'survey_answers': answer_history, 'scene': updated.model_dump(), 'evidence_audit': updated._evidence_audit, **law_rule_bundle(updated, linked_after_survey), 'uncertainty_details': uncertainty_details(updated, linked_after_survey), 'similar_accidents': public_scenarios(updated, linked_after_survey), 'reference_scenarios': reference_scenarios(updated, linked_after_survey), 'accident_type_candidates': [{'accident_type_id': i['accident_type'], 'csv_accident_type': i.get('csv_accident_type'), 'status': o.get('display_status')} for i in public_scenarios(updated, linked_after_survey) for o in i.get('ratio_options', [])], 'internal_candidate_scenarios': linked_after_survey, 'matching_context': context.model_dump(), 'survey': [q.model_dump() for q in supplemental_survey(context)], 'survey_update_llm_tokens': 0, 'csv_comparison': {'scope': 'all_rows', 'total': len(ctx.table), 'compared': len(rows), 'prefiltered': 0, 'passed_to_model_ids': [r['accident_type'] for r in rows], 'method': 'local_all_row_recheck_after_survey'}, 'catalog_assessments': compare_all_csv_rows(rows, context), 'no_match_reason': '' if linked_after_survey else '전체 CSV를 재검토했으나 입력 조건과 양립하는 유형을 찾지 못함'})
    saved.setdefault('timeline', [])
    saved.setdefault('timeline_notice', TIMELINE_NOTICE)
    saved.setdefault('timeline_warnings', [])
    if updated.b_vehicle_id != original_b:
        saved['derived_screen_direction'] = None
        saved.setdefault('original_video_timeline', saved['timeline'])
        if saved.get('frame_times'):
            refreshed = build_timeline(updated, saved['frame_times'])
            for key in ('timeline', 'timeline_notice', 'timeline_warnings'):
                saved[key] = refreshed[key]
        else:
            saved['timeline'] = [e for e in saved['timeline'] if e.get('kind') != 'B 확인 구간']
            for e in saved['timeline']:
                if e.get('actor') == 'A/B':
                    e['actor'] = 'A/상대 후보'
    saved['user_report'] = build_user_report(updated, saved, linked_after_survey, supplemental_survey(context), saved.get('derived_screen_direction'))
    if persist:
        destination.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
        print('[설문 반영 / 추가 LLM 토큰 0]')
        print(saved['user_report'])
        print('보고서 저장:', save_user_report(destination, saved['user_report']))
        print('저장:', destination)
        if 'timeline' in saved:
            print('타임라인 저장:', save_timeline_text(destination, saved, Path(saved.get('video', '')).name))
    return saved

def supplemental_survey_v29(scene):
    base = supplemental_survey_base(scene)
    questions = []
    if scene.b_vehicle_id is None or scene.b_identity != '구별됨':
        questions.extend((q for q in base if q.answer_key == 'b_vehicle_id'))
    if scene._evidence_audit.get('contact_user_answer') == '없음':
        questions.append(Question(answer_key='b_vehicle_id', question='실제로 접촉한 상대 차량을 다시 선택해주세요.', options=[f'{t.vehicle_id}: {t.appearance}' for t in scene.tracks][:5] + ['다른 차량', '미확인']))
    elif scene.contact != '접촉 관찰' and scene._evidence_audit.get('contact_user_answer') != '있음':
        questions.append(Question(answer_key='contact_confirmed', question='선택된 상대 차량과 실제로 접촉했나요?', options=['있음', '없음', '미확인']))
    for who in ('A', 'B'):
        audit = scene._evidence_audit.get(who, {})
        for name, label in SPECIAL_LABELS.items():
            item = audit.get(name, {})
            if item and item.get('status') in ('unknown', 'conflicted'):
                questions.append(Question(answer_key=who.lower() + '_' + name, question=f"사고 직전 {('내 차' if who == 'A' else '상대 차')}에 {label}이 있었나요?", options=['있음', '없음', '미확인']))
    questions.extend(base)
    unique = {}
    for q in questions:
        unique.setdefault(q.answer_key, q)
    return list(unique.values())[:2]

def supplemental_survey_v291(scene):
    questions = supplemental_survey_v29(scene)
    unanswered = []
    for q in questions:
        if q.answer_key in ('a_action', 'b_action'):
            _, support = action_support(scene, q.answer_key[0].upper())
            if support.get('status') in ('observed', 'user'):
                continue
        unanswered.append(q)
    return unanswered[:2]

def supplemental_survey_v292(scene):
    questions = supplemental_survey_v291(scene)
    if not parking_environment(scene):
        return questions
    priority = []
    if scene.b_vehicle_id is None or scene.b_identity != '구별됨':
        priority.extend((q for q in questions if q.answer_key == 'b_vehicle_id'))
    else:
        for who in ('B', 'A'):
            route = scene._evidence_audit.get(who, {}).get('parking_route', {})
            if route.get('status') not in ('observed', 'user'):
                priority.append(Question(answer_key=who.lower() + '_parking_route', question=f"사고 직전 {('상대 차' if who == 'B' else '내 차')}는 어디에서 진행했나요?", options=['통로 주행', '주차구역에서 출차', '통로에서 주차구역 진입', '미확인']))
    merged = {}
    for q in priority + questions:
        merged.setdefault(q.answer_key, q)
    return list(merged.values())[:2]

def supplemental_survey_handover(scene):
    base = supplemental_survey_v292(scene)
    if scene.road_shape != '교차로':
        return base
    prioritized = []
    answer = scene._evidence_audit.get('context_answers', {})
    if '신호등' in scene.road_evidence and scene.signal_check.signal_present == '없음' and (not scene._evidence_audit.get('signal_user_answers', {}).get('signal_present')):
        prioritized.append(Question(answer_key='signal_present', question='사고 교차로에 신호등이 있었나요?', options=['있음', '없음', '미확인']))
    if answer.get('approach_relation', '미확인') == '미확인':
        prioritized.append(Question(answer_key='approach_relation', question='사고 전 두 차량은 어떤 도로 관계로 접근했나요?', options=['마주보며 진행', '교차하는 도로에서 진행', '같은 방향 진행', '미확인']))
    if answer.get('road_width_relation', '미확인') == '미확인':
        prioritized.append(Question(answer_key='road_width_relation', question='두 차량의 진입 도로 폭은 어땠나요?', options=['동일폭', '내 차 도로가 넓음', '상대 차 도로가 넓음', '미확인']))
    merged = {}
    for q in prioritized + base:
        merged.setdefault(q.answer_key, q)
    return list(merged.values())[:2]

def supplemental_survey_v2112(scene):
    questions = supplemental_survey_handover(scene)
    if accident_input_confirmed(scene) and scene._evidence_audit.get('contact_user_answer') != '없음':
        questions = [q for q in questions if q.answer_key != 'contact_confirmed']
    return questions

def supplemental_survey_v212(scene):
    base = supplemental_survey_v2112(scene)
    extra = []
    if scene.road_shape == '회전교차로':
        for who, label in (('A', '내 차'), ('B', '상대 차')):
            _, support = action_support(scene, who)
            if support.get('status') not in ('observed', 'user'):
                extra.append(Question(answer_key=who.lower() + '_route', question=f'사고 직전 {label}는 회전교차로에서 어떻게 진행했나요?', options=['진입', '내부 회전', '진출', '진입 전 대기', '미확인']))
    merged = {}
    for q in extra + base:
        merged.setdefault(q.answer_key, q)
    return list(merged.values())[:2]

def supplemental_survey_straight_baseline(scene):
    base = supplemental_survey_v212(scene)
    if scene.road_shape != '직선 도로':
        return base
    r = straight_audit(scene)
    extra = []
    if r.get('b_position', '미확인') == '미확인':
        extra.append(Question(answer_key='b_relative_position', question='사고 직전 상대 차량은 내 차의 어디에 있었나요?', options=['앞', '뒤', '옆', '미확인']))
    if scene._evidence_audit.get('B', {}).get('lane_change', {}).get('status') not in ('observed', 'user', 'inferred'):
        extra.append(Question(answer_key='b_lane_change', question='상대 차가 사고 직전에 내 차로로 차로변경했나요?', options=['있음', '없음', '미확인']))
    merged = {}
    for q in extra + base:
        merged.setdefault(q.answer_key, q)
    return list(merged.values())[:2]

def supplemental_survey_analysis_baseline(scene):
    base = supplemental_survey_straight_baseline(scene)
    if not parking_environment(scene):
        return base
    extra = []
    for who, label in (('B', '상대 차'), ('A', '내 차')):
        support = scene._evidence_audit.get(who, {}).get('progress', {})
        if support.get('status') in ('unknown', 'conflicted') or getattr(scene, who.lower() + '_action') == '미확인':
            extra.append(Question(answer_key=who.lower() + '_action', question=f'가장 가까워지기 직전 {label}는 어떻게 움직였나요?', options=['직진', '후진', '정지/대기', '주차 출차', '미확인']))
    merged = {}
    for q in extra + base:
        merged.setdefault(q.answer_key, q)
    return list(merged.values())[:2]

def supplemental_survey(scene):
    questions = supplemental_survey_analysis_baseline(scene)
    if len(questions) >= 2:
        return questions
    candidates = conditional_candidates(ctx.table, scene)
    linked = [link_match(c, next((r for r in ctx.table if r['accident_type'] == c.accident_type)), scene) for c in candidates]
    out = evaluate_rule_input(build_rule_input(scene, linked))
    seen = {q.answer_key for q in questions}
    priority = {'unjustified_sudden_stop': 0, 'signal_delay': 1, 'prohibited_change': 2, 'brake_light_fault': 3}
    for result in out['results']:
        for f in sorted(result['pending'], key=lambda f: priority.get(f['factor'], 9)):
            if f['factor'] in ('gross_negligence', 'serious_negligence'):
                continue
            key = f['actor'].lower() + '_factor_' + f['factor']
            if key in seen:
                continue
            actor = '내 차' if f['actor'] == 'A' else '상대 차'
            questions.append(Question(answer_key=key, question=f"{actor}의 '{f['label']}' 요소가 확인됐나요?", options=['있음', '없음', '미확인']))
            seen.add(key)
            if len(questions) >= 2:
                return questions
    return questions

def survey_questions(scene):
    track = next((t for t in scene.tracks if t.vehicle_id == scene.b_vehicle_id), None)
    partner = track.appearance if track else '분석에서 선택한 상대 후보'
    return [('1. 신호', 'signal_present', '사고 위치에 신호등이 있었나요?', ['있음', '없음', '미확인']), ('2. 내 차 신호·차량 상태', 'a_indicator_timing', '내 차가 방향을 바꿀 때 방향지시등을 어떻게 사용했나요?', SURVEY_CONTEXT_OPTIONS['a_indicator_timing']), ('2. 내 차 신호·차량 상태', 'a_vehicle_condition', '사고 당시 직접 알고 있던 내 차의 상태는 무엇인가요?', SURVEY_CONTEXT_OPTIONS['a_vehicle_condition']), ('3. 사고 상대 확인', 'b_vehicle_confirm', partner + '이(가) 실제 사고 상대인가요?', SURVEY_CONTEXT_OPTIONS['b_vehicle_confirm']), ('4. 도로·진행 경로', 'road_shape', '사고가 발생한 장소는 어디인가요?', SURVEY_CONTEXT_OPTIONS['road_shape']), ('5. 날씨·노면', 'weather', '사고 당시 날씨는 어땠나요?', SURVEY_CONTEXT_OPTIONS['weather']), ('5. 날씨·노면', 'road_surface', '노면 상태는 어땠나요?', SURVEY_CONTEXT_OPTIONS['road_surface']), ('6. 운전자 관찰', 'a_first_notice', '상대 차량을 처음 확인한 시점은 언제인가요?', SURVEY_CONTEXT_OPTIONS['a_first_notice'])]

def collect_questionnaire(saved, input_fn=None, print_fn=None):
    read = input_fn or input
    say = print_fn or print
    scene = Observation.model_validate(saved['scene'])
    answers = {}
    asked = []
    say('\n추가 확인 설문 · 번호로 선택하세요. 0 또는 Enter는 잘 모르겠어요입니다.')
    say('사용자 답변은 영상 관찰과 구분하며, 사실로 독립 검증된 것은 아닙니다.')

    def ask(group, key, label, options):
        options = list(dict.fromkeys((o for o in options if o != '미확인')))
        say('\n' + group + ' | ' + label)
        say(' / '.join((f'{i + 1}. {o}' for i, o in enumerate(options))) + ' / 0. 잘 모르겠어요')
        while True:
            value = read('선택: ').strip()
            if value in ('', '0', '모름', '잘 모르겠어요'):
                value = '미확인'
                break
            if value.isdigit() and 1 <= int(value) <= len(options):
                value = options[int(value) - 1]
                break
            if value in options:
                break
            say('표시된 번호를 입력하세요.')
        answers[key] = value
        asked.append({'key': key, 'group': group, 'question': label, 'options': options + ['미확인']})
    for group, key, label, options in survey_questions(scene):
        ask(group, key, label, options)
        if key == 'signal_present' and answers[key] == '있음':
            ask(group, 'signal_operating', '신호등은 어떻게 작동했나요?', ['정상 작동', '점멸', '꺼짐', '미확인'])
            if answers['signal_operating'] == '정상 작동':
                ask(group, 'a_signal', '사고 직전 내 차에 적용된 신호는 무엇이었나요?', ['녹색', '황색', '적색', '미확인'])
        if key == 'road_shape':
            shape = answers[key] if answers[key] != '미확인' else scene.road_shape
            if shape == '회전교차로':
                for who, label in [('a', '내 차'), ('b', '상대 차')]:
                    ask(group, who + '_route', label + '는 사고 직전 어떻게 진행했나요?', ['진입', '내부 회전', '진출', '진입 전 대기', '미확인'])
                ask(group, 'roundabout_lanes', '회전교차로 내부 차로 수는 무엇이었나요?', ['1차로', '2차로 이상', '미확인'])
            else:
                ask(group, 'a_action', '사고 직전 내 차는 어떻게 움직였나요?', ['직진', '정지/대기', '후진', '좌회전', '우회전', '진로변경', '주차 출차', '미확인'])
            if shape == '교차로':
                ask(group, 'road_width_relation', '내 차와 상대 차가 접근한 도로의 폭은 어떻게 달랐나요?', ['동일폭', '내 차 도로가 넓음', '상대 차 도로가 넓음', '미확인'])
                ask(group, 'approach_relation', '사고 전 두 차량의 진행 관계는 무엇이었나요?', ['마주보며 진행', '교차하는 도로에서 진행', '같은 방향 진행', '미확인'])
            if shape == '주차장':
                for who, label in [('a', '내 차'), ('b', '상대 차')]:
                    ask(group, who + '_parking_route', label + '는 어디에서 어디로 진행했나요?', ['통로 주행', '주차구역에서 출차', '통로에서 주차구역 진입', '미확인'])
            if answers.get('a_action') == '진로변경':
                ask(group, 'lane_boundary', '내 차가 실제로 넘어간 차선은 무엇이었나요?', SURVEY_CONTEXT_OPTIONS['lane_boundary'])
    return (answers, asked)

def apply_survey_context(scene, saved, context):
    saved.setdefault('before_survey', {'scene': json.loads(json.dumps(saved['scene'])), 'evidence_audit': json.loads(json.dumps(saved.get('evidence_audit', {}))), 'rule_engine_output': json.loads(json.dumps(saved.get('rule_engine_output', {}))), 'source_file': '원본 분석 JSON'})
    record = scene._evidence_audit.setdefault('questionnaire', {})
    record.update(answers=context, source='사용자 설문 · 영상 관찰과 별도', verified_by_video=False)
    old = scene.road_shape
    if context.get('road_shape') not in (None, '미확인'):
        scene.road_shape = context['road_shape']
        scene.road_place_codes = list(dict.fromkeys((r['accident_place'] for r in ctx.table if r['accident_place_name'] == scene.road_shape)))
        scene._evidence_audit['user_road_context'] = {'status': 'user', 'value': scene.road_shape, 'model_value': old, 'source': '이번 설문 답변'}
    record['model_road_shape_before_answer'] = old

def survey_then_report(path, input_fn=None):
    path = Path(path)
    saved = json.loads(path.read_text(encoding='utf-8'))
    try:
        answers, questions = collect_questionnaire(saved, input_fn=input_fn)
    except (EOFError, KeyboardInterrupt):
        print('\n설문이 완료되지 않았습니다. 분석 원본은 저장되어 있습니다: ' + str(path))
        print("나중에 survey_then_report(r'" + str(path) + "')로 다시 진행할 수 있습니다.")
        return None
    result = update_estimates(answers, path, questions, display_report=False)
    target = path.with_name(path.stem.removesuffix('_survey') + '_survey.json')
    print('\n' + result['user_report'])
    print('\n보고서:', target.with_name(target.stem + '_report.txt'))
    print('JSON:', target)
    return result

def survey_candidates(saved, scene, rows):
    if not scene.b_vehicle_id or scene.b_identity != '구별됨':
        return []
    byid = {r['accident_type']: r for r in rows}
    kept = []
    seen = set()
    for item in saved.get('internal_candidate_scenarios', []):
        row = byid.get(item['accident_type'])
        if not row:
            continue
        roles = [r for r in ('A', 'B') if orientation_compatible(row, scene, r) and (not strict_user_conflicts(row, scene, r))]
        if not roles:
            continue
        role = item.get('dashcam_table_role')
        if role not in roles:
            role = roles[0] if len(roles) == 1 else '미확인'
        swap = role == 'B'
        kept.append(Candidate(accident_type=row['accident_type'], dashcam_table_role=role, common_observed_facts=['기존 후보를 사용자 답변과 재검증'], assumed_conditions=['사용자 답변이 실제 상황과 같다는 조건'], a_role_evidence='진행·경로 비교', b_role_evidence='진행·경로 비교', mapped_a_progress=row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name'], mapped_b_progress=row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name'], a_evidence_frame_ids=list(scene.a_pre_frame_ids), b_evidence_frame_ids=list(scene.b_pre_frame_ids), a_condition_status='가정', b_condition_status='가정', reason='기존 후보 우선 재검증'))
        seen.add(row['accident_type'])
    if kept:
        return kept[:2]
    return [c for c in conditional_candidates(rows, scene) if c.accident_type not in seen and any((not strict_user_conflicts(byid[c.accident_type], scene, r) for r in ('A', 'B')))]

def survey_base(saved, path):
    if saved.get('survey_baseline'):
        return json.loads(json.dumps(saved['survey_baseline']))
    if saved.get('questionnaire') or saved.get('before_survey'):
        original = path.with_name(path.stem.removesuffix('_survey') + '.json')
        if original != path and original.exists():
            candidate = json.loads(original.read_text(encoding='utf-8'))
            if candidate.get('video_sha256') == saved.get('video_sha256') and candidate.get('csv_sha256') == saved.get('csv_sha256'):
                return candidate
        raise ValueError('원본 분석 JSON이 필요합니다. _survey가 붙지 않은 원본을 먼저 복원하세요.')
    return json.loads(json.dumps(saved))

def update_estimates_v220(answers, result_path=None, asked_questions=None, display_report=True):
    path = Path(result_path or ctx.output_path)
    saved = json.loads(path.read_text(encoding='utf-8'))
    baseline = survey_base(saved, path)
    previous = dict(saved.get('questionnaire', {}).get('answers', {}))
    updates = {k: '미확인' if v in ('모름', '잘 모르겠어요', '', None) else v for k, v in answers.items()}
    current = {**previous, **updates}
    for key, options in SURVEY_CONTEXT_OPTIONS.items():
        if key in current and current[key] not in options:
            raise ValueError(key + ': 선택지를 확인하세요.')
    core = {k: v for k, v in current.items() if k not in SURVEY_CONTEXT_OPTIONS and v != '미확인'}
    context = {k: v for k, v in current.items() if k in SURVEY_CONTEXT_OPTIONS}
    target = current.get('b_vehicle_confirm')
    if target == '아니에요':
        core = {k: v for k, v in core.items() if not k.startswith('b_')}
        core['b_vehicle_id'] = '다른 차량'
    if core.get('b_lane_change') == '있음':
        if core.get('b_action') not in (None, '진로변경'):
            raise ValueError('상대 차 진행과 차로변경 답변이 다릅니다. 다시 확인해주세요.')
        core['b_action'] = '진로변경'
    for who in ('a','b'):
        direction=current.get(who+'_parking_direction')
        if direction in ('전진','후진','정지/대기'):core[who+'_action']={'전진':'직진','후진':'후진','정지/대기':'정지/대기'}[direction]
    for who in ('a', 'b'):
        speed=current.get(who+'_speed_state')
        action=core.get(who+'_action')
        if action == '정지/대기' and speed in ('주행 중', '브레이크를 밟거나 감속 중 (움직이고 있음)'):
            raise ValueError(('내 차' if who=='a' else '상대 차')+': 완전 정지와 이동 중 답변이 충돌합니다. 감속하며 직진했다면 진행 방향을 직진으로 선택하세요.')
    indicator = current.get('a_indicator_timing')
    if indicator in ('변경 전 켜고 유지', '변경 중 늦게 켬', '켜지 않음'):
        value = '없음' if indicator == '변경 전 켜고 유지' else '있음'
        if core.get('a_action') == '진로변경':
            core['a_factor_signal_delay'] = value
        elif core.get('a_route') == '진입':
            core['a_factor_round_entry_signal_delay'] = value
    if core.get('a_action') == '진로변경' and current.get('lane_boundary') == '실선':
        core['a_factor_prohibited_change'] = '있음'
    if core.get('b_action') == '진로변경' and current.get('b_lane_boundary') == '실선':
        core['b_factor_prohibited_change'] = '있음'
    if current.get('a_vehicle_condition') == '제동등 고장을 확인함':
        core['a_factor_brake_light_fault'] = '있음'
    shape_changed = context.get('road_shape') not in (None, '미확인', baseline['scene']['road_shape'])
    scope_known = context.get('parking_scope') not in (None, '미확인')
    unchanged = not core and (not shape_changed) and (not scope_known)
    if unchanged:
        result = json.loads(json.dumps(baseline))
        scene = Observation.model_validate(result['scene'])
        scene._evidence_audit = json.loads(json.dumps(result.get('evidence_audit', {})))
        apply_survey_context(scene, result, context)
        result.update(scene=scene.model_dump(), evidence_audit=scene._evidence_audit)
    else:
        result = recompute_survey(core, path, context, baseline_data=baseline, persist=False)
    scene = Observation.model_validate(result['scene'])
    scene._evidence_audit = json.loads(json.dumps(result['evidence_audit']))
    conflicts = []
    for key, value in current.items():
        old = baseline['scene'].get(key, baseline['scene'].get('signal_check', {}).get(key))
        if old not in (None, '미확인', value) and value != '미확인':
            conflicts.append({'field': key, 'analysis_value': old, 'user_value': value})
    result['version'] = CODE_VERSION
    result['survey_baseline'] = baseline
    result['survey_answers'] = current
    result['survey_update_llm_tokens'] = 0
    result['survey_update_api_tokens'] = 0
    result['questionnaire'] = {'status': 'submitted', 'answers': current, 'questions': asked_questions or saved.get('questionnaire', {}).get('questions', []), 'derived_inputs': core, 'conflicts': conflicts, 'selection_policy': 'unchanged_without_new_facts' if unchanged else 'baseline_rebuild_preserve_valid_candidates', 'context_only_fields': ['weather', 'road_surface', 'a_first_notice'], 'additional_llm_calls': 0, 'legal_case_api_may_be_called': not unchanged, 'source': '사용자 진술; 영상 관찰과 구분', 'video_observations_preserved_in': 'survey_baseline'}
    result['survey_history'] = list(saved.get('survey_history', [])) + [{'answers': dict(current), 'changes': updates, 'withdrawn': [k for k, v in updates.items() if v == '미확인' and previous.get(k) not in (None, '미확인')]}]
    if target == '맞아요':
        scene._evidence_audit.setdefault('accident_input_context', {})['selected_partner_confirmed'] = True
    out = result.get('rule_engine_output', {})
    for owner in [out] + out.get('results', []):
        owner['related_cases'] = [c for c in owner.get('related_cases', []) if not re.search('\\d(?:도|노|고합|고단|고정|구합|구단)', c.get('case_number', ''))]
    for audit in out.get('case_lookup', []):
        audit['count'] = len({c['case_number'] for r in out.get('results', []) if r['accident_type'] == audit.get('accident_type') for c in r.get('related_cases', [])})
        if audit['count'] < 3:
            audit['reason'] = '장소·진행·민사 과실 쟁점이 맞는 자료만 표시; 무관한 판례로 개수를 채우지 않음'
    result['evidence_audit'] = scene._evidence_audit
    bundle = {'rule_engine_input': result.get('rule_engine_input', {}), 'rule_engine_output': out}
    result['user_report'] = build_user_report(scene, result, result.get('internal_candidate_scenarios', []), [], bundle_override=bundle)
    notes = ['', '설문 반영: 사용자 진술과 영상 관찰을 구분했습니다.']
    if unchanged:
        notes.append('새 판단 정보가 없어 기존 후보와 기본비율을 유지했습니다.')
    if current.get('road_shape') == '주차장' and current.get('a_parking_route') == current.get('b_parking_route') == '주차구역에서 출차' and (not out.get('results')):
        notes.append('두 차량 모두 출차로 답변했습니다. 통로 주행 대 출차 기준을 적용하지 않았으며, 이 조건의 CSV 유형·진행 방향 확인이 필요합니다.')
    if target == '아니에요':
        notes.append('사고 상대 불일치로 기존 상대의 과실 계산을 중단했습니다. 영상 재검토가 필요합니다.')
    for key, label in [('weather', '날씨'), ('road_surface', '노면'), ('a_first_notice', '상대 차량 최초 확인'), ('a_indicator_timing', '내 차 방향지시등')]:
        if current.get(key) not in (None, '미확인'):
            notes.append(label + ': ' + current[key])
    if conflicts:
        notes.append('분석 기록과 다른 답변 ' + str(len(conflicts)) + '건을 별도로 보존했습니다.')
    result['user_report'] = result['user_report'].replace('5. 최종 과실비율', '5. 조건에 따른 과실비율 참고') + '\n' + '\n'.join(notes)
    destination = path.with_name(path.stem.removesuffix('_survey') + '_survey.json')
    safe_write_result(destination, result)
    if display_report:
        print(result['user_report'])
        print('\n보고서:', destination.with_name(destination.stem + '_report.txt'))
        print('JSON:', destination)
    return result

def widget_specs(scene):
    specs = [{'group': g, 'key': k, 'label': label, 'options': opts} for g, k, label, opts in survey_questions(scene)]

    def add(group, key, label, options):
        if key not in {s['key'] for s in specs}:
            specs.append({'group': group, 'key': key, 'label': label, 'options': options})
    road = '4. 도로·진행 경로'
    signal = '1. 신호'
    add(signal, 'signal_operating', '신호등은 어떻게 작동했나요?', ['정상 작동', '점멸', '꺼짐', '미확인'])
    add(signal, 'a_signal', '내 차에 적용된 신호는 무엇이었나요?', ['녹색', '황색', '적색', '미확인'])
    actions = ['직진', '정지/대기', '후진', '좌회전', '우회전', '진로변경', '주차 출차', '미확인']
    for who, label in [('a', '내 차'), ('b', '상대 차')]:
        add(road, who + '_action', '사고 직전 ' + label + '는 어떻게 움직였나요?', actions)
        add(road, who + '_route', '회전교차로에서 ' + label + '는 어떻게 진행했나요?', ['진입', '내부 회전', '진출', '진입 전 대기', '미확인'])
        add(road, who + '_parking_route', label + '는 어디에서 어디로 진행했나요?', ['통로 주행', '주차구역에서 출차', '통로에서 주차구역 진입', '미확인'])
    for who,label in [('a','내 차'),('b','상대 차')]:add(road,who+'_parking_direction',label+'는 가장 가까워지기 전에 어떻게 이동했나요?',SURVEY_CONTEXT_OPTIONS[who+'_parking_direction'])
    add(road, 'parking_encounter', '주차장 통로에서 두 차량은 어떻게 접근했나요?', SURVEY_CONTEXT_OPTIONS['parking_encounter'])
    add(road, 'parking_scope', '사고 위치는 주차장 내부인가요, 일반 도로와 이어지는 곳인가요?', SURVEY_CONTEXT_OPTIONS['parking_scope'])
    add(road, 'roundabout_lanes', '회전교차로 내부 차로 수는 무엇인가요?', ['1차로', '2차로 이상', '미확인'])
    add(road, 'road_width_relation', '두 차량이 접근한 도로의 폭은 어떻게 달랐나요?', ['동일폭', '내 차 도로가 넓음', '상대 차 도로가 넓음', '미확인'])
    add(road, 'approach_relation', '두 차량은 어떤 관계로 접근했나요?', ['마주보며 진행', '교차하는 도로에서 진행', '같은 방향 진행', '미확인'])
    add(road, 'lane_boundary', '내 차가 실제로 넘어간 차선은 무엇인가요?', SURVEY_CONTEXT_OPTIONS['lane_boundary'])
    add(road, 'b_lane_change', '충돌 전에 상대 차가 다른 차로에서 내 차로 들어왔나요?', ['있음', '없음', '미확인'])
    add(road, 'b_lane_boundary', '상대 차가 충돌 전에 내 차로로 들어올 때 실제로 넘어간 선은 무엇인가요?', SURVEY_CONTEXT_OPTIONS['b_lane_boundary'])
    for who, label in [('a', '내 차'), ('b', '상대 차')]:
        add(road, who + '_speed_state', label + '는 충돌 직전 어느 상태였나요? (진행 방향과 별개)', SURVEY_CONTEXT_OPTIONS[who + '_speed_state'])
    add(road, 'b_relative_position', '사고 직전 상대 차는 내 차를 기준으로 어디에 있었나요?', ['앞', '뒤', '옆', '미확인'])
    for spec in specs:
        if spec['key'] in ('a_action', 'b_action'):
            spec['label'] += ' (충돌 후 모습이 아닌, 충돌 전 진행 방향)'
    supported = {s['key'] for s in specs}
    excluded = []
    for q in supplemental_survey(scene):
        if q.answer_key in supported:
            continue
        if q.answer_key in ('a_approach_side', 'b_approach_side'):
            excluded.append({'key': q.answer_key, 'reason': '방향 기준의 혼동을 줄이기 위해 도로 관계 질문으로 대체'})
        else:
            excluded.append({'key': q.answer_key, 'reason': '상대 위반·의도 추정 또는 별도 영상 재검토가 필요한 항목'})
    return (specs, excluded)

def survey_field_visible(key, answers, scene):
    shape = answers.get('road_shape')
    if shape in (None, '미확인'):
        shape = scene.road_shape
    if answers.get('b_vehicle_confirm') == '아니에요' and key.startswith('b_') and (key != 'b_vehicle_confirm'):
        return False
    if key == 'signal_operating':
        return answers.get('signal_present') == '있음'
    if key == 'a_signal':
        return answers.get('signal_present') == '있음' and answers.get('signal_operating') == '정상 작동'
    if key in ('a_route', 'b_route', 'roundabout_lanes'):
        return shape == '회전교차로'
    if key in ('a_action', 'b_action'):
        return shape not in ('회전교차로','주차장')
    if key in ('a_parking_direction','b_parking_direction'):return shape=='주차장'
    if key in ('parking_scope', 'a_parking_route', 'b_parking_route', 'parking_encounter'):
        return shape == '주차장'
    if key in ('road_width_relation', 'approach_relation'):
        return shape == '교차로'
    if key in ('b_lane_change', 'b_relative_position'):
        return shape == '직선 도로'
    if key == 'b_lane_boundary':
        return shape == '직선 도로' and (answers.get('b_lane_change') == '있음' or answers.get('b_action') == '진로변경')
    if key in ('a_speed_state', 'b_speed_state'):
        return shape != '주차장'
    if key == 'lane_boundary':
        return answers.get('a_action') == '진로변경' and shape != '회전교차로'
    if key == 'a_indicator_timing':
        return answers.get('a_action') in ('좌회전', '우회전', '진로변경') or answers.get('a_route') in ('진입', '진출')
    return True

def parking_guidance(saved):
    baseline=saved.get('survey_baseline') or saved.get('before_survey') or saved
    scene=baseline.get('scene',saved['scene'])
    lines=['<b>주차장 질문의 뜻</b><br>주차칸 출차: 그려진 주차칸에서 통로로 나오는 움직임입니다. 주차장 건물 밖으로 나가려고 통로를 달리는 것은 통로 주행입니다.<br>전진·후진과 출발 구역은 별도 항목입니다. 아래 영상 기록도 오인식할 수 있으므로 실제 상황을 선택하세요.']
    for who,label in [('A','내 차'),('B','상대 차')]:
        route=next((r for r in scene.get('parking_route_checks',[]) if r['vehicle']==who),None)
        if route:lines.append(html.escape(label+' 영상 기록: '+(route.get('explanation') or '출발 구역 미확인')))
    return '<br>'.join(lines)

def survey_diagnostics(result,baseline,current):
    scene=Observation.model_validate(result['scene']);scene._evidence_audit=result['evidence_audit']
    out=result.get('rule_engine_output',{});empty=not out.get('results')
    diagnostics={'selected_type_count':len({r['accident_type'] for r in out.get('results',[])}),'legal_api_status':out.get('legal_context',{}).get('status'),
        'case_search_status':'no_applicable_type' if empty and not out.get('case_lookup') else 'see_case_lookup',
        'reason_code':None,'missing_fields':[],'observation_answer_differences':[],'comparison_only_scenarios':[]}
    if scene.road_shape!='주차장' or not empty:return diagnostics
    both=all(current.get(w+'_parking_route')=='주차구역에서 출차' for w in ('a','b'))
    diagnostics['reason_code']='both_parking_exit_not_aisle_exit' if both else 'parking_route_or_motion_unresolved'
    for who in ('a','b'):
        if current.get(who+'_parking_direction') in (None,'미확인') and current.get(who+'_action') in (None,'미확인','주차 출차'):
            diagnostics['missing_fields'].append({'key':who+'_parking_direction','question':('내 차' if who=='a' else '상대 차')+'는 가장 가까워지기 전에 전진·후진·정지 중 어느 상태였나요?'})
    routes=baseline['scene'].get('parking_route_checks',[])
    for who in ('A','B'):
        model=next((p for p in routes if p['vehicle']==who),{})
        if model.get('start_zone')=='통로' and current.get(who.lower()+'_parking_route')=='주차구역에서 출차':
            diagnostics['observation_answer_differences'].append({'vehicle':who,'model_record':model.get('explanation'),'user_answer':'주차구역에서 출차','note':'관찰 기록과 사용자 진술이 다름; 모델 오류 가능성도 있어 어느 쪽도 임의 변경하지 않음'})
    if all(current.get(w+'_parking_route')=='통로 주행' for w in ('a','b')):
        diagnostics['reason_code']='both_aisle_no_registered_parking_type'
        diagnostics['confirmed_answers']={w:{'route':current.get(w+'_parking_route'),'direction':current.get(w+'_parking_direction')} for w in ('a','b')}
        diagnostics['coverage_note']='현재 CSV의 주차장 유형126·127은 통로 주행 대 주차칸 출차 조건입니다. 양차 통로 주행에 직접 대응하는 주차장 항목은 등록되어 있지 않습니다.'
        if current.get('parking_encounter') in (None,'미확인'):
            diagnostics['missing_fields'].append({'key':'parking_encounter','question':'두 차량은 다른 통로에서 교차했나요, 같은 방향으로 진행했나요, 마주 왔나요?'})
    if both:
        # These are excluded alternative conditions, never applied calculation scenarios.
        for role in ('A','B'):
            direction=current.get(('b' if role=='A' else 'a')+'_parking_direction')
            row=next(r for r in ctx.table if r['accident_type']==(127 if direction=='후진' else 126))
            swap=role=='B'
            diagnostics['comparison_only_scenarios'].append({'accident_type':row['accident_type'],'status':'comparison_only_not_applied',
                'a_condition':row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name'],
                'b_condition':row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name'],
                'base_fault':{'A':row['negligence_b' if swap else 'negligence_a'],'B':row['negligence_a' if swap else 'negligence_b']},
                'notice':'한 차량이 실제 통로 주행이었다고 조건을 다르게 확인한 경우의 CSV 비교이며 현재 양차 출차 답변에는 적용하지 않음',
                'direction_assumption':'후진 출차 조건' if direction=='후진' else '전진 출차를 별도로 가정; 실제 방향 미확인 시 확정하지 않음'})
    return diagnostics

def update_estimates(answers,result_path=None,asked_questions=None,display_report=True):
    path=Path(result_path or ctx.output_path)
    result=update_estimates_v220(answers,path,asked_questions,display_report=False)
    baseline=result['survey_baseline'];current=result['survey_answers'];diagnostics=survey_diagnostics(result,baseline,current)
    result['diagnostics']=diagnostics;result['version']=CODE_VERSION
    if not result['rule_engine_output'].get('results') and result['scene'].get('road_shape') != '주차장':
        reasons=[]
        for who,label in [('a','내 차'),('b','상대 차')]:
            if current.get(who+'_action') == '정지/대기':
                reasons.append(label+'를 완전 정지로 답해 직진을 전제로 하는 CSV 후보가 제외될 수 있습니다. 브레이크를 밟으면서 이동한 상황이면 진행 방향은 직진, 속도 상태는 감속 중으로 구분해주세요.')
        detail=' '.join(reasons) or '현재 진행·차량 역할 답변에 대응하는 CSV 후보가 없습니다. 진행 방향과 차로변경 전후 관계를 확인해주세요.'
        diagnostics['no_candidate_reason']=detail
        result['user_report']=result['user_report'].replace('사고 유형·진행 조건 확인 필요',detail,1).replace('관련 판례 확인 필요','연결할 사고 유형이 없어 사고별 판례가 표시되지 않았습니다. '+detail,1)
    speed_notes=[('내 차' if w=='a' else '상대 차')+' 속도 상태: '+current[w+'_speed_state']+' (사용자 진술)' for w in ('a','b') if current.get(w+'_speed_state') not in (None,'미확인')]
    if speed_notes:result['user_report']+='\n'+'\n'.join(speed_notes)

    if diagnostics['reason_code']:
        lines=['현재 답변: '+('두 차량 모두 주차칸에서 통로로 출차' if diagnostics['reason_code']=='both_parking_exit_not_aisle_exit' else '주차장 경로 또는 이동 방향 확인 필요')]
        if diagnostics['reason_code']=='both_parking_exit_not_aisle_exit':
            lines.append('적용하지 않은 이유: CSV126·127은 한 차량의 통로 주행과 다른 차량의 주차칸 출차를 전제로 합니다.')
        for item in diagnostics['observation_answer_differences']:lines.append(('내 차' if item['vehicle']=='A' else '상대 차')+'의 영상 기록과 출발 구역 답변이 다릅니다. 주차칸 출차인지 출구로 향하는 통로 주행인지 확인해주세요.')
        for item in diagnostics['missing_fields']:lines.append('추가 확인: '+item['question'])
        comparisons=diagnostics['comparison_only_scenarios']
        if comparisons:
            lines.append('조건별 CSV 비교 · 현재 답변에 적용된 예상비율이 아닙니다.')
            for item in comparisons:lines.append('  내 차 '+item['a_condition']+' / 상대 차 '+item['b_condition']+'일 때만: '+compact_fault(item['base_fault']))
            lines.append('  두 차량 모두 주차칸 출차라면 위 비교비율을 선택하지 않습니다.')
        if diagnostics['reason_code']=='both_aisle_no_registered_parking_type':
            lines=['현재 답변: 두 차량 모두 통로 주행 / 내 차 '+str(current.get('a_parking_direction','미확인'))+' / 상대 차 '+str(current.get('b_parking_direction','미확인')),diagnostics['coverage_note'],'설문 답변은 계산에 반영됐습니다. 주차칸 출차 조건을 임의로 적용하지 않았습니다.']
            for item in diagnostics['missing_fields']:lines.append('추가 확인: '+item['question'])
            if current.get('parking_encounter') not in (None,'미확인'):lines.append('통로 접근 관계: '+current['parking_encounter']+' (사용자 진술). 접근 관계 답변만으로 미등록 과실 기준을 생성하지 않습니다.')
        report=result['user_report'].replace('사고 유형·진행 조건 확인 필요','\n'.join(lines),1)
        report=report.replace('3. 법령 및 가감요소','3. 법령 및 가감요소\n아래는 장소에 따른 일반 참고 조문이며, 적용 사고 유형이 확정된 것은 아닙니다.',1)
        if diagnostics['case_search_status']=='no_applicable_type' and not result['rule_engine_output'].get('related_cases'):
            report=report.replace('관련 판례 확인 필요','적용할 유형이 없어 사고별 판례 검색을 진행하지 않았습니다. API 연결 실패를 뜻하지 않습니다.',1)
        report=report.replace('산정 대기 · 사고 유형과 차량 역할 확인 필요','현재 답변에 적용할 비율은 미산정입니다. 위의 출발 구역·이동 방향을 확인한 뒤 다시 비교합니다.',1)
        if diagnostics['reason_code']=='both_aisle_no_registered_parking_type':
            report=report.replace('현재 답변에 적용할 비율은 미산정입니다. 위의 출발 구역·이동 방향을 확인한 뒤 다시 비교합니다.','현재 답변에 직접 대응하는 주차장 과실 기준이 CSV에 없어 미산정입니다. 양차 통로 사고 기준과 가감 규칙·판례 연결 자료의 확충이 필요합니다.')
        result['user_report']=report
    destination=path.with_name(path.stem.removesuffix('_survey')+'_survey.json');safe_write_result(destination,result)
    if display_report:print(result['user_report']);print('\n보고서:',destination.with_name(destination.stem+'_report.txt'));print('JSON:',destination)
    return result

update_estimates_detailed = update_estimates

def widget_specs(scene):
    specs=[{'group':g,'key':k,'label':label,'options':opts} for g,k,label,opts in survey_questions(scene)]
    specs.extend([
        {'group':'1. 신호','key':'signal_operating','label':'신호등 작동 상태 (신호등이 없거나 모르면 잘 모르겠어요)','options':['정상 작동','점멸','꺼짐','미확인']},
        {'group':'1. 신호','key':'a_signal','label':'내 차에 적용된 신호 (해당 없거나 모르면 잘 모르겠어요)','options':['녹색','황색','적색','미확인']}])
    for spec in specs:
        if spec['key']=='road_shape':spec['group']='4. 사고 장소'
        if spec['key']=='a_indicator_timing':spec['label']='내 차가 방향을 바꿀 때 방향지시등을 사용했나요? (방향을 바꾸지 않았다면 해당 없음)'
    return specs, []

def survey_field_visible(key,answers,scene):
    return True

def parking_guidance(saved):
    return '<p>모든 영상에 동일한 기본 설문을 사용합니다. 직접 아는 내용만 선택하고, 모르면 잘 모르겠어요를 선택하세요. 차량의 상세 경로·차로변경은 영상 분석 기록과 별도로 검토합니다.</p>'

def collect_questionnaire(saved,input_fn=None,print_fn=None):
    read=input_fn or input;say=print_fn or print
    scene=Observation.model_validate(saved['scene']);specs,_=widget_specs(scene)
    answers={};questions=[]
    for spec in specs:
        values=[v for v in spec['options'] if v!='미확인']
        say(spec['label']);say(' / '.join(str(i+1)+'. '+v for i,v in enumerate(values))+' / 0. 잘 모르겠어요')
        while True:
            value=read('선택: ').strip()
            if value in ('','0','미확인','잘 모르겠어요'):value='미확인';break
            if value in values:break
            if value.isdigit() and 1<=int(value)<=len(values):value=values[int(value)-1];break
            say('표시된 번호 또는 선택지를 입력하세요.')
        answers[spec['key']]=value;questions.append({k:v for k,v in spec.items() if k!='options'})
    return answers,questions

def update_estimates(answers,result_path=None,asked_questions=None,display_report=True):
    path=Path(result_path or ctx.output_path);saved=json.loads(path.read_text(encoding='utf-8'))
    scene=Observation.model_validate(saved['scene']);specs,_=widget_specs(scene)
    allowed={s['key'] for s in specs} | CAUSE_KEYS
    unknown=set(answers)-allowed
    if unknown:raise ValueError('기본 설문에서 지원하지 않는 상세 항목: '+', '.join(sorted(unknown)))
    previous=saved.get('questionnaire',{}).get('answers',{})
    retired={k:'미확인' for k in previous if k not in allowed}
    updates={**retired,**answers}
    signal=updates.get('signal_present',previous.get('signal_present'))
    operating=updates.get('signal_operating',previous.get('signal_operating'))
    if signal!='있음':updates.update(signal_operating='미확인',a_signal='미확인')
    elif operating!='정상 작동':updates['a_signal']='미확인'
    result=update_estimates_detailed(updates,path,asked_questions,display_report=False)
    result['questionnaire']['form_mode']='basic_fixed_v1'
    result['questionnaire']['retired_detail_fields']=sorted(retired)
    result['questionnaire']['questions']=asked_questions or [{k:v for k,v in s.items() if k!='options'} for s in specs]
    if retired:
        result['user_report']+='\n기본 설문 전환: 이전 상세 경로·진행 답변은 현재 계산에서 제외하고 영상 관찰을 기준으로 재검토했습니다. 이전 답변은 설문 이력에 보존했습니다.'
    result['user_report']+='\n※ 기본 설문은 영상 분석을 보완합니다. 대응하는 과실 기준이나 판례 자료가 부족하면 결과 일부가 미산정될 수 있습니다.'
    destination=path.with_name(path.stem.removesuffix('_survey')+'_survey.json');safe_write_result(destination,result)
    if display_report:
        print(result['user_report']);print('\n보고서:',destination.with_name(destination.stem+'_report.txt'));print('JSON:',destination)
    return result

def restore_saved_identity(saved):
    result = json.loads(json.dumps(saved))
    scene = Observation.model_validate(result['scene'])
    scene._evidence_audit = json.loads(json.dumps(result.get('evidence_audit', {})))
    if scene.b_vehicle_id and any(t.vehicle_id == scene.b_vehicle_id for t in scene.tracks):
        return result
    # Recovery uses recorded raw fields, never creates a vehicle from a guessed description.
    sources = [s.get('raw_identity') for s in reversed(result.get('stages', [])) if '상세' in s.get('stage','') and s.get('raw_identity')]
    sources += [result.get('raw_review_scene', {})]
    for raw in sources:
        target = raw.get('b_vehicle_id')
        if not target or target == 'A' or len([t for t in raw.get('tracks', []) if t.get('vehicle_id') == target]) != 1:
            continue
        trial = scene.model_copy(deep=True)
        trial.tracks = [Track.model_validate(t) for t in raw['tracks']]
        trial.b_vehicle_id = target
        trial.b_identity = '구별됨'
        relation = trial.straight_relation
        known = {f['id'] for key in ('overview_frames','review_frames','frame_times') for f in result.get(key,[]) if isinstance(f,dict) and 'id' in f}
        referenced = {i for t in trial.tracks for i in [t.first_frame_id,t.last_frame_id,*t.evidence_frame_ids]}
        if known and not referenced <= known:
            continue
        normalize_tracks(trial)
        if trial.b_vehicle_id != target:
            continue
        selected = next(t for t in trial.tracks if t.vehicle_id == target)
        ids = preimpact_ids(trial, [i for i in relation.evidence_frame_ids if i in selected.evidence_frame_ids])
        if relation.b_vehicle_id != target or len(ids) < 2:
            continue
        trial.b_pre_frame_ids = ids
        check = next((c for c in trial.maneuver_checks if c.vehicle == 'B' and c.support != '미확인' and len(set(c.evidence_frame_ids) & set(ids)) >= 2), None)
        if check:
            trial.b_action = check.action
        collect_match_facts(trial)
        mark_accident_input(trial)
        # Explicit prior user information is tied to the exact video digest and stays labelled user.
        apply_confirmed_video_context(trial, result.get('video_sha256',''))
        result.setdefault('before_identity_recovery', {'scene':result['scene'],'evidence_audit':result.get('evidence_audit',{})})
        result['scene'] = trial.model_dump()
        result['evidence_audit'] = trial._evidence_audit
        result['identity_recovery'] = {'status': 'recovered_from_recorded_raw_identity', 'vehicle_id': target, 'additional_llm_calls': 0}
        return result
    result['identity_recovery'] = {'status': 'not_recovered', 'reason': '상대 ID와 프레임 근거를 일관되게 연결할 원본 기록 부족'}
    return result

_survey_base_before_recovery = survey_base

def survey_base(saved, path):
    return restore_saved_identity(_survey_base_before_recovery(saved, path))

_survey_candidates_before_recovery = survey_candidates

def survey_candidates(saved, scene, rows):
    candidates = _survey_candidates_before_recovery(saved, scene, rows)
    # A rejected LLM choice must not suppress deterministic comparison of all CSV rows.
    return candidates or conditional_candidates(rows, scene)

_recompute_survey_before_recovery = recompute_survey

def recompute_survey(answers, result_path=None, survey_context=None, baseline_data=None, persist=True):
    baseline = baseline_data
    if baseline is not None and answers.get('b_lane_change') == '없음':
        baseline = json.loads(json.dumps(baseline))
        state = baseline.get('scene',{})
        audit = baseline.get('evidence_audit',{})
        # A current explicit answer overrides historical video-specific user context.
        if audit.get('user_confirmed_context'):
            audit.pop('user_confirmed_context',None)
            audit.setdefault('adjustment_answers',{}).pop('b_factor_prohibited_change',None)
            audit.get('B',{}).pop('lane_change',None)
            audit.get('B',{}).pop('progress',None)
            if state.get('b_action') == '진로변경':
                checks = [c for c in state.get('maneuver_checks',[]) if c.get('vehicle')=='B' and c.get('action')!='진로변경']
                state['b_action'] = checks[0]['action'] if len(checks)==1 else '미확인'
            state.get('b_state',{})['lane_change'] = '없음'
            original = state.get('straight_relation',{})
            audit['straight_relation'] = {**original,'status':'inferred','cause_source':'model_record'}
    return _recompute_survey_before_recovery(answers,result_path,survey_context,baseline,persist)

_collect_basic_questionnaire = collect_questionnaire

def collect_questionnaire(saved, input_fn=None, print_fn=None):
    saved = restore_saved_identity(saved)
    answers, questions = _collect_basic_questionnaire(saved, input_fn, print_fn)
    read, say = input_fn or input, print_fn or print
    shape = answers.get('road_shape')
    if shape in (None,'미확인'):
        shape = saved['scene']['road_shape']
    say('\n사고 조건 확인 · 모르는 항목은 0 또는 Enter를 선택하세요.')
    for key, label, options in CAUSE_QUESTIONS.get(shape, []):
        if key == 'b_lane_boundary' and answers.get('b_lane_change') != '있음':
            answers[key] = '미확인'
            continue
        values = [v for v in options if v != '미확인']
        say(label + (' (정지/대기 = 완전히 멈춘 상태)' if '정지/대기' in values else ''))
        say(' / '.join(f'{i+1}. {v}' for i,v in enumerate(values))+' / 0. 잘 모르겠어요')
        while True:
            value = read('선택: ').strip()
            if value in ('','0','미확인','잘 모르겠어요'): value='미확인'; break
            if value in values: break
            if value.isdigit() and 1 <= int(value) <= len(values): value=values[int(value)-1]; break
            say('표시된 번호 또는 선택지를 입력하세요.')
        answers[key] = value
        questions.append({'key':key,'group':'사고 조건 확인','label':label,'options':options})
    return answers, questions

_update_estimates_before_recovery = update_estimates

def update_estimates(answers, result_path=None, asked_questions=None, display_report=True):
    path = Path(result_path or ctx.output_path)
    result = _update_estimates_before_recovery(answers,path,asked_questions,display_report=False)
    # Baseline preservation is only useful when that baseline actually has calculation scenarios.
    if not result.get('rule_engine_output',{}).get('results') and answers.get('b_vehicle_confirm') != '아니에요':
        scene = Observation.model_validate(result['scene'])
        scene._evidence_audit = json.loads(json.dumps(result.get('evidence_audit',{})))
        collect_match_facts(scene)
        context, notes = matching_context(scene)
        rows = search_rows(context)
        candidates = survey_candidates(result,context,rows)
        byid = {r['accident_type']:r for r in rows}
        linked = [link_match(c,byid[c.accident_type],context) for c in candidates if c.accident_type in byid]
        bundle = law_rule_bundle(scene,linked)
        result.update(bundle, scene=scene.model_dump(), evidence_audit=scene._evidence_audit,
                      internal_candidate_scenarios=linked, matching_context=context.model_dump(), matching_notes=notes,
                      similar_accidents=public_scenarios(scene,linked),reference_scenarios=reference_scenarios(scene,linked))
        result['accident_type_candidates'] = [{'accident_type_id':s['accident_type'],'status':s.get('scenario_status','조건부 참고')} for s in bundle['rule_engine_input'].get('scenarios',[])]
        result['catalog_assessments'] = compare_all_csv_rows(rows,context)
        result['csv_comparison'] = {'scope':'all_rows','total':len(ctx.table),'compared':len(rows),'prefiltered':0,'method':'post_survey_empty_baseline_recheck'}
        result['no_match_reason'] = '' if bundle['rule_engine_output'].get('results') else '현재 답변·관찰과 양립하는 등록 기준 부족'
        result['user_report'] = build_user_report(scene,result,linked,[],bundle_override=bundle)
        result['user_report'] += '\n설문 반영: 사용자 진술과 영상 관찰을 구분했습니다. 빈 후보를 전체 CSV와 재비교했습니다.'
        result.setdefault('questionnaire',{})['empty_result_recheck'] = {'compared_csv_count':len(rows),'additional_llm_calls':0}
        result['questionnaire']['selection_policy'] = 'empty_baseline_rechecked'
    out = result.get('rule_engine_output',{})
    results = out.get('results',[])
    result.setdefault('diagnostics',{})['selected_type_count'] = len({r['accident_type'] for r in results})
    result['result_status'] = {
        'status': 'conditional_reference' if any(s.get('reference_only') for s in result.get('rule_engine_input',{}).get('scenarios',[])) else 'calculated_reference' if results else 'needs_evidence_or_supported_standard',
        'scenario_count':len(results),'report_available':True,
        'reason': '' if results else '답변·영상과 양립하는 등록 기준 부족. 결과 보고서는 제공하며 임의 비율·판례는 생성하지 않음'}
    if not results:
        result['user_report'] += '\n계산 조건 확인 결과: 현재 답변에 맞는 기준을 찾지 못했습니다. 답변·관찰·제외 사유는 JSON에 보존됩니다.'
    result['version'] = CODE_VERSION
    result['user_report'] = finish_report(result['user_report'])
    destination = path.with_name(path.stem.removesuffix('_survey')+'_survey.json')
    safe_write_result(destination,result)
    if display_report:
        print(result['user_report']); print('\n보고서:',destination.with_name(destination.stem+'_report.txt'));print('JSON:',destination)
    return result
