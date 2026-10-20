"""사용자용 보고서 생성과 저장."""
import json
import re
from pathlib import Path
from .constants import CODE_VERSION, REPORT_NOTICE
from .tables import ADJUSTMENT_RULES, FACTOR_LABELS
from .context import ctx
from .schemas import Observation
from .matching import csv_accident_type_details
from .law import case_date, law_article_label, sanitize_case_bundle
from .adjustments import compact_fault, law_rule_bundle
from .pdf_reference import pdf_report_lines
from .timeline import major_accident_timeline, save_timeline_text


def save_user_report(result_path, text):
    path = Path(result_path).with_name(Path(result_path).stem + '_report.txt')
    path.write_text(text + '\n', encoding='utf-8-sig')
    return path

def neat_text(text, limit=110):
    text = re.sub('frame_\\d+(?:\\s*[~～-]\\s*(?:frame_)?\\d+)?', '', str(text))
    text = re.sub('\\s+', ' ', text).strip(' ,;:/')
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'

def build_user_report(scene, timeline_payload, linked, survey, direction=None, bundle_override=None):
    bundle = bundle_override if bundle_override is not None else law_rule_bundle(scene, linked)
    payload, out = (bundle['rule_engine_input'], bundle['rule_engine_output'])
    scenarios = {s['scenario_id']: s for s in payload['scenarios']}
    results = out['results']
    context = out['legal_context']
    titles = {r['accident_type']: csv_accident_type_details(r)['accident_type_display_name'] for r in ctx.table}
    lines = ['에블리 | 사고 분석 보고서', '────────────────────────────', '', '1. 사고 타임라인']
    timeline = timeline_payload or {}
    major = major_accident_timeline(timeline)
    if not major:
        lines.append('핵심 장면 확인 필요')
    for line in major:
        lines.append(line.replace(' (접촉 확인 필요)', ' · 접촉 미확인'))
        nums = re.findall('\\d+\\.\\d+', line.split('|')[0])
        if not nums:
            continue
        start, end = (float(nums[0]), float(nums[-1]))
        event = next((e for e in timeline.get('timeline', []) if round(e.get('start_sec', -1), 2) == start and round(e.get('end_sec', -1), 2) == end), None)
        if event:
            explanation = neat_text(event.get('evidence_text') or event.get('description') or '')
            if explanation:
                lines.append('  ' + explanation)
    lines.append('※ 프레임 기준의 관찰 구간이며 정확한 충돌 시각은 아닙니다.')
    if scene._evidence_audit.get('user_confirmed_context'):
        lines.append('※ 사고 전 실선 진로변경은 사용자 확인 정보입니다.')
    if scene._evidence_audit.get('user_road_context'):
        lines.append('※ 장소: ' + scene.road_shape + ' · 사용자 확인 정보, Vision 판단과 구분')
    lines += ['', '2. 기본 과실비율']
    if not results:
        pattern = out.get('observed_accident_pattern')
        if pattern:
            lines.append('관찰 형태: ' + pattern['title'])
            lines.append('  내 차 ' + pattern['ego_motion'] + ' 추정 / 상대 차 후진 추정')
            lines.append('  CSV 대응: ' + pattern['csv_limit'])
        else:
            lines.append('사고 유형·진행 조건 확인 필요')
    for n, r in enumerate(results, 1):
        s = scenarios[r['scenario_id']]
        prefix = f'후보 {n} · ' if len(results) > 1 else ''
        lines.append(prefix + titles.get(r['accident_type'], '유형 확인 필요'))
        progress = s.get('service_progress', {})
        if progress:
            lines.append(f"  내 차 {progress.get('A', '미확인')} / 상대 차 {progress.get('B', '미확인')}")
        lines.append('  기본값  ' + compact_fault(r['base_fault']))
        lines.append('  상태  ' + ('진행·역할을 가정한 참고값' if s.get('reference_only') else '표시한 진행 조건이 맞는 경우의 기본값'))
        if s.get('reference_only'):
            for condition in list(dict.fromkeys(s.get('unconfirmed_conditions', [])))[:3]:
                lines.append('  조건: ' + condition)
    lines += ['', '3. 법령 및 가감요소']
    articles = context.get('articles', [])
    if articles:
        if out.get('observed_accident_pattern') and (not results):
            lines.append('후진 접근 관련 일반 참고 조문 · 실제 적용 여부는 장소·사고 조건 확인 필요')
        labels = []
        for a in articles:
            para = ' 제3항' if a['article'] == 18 and any((r['accident_type'] == 126 for r in results)) else ''
            labels.append(f"{law_article_label(a['article'])}{para} · {a['title']}")
        lines.append('관련 법령: 도로교통법')
        for label in labels:
            lines.append('  ' + label)
        dates = sorted({a['effective_date'] for a in articles})
        lines.append('법령 판본: ' + ('사고일 이전 시행 판본' if context.get('requested_accident_date') else '현행법령 · 사고 당시 판본 확인 아님') + ' / 시행일 ' + ', '.join(dates))
        if any((r['accident_type'] == 126 for r in results)):
            lines.append('※ 주차장 출차 기준에서 준용하는 근거이며 직접 적용을 확정하지 않습니다.')
    else:
        lines.append('법령 조회: ' + {'disabled': '비활성', 'unavailable': '조회 실패', 'not_mapped': '연결 근거 확인 필요'}.get(context['status'], context['status']))
    shown = set()
    for n, r in enumerate(results, 1):
        s = scenarios[r['scenario_id']]
        if len(results) > 1:
            lines.append(f'후보 {n}')
        if r['applied_adjustments']:
            lines.append('  적용: ' + ' / '.join((f"{('내 차' if f['actor'] == 'A' else '상대 차')} {f['label']} {f['delta_pp']:+d}%p" for f in r['applied_adjustments'])))
        elif s.get('reference_only') or (ADJUSTMENT_RULES.get(str(r['accident_type'])) and (not s.get('eligible_for_adjustment'))):
            lines.append('  적용: 대기 · 진행·차량 역할 미확인')
        elif ADJUSTMENT_RULES.get(str(r['accident_type'])):
            lines.append('  적용: 없음')
        else:
            lines.append('  적용: 계산 규칙 준비 필요')
        projection = r.get('conditional_projection')
        if projection:
            for f in projection['applied_adjustments']:
                lines.append('  조건부 계산: ' + ('내 차' if f['actor'] == 'A' else '상대 차') + ' ' + f['label'] + f" {f['delta_pp']:+d}%p")
            if not projection['applied_adjustments']:
                lines.append('  조건부 계산: 확인된 가감요소 없음 · 미확인은 미적용으로 확정하지 않음')
            pending_labels = list(dict.fromkeys((('내 차 ' if f['actor'] == 'A' else '상대 차 ') + f['label'] for f in projection['pending'])))
            if pending_labels:
                lines.append('  추가 확인: ' + ', '.join(pending_labels))
        pending = {who: list(dict.fromkeys((f['label'] for f in r['pending'] if f['actor'] == who))) for who in ('A', 'B')}
        if pending['A'] and pending['A'] == pending['B']:
            lines.append('  미확인(양측): ' + ', '.join(pending['A']))
        else:
            for who, label in (('A', '내 차'), ('B', '상대 차')):
                if pending[who]:
                    lines.append(f'  미확인({label}): ' + ', '.join(pending[who]))
        config = ADJUSTMENT_RULES.get(str(r['accident_type']))
        if config and r['accident_type'] not in shown:
            shown.add(r['accident_type'])
            grouped = {who: [f"{FACTOR_LABELS[x['factor']]} {x['delta_pp']:+d}%p" for x in config['rules'] if x['actor'] == who] for who in ('A', 'B')}
            if grouped['A'] == grouped['B']:
                lines.append('  기준(양측): ' + ', '.join(grouped['A']))
            else:
                role = s.get('dashcam_table_role')
                for who in ('A', 'B'):
                    name = ('내 차' if (who == 'A') == (role == 'A') else '상대 차') if role in ('A', 'B') else '표 ' + who + ' 차량'
                    lines.append('  기준(' + name + '): ' + ', '.join(grouped[who]))
            lines.append('  수치 출처: 손해보험협회 ' + config['official_chart'])
    lines += ['', '4. 관련 판례']
    cases = out.get('related_cases', [])[:3]
    if not cases:
        lines.append('관련 판례 확인 필요')
    for n, c in enumerate(cases, 1):
        lines.append(f"{n}) {c['court']} · {case_date(c['date'])} · {c['case_number']}")
        lines.append('   요지: ' + neat_text(c['summary'], 140))
        lines.append('   비교: ' + neat_text(c['comparison_limit'], 140))
        lines.append('   자료: ' + ('국가법령정보 판례 본문 발췌' if c.get('case_api_id') else '손해보험협회 판례 요약 · 판결문 원문 조회 아님'))
    for audit in out.get('case_lookup', []):
        if audit['count'] < 3:
            lines.append(f"※ 유형 {audit['accident_type']}: {audit['count']}/3건 · " + audit.get('reason', audit['status']))
    lines += ['', '5. 최종 과실비율']
    if not results:
        lines.append('산정 대기 · 정지 차량과 후진 차량 조건을 지원하는 기준 추가 필요' if out.get('observed_accident_pattern') and scene.a_action == '정지/대기' else '산정 대기 · 사고 유형과 차량 역할 확인 필요')
    for n, r in enumerate(results, 1):
        if len(results) > 1:
            lines.append(f'후보 {n}')
        s = scenarios[r['scenario_id']]
        projection = r.get('conditional_projection')
        if projection and projection['adjusted_fault']:
            label = '가정하의 가감 반영 참고값' if projection['applied_adjustments'] else '가정하의 기본 참고값 · 확인된 가감 없음'
            lines.append('  ' + label + '  ' + compact_fault(projection['adjusted_fault']))
            lines.append('  유형·차량 역할을 가정한 계산이며 실제 적용 최종값은 미확정')
            if projection['pending']:
                lines.append('  추가 가감요소 미확인')
        elif r['final_fault']:
            lines.append('  ' + compact_fault(r['final_fault']))
            lines.append('  등록 규칙의 평가 완료 · 표시한 사고 조건에 따른 참고값')
        elif r['applied_adjustments'] and r['adjusted_fault']:
            lines.append('  현재 계산값  ' + compact_fault(r['adjusted_fault']))
            lines.append('  최종 산정 미완료 · 추가 가감요소 확인 필요')
        else:
            lines.append('  최종 산정 미완료')
            lines.append('  기본 참고값  ' + compact_fault(r['base_fault']))
            lines.append('  사유: ' + ('진행·차량 역할 확인 필요' if s.get('reference_only') else '가감요소 확인 필요' if r['pending'] else r['status']))
    lines += ['', '※ AI 참고 분석입니다. 판례의 비율을 이번 사고에 그대로 적용하지 않습니다.', '※ 법령 원문·출처 링크·상세 판단 근거는 결과 JSON에 저장됩니다.']
    return '\n'.join(lines)

