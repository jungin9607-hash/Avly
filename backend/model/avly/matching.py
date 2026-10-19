"""CSV 과실표와 비교해 후보를 고르고 연결."""
import re
from .tables import SPECIAL_LABELS, SUPPORT_LABELS
from .context import ctx
from .schemas import Candidate
from .facts import action_support, original_frame_index, parking_environment, preimpact_ids, progress_actions, straight_audit


def orientation_compatible_v291(row, scene, role):
    if not mechanism_compatible(row, scene) or not special_requirements_met(row, scene, role):
        return False
    sig = scene.signal_check
    feature = str(row.get('accident_place_feature_name', ''))
    signal_free = bool(re.search('신호등\\\\s*없음|신호기\\\\s*없음|신호등\\\\s*없는|신호기\\\\s*없는|무신호', feature))
    if signal_free and sig.signal_present == '있음' and (sig.signal_operating == '정상 작동'):
        return False
    swap = role == 'B'
    for action, state, text in ((scene.a_action, scene.a_state, row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name']), (scene.b_action, scene.b_state, row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name'])):
        choices = progress_actions(text)
        if state.lane_change == '없음' and '진로변경' in choices:
            return False
        if action not in ('미확인', '기타') and choices and (action not in choices):
            return False
    return True

def matching_context(scene):
    context = scene.model_copy(deep=True)
    notes = []
    if scene.road_shape == '회전교차로' and len(scene.road_shape_evidence_frame_ids) >= 2:
        for who, field in (('A', 'a_action'), ('B', 'b_action')):
            if getattr(scene, field) == '직진':
                setattr(context, field, '미확인')
                notes.append(f'{who} 관찰은 직진이나 회전교차로 진입/내부 진행 대응은 미확인. 표 역할은 가정으로 비교')
    for who in ('A', 'B'):
        action = getattr(context, who.lower() + '_action')
        field, support = action_support(scene, who)
        if support and support.get('status') not in ('observed', 'user'):
            setattr(context, who.lower() + '_action', '미확인')
            notes.append(f"{who}의 진행은 {support.get('status')} 상태: 검색에서 확정 조건으로 사용하지 않음")
        lane_support = scene._evidence_audit.get(who, {}).get('lane_change', {})
        if lane_support and lane_support.get('status') not in ('observed', 'user'):
            getattr(context, who.lower() + '_state').lane_change = '미확인'
    context.observation_issues = list(dict.fromkeys(context.observation_issues + notes))
    return (context, notes)

def conditional_candidates(rows, scene):
    if scene.b_vehicle_id is None or scene.b_identity != '구별됨' or len(scene.road_shape_evidence_frame_ids) < 2:
        return []
    candidates = []
    for row in sorted(rows, key=lambda r: best_row_key(r, scene)):
        allowed, _ = candidate_eligibility(row, scene)
        if not allowed:
            continue
        assessments = row_assessment(row, scene)
        if not assessments:
            continue
        best = assessments[0]
        if best['progress_agreement_count'] != 2 or best['progress_mismatch_count']:
            continue
        if not special_requirements_met(row, scene, best['role']):
            continue
        roles = [x['role'] for x in assessments if x['progress_agreement_count'] == 2 and (not x['progress_mismatch_count']) and special_requirements_met(row, scene, x['role'])]
        role = roles[0] if len(roles) == 1 else '미확인'
        swap = role == 'B'
        candidates.append(Candidate(accident_type=row['accident_type'], dashcam_table_role=role, common_observed_facts=['두 차량의 진행 조건을 비교한 후보'], assumed_conditions=['사용자 사고 상황 확인 전 후보'], a_role_evidence='관찰·사용자 답변과 표 조건 비교', b_role_evidence='관찰·사용자 답변과 표 조건 비교', mapped_a_progress=row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name'], mapped_b_progress=row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name'], a_evidence_frame_ids=list(scene.a_pre_frame_ids), b_evidence_frame_ids=list(scene.b_pre_frame_ids), a_condition_status='가정', b_condition_status='가정', reason='두 차량 진행 및 핵심 조건과 양립하는 후보. 비율 표시 여부는 별도 검증.'))
        if len(candidates) == 2:
            break
    return candidates

