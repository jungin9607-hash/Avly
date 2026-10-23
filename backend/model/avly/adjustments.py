"""기본 과실비율에 가감요소를 적용."""
import json
import re
import time
from .constants import CASE_API_ENABLED, CASE_TARGET_COUNT, LAW_ACCIDENT_DATE, LAW_API_ENABLED, RULE_ENGINE_VERSION
from .tables import ADJUSTMENT_RULES, FACTOR_LABELS, LAW_ARTICLES_BY_TYPE, VERIFIED_CASES
from .context import ctx
from .facts import accident_input_confirmed, action_support, original_frame_index, parking_environment, progress_actions, scene_missing_conditions, straight_audit
from .matching import assess_row, assessment_sort_key, candidate_eligibility, context_requirements, csv_accident_type_details, matching_context, mechanism_compatible, orientation_compatible, place_compatible, strict_user_conflicts
from .law import case_profile, legal_context_for_input, related_cases_for_row, sanitize_case_bundle
from .reference_rank import order_references, soft_actions


def public_scenarios(scene, linked):
    result = []
    for item in linked:
        options = []
        for option in item.get('ratio_options', [])[:2]:
            status, reasons = scenario_display_status(scene, item, option)
            if status not in ('보류', '제외'):
                options.append({**option, 'display_status': status, 'unconfirmed_conditions': reasons})
        if options:
            result.append({**item, 'ratio_options': options})
    return result

def scenario_display_status(scene, item, option):
    if scene._evidence_audit.get('contact_user_answer') == '없음':
        return ('보류', ['사용자가 선택된 차량과 접촉하지 않았다고 답변함: 상대 재지정 필요'])
    if scene.b_identity != '구별됨' or not scene.b_vehicle_id:
        return ('보류', ['사고 상대 차량을 특정할 근거 부족'])
    row = next((r for r in ctx.table if r['accident_type'] == item.get('accident_type')), None)
    if row is None:
        return ('제외', ['CSV에 없는 사고 유형'])
    role = option.get('dashcam_table_role')
    if role not in ('A', 'B'):
        return ('보류', ['비율 시나리오의 차량 역할이 지정되지 않음'])
    if not candidate_eligibility(row, scene)[0] or not orientation_compatible(row, scene, role):
        return ('제외', ['관찰 장소·진행·사고 대상 또는 필수조건과 표가 모순됨'])
    context = context_requirements(row, scene, role)
    if option.get('progress_mismatches') or any((c['contradicted'] for c in context)):
        return ('제외', ['현재 관찰 또는 사용자 답변과 CSV 조건이 모순됨'])
    actors = option.get('actor_conditions', [])
    supported = [c for c in actors if c.get('relation') == '기본 진행 대응' and c.get('status') in ('observed', 'user', 'inferred')]
    if len(actors) != 2 or not supported:
        return ('보류', ['두 차량 모두 표의 진행과 연결할 근거가 없음'])
    confirmed = accident_input_confirmed(scene)
    if not confirmed and scene._evidence_audit.get('contact_user_answer') != '있음' and (scene.contact not in ('접촉 관찰', '접촉 추정', '충돌 정황 강함')):
        return ('보류', ['사고 발생 정황 미확인'])
    pending = list(option.get('unresolved_conditions', []))
    pending += [c['note'] for c in context if c['status'] == 'unknown']
    for c in actors:
        label = '내 차' if c['field'] == 'a_progress' else '상대 차'
        if c not in supported:
            pending.append(label + '가 ' + c['expected'] + '이었다는 가정: 영상에서 진행 미확인')
        elif c.get('status') == 'inferred':
            pending.append(label + '의 진행은 영상 추정')
    if item.get('dashcam_table_role') not in ('A', 'B'):
        pending.append('차량 역할 미확정: 아래 진행 조건과 비율은 역할별 가정이며 한쪽을 확정하지 않음')
    pending += [c.removeprefix('추가 가정(모델 제안, 영상 확인 아님): ') for c in item.get('conditions', []) if c.startswith('추가 가정(모델 제안, 영상 확인 아님): ')]
    if scene.contact != '접촉 관찰' and scene._evidence_audit.get('contact_user_answer') != '있음':
        pending.append('사고 발생은 사용자 확인; 직접 접촉 장면은 영상에서 미확인' if confirmed else '실제 접촉 여부 확인 필요')
    pending = list(dict.fromkeys(pending))
    return ('조건부 예상 — 표시한 진행·역할을 가정한 CSV 기본값', pending) if pending else ('확인된 조건의 CSV 기본값 참고', [])

def no_candidate_diagnostics(scene):
    reasons = list(scene._evidence_audit.get('consistency_notes', []))
    compatible = [r for r in ctx.table if place_compatible(r, scene) and (not scene.accident_object or r.get('accident_object_name') == scene.accident_object)]
    ranked = []
    for row in compatible:
        for role in ('A', 'B'):
            assessment = assess_row(row, scene, role)
            ranked.append((assessment['score'], row, assessment))
    for _, row, assessment in sorted(ranked, key=lambda x: x[0], reverse=True)[:2]:
        for text in assessment.get('progress_mismatches', []):
            reasons.append(f"CSV {row['accident_type']}번: {text}")
        reasons.extend(assessment.get('unresolved_conditions', []))
    if not compatible:
        reasons.append('현재 장소·사고 대상과 대응하는 CSV 유형이 없음: 관찰 또는 CSV 지원 범위 확인 필요')
    return list(dict.fromkeys(reasons + scene_missing_conditions(scene)))[:5]