def safe_write_result(path, result):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)
    save_user_report(path, result['user_report'])
    save_timeline_text(path, result, Path(result.get('video', '')).name)

build_user_report_before_case_guard = build_user_report

def build_user_report(scene,timeline_payload,linked,survey,direction=None,bundle_override=None):
    bundle=sanitize_case_bundle(bundle_override if bundle_override is not None else law_rule_bundle(scene,linked))
    report=build_user_report_before_case_guard(scene,timeline_payload,linked,survey,direction,bundle_override=bundle)
    report=report.replace('4. 관련 판례','4. 관련 판례 · 사고 유형의 참고 사례',1)
    for case in bundle['rule_engine_output'].get('related_cases',[]):
        identity=case['case_number']
        start=report.find(identity)
        if start<0:continue
        marker='   자료: '
        pos=report.find(marker,start)
        if pos<0:continue
        end=report.find('\n',pos)
        if end<0:end=len(report)
        additions=[]
        if case.get('case_name'):additions.append('   사건명: '+neat_text(case['case_name'],80))
        if case.get('source'):additions.append('   출처: '+case['source'])
        if case.get('relevance_status')=='registered_chart_reference':
            additions.append('   연결 기준: 후보 사고 유형의 도표에 소개된 사례이며, 영상과 동일한 사고라는 뜻은 아닙니다.')
        if additions:report=report[:end]+'\n'+'\n'.join(additions)+report[end:]
    return report