def role_validation_v212(candidate, row, scene):
    issues = []
    role = candidate.dashcam_table_role
    if role == '미확인':
        return ['표의 A/B 역할 대응 미확인']
    if scene.a_action == '미확인' and scene.b_action == '미확인':
        issues.append('A/B 진행 역할의 관찰 또는 사용자 답변 근거가 없어 단일 역할을 선택할 수 없음')
    swap = role == 'B'
    expected_a = row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name']
    expected_b = row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name']
    canon = lambda text: re.sub('\\s+', '', text)
    if canon(candidate.mapped_a_progress) != canon(expected_a) or canon(candidate.mapped_b_progress) != canon(expected_b):
        issues.append('선택한 표 역할과 모델이 연결한 A/B 진행 문구 불일치')
    for who, action, expected, evidence, explanation, status in (('A', scene.a_action, expected_a, candidate.a_evidence_frame_ids, candidate.a_role_evidence, candidate.a_condition_status), ('B', scene.b_action, expected_b, candidate.b_evidence_frame_ids, candidate.b_role_evidence, candidate.b_condition_status)):
        allowed = set(scene.a_pre_frame_ids if who == 'A' else scene.b_pre_frame_ids)
        if any((f not in allowed for f in evidence)):
            issues.append(f'{who} 진행 근거가 검토된 사고 직전 프레임에 없음')
        if status == '관찰됨' and (not evidence or not explanation.strip()):
            issues.append(f'{who} 진행을 관찰했다고 했지만 근거가 비어 있음')
        if status == '관찰됨' and action == '미확인':
            issues.append(f'{who} 행동이 미확인인데 후보에서 관찰됨으로 표시함')
        compatible = progress_actions(expected)
        if action not in ('미확인', '기타') and compatible and (action not in compatible):
            issues.append(f'{who} 사고 직전 행동({action})이 표의 진행({expected})과 모순')
    return issues

def assess_row_base(row, scene, role):
    checks, points, assumptions = ([], 0.0, 0)
    mismatches, agreements, unresolved = ([], [], [])
    route_actions = {'진입': '교차로 진입', '내부 회전': '교차로 내 회전', '진입 전 대기': '정지/대기'}
    for who in ('A', 'B'):
        swap = role == 'B'
        table_who = ('B' if who == 'A' else 'A') if swap else who
        expected = row[f'vehicle_{table_who.lower()}_progress_info_name']
        choices = progress_actions(expected)
        action = getattr(scene, who.lower() + '_action')
        state = getattr(scene, who.lower() + '_state')
        field, evidence = action_support(scene, who, choices)
        geometry = evidence.get('geometry_check', {}) if field == 'roundabout_position' else {}
        if geometry.get('valid') and evidence.get('status') in ('unknown', 'conflicted'):
            evidence = {**evidence, 'status': 'inferred', 'value': geometry['recorded_transition_route'], 'direct_frame_ids': [], 'linked_frame_ids': geometry.get('frame_ids', []), 'sources': ['도로 기준 위치 가설 (기존 상태 설명과의 모순은 미해결)']}
        status = 'unknown'
        hypothesis = evidence.get('value') if field == 'progress' else ('진로변경' if evidence.get('value', state.lane_change) == '있음' else None) if field == 'lane_change' else route_actions.get(evidence.get('value', state.roundabout_position))
        evidence_status = evidence.get('status', 'unknown')
        reference = action if action not in ('미확인', '기타') else hypothesis
        relation = '미확인'
        if reference and choices:
            if reference in choices and (action not in ('미확인', '기타') or evidence_status in ('observed', 'user', 'inferred')):
                relation = '기본 진행 대응'
                agreements.append(f'{who}: {reference}가 표의 기본 진행과 대응 (세부 조건은 별도)')
            elif reference not in choices and evidence_status in ('observed', 'user', 'inferred'):
                relation = '추정과 불일치' if evidence_status == 'inferred' else '확인된 진행과 불일치'
                mismatches.append(f'{who}의 현재 진행은 {reference}이나 이 표는 {expected}를 요구함')
            elif evidence_status == 'conflicted':
                relation = '관찰 자체가 상충됨'
                unresolved.append(f'{who} 진행 관찰이 상충되어 표와의 대응을 판단하기 어려움')
        if action not in ('미확인', '기타') and action in choices:
            status = evidence.get('status', 'observed')
        elif hypothesis in choices and evidence.get('status') in ('observed', 'user', 'inferred', 'conflicted'):
            status = evidence['status']
        points += {'user': 4, 'observed': 4, 'inferred': 2, 'conflicted': 0.5}.get(status, 0)
        if status not in ('observed', 'user'):
            assumptions += 1
        if relation == '미확인':
            unresolved.append(f"{who}의 '{expected}' 진행 조건은 미확인: 추가 가정이 필요함")
        checks.append({'field': who.lower() + '_progress', 'expected': expected, 'status': status, 'state_value': getattr(state, field, action), 'frame_ids': evidence.get('direct_frame_ids', []) + evidence.get('linked_frame_ids', []), 'sources': evidence.get('sources', []), 'conflicts': evidence.get('conflicts', []), 'relation': relation, 'reference_action': reference, 'route_hypotheses': evidence.get('route_hypotheses', [])})
        if geometry.get('valid') and (not geometry.get('accepted')):
            unresolved.append(f"{who}의 기존 {geometry['original_route']} 판단과 도로 기준 {geometry['recorded_transition_route']} 가설이 다름: 추가 확인 필요")
        if re.search('[12]차로|대진입|신호', expected):
            assumptions += 1
            details = []
            if re.search('[12]차로', expected):
                details.append('차로 위치·이동 경로')
            if '대진입' in expected:
                details.append('표의 대진입 조건')
            if '신호' in expected:
                details.append('신호 조건')
            detail_note = f"{who}의 '{expected}'에 포함된 {' / '.join(details)} 확인 필요"
            unresolved.append(detail_note)
            checks.append({'field': who.lower() + '_specific_condition', 'expected': expected, 'status': 'unknown', 'note': detail_note})
    place_matches = place_compatible(row, scene)
    points += 2 if place_matches else 0
    checks.append({'field': 'place', 'expected': row['accident_place_name'], 'status': 'observed' if place_matches and len(scene.road_shape_evidence_frame_ids) >= 2 else 'unknown'})
    if row['accident_place_name'] == '회전교차로':
        expected_lanes = '1차로' if '1차로형' in row['accident_place_feature_name'] else '2차로 이상'
        support = scene._evidence_audit.get('lane_count', {})
        matches = scene.roundabout_lane_count == expected_lanes
        lane_status = support.get('status', 'inferred') if matches else 'unknown'
        points += 1 if matches else 0
        if lane_status != 'user':
            assumptions += 1
            unresolved.append(f'이 표의 {expected_lanes} 회전차로 조건 확인 필요')
        checks.append({'field': 'lane_count', 'expected': expected_lanes, 'status': lane_status, 'observed_value': scene.roundabout_lane_count, 'note': '차로 수가 모델 추정이면 다른 차로형의 표도 조건부 비교'})
    required = special_requirement_checks(row, scene, role)
    checks.extend(required)
    for check in required:
        if check['status'] not in ('observed', 'user') or check['value'] != '있음':
            assumptions += 1
            unresolved.append(check['note'])
    return {'role': role, 'score': points - 0.5 * assumptions, 'assumption_count': assumptions, 'progress_mismatch_count': len(mismatches), 'progress_agreement_count': len(agreements), 'progress_mismatches': mismatches, 'progress_agreements': agreements, 'unresolved_conditions': list(dict.fromkeys(unresolved)), 'checks': checks, 'score_notice': '후보 정렬 점수이며 확률이 아님'}