def uncertainty_details_base(scene, linked):
    details = []

    def add(field, label, status, observed, reasons, missing, impact, next_step, ids=(), source='관찰 기록·후처리 검증'):
        reasons = list(dict.fromkeys((x for x in reasons if x)))
        details.append({'field': field, 'label': label, 'status': status, 'observed': observed, 'reasons': reasons, 'missing_information': missing, 'impact_on_result': impact, 'next_step': next_step, 'evidence_frame_ids': list(dict.fromkeys(ids)), 'source': source})
    if scene.road_shape in ('미확인', '기타', '주차장/기타'):
        add('road_shape', '사고 장소', '미확인', scene.road_evidence or '장소를 구분할 관찰 기록이 없음', ['관찰된 장소 단서만으로 하나의 도로 형태를 확정하지 못함'], '주차 구획·통로, 교차 도로 또는 교통섬의 구분', '장소가 다른 CSV 유형을 하나로 좁히기 어려움', '차량이 가까워지기 전 주변 구조가 보이는 장면 또는 사고 장소 정보를 확인', scene.road_shape_evidence_frame_ids)
    if scene.b_vehicle_id is None or scene.b_identity != '구별됨':
        names = [t.vehicle_id + ': ' + t.appearance for t in scene.tracks]
        add('b_vehicle_id', '상대 차량', '미확인', ' / '.join(names) or '외부 차량의 식별 기록이 없음', ['실제 접촉 상대를 하나의 차량으로 연결하지 못함'], '실제 접촉 상대 차량', '상대 차량의 진행과 CSV 역할을 확정할 수 없음', '영상에 표시된 차량 중 실제 접촉 상대를 선택')
    for who, label in (('A', '내 차'), ('B', '상대 차')):
        action = getattr(scene, who.lower() + '_action')
        _, support = action_support(scene, who)
        if action not in ('미확인', '기타') and support.get('status') in ('observed', 'user'):
            continue
        checks = [c for c in scene.maneuver_checks if c.vehicle == who]
        reasons = list(support.get('conflicts', []))
        if support.get('status') == 'inferred':
            reasons.append('진행 행동이 직접 관찰된 사실이 아니라 연결된 단서에 따른 추정임')
        elif not reasons:
            reasons.append('사고 직전 진행을 확정할 충분하고 일관된 근거가 기록되지 않음')
        if checks:
            reasons.extend((c.alternative_explanation for c in checks if c.alternative_explanation))
            if any((len(set(c.evidence_frame_ids)) < 2 for c in checks)):
                reasons.append('행동 비교에 인용된 서로 다른 프레임이 2장 미만임')
        geometry = scene._evidence_audit.get(who, {}).get('roundabout_position', {}).get('geometry_check', {})
        if scene.road_shape == '회전교차로' and geometry and (not geometry.get('accepted')):
            reasons.append(geometry.get('reason', '진입·회전 위치 기록이 기존 판단과 일치하지 않음'))
        observed = ' / '.join((c.path_description for c in checks)) or getattr(scene, 'pre_contact_' + who.lower() + '_movement')
        ids = [i for c in checks for i in c.evidence_frame_ids] or support.get('direct_frame_ids', []) + support.get('linked_frame_ids', [])
        add(who.lower() + '_action', label + '의 사고 직전 진행', '추정' if support.get('status') == 'inferred' else '미확인', observed, reasons, '접촉이 의심되는 순간 직전의 실제 진행', '직진·후진·정지 또는 진입·회전 조건에 따라 사고 유형과 기본과실이 달라질 수 있음', label + '의 진행을 확인하고, 영상 검토 시 차량 방향과 고정 배경의 전후 위치를 비교', ids)
    if parking_environment(scene):
        for who, label in (('A', '내 차'), ('B', '상대 차')):
            route = scene._evidence_audit.get(who, {}).get('parking_route', {})
            if route.get('status') in ('observed', 'user') and route.get('start_zone') not in (None, '미확인'):
                continue
            add(who.lower() + '_parking_route', label + '의 주차장 진행 경로', '미확인', route.get('explanation') or '주차구역과 통로 사이의 출발·도착 위치 기록이 없음', route.get('conflicts', []) or ['현재 위치만으로 주차구역에서 출차했는지, 원래 통로를 주행했는지 확정하지 못함'], '주차구역 출차 / 통로 주행 / 주차구역 진입 중 어느 경로인지', '주차구역 출차를 전제로 하는 CSV 유형의 적용 여부를 확정할 수 없음', label + '가 사고 직전 어디에서 출발해 어디로 이동했는지 확인', route.get('frame_ids', []))
    if scene.contact != '접촉 관찰' and scene._evidence_audit.get('contact_user_answer') != '있음':
        denied = scene._evidence_audit.get('contact_user_answer') == '없음'
        add('contact', '실제 접촉 여부', '사용자 답변: 없음' if denied else '미확인', scene.contact_evidence or '직접 접촉을 설명하는 관찰 기록이 없음', ['사용자가 선택한 차량과 접촉하지 않았다고 답변함' if denied else "현재 접촉 판정은 '" + scene.contact + "'이며 직접 접촉이 확인된 상태가 아님"], '선택된 상대 차량과의 실제 접촉 여부', '영상 정황을 확정 사고로 표현할 수 없으며 과실비율이 보류되거나 조건부로 표시됨', '선택된 차량과 접촉했는지 확인하고, 필요하면 다른 시점 영상·손상 사진을 함께 확인', scene.contact_frame_ids)
    usable = [item for item in linked if any((r['accident_type'] == item.get('accident_type') and candidate_eligibility(r, scene)[0] for r in ctx.table))]
    if not usable:
        add('accident_type', '사고 유형·과실비율', '보류', f'CSV 전체 {len(ctx.table)}개 유형 비교', no_candidate_diagnostics(scene), 'CSV의 장소·진행·역할·필수조건과 대응하는 관찰', '현재 조건으로 적용할 유형과 비율을 확정하지 못함', '위의 미확인 항목을 확인해 다시 비교; 조건이 확인돼도 후보가 없으면 CSV 지원 범위를 검토', source='CSV 조건 비교·후처리 검증')
    else:
        for item in usable[:2]:
            options = item.get('ratio_options', [])
            for option in options[:1]:
                status, reasons = scenario_display_status(scene, item, option)
                if not reasons and status not in ('보류', '제외'):
                    continue
                add('fault_' + str(item['accident_type']), 'CSV ' + str(item['accident_type']) + '번 적용 조건', status, '내 차 ' + option['a_progress'] + ' / 상대 차 ' + option['b_progress'], reasons or ['차량 역할 또는 진행 조건이 충분히 확인되지 않음'], ' / '.join(reasons) or '해당 유형의 필수 적용 조건', '후보의 기본과실이 확정값이 되지 않으며 가감요소까지 확인한 최종 비율을 의미하지 않음', '기록된 미확인 조건에 답한 뒤 같은 CSV 유형이 유지되는지 재검토', source='CSV 조건 비교·후처리 검증')
    return details