def refresh_saved_case_report(result_path):
    path=Path(result_path);saved=json.loads(path.read_text(encoding='utf-8'))
    scene=Observation.model_validate(saved['scene']);scene._evidence_audit=saved.get('evidence_audit',{})
    bundle=sanitize_case_bundle({'rule_engine_input':saved.get('rule_engine_input',{}),'rule_engine_output':saved.get('rule_engine_output',{})})
    saved.update(bundle);saved['version']=CODE_VERSION
    saved['user_report']=build_user_report(scene,saved,saved.get('internal_candidate_scenarios',[]),[],bundle_override=bundle)
    saved['case_report_refresh']={'mode':'existing_sources_only','additional_llm_calls':0,'additional_case_api_calls':0,
                                  'removed_cases':bundle['rule_engine_output']['case_validation']['excluded']}
    destination=path.with_name(path.stem+'_case_fixed.json')
    safe_write_result(destination,saved)
    print(saved['user_report']);print('\nJSON:',destination)
    return saved

def finish_report(text):
    lines = [line.rstrip() for line in text.splitlines() if line.strip() != REPORT_NOTICE]
    while lines and not lines[-1].strip():
        lines.pop()
    return '\n'.join(lines) + '\n\n' + REPORT_NOTICE

def build_user_report(scene, timeline_payload, linked, survey, direction=None, bundle_override=None):
    bundle = sanitize_case_bundle(bundle_override if bundle_override is not None else law_rule_bundle(scene, linked))
    payload, out = bundle.get('rule_engine_input', {}), bundle.get('rule_engine_output', {})
    scenarios = {s['scenario_id']: s for s in payload.get('scenarios', [])}
    results = out.get('results', [])
    titles = {r['accident_type']: csv_accident_type_details(r)['accident_type_display_name'] for r in ctx.table}
    lines = ['에블리 | 사고 분석 보고서', '────────────────────────────', '', '1. 사고 타임라인']
    timeline = timeline_payload or {}
    major = major_accident_timeline(timeline)
    for line in major:
        lines.append(line.replace(' (접촉 확인 필요)', ' · 접촉 미확인'))
        times = re.findall(r'\d+\.\d+', line.split('|')[0])
        if times:
            start, end = float(times[0]), float(times[-1])
            kind = 'B 확인 구간' if '상대 차량' in line else 'A 움직임' if '내 차' in line else '접촉 근거 구간'
            event = next((e for e in timeline.get('timeline', []) if e.get('kind') == kind and round(e.get('start_sec', -1), 2) == start and round(e.get('end_sec', -1), 2) == end), {})
            detail = neat_text(event.get('evidence_text') or event.get('description') or '', 90)
            if detail:
                lines.append('  ' + detail)
    if not major:
        lines.append('핵심 장면 확인 필요')
    lines.append('※ 프레임 기준의 관찰 구간이며 접촉 시각은 미확정입니다.')
    audit = getattr(scene, '_evidence_audit', {})
    if audit.get('user_road_context'):
        lines.append('장소: ' + scene.road_shape + ' (사용자 진술)')
    if audit.get('user_confirmed_context'):
        lines.append('사고 전 실선 진로변경: 사용자 진술 (영상 관찰과 구분)')

    lines += ['', '2. 기본 과실비율']
    pattern = out.get('observed_accident_pattern')
    if not results:
        if pattern:
            lines.append('인식한 사고 형태: ' + pattern['title'])
            lines.append('  내 차 ' + pattern.get('ego_motion','미확인') + ' / 상대 차 ' + pattern.get('other_motion','미확인'))
            lines.append('  기본값 미산정 · 정지 차량 조건에 직접 대응하는 등록 기준이 없습니다.')
            lines.append('  통로 주행을 전제로 하는 CSV127번을 정지 차량에 적용하지 않았습니다.')
        else:
            lines.append('미산정 · 사고 유형과 차량 진행 조건 확인 필요')
    for n, r in enumerate(results, 1):
        s = scenarios.get(r['scenario_id'], {})
        prefix = f'후보 {n} · ' if len(results) > 1 else ''
        lines.append(prefix + titles.get(r['accident_type'], '사고 유형 확인 필요'))
        progress = s.get('service_progress', {})
        lines.append(f"  내 차 {progress.get('A', '미확인')} / 상대 차 {progress.get('B', '미확인')}")
        lines.append('  기본값: ' + compact_fault(r['base_fault']))
        if s.get('reference_only'):
            lines.append('  조건 비교용 참고값 · 영상에 적용된 유형은 미확정')
    if results:
        lines.append('※ 표시한 진행 조건이 실제와 일치하는 경우의 기본값입니다.')

    lines += ['', '3. 법령 및 가감요소']
    lines.extend(pdf_report_lines(bundle.get('pdf_reference_context')))
    context = out.get('legal_context', {})
    articles = context.get('articles', [])
    if articles:
        labels = []
        for a in articles:
            para = ' 제3항' if a['article'] == 18 and any(r['accident_type'] == 126 for r in results) else ''
            labels.append(law_article_label(a['article']) + para + ' ' + a.get('title', ''))
        lines.append('참고 법령: 도로교통법 ' + ' / '.join(dict.fromkeys(labels)))
        edition = '사고일 이전 시행 판본 조회' if context.get('requested_accident_date') else '현행 판본 조회 · 사고 당시 판본 미확인'
        lines.append('  ' + edition + ' · 법령 적용 여부는 별도 확인 필요')
        if any(r['accident_type'] == 126 for r in results):
            lines.append('  주차장 출차 기준에서 준용한 조문입니다.')
    else:
        lines.append('참고 법령: ' + {'disabled': '조회 비활성', 'unavailable': '조회 실패', 'not_mapped': '연결 근거 확인 필요'}.get(context.get('status'), '확인 필요'))
    for n, r in enumerate(results, 1):
        prefix = f'후보 {n}: ' if len(results) > 1 else ''
        projection = r.get('conditional_projection') or {}
        applied = r.get('applied_adjustments') or projection.get('applied_adjustments') or []
        if applied:
            labels = [('내 차' if f['actor'] == 'A' else '상대 차') + ' ' + f['label'] + f" {f['delta_pp']:+d}%p" for f in applied]
            lines.append(prefix + '반영 ' + ' / '.join(dict.fromkeys(labels)))
        else:
            lines.append(prefix + '확인된 가감요소 없음')
        pending = r.get('pending') or projection.get('pending') or []
        s = scenarios.get(r['scenario_id'], {})
        if pending or s.get('reference_only') or not s.get('eligible_for_adjustment'):
            lines.append('  추가 확인: ' + ('유형·차량 역할 및 가감요소' if s.get('reference_only') or not s.get('eligible_for_adjustment') else '가감요소') + ' · 미확인은 미적용 확정이 아닙니다.')
        config = ADJUSTMENT_RULES.get(str(r['accident_type']))
        if config:
            lines.append('  수치 기준: 손해보험협회 ' + config['official_chart'])
        else:
            lines.append('  해당 유형의 가감 규칙 미등록')

    lines += ['', '4. 관련 판례']
    cases = out.get('related_cases', [])[:3]
    for n, c in enumerate(cases, 1):
        lines.append(f"{n}) {c['court']} {case_date(c['date'])} · {c['case_number']}")
        lines.append('  요지: ' + neat_text(c.get('summary', ''), 100))
        lines.append('  차이: ' + neat_text(c.get('comparison_limit', ''), 90))
        lines.append('  자료: ' + ('국가법령정보 판례 본문 발췌' if c.get('case_api_id') else '손해보험협회 요약 · 판결문 원문 조회 아님'))
    if not cases:
        lookups = out.get('case_lookup',[])
        failed = any(a.get('status') in ('unavailable','error') for a in lookups)
        if failed:
            lines.append('판례 조회 실패 · 이번 실행에서 관련 판례를 확인하지 못했습니다.')
        elif lookups:
            lines.append('판례 조회는 진행했으나 관련성 검토를 통과한 자료가 없습니다.')
        else:
            lines.append('연결할 사고 유형이 없어 판례 검색이 진행되지 않았습니다.')
    else:
        lines.append('※ 유사 쟁점의 참고 사례이며 같은 과실비율을 적용하지 않습니다.')

    lines += ['', '5. 과실비율 참고 결과']
    if not results:
        if pattern:
            lines.append('미산정 · 정지 차량 대 후진 차량의 대응 기준·가감 규칙 보강 필요')
        else:
            lines.append('미산정 · 사고 유형과 차량 역할 확인 필요')
    for n, r in enumerate(results, 1):
        s = scenarios.get(r['scenario_id'], {})
        projection = r.get('conditional_projection') or {}
        fault = r.get('final_fault') or r.get('adjusted_fault') or projection.get('adjusted_fault') or r['base_fault']
        prefix = f'후보 {n}: ' if len(results) > 1 else ''
        lines.append(prefix + compact_fault(fault))
        if s.get('reference_only'):
            lines.append('  진행·차량 역할을 가정한 참고값 · 실제 적용 미확정')
        elif not r.get('final_fault'):
            lines.append('  추가 확인이 필요한 계산값 · 최종 비율 미확정')
        else:
            lines.append('  확인된 조건과 등록된 가감 기준에 따른 참고값')
    lines += ['', '상세 조건·가감 기준·법령 및 판례 출처는 결과 JSON에 저장됩니다.']
    return finish_report('\n'.join(lines))

_save_user_report_verbose = save_user_report

def save_user_report(result_path, text):
    return _save_user_report_verbose(result_path, finish_report(text))

_safe_write_result_verbose = safe_write_result

def safe_write_result(path, result):
    if result.get('user_report'):
        result['user_report'] = finish_report(result['user_report'])
    return _safe_write_result_verbose(path, result)