def assessment_sort_key(item):
    return (item['progress_mismatch_count'], -item['score'], item['assumption_count'])

def scenario_description(assessment):
    if assessment['progress_mismatch_count']:
        return '현재 진행 추정과 다른 조건을 가정한 대안'
    count = assessment['progress_agreement_count']
    if count == 2:
        return 'A/B 기본 진행 모두 대응 — 세부 조건은 별도 확인'
    if count == 1:
        return '한 차량의 기본 진행만 대응 — 다른 차량 조건은 추가 가정'
    return 'A/B 진행 대응 미확인 시나리오'

def row_assessment(row, scene):
    alternatives = [assess_row(row, scene, role) for role in ('A', 'B') if orientation_compatible(row, scene, role)]
    return sorted(alternatives, key=assessment_sort_key)

def csv_accident_type_details(row, table_role='미확인'):
    swap = table_role == 'B'
    a_progress = row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name']
    b_progress = row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name']
    place = str(row.get('accident_place_name', '')).strip()
    feature = str(row.get('accident_place_feature_name', '')).strip()
    obj = str(row.get('accident_object_name', '')).strip()
    parts = [x for x in (place, feature) if x and x.lower() != 'nan']
    display_name = ' / '.join(dict.fromkeys(parts)) or '사고 유형 명칭 확인 필요'
    return {'accident_type_id': row['accident_type'], 'accident_type_display_name': display_name, 'accident_type_title_kind': 'CSV 장소·특징으로 구성한 설명형 제목 (공식 유형명 아님)', 'accident_object': obj, 'accident_place': place, 'accident_place_feature': feature, 'dashcam_table_role': table_role, 'dashcam_progress_condition': a_progress, 'other_vehicle_progress_condition': b_progress, 'source': 'fault_table.csv'}