def uncertainty_details(scene, linked):
    details = uncertainty_details_base(scene, linked)
    for item in details:
        if item['field'] in ('a_parking_route', 'b_parking_route'):
            who = item['field'][0].upper()
            reason = scene._evidence_audit.get(who, {}).get('parking_route', {}).get('origin_reason')
            if reason:
                item['reasons'] = list(dict.fromkeys([reason] + item['reasons']))
    if accident_input_confirmed(scene) and scene._evidence_audit.get('contact_user_answer') != '없음':
        for d in details:
            if d['field'] == 'contact':
                d.update(label='직접 접촉 장면의 가시성 (사고 발생은 사용자 확인)', reasons=['사용자 확인으로 사고 발생을 전제하되 직접 접촉을 관찰한 것으로 바꾸지 않음'], impact_on_result='직접 접촉 장면 미확인만으로 비율을 보류하지 않음', next_step='사고 발생 여부를 다시 답할 필요 없음. 진행·상대 차량·접촉 위치를 확인')
    return details

def reference_scenarios_v2151(scene, linked):
    if public_scenarios(scene, linked):
        return []
    if not accident_input_confirmed(scene) or scene._evidence_audit.get('contact_user_answer') == '없음':
        return []
    if scene.road_shape in ('미확인', '기타', '주차장/기타') or not scene.accident_object:
        return []
    context = scene.model_copy(deep=True)
    caveats = []
    for who, label in (('A', '내 차'), ('B', '상대 차')):
        _, support = action_support(scene, who)
        if support.get('status') not in ('observed', 'user'):
            caveats.append(label + '의 진행·도로 위치를 확정하지 못해 아래 조건을 별도로 가정함')
            setattr(context, who.lower() + '_action', '미확인')
            if context._evidence_audit.get(who, {}).get('roundabout_position', {}).get('status') != 'user':
                getattr(context, who.lower() + '_state').roundabout_position = '미확인'
    candidates = []
    soft = soft_actions(scene.a_action, scene.b_action, scene.maneuver_checks)   # 확정은 아니지만 AI 가 기록한 움직임: 후보 순서를 정하는 데만 쓴다
    known_places = {r['accident_place'] for r in ctx.table}
    preferred_places = {int(code) for code in scene.road_place_codes if code in known_places}   # AI 가 가리킨 장소. 표에 없는 번호는 버린다
    for row in ctx.table:
        if row['accident_object_name'] != scene.accident_object or not place_compatible(row, scene):
            continue
        if not mechanism_compatible(row, context):
            continue
        options = []
        for role in ('A', 'B'):
            if not orientation_compatible(row, context, role):
                continue
            if any((c['contradicted'] for c in context_requirements(row, context, role))):
                continue
            a = assess_row(row, context, role)
            if a.get('progress_mismatches'):
                continue
            swap = role == 'B'
            option = {'dashcam_table_role': role, 'a_progress': row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name'], 'b_progress': row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name'], 'a_fault': row['negligence_b' if swap else 'negligence_a'], 'b_fault': row['negligence_a' if swap else 'negligence_b'], 'unconfirmed_conditions': list(dict.fromkeys(a['unresolved_conditions'] + caveats)), 'display_status': '장소 기반 가정별 참고 — 영상 진행과의 대응 미확정'}
            options.append((a, option))
        if options:
            candidates.append((row, options))
    return [{'accident_type': row['accident_type'], 'title': csv_accident_type_details(row)['accident_type_display_name'], 'reference_only': True, 'basis': '관찰 장소·사고 대상에 따른 CSV 비교 시나리오; 적용 유형의 확정 또는 확률 예측 아님', 'ratio_options': chosen} for row, chosen in order_references(candidates, soft, progress_actions, preferred_places)]