def link_match(candidate, row, scene):
    conditions = ['추가 가정(모델 제안, 영상 확인 아님): ' + text for text in candidate.assumed_conditions]
    if scene.contact != '접촉 관찰':
        conditions.append('추정 접촉 상대와 실제 접촉했는지 확인 필요')
    if scene.b_identity != '구별됨' or scene.b_vehicle_id is None:
        conditions.append('B의 차량 동일성 및 접촉 상대 지정 확인 필요')
    role = candidate.dashcam_table_role
    issues = role_validation(candidate, row, scene)
    if issues:
        role = '미확인'
        conditions.extend(issues)
    if scene.b_vehicle_id is None or scene.accident_object is None or scene.b_identity != '구별됨':
        role = '미확인'
    options = []
    supported_roles = [r for r in ('A', 'B') if orientation_compatible(row, scene, r)]
    assessments = row_assessment(row, scene)
    supported_roles = [item['role'] for item in assessments]
    for table_role in [role] if role != '미확인' else supported_roles:
        swap = table_role == 'B'
        options.append({'dashcam_table_role': table_role, 'a_progress': row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name'], 'b_progress': row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name'], 'a_fault': row['negligence_b' if swap else 'negligence_a'], 'b_fault': row['negligence_a' if swap else 'negligence_b']})
        options[-1]['basis'] = assess_row(row, scene, table_role)['checks']
        assessment = assess_row(row, scene, table_role)
        options[-1]['progress_mismatches'] = assessment['progress_mismatches']
        options[-1]['unresolved_conditions'] = assessment['unresolved_conditions']
        options[-1]['required_condition_checks'] = special_requirement_checks(row, scene, table_role)
        options[-1]['scenario_relation'] = scenario_description(assessment)
        options[-1]['actor_conditions'] = [check for check in assessment['checks'] if check['field'] in ('a_progress', 'b_progress')]
    explanation = ' / '.join((f"A가 {o['a_progress']}, B가 {o['b_progress']}인 경우" for o in options))
    best = assessments[0]
    differences = best['progress_mismatches']
    required_conditions = best['unresolved_conditions']
    conditions = differences + required_conditions + conditions
    basis_summary = scenario_description(best) + '. '
    if differences:
        basis_summary += ' / '.join(differences) + '. '
    else:
        actor_notes = []
        for check in best['checks']:
            if check['field'] not in ('a_progress', 'b_progress'):
                continue
            who = check['field'][0].upper()
            if check['relation'] == '기본 진행 대응':
                actor_notes.append(f"{who}의 {check['reference_action']}은 대응 ({SUPPORT_LABELS.get(check['status'], '근거 부족')})")
            else:
                actor_notes.append(f"{who}의 {check['expected']} 조건은 {check['relation']}")
        basis_summary += ' / '.join(actor_notes) + '. '
    observed_facts = [f'관찰 장소: {scene.road_shape}'] if scene.road_shape != '미확인' and len(scene.road_shape_evidence_frame_ids) >= 2 else []
    hypotheses = list(dict.fromkeys(conditions + [explanation]))
    if role == '미확인':
        conditions.append('CSV A/B 진행 역할 대응 확인 필요')
    if scene.a_action == '미확인':
        conditions.append('사고 직전 A의 도로상 진행 미확인')
    if scene.b_action == '미확인':
        conditions.append('사고 직전 B의 도로상 진행 미확인')
    for who, status in (('A', candidate.a_condition_status), ('B', candidate.b_condition_status)):
        if status != '관찰됨':
            conditions.append(f'{who}의 표 진행 조건은 {status} 상태')
    conditions.extend(scene.observation_issues)
    csv_type = csv_accident_type_details(row, role)
    return {**candidate.model_dump(), **csv_type, 'csv_accident_type': csv_type, 'dashcam_table_role': role, 'validation_issues': issues, 'common_observed_facts': observed_facts, 'assumed_conditions': hypotheses, 'assessment': assessments, 'ranking_basis': {'progress_agreements': best['progress_agreements'], 'progress_mismatches': differences, 'unresolved_conditions': required_conditions, 'notice': '진행 불일치 수를 먼저 비교하고 근거 점수·가정 수로 정렬. 확률 아님'}, 'model_reason': candidate.reason, 'reason': basis_summary + explanation + '의 CSV 기본 비율입니다. 진행·차로 조건이 미확인인 부분은 가정입니다.', 'place': row['accident_place_name'], 'feature': row['accident_place_feature_name'], 'conditions': list(dict.fromkeys(conditions)), 'ratio_options': options, 'label': '진행 추정과 차이 있음 — 대안 시나리오' if differences else '일부 진행만 대응 — 추가 가정 시나리오' if best['progress_agreement_count'] == 1 else '역할 검증 미완료 — 유사표 시나리오' if issues else '조건부 예상' if conditions else '관찰상 대응하는 기본값', 'source': 'CSV 기본값 / 가감산 미적용'}

def prepare_matches_v292(match, rows, scene):
    by_id = {r['accident_type']: r for r in rows}
    selected, rejected, seen = ([], [], set())
    for candidate in match.candidates:
        row = by_id.get(candidate.accident_type)
        if row is None or candidate.accident_type in seen:
            rejected.append({'id': candidate.accident_type, 'reason': 'CSV에 없는 ID 또는 중복'})
            continue
        seen.add(candidate.accident_type)
        allowed, reasons = candidate_eligibility(row, scene)
        if not allowed:
            rejected.append({'id': candidate.accident_type, 'reason': ' / '.join(reasons)})
            continue
        selected.append(candidate)
        if len(selected) == 2:
            break
    if not selected:
        selected = conditional_candidates(rows, scene)
    match.candidates = selected
    if not selected and (not match.no_match_reason):
        match.no_match_reason = '전체 CSV를 비교했으나 사고 장소·대상·진행 및 필수조건과 양립하는 유형을 선택하지 못했습니다.'
    return rejected

def special_requirement_checks(row, scene, role):
    result = []

    def requirements(text):
        names = []
        if '중앙선' in text:
            names.append('centerline_crossing')
        if re.search('역주행|역방향', text):
            names.append('wrong_way')
        if '추월' in text:
            names.append('overtaking')
        if re.search('마주보|교행|대향', text):
            names.append('opposing_travel')
        return names
    assigned = set()
    for who in ('A', 'B'):
        table_who = ('B' if who == 'A' else 'A') if role == 'B' else who
        for name in requirements(str(row.get(f'vehicle_{table_who.lower()}_progress_info_name', ''))):
            assigned.add(name)
            result.append(condition_record(scene, who, name))
    for name in requirements(str(row.get('accident_place_feature_name', row.get('feature', '')))):
        if name not in assigned:
            options = [condition_record(scene, who, name) for who in ('A', 'B')]
            accepted = [x for x in options if x['value'] == '있음' and x['status'] in ('observed', 'user')]
            result.append(accepted[0] if accepted else {'field': 'either_' + name, 'condition': name, 'vehicle': 'A/B', 'status': 'unknown', 'value': '미확인', 'note': SPECIAL_LABELS[name] + ' 조건 확인 필요'})
    return result

def condition_record(scene, who, name):
    item = scene._evidence_audit.get(who, {}).get(name, {})
    return {'field': who.lower() + '_' + name, 'vehicle': who, 'condition': name, 'value': item.get('value', '미확인'), 'status': item.get('status', 'unknown'), 'note': f'{who}의 {SPECIAL_LABELS[name]} 조건 확인 필요', 'frame_ids': item.get('frame_ids', [])}

def mechanism_compatible_v284(row, scene):
    return mechanism_compatible_base(row, scene) and any((special_requirements_met(row, scene, role) for role in ('A', 'B')))

def place_compatible_v219(row, scene):
    place = str(row.get('accident_place_name', ''))
    if parking_environment(scene):
        return '주차장' in place or '차도가 아닌' in place or '노외' in place
    if scene.road_shape == '교차로':
        return '교차로' in place and '회전교차로' not in place
    if scene.road_shape in ('직선 도로', '회전교차로'):
        return place == scene.road_shape
    return row.get('accident_place') in scene.road_place_codes

def mechanism_compatible_v212(row, scene):
    if not mechanism_compatible_v284(row, scene):
        return False
    return True

def assess_row_v291(row, scene, role):
    assessment = assess_row_base(row, scene, role)
    known = set()
    for who in ('A', 'B'):
        table_who = ('B' if who == 'A' else 'A') if role == 'B' else who
        expected = row[f'vehicle_{table_who.lower()}_progress_info_name']
        if '신호' not in expected:
            continue
        colors = [color for color in ('녹색', '황색', '적색') if color in expected]
        sig = scene.signal_check
        users = scene._evidence_audit.get('signal_user_answers', {})
        key = who.lower() + '_signal'
        supported = users.get(key) == getattr(sig, key) or len(set(sig.evidence_frame_ids)) >= 2
        if len(colors) == 1 and getattr(sig, key) == colors[0] and supported:
            known.add(who.lower() + '_specific_condition')
    removed = [check['note'] for check in assessment['checks'] if check.get('field') in known and '신호 조건' in check.get('note', '') and (not re.search('[12]차로|대진입', check.get('expected', '')))]
    for check in assessment['checks']:
        if check.get('note') in removed:
            check['status'] = 'user' if scene._evidence_audit.get('signal_user_answers') else 'observed'
    assessment['unresolved_conditions'] = [x for x in assessment['unresolved_conditions'] if x not in removed]
    assessment['assumption_count'] -= len(removed)
    assessment['score'] += 0.5 * len(removed)
    return assessment

def search_rows(scene):
    return list(ctx.table)

def candidate_eligibility(row, scene):
    reasons = []
    if scene.accident_object and row.get('accident_object_name') != scene.accident_object:
        reasons.append('사고 대상 종류가 다름')
    if scene.road_shape not in ('미확인', '기타') and len(scene.road_shape_evidence_frame_ids) >= 2 and (not place_compatible(row, scene)):
        reasons.append('관찰 장소와 유형 장소가 다름')
    if not any((orientation_compatible(row, scene, role) for role in ('A', 'B'))):
        reasons.append('차량 진행 또는 중앙선·역주행 등 필수조건이 맞지 않음')
    return (not reasons, reasons)

def best_row_key(row, scene):
    allowed, _ = candidate_eligibility(row, scene)
    assessments = row_assessment(row, scene)
    return (0 if allowed else 1, *assessment_sort_key(assessments[0])) if assessments else (1, 99, 100, 99)

def compare_all_csv_rows(rows, scene):
    audit = []
    for row in rows:
        allowed, reasons = candidate_eligibility(row, scene)
        roles = [assess_row(row, scene, role) for role in ('A', 'B')]
        audit.append({'id': row['accident_type'], 'eligible_for_candidate': allowed, 'blocking_reasons': reasons, 'roles': sorted(roles, key=assessment_sort_key)})
    return audit