def evaluate_rule_input(payload):
    results = []
    for scenario in payload.get('scenarios', []):
        base = scenario['base_fault']
        if any((not isinstance(base[k], int) or not 0 <= base[k] <= 100 for k in ('A', 'B'))) or base['A'] + base['B'] != 100:
            raise ValueError('기본과실은 0~100 정수이며 합계가 100이어야 합니다.')
        result = {'scenario_id': scenario['scenario_id'], 'accident_type': scenario['accident_type'], 'base_fault': dict(base), 'applied_adjustments': [], 'not_applied': [], 'pending': [], 'adjusted_fault': None, 'final_fault': None, 'source': None, 'available_adjustments': []}
        config = ADJUSTMENT_RULES.get(str(scenario['accident_type']))
        if config is None:
            result.update(status='가감 규칙 미등록', reason='해당 유형은 기본과실만 지원합니다. 가감 규칙이 없다는 뜻은 아닙니다.')
            results.append(result)
            continue
        result['source'] = config['source']
        result['coverage'] = config['coverage']
        role = scenario.get('dashcam_table_role')
        result['available_adjustments'] = [{'label': FACTOR_LABELS.get(r['factor'], r['factor']), 'delta_pp': r['delta_pp'], 'table_actor': r['actor']} for r in config['rules']]
        if not scenario.get('eligible_for_adjustment'):
            result.update(status='유형·차량 역할 확인 필요', reason='장소 기반 참고 또는 진행·역할 미확정 시나리오에는 가감산을 적용하지 않습니다.')
            results.append(result)
            continue
        role = scenario['dashcam_table_role']
        mapping = {'A': 'A', 'B': 'B'} if role == 'A' else {'A': 'B', 'B': 'A'}
        expected = dict(zip(('A', 'B'), config['expected_base']))
        if any((base[mapping[k]] != expected[k] for k in ('A', 'B'))) or (scenario['table_progress']['A'] != config['expected_a_progress'] or scenario['table_progress']['B'] != config['expected_b_progress']):
            result.update(status='규칙표와 CSV 불일치', reason='등록된 기준의 진행·기본비율이 현재 CSV와 달라 적용하지 않습니다.')
            results.append(result)
            continue
        facts = {(f['actor'], f['factor']): f for f in payload.get('factors', [])}
        selected = {}
        confirmed_by_group = {}   # 사용자가 '있음'으로 확인한 항목을 그룹별로 모아 둔다 (서로 양립하지 않는 답을 찾는 데 쓴다)
        for rule in config['rules']:
            actor = mapping[rule['actor']]
            fact = facts.get((actor, rule['factor']), {'value': '미확인', 'status': 'unknown'})
            item = {'rule_id': rule['id'], 'actor': actor, 'table_actor': rule['actor'], 'factor': rule['factor'], 'label': FACTOR_LABELS.get(rule['factor'], rule['factor']), 'delta_pp': rule['delta_pp'], 'evidence': fact, 'source': config['source']}
            accepted = fact.get('status') == 'user' or (fact.get('status') == 'observed' and (not rule.get('manual_only')))
            if fact.get('value') == '미확인' or not accepted:
                result['pending'].append(item)
                continue
            if fact['value'] == '없음':
                result['not_applied'].append({**item, 'reason': '해당 요소 없음으로 확인'})
                continue
            if fact['value'] != '있음':
                raise ValueError('가감 요소는 있음/없음/미확인으로 기록하세요.')
            confirmed_by_group.setdefault(rule['group'], []).append(item)
            old = selected.get(rule['group'])
            if old and old['delta_pp'] >= item['delta_pp']:
                result['not_applied'].append({**item, 'reason': '같은 과실 정도 그룹의 상위 항목 적용'})
                continue
            if old:
                result['not_applied'].append({**old, 'reason': '같은 과실 정도 그룹의 상위 항목 적용'})
            selected[rule['group']] = item
        # 같은 exclusive 그룹(예: 서행 불이행 / 서행 또는 일시정지)에서 서로 다른 요소에 모두 '있음'이라고 답했으면 앞뒤가 맞지 않으므로
        # 어느 쪽도 적용하지 않고 다시 확인하게 한다.
        for group in config.get('exclusive_groups', []):
            conflict = confirmed_by_group.get(group, [])
            if len({x['factor'] for x in conflict}) > 1:
                selected.pop(group, None)
                ids = {x['rule_id'] for x in conflict}
                result['not_applied'] = [x for x in result['not_applied'] if x['rule_id'] not in ids]
                result['pending'].extend({**x, 'reason': '서로 양립하지 않는 답변이라 다시 확인이 필요합니다'} for x in conflict)
        if str(scenario['accident_type']) == '1':
            conditional_ids = {r['id'] for r in config['rules'] if r.get('requires_B_adjustment')}
            front_service_actor = mapping['B']
            front_applied = any((x['actor'] == front_service_actor for x in selected.values()))
            front_pending = any((x['actor'] == front_service_actor for x in result['pending']))
            if not front_applied:
                for group, item in list(selected.items()):
                    if item['rule_id'] in conditional_ids:
                        selected.pop(group)
                        target = result['pending'] if front_pending else result['not_applied']
                        target.append({**item, 'reason': '선행차량의 수정요소가 인정되어야 후행차량 요소 적용 가능'})
                if not front_pending:
                    kept = []
                    for item in result['pending']:
                        if item['rule_id'] in conditional_ids:
                            result['not_applied'].append({**item, 'reason': '선행차량 수정요소 없음으로 후행차량 요소 적용 요건 불충족'})
                        else:
                            kept.append(item)
                    result['pending'] = kept
        applied = list(selected.values())
        delta_a = sum((x['delta_pp'] if x['actor'] == 'A' else -x['delta_pp'] for x in applied))
        adjusted_a = max(0, min(100, base['A'] + delta_a))
        result.update(applied_adjustments=applied, adjusted_fault={'A': adjusted_a, 'B': 100 - adjusted_a}, raw_delta_A_pp=delta_a, bounds_applied=adjusted_a != base['A'] + delta_a)
        result['source_review_pending'] = config.get('source_review_pending', [])   # 원문에서 역할·수치가 불분명해 계산에서 뺀 항목
        if result['source_review_pending']:
            result.update(status='확인된 요소만 반영 — 원문 항목 추가 검토 필요', reason='원문에서 역할이나 수치가 불분명한 항목은 계산에서 제외했으므로 최종 비율을 확정하지 않습니다.')
        elif result['pending']:
            result.update(status='확인된 요소만 반영 — 추가 가감 미확인', reason='미확인 요소는 0으로 확정하지 않았습니다.')
        else:
            result.update(status='등록된 가감요소 평가 완료 — 조건부 계산값', final_fault=dict(result['adjusted_fault']), reason='해당 유형·사실·등록 규칙이 맞는 조건의 계산값입니다. 일방과실 예외는 별도 검토 대상입니다.')
        results.append(result)
    return {'engine_version': RULE_ENGINE_VERSION, 'results': results}