def mechanism_compatible_base(row, scene):
    feature = str(row.get('accident_place_feature_name', ''))
    progress = ' '.join((str(row.get(k, '')) for k in ('vehicle_a_progress_info_name', 'vehicle_b_progress_info_name')))
    text = feature + ' ' + progress
    evidence = scene._evidence_audit.get('collision_pattern', {})
    user = evidence.get('status') == 'user'
    value = evidence.get('value', '미확인')
    if re.search('1차\\s*사고|선행\\s*자동차\\(1차', text) and (not evidence.get('prior_accident_evidence')):
        return False
    stationary_required = any((re.search('주\\(정\\)차|주정차|주차\\s*중|정차\\s*중', str(row.get(k, ''))) for k in ('vehicle_a_progress_info_name', 'vehicle_b_progress_info_name')))
    if stationary_required and (not evidence.get('parked_evidence')) and (not (user and value == '주정차 차량 충돌')):
        return False
    if '추돌' in text:
        if not evidence.get('rear_evidence') and (not (user and value in ('후행 추돌', '주정차 차량 충돌'))):
            return False
        if user and value == '교차 진행/측면 접근':
            return False
        if evidence.get('crossing_evidence') and (not evidence.get('rear_evidence')):
            return False
    return True

def parking_requirements(row, scene, role):
    checks = []
    for who in ('A', 'B'):
        table_who = ('B' if who == 'A' else 'A') if role == 'B' else who
        text = str(row.get(f'vehicle_{table_who.lower()}_progress_info_name', '')).replace('출자', '출차')
        if '주차구역' in text and '출차' in text:
            expected = ('주차구역', '통로')
            note = f"{('내 차' if who == 'A' else '상대 차')}가 주차구역에서 통로로 출차했는지 확인 필요"
        elif '통로' in text and ('직진' in text or '전진' in text):
            expected = ('통로', None)
            note = f"{('내 차' if who == 'A' else '상대 차')}가 주차장 통로를 주행했는지 확인 필요"
        else:
            continue
        observed = scene._evidence_audit.get(who, {}).get('parking_route', {})
        matches = observed.get('start_zone') == expected[0] and (expected[1] is None or observed.get('end_zone') == expected[1])
        contradicted = observed.get('status') in ('observed', 'user') and (observed.get('start_zone', '미확인') not in ('미확인', expected[0]) or (expected[1] is not None and observed.get('end_zone', '미확인') not in ('미확인', expected[1])))
        checks.append({'field': who.lower() + '_parking_route', 'status': observed.get('status', 'unknown') if matches else 'unknown', 'matches': matches, 'contradicted': contradicted, 'note': note, 'frame_ids': observed.get('frame_ids', [])})
    return checks

def assess_row_v292(row, scene, role):
    result = assess_row_v291(row, scene, role)
    for check in parking_requirements(row, scene, role):
        result['checks'].append(check)
        if check['status'] not in ('observed', 'user'):
            result['unresolved_conditions'].append(check['note'])
            result['assumption_count'] += 1
            result['score'] -= 0.5
    result['unresolved_conditions'] = list(dict.fromkeys(result['unresolved_conditions']))
    return result

def orientation_compatible_v212(row, scene, role):
    return orientation_compatible_v291(row, scene, role) and (not any((x['contradicted'] for x in parking_requirements(row, scene, role))))

def special_requirements_met(row, scene, role):
    for check in special_requirement_checks(row, scene, role):
        if check['condition'] == 'opposing_travel':
            if check['status'] in ('observed', 'user') and check['value'] == '없음':
                return False
        elif check['value'] != '있음' or check['status'] not in ('observed', 'user'):
            return False
    return True

def context_requirements_v219(row, scene, role):
    checks = []
    answers = scene._evidence_audit.get('context_answers', {})

    def add(key, expected, note):
        value = answers.get(key, '미확인')
        checks.append({'field': key, 'expected': expected, 'status': 'user' if value == expected else 'unknown', 'contradicted': value not in ('미확인', expected), 'note': note})
    feature = str(row.get('accident_place_feature_name', ''))
    place = str(row.get('accident_place_name', ''))
    if '동일폭' in feature:
        add('road_width_relation', '동일폭', '두 진입 도로가 동일폭이라는 조건 확인 필요')
    if '신호등 없음' in place:
        present = scene.signal_check.signal_present
        text = scene.road_evidence
        conflicting = present == '없음' and '신호등' in text and (not re.search('신호등.{0,12}(?:없|미식별|안 보)|신호등.{0,5}유무', text))
        user_present = scene._evidence_audit.get('signal_user_answers', {}).get('signal_present')
        known = user_present == '없음' or (present == '없음' and (not conflicting))
        checks.append({'field': 'signal_present', 'expected': '없음', 'status': 'user' if user_present == '없음' else 'observed' if known else 'unknown', 'contradicted': present == '있음' and scene.signal_check.signal_operating == '정상 작동', 'note': '신호등이 없는 교차로라는 조건 확인 필요'})
    for who in ('A', 'B'):
        table_who = ('B' if who == 'A' else 'A') if role == 'B' else who
        text = str(row.get(f'vehicle_{table_who.lower()}_progress_info_name', ''))
        if '왼쪽 도로' in text or '오른쪽 도로' in text:
            side = '왼쪽 도로' if '왼쪽 도로' in text else '오른쪽 도로'
            add(who.lower() + '_approach_side', side, f"{('내 차' if who == 'A' else '상대 차')}의 {side} 진입 조건 확인 필요")
    return checks

def assess_row_v212(row, scene, role):
    result = assess_row_v292(row, scene, role)
    for check in context_requirements(row, scene, role):
        result['checks'].append(check)
        if check['status'] == 'unknown':
            result['unresolved_conditions'].append(check['note'])
            result['assumption_count'] += 1
            result['score'] -= 0.5
        if check['contradicted']:
            result['progress_mismatches'].append(check['note'] + ' / 사용자 답변 또는 확인된 조건과 모순')
    result['progress_mismatch_count'] = len(result['progress_mismatches'])
    result['unresolved_conditions'] = list(dict.fromkeys(result['unresolved_conditions']))
    return result

def prepare_matches(match, rows, scene):
    by_id = {r['accident_type']: r for r in rows}
    for candidate in match.candidates:
        row = by_id.get(candidate.accident_type)
        if row is None:
            continue
        roles = [role for role in ('A', 'B') if orientation_compatible(row, scene, role) and (not any((c['contradicted'] for c in context_requirements(row, scene, role))))]
        if candidate.dashcam_table_role not in roles and len(roles) == 1:
            candidate.dashcam_table_role = roles[0]
        if candidate.dashcam_table_role in roles:
            swap = candidate.dashcam_table_role == 'B'
            candidate.mapped_a_progress = row['vehicle_b_progress_info_name' if swap else 'vehicle_a_progress_info_name']
            candidate.mapped_b_progress = row['vehicle_a_progress_info_name' if swap else 'vehicle_b_progress_info_name']
    rejected = prepare_matches_v292(match, rows, scene)
    match.candidates = [c for c in match.candidates if any((orientation_compatible(by_id[c.accident_type], scene, role) and (not any((x['contradicted'] for x in context_requirements(by_id[c.accident_type], scene, role)))) for role in ('A', 'B')))]
    return rejected

def pack_catalog(rows):
    columns = ['accident_object_name', 'accident_place_name', 'accident_place_feature_name', 'vehicle_a_progress_info_name', 'vehicle_b_progress_info_name']
    objects = []
    places = []
    features = []
    progress = []
    pools = [objects, places, features, progress, progress]

    def intern(pool, value):
        if value not in pool:
            pool.append(value)
        return pool.index(value)
    encoded = [[r['accident_type']] + [intern(pool, str(r[k])) for k, pool in zip(columns, pools)] for r in rows]
    return {'objects': objects, 'places': places, 'features': features, 'progress': progress, 'rows': encoded}

def longitudinal_context(row, scene):
    if scene.road_shape != '직선 도로' or row.get('accident_type') != 1:
        return scene
    r = straight_audit(scene)
    if r.get('same_direction') != '같은 방향' or r.get('b_position') not in ('앞', '뒤'):
        return scene
    front = 'B' if r['b_position'] == '앞' else 'A'
    if getattr(scene, front.lower() + '_action') != '정지/대기' or r.get('moving_before_stop') != '있음':
        return scene
    copy = scene.model_copy(deep=True)
    setattr(copy, front.lower() + '_action', '직진')
    copy._evidence_audit.setdefault(front, {})['progress'] = {'value': '직진', 'status': 'inferred', 'linked_frame_ids': r.get('evidence_frame_ids', []), 'sources': ['진행 후 정지 직후를 포함하는 추돌 조건'], 'conflicts': []}
    return copy

def mechanism_compatible_v2153(row, scene):
    if not mechanism_compatible_v212(row, scene):
        return False
    if scene.road_shape != '직선 도로':
        return True
    r = straight_audit(scene)
    text = str(row.get('accident_place_feature_name', ''))
    if '합류' in text or '차로 감소' in text:
        return r.get('mechanism') == '합류' and r.get('status') in ('observed', 'inferred', 'user') and bool(r.get('merge_path_evidence', '').strip())
    if '교행' in text and r.get('same_direction') != '반대 방향':
        return False
    if row.get('accident_type') == 2 and r.get('moving_before_stop') == '있음':
        return False
    return True

def orientation_compatible(row, scene, role):
    if not orientation_compatible_v212(row, longitudinal_context(row, scene), role):
        return False
    if scene.road_shape != '직선 도로':
        return True
    r = straight_audit(scene)
    if r.get('status') not in ('observed', 'inferred', 'user') or r.get('same_direction') != '같은 방향' or r.get('b_position') not in ('앞', '뒤'):
        return True
    for who in ('A', 'B'):
        table_who = ('B' if who == 'A' else 'A') if role == 'B' else who
        text = row['vehicle_' + table_who.lower() + '_progress_info_name']
        actual = '후행' if (who == 'A') == (r['b_position'] == '앞') else '선행'
        if '후행' in text and actual != '후행':
            return False
        if '선행' in text and actual != '선행':
            return False
    return True

def role_validation(candidate, row, scene):
    return role_validation_v212(candidate, row, longitudinal_context(row, scene))