def basic_rule_input(scene, linked):
    facts = {}
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    for f in scene.adjustment_observations:
        ids = list(dict.fromkeys(f.evidence_frame_ids))
        valid = len(ids) >= 2 and bool(f.explanation.strip()) and all((original_frame_index(i) is not None and (anchor is None or original_frame_index(i) <= anchor) for i in ids))
        status = 'observed' if valid and f.support == '관찰' else 'inferred' if valid and f.support == '추정' else 'unknown'
        entry = {'actor': f.actor, 'factor': f.factor, 'value': f.value, 'status': status, 'evidence_frame_ids': ids, 'reason': f.explanation, 'source': 'Vision AI 관찰 기록; 독립 검증과 별도'}
        key = (f.actor, f.factor)
        if key in facts and (facts[key]['value'] != entry['value'] or facts[key]['status'] != entry['status']):
            entry.update(value='미확인', status='unknown', reason='동일 요소에 서로 다른 관찰 기록이 있어 확인 필요')
        facts[key] = entry
    for key, value in scene._evidence_audit.get('adjustment_answers', {}).items():
        who, factor = key.split('_factor_', 1)
        facts[who.upper(), factor] = {'actor': who.upper(), 'factor': factor, 'value': value, 'status': 'user' if value != '미확인' else 'unknown', 'evidence_frame_ids': [], 'source': '사용자 확인; 영상 검증과 별도', 'reason': '가감 요소 확인 질문에 대한 사용자 답변'}
    scenarios = []
    for item in linked:
        for n, option in enumerate(item.get('ratio_options', [])[:2]):
            state, reasons = scenario_display_status(scene, item, option)
            if state in ('보류', '제외'):
                continue
            role = option.get('dashcam_table_role')
            actor_checks = option.get('actor_conditions', [])
            eligible = role in ('A', 'B') and item.get('dashcam_table_role') == role and (len(actor_checks) == 2) and all((c.get('relation') == '기본 진행 대응' and c.get('status') in ('observed', 'user', 'inferred') for c in actor_checks))
            row = next((r for r in ctx.table if r['accident_type'] == item['accident_type']))
            scenarios.append({'scenario_id': f"{item['accident_type']}:{role}:{n}", 'accident_type': item['accident_type'], 'dashcam_table_role': role, 'eligible_for_adjustment': eligible, 'base_fault': {'A': option['a_fault'], 'B': option['b_fault']}, 'table_progress': {'A': row['vehicle_a_progress_info_name'], 'B': row['vehicle_b_progress_info_name']}, 'service_progress': {'A': option['a_progress'], 'B': option['b_progress']}, 'scenario_status': state, 'unconfirmed_conditions': reasons})
    return {'schema_version': 'avly-rule-input-v1', 'vehicle_roles': {'A': '블랙박스 차량', 'B': '선택된 사고 상대'}, 'b_vehicle_id': scene.b_vehicle_id, 'b_identity': scene.b_identity, 'road_shape': scene.road_shape, 'accident_object': scene.accident_object, 'scenarios': scenarios, 'factors': list(facts.values()), 'reference_only_scenarios': reference_scenarios(scene, linked)}

def build_rule_input_v2154(scene, linked):
    p = basic_rule_input(scene, linked)
    p['straight_relation'] = straight_audit(scene)
    if not p['scenarios']:
        for ref in p['reference_only_scenarios']:
            row = next((r for r in ctx.table if r['accident_type'] == ref['accident_type']))
            for n, o in enumerate(ref['ratio_options']):
                p['scenarios'].append({'scenario_id': f"reference:{ref['accident_type']}:{n}", 'accident_type': ref['accident_type'], 'dashcam_table_role': o['dashcam_table_role'], 'eligible_for_adjustment': False, 'reference_only': True, 'base_fault': {'A': o['a_fault'], 'B': o['b_fault']}, 'table_progress': {'A': row['vehicle_a_progress_info_name'], 'B': row['vehicle_b_progress_info_name']}, 'service_progress': {'A': o['a_progress'], 'B': o['b_progress']}, 'scenario_status': o['display_status'], 'unconfirmed_conditions': o['unconfirmed_conditions']})
    for scenario in p['scenarios']:
        scenario['calculation_basis'] = '유형·역할 및 가정 조건이 맞는 경우의 조건부 계산'
    return p

def law_rule_bundle_v2152(scene, linked):
    p = build_rule_input(scene, linked)
    key = (p.get('road_shape'), tuple(sorted({x['accident_type'] for x in p['scenarios']})), LAW_ACCIDENT_DATE, LAW_API_ENABLED)
    memo = globals().setdefault('_avly_legal_context_memo', {})
    stored = memo.get(key)
    if stored is None or time.time() - stored[0] >= 86400:
        context = legal_context_for_input(p)
        if context['status'] in ('ok', 'not_mapped', 'disabled'):
            memo[key] = (time.time(), context)
    else:
        context = stored[1]
    p['legal_context'] = context
    out = evaluate_rule_input(p)
    out['legal_context'] = context
    for result in out['results']:
        relevant = LAW_ARTICLES_BY_TYPE.get(result['accident_type'], [])
        result['legal_basis'] = [a for a in context['articles'] if a['article'] in relevant]
        result['legal_lookup_status'] = context['status']
        for section in ('applied_adjustments', 'pending', 'not_applied'):
            for item in result[section]:
                item['legal_references'] = [{'article': a['article'], 'title': a['title'], 'source_url': a['source_url']} for a in result['legal_basis']]
                item['legal_reference_scope'] = '관련 조문 참고; 이 요소의 위반 확정이나 가감 수치 생성 근거와 구분'
    out['legal_api_controls'] = '조문 조회는 근거 첨부이며 가감 수치를 생성하거나 변경하지 않음'
    return {'rule_engine_input': p, 'rule_engine_output': out}