def assess_row(row, scene, role):
    result = assess_row_v212(row, longitudinal_context(row, scene), role)
    if scene.road_shape != '직선 도로':
        return result
    r = straight_audit(scene)
    if r.get('status') not in ('observed', 'inferred', 'user') or r.get('same_direction') != '같은 방향':
        return result
    for c in result['checks']:
        if c.get('field') not in ('a_progress', 'b_progress') or '후행 추돌' not in c.get('expected', ''):
            continue
        who = c['field'][0].upper()
        trailing = who == 'A' and r.get('b_position') == '앞' or (who == 'B' and r.get('b_position') == '뒤')
        if not trailing or r.get('mechanism') != '추돌' or c.get('relation') == '기본 진행 대응':
            continue
        c.update(relation='기본 진행 대응', status=r['status'], frame_ids=r.get('evidence_frame_ids', []), sources=[r['explanation']])
        result['progress_agreement_count'] += 1
        result['score'] += 3
        result['progress_agreements'].append(who + ': 후행 위치·선행차 뒤쪽 접근과 추돌 조건 대응')
        notes = [x for x in result['unresolved_conditions'] if who + "의 '후행 추돌'" in x]
        result['unresolved_conditions'] = [x for x in result['unresolved_conditions'] if x not in notes]
        result['assumption_count'] = max(0, result['assumption_count'] - len(notes))
    if row.get('accident_type') == 1:
        result['unresolved_conditions'].append('사고 직전 상대 차량의 차로변경 유무에 따라 적용 유형이 달라질 수 있음')
    return result

def mechanism_compatible_v2157(row, scene):
    text = ' '.join((str(row.get(k, '')) for k in ('accident_place_feature_name', 'vehicle_a_progress_info_name', 'vehicle_b_progress_info_name')))
    if '유턴' in text:
        user = scene._evidence_audit.get('u_turn', {})
        known = user.get('status') == 'user' and user.get('value') == '있음'
        anchor = original_frame_index(scene.impact_anchor_frame_id)
        for check in scene.maneuver_checks:
            ids = set(check.evidence_frame_ids)
            path = check.path_description
            positive = '유턴' in path and (not re.search('유턴.{0,8}(?:아님|없|미확인|불명|불확실)', path))
            if positive and check.support == '관찰' and (len(ids) >= 2) and check.fixed_background.strip() and all((original_frame_index(i) is not None and (anchor is None or original_frame_index(i) <= anchor) for i in ids)):
                known = True
        if not known:
            return False
    return mechanism_compatible_v2153(row, scene)

def mechanism_compatible(row, scene):
    text = ' '.join((str(row.get(k, '')) for k in ('accident_place_feature_name', 'vehicle_a_progress_info_name', 'vehicle_b_progress_info_name')))
    if '긴급자동차' in text:
        appearance = ' '.join((t.appearance for t in scene.tracks if t.vehicle_id == scene.b_vehicle_id))
        if not re.search('긴급자동차|구급차|소방차', appearance):
            return False
    if '안전지대' in text:
        known = any(('안전지대' in c.path_description and c.support == '관찰' and (len(preimpact_ids(scene, c.evidence_frame_ids)) >= 2) for c in scene.maneuver_checks))
        if not known:
            return False
    if '정체차로' in text:
        known = scene._evidence_audit.get('queued_lane', {}).get('status') == 'user' and scene._evidence_audit['queued_lane'].get('value') == '있음'
        for check in scene.maneuver_checks:
            if '정체차로' in check.path_description and re.search('대기|정차', check.path_description) and (check.support == '관찰') and (len(preimpact_ids(scene, check.evidence_frame_ids)) >= 2):
                known = True
        if not known:
            return False
    return mechanism_compatible_v2157(row, scene)

def strict_user_conflicts(row, scene, role):
    if not place_compatible(row, scene):
        return True
    if any((c['contradicted'] for c in context_requirements(row, scene, role) + parking_requirements(row, scene, role))):
        return True
    for who in ('A', 'B'):
        tw = ('B' if who == 'A' else 'A') if role == 'B' else who
        choices = progress_actions(row['vehicle_' + tw.lower() + '_progress_info_name'])
        fact = scene._evidence_audit.get(who, {}).get('progress', {})
        if fact.get('status') == 'user' and choices and (getattr(scene, who.lower() + '_action') not in choices):
            return True
    return False

def place_compatible(row, scene):
    if scene.road_shape == '주차장':
        scope = scene._evidence_audit.get('questionnaire', {}).get('answers', {}).get('parking_scope')
        name = str(row.get('accident_place_name', ''))
        if scope == '주차장과 일반 도로 사이':
            return '차도가 아닌' in name or '주차장' in name
        return '주차장' in name
    return place_compatible_v219(row, scene)

def context_requirements(row, scene, role):
    checks = context_requirements_v219(row, scene, role)
    answer = scene._evidence_audit.get('context_answers', {}).get('road_width_relation', '미확인')
    if '대로와 소로' in str(row.get('accident_place_feature_name', '')) and answer != '미확인':
        text = row['vehicle_b_progress_info_name' if role == 'B' else 'vehicle_a_progress_info_name']
        expected = '내 차 도로가 넓음' if '대로' in text else '상대 차 도로가 넓음'
        checks.append({'field': 'road_width_relation', 'expected': expected, 'status': 'user', 'contradicted': answer != expected, 'note': '대로·소로 역할과 사용자 도로 폭 답변 비교'})
    return checks