def reference_scenarios_v2172(scene, linked):
    refs = reference_scenarios_v2151(scene, linked)
    if not parking_environment(scene) or public_scenarios(scene, linked) or (not accident_input_confirmed(scene)):
        return refs
    if scene._evidence_audit.get('contact_user_answer') == '없음':
        return refs
    internal = []
    for ref in refs:
        row = next((r for r in ctx.table if r['accident_type'] == ref['accident_type']))
        if '주차구역' in row['vehicle_a_progress_info_name'] + row['vehicle_b_progress_info_name'] or '통로' in row['vehicle_a_progress_info_name'] + row['vehicle_b_progress_info_name']:
            internal.append(ref)
    if internal:
        return internal
    subset = [r for r in ctx.table if r['accident_object_name'] == scene.accident_object and place_compatible(r, scene) and ('통로' in r['vehicle_a_progress_info_name'] + r['vehicle_b_progress_info_name'])]
    candidates = []
    context, _ = matching_context(scene)
    for who in ('A', 'B'):
        progress = context._evidence_audit.get(who, {}).get('progress', {})
        if progress.get('status') not in ('observed', 'user'):
            context._evidence_audit.setdefault(who, {})['progress'] = {'value': '미확인', 'status': 'unknown', 'original_hypothesis': progress.get('value'), 'direct_frame_ids': [], 'linked_frame_ids': [], 'note': '가정별 참고 비교 사본; 원본 정지/회전 추정과 미해결 조건은 별도 보존'}
    for row in subset:
        for role in ('A', 'B'):
            if not orientation_compatible(row, context, role):
                continue
            if any((c['contradicted'] for c in context_requirements(row, context, role))):
                continue
            a = assess_row(row, context, role)
            if a['progress_mismatches']:
                continue
            swap = role == 'B'
            candidates.append((row, a, {'dashcam_table_role': role, 'a_progress': row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name'], 'b_progress': row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name'], 'a_fault': row['negligence_b' if swap else 'negligence_a'], 'b_fault': row['negligence_a' if swap else 'negligence_b'], 'unconfirmed_conditions': list(dict.fromkeys(a['unresolved_conditions'] + ['주차장 통로·출차·사고 직전 진행 조건이 맞는 경우의 가정; 현재 정지/회전 추정을 직진 확정으로 바꾸지 않음'])), 'display_status': '주차장 경로 가정별 참고 — 영상 진행과의 대응 미확정'}))
    if not candidates:
        return refs
    row = min(candidates, key=lambda x: assessment_sort_key(x[1]))[0]
    return [{'accident_type': row['accident_type'], 'title': csv_accident_type_details(row)['accident_type_display_name'], 'reference_only': True, 'basis': '주차장 내부 통로·출차 경로 가정; 실제 사고 유형의 확정 아님', 'ratio_options': [o for r, a, o in candidates if r['accident_type'] == row['accident_type']]}]

def law_rule_bundle_v2161(scene, linked):
    bundle = law_rule_bundle_v2152(scene, linked)
    out = bundle['rule_engine_output']
    cases = []
    for result in out['results']:
        is_parking = result['accident_type'] == 126
        relations = []
        for a in result.get('legal_basis', []):
            relations.append({'article': a['article'], 'paragraph': 3 if is_parking and a['article'] == 18 else None, 'application_mode': '과실 기준에서 준용하는 근거' if is_parking else '관련 참고 조문', 'relevance': '주차구역 출차와 통로 주행 조건이 맞는 경우 차51-1에서 참고하는 조문; 주차장 내부에 직접 적용됐다고 확정하지 않음' if is_parking else '실제 진행·위반 조건과 법령 적용 여부를 별도로 확인해야 함', 'actual_violation_confirmed': False, 'source_url': a['source_url']})
        result['legal_relationships'] = relations
        result['related_cases'] = VERIFIED_CASES.get(result['accident_type'], [])
        for case in result['related_cases']:
            if not any((c['case_number'] == case['case_number'] for c in cases)):
                cases.append(dict(case))
    out['related_cases'] = cases[:3]
    out['related_case_display_limit'] = 3
    return bundle

def compact_fault(value):
    return f"내 차 {value['A']}% / 상대 차 {value['B']}%"

def build_rule_input(scene, linked):
    p = build_rule_input_v2154(scene, linked)
    r = straight_audit(scene)
    lane = scene._evidence_audit.get('B', {}).get('lane_change', {})
    if scene.road_shape == '직선 도로' and r.get('status') in ('observed', 'inferred', 'user') and (r.get('b_position') == '앞') and (r.get('same_direction') == '같은 방향') and (r.get('rear_contact_geometry') == 'inferred' or r.get('mechanism') == '추돌') and any((s['accident_type'] == 1 for s in p['scenarios'])) and (lane.get('status') not in ('observed', 'user')) and (not any((s['accident_type'] == 11 for s in p['scenarios']))):
        row = next((t for t in ctx.table if t['accident_type'] == 11))
        p['scenarios'].append({'scenario_id': 'alternative:11:B_lane_change', 'accident_type': 11, 'dashcam_table_role': 'A', 'eligible_for_adjustment': False, 'reference_only': True, 'base_fault': {'A': row['negligence_a'], 'B': row['negligence_b']}, 'service_progress': {'A': row['vehicle_a_progress_info_name'], 'B': row['vehicle_b_progress_info_name']}, 'table_progress': {'A': row['vehicle_a_progress_info_name'], 'B': row['vehicle_b_progress_info_name']}, 'unconfirmed_conditions': ['상대 차량이 사고 직전 내 차로로 진로변경한 경우에만 비교하는 대안; 차로변경 관찰 확정 아님'], 'calculation_basis': '차로변경 유무에 따른 별도 원인 가정'})
    return p

def law_rule_bundle_v217(scene, linked):
    bundle = law_rule_bundle_v2161(scene, linked)
    out = bundle['rule_engine_output']
    memo = globals().setdefault('_avly_case_memo', {})
    merged = []
    audits = []
    for result in out['results']:
        row = next((r for r in ctx.table if r['accident_type'] == result['accident_type']))
        key = (row['accident_type'], case_profile(row)['text'], CASE_API_ENABLED, 'v2205-civil-claim-context')
        saved = memo.get(key)
        if saved and time.time() - saved[0] < (60 if saved[2]['status'] == 'unavailable' else 86400):
            cases, audit = saved[1:]
        else:
            cases, audit = related_cases_for_row(row)
            memo[key] = (time.time(), cases, audit)
        result['related_cases'] = cases
        result['case_lookup'] = audit
        audits.append(audit)
        for c in cases:
            if not any((re.sub('\\s+', '', x['case_number']) == re.sub('\\s+', '', c['case_number']) for x in merged)):
                merged.append(c)
    out['related_cases'] = merged[:CASE_TARGET_COUNT]
    out['case_lookup'] = audits
    out['case_support_notice'] = '모든 CSV 유형에 검색 로직 제공; 모든 유형에서 검증된3건 확보를 보장하지 않음'
    return bundle

def law_rule_bundle_v2172(scene, linked):
    bundle = law_rule_bundle_v217(scene, linked)
    bundle['rule_engine_output']['registry_coverage'] = {'csv_type_count': len(ctx.table), 'adjustment_registered_types': sorted((int(x) for x in ADJUSTMENT_RULES)), 'case_seed_types': sorted(VERIFIED_CASES), 'dynamic_case_search': '전체 CSV 유형에 제공', 'all_adjustment_types_registered': len(ADJUSTMENT_RULES) == len(ctx.table)}
    return bundle

def reference_scenarios_v2173(scene, linked):
    refs = reference_scenarios_v2172(scene, linked)
    if scene._evidence_audit.get('observed_parking_pattern') and scene.a_action == '정지/대기':
        return [r for r in refs if not any(('통로 직진' in o['a_progress'] for o in r['ratio_options']))]
    return refs

def law_rule_bundle_v2174(scene, linked):
    bundle = law_rule_bundle_v2172(scene, linked)
    out = bundle['rule_engine_output']
    pattern = scene._evidence_audit.get('observed_parking_pattern')
    out['observed_accident_pattern'] = pattern
    if pattern and (not out['results']):
        key = ('parking_reverse_context', CASE_API_ENABLED)
        memo = globals().setdefault('_avly_case_memo', {})
        saved = memo.get(key)
        if saved and time.time() - saved[0] < (60 if saved[2]['status'] == 'unavailable' else 86400):
            cases, audit = saved[1:]
        else:
            row = next((r for r in ctx.table if r['accident_type'] == 127))
            cases, audit = related_cases_for_row(row)
            memo[key] = (time.time(), cases, audit)
        out['related_cases'] = cases
        out['case_lookup'] = [{**audit, 'scope': '후진 접근 형태의 참고 자료; CSV127 적용 확정 아님'}]
    return bundle

def parking_approach_reference(scene):
    if not parking_environment(scene) or scene.accident_object != '차대차' or scene.b_identity != '구별됨':
        return None
    if not accident_input_confirmed(scene) or scene._evidence_audit.get('contact_user_answer') == '없음':
        return None
    if scene._evidence_audit.get('observed_parking_pattern'):
        return None
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    if anchor is None or not ctx.fps or ctx.fps <= 0:
        return None
    audit = scene._evidence_audit
    if audit.get('A', {}).get('progress', {}).get('status') == 'user':
        return None
    if scene.a_action != '정지/대기' or scene.b_action != '직진':
        return None
    route = audit.get('B', {}).get('parking_route', {})
    if route.get('status') == 'user':
        return None
    if route.get('start_zone') == '통로' and route.get('origin_visibility') == '출발 구역부터 연속 관찰':
        return None
    approaching = []
    stopping = []
    for p in scene.parking_motion_phases:
        if p.vehicle != 'A' or p.support == '미확인' or len(set(p.evidence_frame_ids)) < 2 or (not p.fixed_background.strip()):
            continue
        first = original_frame_index(p.first_frame_id)
        last = original_frame_index(p.last_frame_id)
        if first is None or last is None:
            continue
        if p.action == '직진' and 0 <= (anchor - last) / ctx.fps <= 1.0 and (first < last):
            approaching.append(p)
        if p.action == '정지/대기' and 0 <= (anchor - first) / ctx.fps <= 0.7 and (last >= anchor):
            stopping.append(p)
    for moving in approaching:
        for stopped in stopping:
            gap = (original_frame_index(stopped.first_frame_id) - original_frame_index(moving.last_frame_id)) / ctx.fps
            if not 0 <= gap <= 0.4:
                continue
            text = moving.explanation + ' ' + moving.vehicle_orientation + ' ' + moving.fixed_background
            if '통로' not in text:
                continue
            return {'status': 'inferred', 'approach_action': '통로 직진', 'instant_action': scene.a_action, 'approach_frame_ids': moving.evidence_frame_ids, 'stop_frame_ids': stopped.evidence_frame_ids, 'anchor_frame_id': scene.impact_anchor_frame_id, 'stop_before_anchor_seconds': round((anchor - original_frame_index(stopped.first_frame_id)) / ctx.fps, 3), 'note': '관찰된 통로 접근 후 짧은 정지를 보존. 출차 여부·적용 과실은 별도 가정'}
    return None

def reference_scenarios_v2174(scene, linked):
    refs = reference_scenarios_v2173(scene, linked)
    if refs or public_scenarios(scene, linked):
        return refs
    approach = parking_approach_reference(scene)
    if not approach:
        return refs
    scene._evidence_audit['parking_approach_reference'] = approach
    row = next((r for r in ctx.table if r['accident_type'] == 126))
    if row['accident_object_name'] != scene.accident_object or not place_compatible(row, scene):
        return refs
    conditions = ['내 차는 통로 접근 후 충돌 직전 짧게 정지한 것으로 기록됨; 정지를 직진 확정으로 변경하지 않음', '상대 차가 주차구역에서 전진 출차한 경우에만 CSV126 비교 가능; 현재 영상에서 출차는 미확인', '상대 차도 다른 통로를 주행한 사고라면 이 출차 기준을 그대로 적용할 수 없음']
    return [{'accident_type': 126, 'title': csv_accident_type_details(row)['accident_type_display_name'], 'reference_only': True, 'basis': '통로 접근 기록과 미확인 출차 조건을 구분한 조건별 비교', 'approach_context': approach, 'ratio_options': [{'dashcam_table_role': 'A', 'a_progress': row['vehicle_a_progress_info_name'], 'b_progress': row['vehicle_b_progress_info_name'], 'a_fault': row['negligence_a'], 'b_fault': row['negligence_b'], 'unconfirmed_conditions': conditions, 'display_status': '출차 조건을 가정한 기본 참고값; 실제 적용 미확정'}]}]

def exploratory_csv_references(scene, linked):
    if public_scenarios(scene, linked) or not accident_input_confirmed(scene):
        return []
    if scene._evidence_audit.get('contact_user_answer') == '없음':
        return []
    if scene.accident_object != '차대차' or scene.b_identity != '구별됨':
        return []
    if scene._evidence_audit.get('observed_parking_pattern'):
        return []
    ranked = []
    for row in ctx.table:
        if row['accident_object_name'] != '차대차' or not place_compatible(row, scene) or (not mechanism_compatible(row, scene)):
            continue
        options = []
        for role in ('A', 'B'):
            comparison = scene.model_copy(deep=True)
            for who in ('A', 'B'):
                actor = scene._evidence_audit.get(who, {})
                if actor.get('progress', {}).get('status') != 'user':
                    setattr(comparison, who.lower() + '_action', '미확인')
                if actor.get('lane_change', {}).get('status') != 'user':
                    getattr(comparison, who.lower() + '_state').lane_change = '미확인'
            if not orientation_compatible(row, comparison, role):
                continue
            if any((c['contradicted'] for c in context_requirements(row, scene, role))):
                continue
            swap = role == 'B'
            a = assess_row(row, scene, role)
            ap = row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name']
            bp = row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name']
            blocked = False
            for who, expected in [('A', ap), ('B', bp)]:
                status = scene._evidence_audit.get(who, {}).get('progress', {}).get('status')
                choices = progress_actions(expected)
                if status == 'user' and choices and (getattr(scene, who.lower() + '_action') not in choices):
                    blocked = True
            if blocked:
                continue
            conflicts = list(a.get('progress_mismatches', []))
            conditions = ['탐색용 조건 비교이며 현재 영상에 적용된 사고 유형이 아님', '내 차 ' + ap + ' / 상대 차 ' + bp + ' 조건이 실제와 맞는 경우에만 아래 비율을 참고']
            if conflicts:
                conditions.append('현재 관찰과 진행 불일치: ' + str(conflicts))
            else:
                conditions += a.get('unresolved_conditions', [])
            options.append((len(conflicts), a, {'dashcam_table_role': role, 'a_progress': ap, 'b_progress': bp, 'a_fault': row['negligence_b' if swap else 'negligence_a'], 'b_fault': row['negligence_a' if swap else 'negligence_b'], 'unconfirmed_conditions': list(dict.fromkeys(conditions)), 'display_status': '탐색용 조건 비교 · 적용 유형 미확정'}))
        if options:
            options.sort(key=lambda x: (x[0], assessment_sort_key(x[1])))
            score = (options[0][0], assessment_sort_key(options[0][1]), row['accident_type'])
            ranked.append((score, row, options))
    ranked.sort(key=lambda x: x[0])
    refs = []
    for score, row, options in ranked[:2]:
        refs.append({'accident_type': row['accident_type'], 'title': csv_accident_type_details(row)['accident_type_display_name'], 'reference_only': True, 'basis': '동일 관찰 장소·차대차 CSV의 제한된 탐색 비교; 정확도·확률 점수 아님', 'ratio_options': [options[0][2]]})
    return refs

def reference_scenarios_v219(scene, linked):
    if not scene.b_vehicle_id or scene.b_identity != '구별됨':
        return []
    refs = reference_scenarios_v2174(scene, linked)
    return refs or exploratory_csv_references(scene, linked)

def law_rule_bundle_v218(scene, linked):
    bundle = law_rule_bundle_v2174(scene, linked)
    payload, out = (bundle['rule_engine_input'], bundle['rule_engine_output'])
    byid = {s['scenario_id']: s for s in payload['scenarios']}
    for result in out['results']:
        scenario = byid[result['scenario_id']]
        result['conditional_projection'] = None
        if not scenario.get('reference_only') or not ADJUSTMENT_RULES.get(str(result['accident_type'])):
            continue
        assumed = json.loads(json.dumps(scenario))
        assumed['eligible_for_adjustment'] = True
        calculation = evaluate_rule_input({**payload, 'scenarios': [assumed]})['results'][0]
        result['conditional_projection'] = {'scope': '사고 유형·역할을 가정한 별도 계산; 영상 적용 확정값 아님', 'assumptions': scenario.get('unconfirmed_conditions', []), 'adjusted_fault': calculation['adjusted_fault'], 'applied_adjustments': calculation['applied_adjustments'], 'pending': calculation['pending'], 'not_applied': calculation['not_applied'], 'all_registered_factors_resolved': calculation['final_fault'] is not None, 'status': calculation['status'], 'source': calculation['source']}
    return bundle

def law_rule_bundle(scene, linked):
    bundle = law_rule_bundle_v218(scene, linked)
    out = bundle['rule_engine_output']
    seen = set()
    lookups = []
    for audit in out.get('case_lookup', []):
        key = (audit.get('accident_type'), audit.get('status'), audit.get('reason'))
        if key not in seen:
            seen.add(key)
            lookups.append(audit)
    out['case_lookup'] = lookups
    return bundle

def reference_scenarios(scene, linked):
    refs = reference_scenarios_v219(scene, linked)
    result = []
    for item in refs:
        row = next((r for r in ctx.table if r['accident_type'] == item['accident_type']))
        options = [o for o in item['ratio_options'] if not strict_user_conflicts(row, scene, o['dashcam_table_role'])]
        if options:
            result.append({**item, 'ratio_options': options})
    return result

law_rule_bundle_before_case_guard = law_rule_bundle

def law_rule_bundle(scene,linked):
    return sanitize_case_bundle(law_rule_bundle_before_case_guard(scene,linked))
