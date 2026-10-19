"""장면(scene)에서 사실을 뽑아내는 공통 함수. 여러 모듈이 함께 쓰므로 가장 아래층에 둔다."""
import re
from .constants import ACCIDENT_CONFIRMED_INPUT
from .context import ctx
from .schemas import Observation, unknown_state


def original_frame_index(frame_id):
    import re
    match = re.fullmatch('frame_(\\d+)', frame_id or '')
    if not match:
        return None
    index = int(match.group(1))
    return index if 0 <= index < ctx.frame_count else None

def normalize_tracks(observation):
    notes = []
    groups = {}
    for track in observation.tracks:
        original = track.vehicle_id
        track.vehicle_id = original.strip()
        if original != track.vehicle_id:
            notes.append(f'차량 ID 앞뒤 공백 제거: {original!r}')
        is_ego = track.camera_role == '카메라 차량' or bool(re.search(r'^(?:A\s*차량|블랙박스\s*(?:장착차|장착\s*차량)|전방\s*카메라\s*차량)(?:\s*본체|\s*자체|$)', track.appearance.strip()))
        if track.vehicle_id == 'A' or is_ego:
            notes.append('상대 차량 목록에 포함된 A 항목 제거: A 움직임은 a_phases로 관리')
            continue
        group = groups.setdefault(track.vehicle_id, [])
        if any((track.model_dump() == other.model_dump() for other in group)):
            notes.append(f'내용이 완전히 같은 중복 항목 제거: {track.vehicle_id}')
        else:
            group.append(track)
    reserved = set(groups)
    ambiguous = set()
    cleaned = []
    for old_id, group in groups.items():
        if len(group) > 1 or not old_id:
            ambiguous.add(old_id)
        for n, track in enumerate(group, 1):
            if n > 1 or not old_id:
                base = old_id or 'V_unassigned'
                suffix = n
                new_id = f'{base}__{suffix}'
                while new_id in reserved:
                    suffix += 1
                    new_id = f'{base}__{suffix}'
                reserved.add(new_id)
                track.vehicle_id = new_id
                notes.append(f'서로 다른 내용을 합치지 않고 별도 ID 부여: {old_id!r} → {new_id}')
            cleaned.append(track)
    observation.tracks = cleaned
    if isinstance(observation, Observation):
        b_id = observation.b_vehicle_id
        if b_id is not None:
            b_id = b_id.strip()
            observation.b_vehicle_id = b_id
            if b_id == 'A' or b_id in ambiguous or b_id not in {t.vehicle_id for t in cleaned}:
                observation.b_vehicle_id = None
                observation.b_identity = '판단 불가'
                observation.b_action = '미확인'
                observation.b_pre_frame_ids = []
                observation.b_screen_points = []
                observation.b_state = unknown_state()
                notes.append('B ID가 A/중복/누락 항목을 가리켜 연결 해제: 상대 차량 확인 필요')
        observation.observation_issues = list(dict.fromkeys(observation.observation_issues + notes))
    return notes

def progress_actions_base(text):
    actions = set()
    for token, action in (('진로변경', '진로변경'), ('차로변경', '진로변경'), ('진입', '교차로 진입'), ('좌회전', '좌회전'), ('우회전', '우회전'), ('직진', '직진')):
        if token in text:
            actions.add(action)
    if not actions and re.search('(?:교차로\\s*내|내부).*회전|회전\\(', text):
        actions.add('교차로 내 회전')
    if not actions and ('정차' in text or '정지' in text or '주(정)차' in text or ('주정차' in text) or ('주차' in text)) and ('출발' not in text):
        actions.add('정지/대기')
    return actions

def action_support(scene, who, expected_choices=None):
    action = getattr(scene, who.lower() + '_action')
    if scene.road_shape != '회전교차로':
        progress = scene._evidence_audit.get(who, {}).get('progress', {})
        if progress.get('status') == 'user':
            return ('progress', progress)
        if action == '진로변경' or (expected_choices and '진로변경' in expected_choices):
            return ('lane_change', scene._evidence_audit.get(who, {}).get('lane_change', {}))
        return ('progress', scene._evidence_audit.get(who, {}).get('progress', {}))
    field = 'lane_change' if expected_choices is not None and '진로변경' in expected_choices or action == '진로변경' else 'roundabout_position'
    return (field, scene._evidence_audit.get(who, {}).get(field, {}))

def collect_match_facts_base(scene, raw_scene=None):
    raw = raw_scene or scene.model_dump()
    source_texts = [raw.get('contact_evidence', ''), *raw.get('impact_cues', [])]
    b_id = scene.b_vehicle_id
    source_texts += [t.get('movement', '') for t in raw.get('tracks', []) if t.get('vehicle_id') == b_id]
    if scene.road_shape != '회전교차로':
        for who in ('A', 'B'):
            action = getattr(scene, who.lower() + '_action')
            ids = list(dict.fromkeys(getattr(scene, who.lower() + '_pre_frame_ids')))
            existing = scene._evidence_audit.get(who, {}).get('progress', {})
            if existing.get('status') == 'user':
                continue
            scene._evidence_audit.setdefault(who, {})['progress'] = {'value': action, 'status': 'inferred' if action not in ('미확인', '기타') and len(ids) >= 2 else 'unknown', 'direct_frame_ids': [], 'linked_frame_ids': ids, 'sources': ['검증된 사고 전 근거 ID와 모델의 진행 추정'], 'conflicts': []}
    text = ' '.join((str(v) for v in source_texts))
    affirmative = ' '.join((part for part in re.split('[。\\n.;]', text) if not re.search('아님|없음|없다|미확인|불명|모름|불확실|확정.*(?:못|어려)', part)))
    previous = scene._evidence_audit.get('collision_pattern', {})
    if previous.get('status') == 'user':
        return
    rear = bool(re.search('후행\\s*추돌|뒤에서\\s*(?:충돌|추돌)|후방\\s*(?:충돌|추돌)|앞차.*추돌', affirmative))
    crossing = bool(re.search('가로지|횡단[·/\\s]|교차\\s*(?:진행|접근)|측면\\s*(?:접근|충돌|접촉)', text))
    pattern = '미확인' if rear and crossing else '후행 추돌' if rear else '교차 진행/측면 접근' if crossing else '미확인'
    scene._evidence_audit['collision_pattern'] = {'value': pattern, 'status': 'inferred' if pattern != '미확인' else 'unknown', 'source': '모델 관찰 문구의 보수적인 분류; 실제 충돌 종류의 확정은 아님', 'rear_evidence': rear, 'crossing_evidence': crossing, 'parked_evidence': bool(re.search('주차|주정차|주\\(정\\)차|노상\\s*정차', affirmative)), 'prior_accident_evidence': bool(re.search('(?:1차|일차|앞선)\\s*사고|이미\\s*사고', affirmative)), 'source_text': text}

def reconcile_actions(scene):
    for who in ('A', 'B'):
        field = who.lower() + '_action'
        action = getattr(scene, field)
        state = getattr(scene, who.lower() + '_state')
        audit = scene._evidence_audit.setdefault(who, {})
        lane = audit.get('lane_change', {})
        progress = audit.get('progress', {})
        if state.lane_change == '있음' and lane.get('status') in ('observed', 'user'):
            if progress.get('status') == 'user' and action not in ('진로변경', '미확인', '기타'):
                setattr(scene, field, '미확인')
                audit['progress'] = {**progress, 'status': 'conflicted', 'value': '미확인'}
                scene.observation_issues.append(f'{who} 사용자 진행 답변과 차로변경 기록이 모순: 재확인 필요')
            elif action in ('직진', '미확인', '기타'):
                setattr(scene, field, '진로변경')
                setattr(scene, who.lower() + '_pre_frame_ids', list(dict.fromkeys(getattr(scene, who.lower() + '_pre_frame_ids') + state.lane_change_frame_ids)))
                scene.observation_issues.append(f'{who} 단순 직진 대신 사고 직전 차로변경 기록을 반영')
    scene.observation_issues = list(dict.fromkeys(scene.observation_issues))
    for who in ('A', 'B'):
        text = f"사고 직전 도로상 진행: {getattr(scene, who.lower() + '_action')}"
        setattr(scene, 'pre_contact_' + who.lower() + '_movement', text)

def collect_match_facts_v284(scene, raw_scene=None):
    reconcile_actions(scene)
    collect_match_facts_base(scene, raw_scene)
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    for check in scene.special_conditions:
        audit = scene._evidence_audit.setdefault(check.vehicle, {})
        if audit.get(check.condition, {}).get('status') == 'user':
            continue
        ids = list(dict.fromkeys(check.evidence_frame_ids))
        valid = anchor is not None and len(ids) >= 2 and check.explanation.strip() and all((original_frame_index(i) is not None and max(0, anchor - round(4 * ctx.fps)) <= original_frame_index(i) <= anchor for i in ids))
        audit[check.condition] = {'value': check.value if valid else '미확인', 'status': 'observed' if valid and check.value != '미확인' else 'unknown', 'frame_ids': ids, 'explanation': check.explanation, 'source': '모델의 독립 조건 기록; 실제 경계를 코드가 시각적으로 검증한 것은 아님'}

def progress_actions_v291(text):
    compact = re.sub('\\s+', '', str(text))
    if '후진' in compact:
        return {'후진'}
    if '출차' in compact:
        return {'주차 출차'}
    if '출발' in compact:
        return {'출발'}
    if re.search('주차중|주정차|주\\(정\\)차', compact):
        return {'주차 중', '정지/대기'}
    if re.search('교차로.*진출|회전.*진출', compact):
        return {'진출'}
    actions = progress_actions_base(text)
    if not actions and re.search('전진|주행|진행', compact):
        actions.add('직진')
    return actions

def parking_environment(scene):
    return scene.road_shape in ('주차장', '주차장/기타')

def collect_match_facts_v291(scene, raw_scene=None):
    collect_match_facts_v284(scene, raw_scene)
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    for check in scene.maneuver_checks:
        who = check.vehicle
        audit = scene._evidence_audit.setdefault(who, {})
        if audit.get('progress', {}).get('status') == 'user':
            continue
        ids = list(dict.fromkeys(check.evidence_frame_ids))
        valid = len(ids) >= 2 and bool(check.path_description.strip()) and all((original_frame_index(i) is not None and (anchor is None or original_frame_index(i) <= anchor) for i in ids))
        if who == 'A' and (not check.fixed_background.strip()):
            valid = False
        if check.action == '후진' and (not check.vehicle_orientation.strip()):
            valid = False
        if scene.road_shape == '회전교차로' and check.action == '직진':
            valid = False
        if check.action == '진로변경':
            valid = valid and any((c.vehicle == who and c.before_frame_id in ids and (c.after_frame_id in ids) and c.visible_lane_boundary.strip() for c in scene.lane_crossings))
        status = ('observed' if check.support == '관찰' else 'inferred') if valid and check.support != '미확인' else 'unknown'
        action = check.action if status != 'unknown' else '미확인'
        lane = audit.get('lane_change', {})
        if action == '직진' and lane.get('value') == '있음' and (lane.get('status') in ('observed', 'user')):
            action = '진로변경'
            ids = list(dict.fromkeys(ids + getattr(scene, who.lower() + '_state').lane_change_frame_ids))
        if check.action != '미확인' and action == '미확인':
            scene.observation_issues.append(f'{who}의 진행 근거 부족: 추정 확인 필요')
        setattr(scene, who.lower() + '_action', action)
        setattr(scene, who.lower() + '_pre_frame_ids', ids if status != 'unknown' else [])
        audit['progress'] = {'value': action, 'status': status, 'direct_frame_ids': ids if status == 'observed' else [], 'linked_frame_ids': ids if status == 'inferred' else [], 'sources': ['차량별 경로 관찰'], 'conflicts': [], 'path_description': check.path_description, 'alternative_explanation': check.alternative_explanation, 'note': '모델의 인용 기록 검토이며 영상 의미의 독립 검증은 아님'}
    parked = any((getattr(scene, who.lower() + '_action') in ('주차 중', '정지/대기') for who in ('A', 'B')))
    if parking_environment(scene) and parked:
        scene._evidence_audit.setdefault('collision_pattern', {})['parked_evidence'] = True
    for who in ('A', 'B'):
        setattr(scene, 'pre_contact_' + who.lower() + '_movement', f"사고 직전 진행: {getattr(scene, who.lower() + '_action')}")

def scene_missing_conditions_handover(scene):
    reasons = []
    contact_answer = scene._evidence_audit.get('contact_user_answer')
    if contact_answer == '없음':
        reasons.append('선택된 차량과 접촉하지 않았다고 답변했습니다. 실제 상대를 다시 확인해주세요.')
    elif contact_answer != '있음' and scene.contact != '접촉 관찰':
        reasons.append('실제 접촉 여부 확인 필요')
    if scene.b_vehicle_id is None or scene.b_identity != '구별됨':
        reasons.append('실제 접촉 상대 차량 확인 필요')
    if scene.road_shape in ('미확인', '기타'):
        reasons.append('사고 장소 확인 필요')
    for who, label in (('A', '내 차'), ('B', '상대 차')):
        _, support = action_support(scene, who)
        if getattr(scene, who.lower() + '_action') in ('미확인', '기타') or support.get('status') not in ('observed', 'user'):
            reasons.append(label + '의 사고 직전 진행 확인 필요')
    return reasons

def progress_actions(text):
    normalized = str(text).replace('출자', '출차')
    compact = re.sub('\\s+', '', normalized)
    if '주차구역' in compact and '출차' in compact:
        if '후진' in compact:
            return {'후진'}
        if '직진' in compact or '전진' in compact:
            return {'직진', '주차 출차'}
        return {'주차 출차'}
    return progress_actions_v291(normalized)

def collect_match_facts_v212(scene, raw_scene=None):
    prior_progress = {who: dict(scene._evidence_audit.get(who, {}).get('progress', {})) for who in ('A', 'B')}
    collect_match_facts_v291(scene, raw_scene)
    for who, previous in prior_progress.items():
        if previous.get('status') in ('observed', 'user') and previous.get('value') == getattr(scene, who.lower() + '_action') and (not any((x.vehicle == who for x in scene.maneuver_checks))):
            scene._evidence_audit.setdefault(who, {})['progress'] = previous
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    for check in scene.parking_route_checks:
        actor = scene._evidence_audit.setdefault(check.vehicle, {})
        if actor.get('parking_route', {}).get('status') == 'user':
            continue
        ids = list(dict.fromkeys(check.evidence_frame_ids))
        valid = len(ids) >= 2 and bool(check.explanation.strip()) and all((original_frame_index(i) is not None and (anchor is None or original_frame_index(i) <= anchor) for i in ids))
        status = ('observed' if check.support == '관찰' else 'inferred') if valid and check.support != '미확인' else 'unknown'
        actor['parking_route'] = {'status': status, 'start_zone': check.start_zone, 'end_zone': check.end_zone, 'frame_ids': ids, 'explanation': check.explanation, 'source': '모델 관찰 기록; 실제 주차 구획의 독립 검증은 아님'}
    normalize_parking_origins(scene)

def accident_input_confirmed(scene):
    return scene._evidence_audit.get('accident_input_context', {}).get('accident_confirmed', ACCIDENT_CONFIRMED_INPUT)

def mark_accident_input(scene):
    scene._evidence_audit.setdefault('accident_input_context', {'accident_confirmed': ACCIDENT_CONFIRMED_INPUT, 'source': '사용자: 사고 발생 영상만 선택해 입력' if ACCIDENT_CONFIRMED_INPUT else '미확인 입력', 'selected_partner_confirmed': False})

def scene_missing_conditions(scene):
    reasons = scene_missing_conditions_handover(scene)
    return [r for r in reasons if r != '실제 접촉 여부 확인 필요'] if accident_input_confirmed(scene) else reasons

def normalize_parking_origins(scene):
    for check in scene.parking_route_checks:
        route = scene._evidence_audit.setdefault(check.vehicle, {}).get('parking_route', {})
        if route.get('status') == 'user':
            continue
        route['origin_visibility'] = check.origin_visibility
        route['boundary_evidence'] = check.boundary_evidence
        proven = check.origin_visibility == '출발 구역부터 연속 관찰' and bool(check.boundary_evidence.strip()) and (len(set(check.evidence_frame_ids)) >= 2) and (check.support == '관찰')
        if route.get('status') == 'observed' and (not proven):
            route['status'] = 'inferred'
            route['original_status'] = 'observed'
            route['origin_reason'] = '현재 통로 위치와 출발 구역을 구분할 연속 경로·구획 경계 근거가 없어 출차 여부를 확정하지 않음'
            route['source'] = '모델 경로 추정: 출발 구역 미검증'

def straight_audit(scene):
    return scene._evidence_audit.get('straight_relation', {})

def preimpact_ids(scene, ids):
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    return list(dict.fromkeys((i for i in ids if original_frame_index(i) is not None and (anchor is None or original_frame_index(i) <= anchor))))

def collect_match_facts_straight_baseline(scene, raw_scene=None):
    collect_match_facts_v212(scene, raw_scene)
    if scene.road_shape != '직선 도로':
        return
    if straight_audit(scene).get('status') == 'user':
        relation = straight_audit(scene)
    else:
        c = scene.straight_relation
        ids = preimpact_ids(scene, c.evidence_frame_ids)
        valid = c.b_vehicle_id == scene.b_vehicle_id and scene.b_vehicle_id is not None and (len(ids) >= 2) and bool(c.explanation.strip()) and (c.support != '미확인')
        relation = {**c.model_dump(), 'status': ('observed' if c.support == '관찰' else 'inferred') if valid else 'unknown', 'evidence_frame_ids': ids, 'source': '사고 전 차량 관계 모델 기록; 영상의 독립 검증은 아님'}
        if not valid:
            paths = ' '.join((x.path_description for x in scene.maneuver_checks))
            raw = raw_scene or scene.model_dump()
            contact = raw.get('contact_evidence', '')
            ahead = bool(re.search('A\\s*앞|A\\s*전방|전방\\s*B|내\\s*차\\s*앞', paths))
            same = bool(re.search('동일\\s*차로|같은\\s*차로|전방\\s*B를\\s*따라', paths))
            ids = preimpact_ids(scene, scene.b_pre_frame_ids)
            if ahead and same and (len(ids) >= 2):
                relation.update(b_position='앞', same_direction='같은 방향', status='inferred', b_visible_face='후면' if re.search('B.*(?:후면|후방)', contact) else '미확인', moving_before_stop='있음' if re.search('급정거|급정지|급감속|급제동|감속', paths + ' ' + contact) else '미확인', mechanism='추돌' if re.search('B.*(?:후면|후방)', contact) else '미확인', explanation='앞차 동일 차로 진행·뒤쪽 급접근 기록 연결 추정', evidence_frame_ids=ids)
        scene._evidence_audit['straight_relation'] = relation
    if relation.get('status') in ('observed', 'inferred', 'user'):
        direction = relation.get('same_direction')
        for who in ('A', 'B'):
            prior = scene._evidence_audit.get(who, {}).get('opposing_travel', {})
            if prior.get('status') != 'user' and direction != '미확인':
                scene._evidence_audit.setdefault(who, {})['opposing_travel'] = {'value': '없음' if direction == '같은 방향' else '있음', 'status': relation['status'], 'source': relation['explanation']}
        if direction == '같은 방향' and relation.get('mechanism') == '추돌':
            pattern = scene._evidence_audit.setdefault('collision_pattern', {})
            if pattern.get('status') != 'user':
                pattern.update(rear_evidence=True, value='후행 추돌', status='inferred')
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    for crossing in scene.lane_crossings:
        pair = preimpact_ids(scene, [crossing.before_frame_id, crossing.after_frame_id])
        if len(pair) != 2 or not crossing.visible_lane_boundary.strip():
            continue
        before, after = map(original_frame_index, pair)
        if before >= after or (anchor is not None and after < anchor - round(2.5 * ctx.fps)):
            continue
        who = crossing.vehicle
        audit = scene._evidence_audit.setdefault(who, {})
        if audit.get('progress', {}).get('status') == 'user':
            continue
        state = getattr(scene, who.lower() + '_state')
        state.lane_change = '있음'
        state.lane_change_frame_ids = pair
        audit['lane_change'] = {'value': '있음', 'status': 'inferred', 'linked_frame_ids': pair, 'direct_frame_ids': [], 'sources': ['사고 직전 차로 경계 통과 기록'], 'conflicts': []}
        setattr(scene, who.lower() + '_action', '진로변경')
        setattr(scene, who.lower() + '_pre_frame_ids', pair)
        relation['mechanism'] = '차로변경 직후 충돌'
    scene.summary = f"도로 형태: {scene.road_shape}. 내 차: {scene.a_action}, 상대 차: {scene.b_action}. 상대 위치: {relation.get('b_position', '미확인')}, 방향: {relation.get('same_direction', '미확인')}."
    for who in ('a', 'b'):
        setattr(scene, 'pre_contact_' + who + '_movement', '사고 직전 진행: ' + getattr(scene, who + '_action'))

def collect_match_facts_v2151(scene, raw_scene=None):
    collect_match_facts_straight_baseline(scene, raw_scene)
    if not parking_environment(scene):
        return
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    history = {}
    notes = []
    for who in ('A', 'B'):
        progress = scene._evidence_audit.setdefault(who, {}).get('progress', {})
        if progress.get('status') == 'user':
            continue
        phases = []
        for p in scene.parking_motion_phases:
            if p.vehicle != who:
                continue
            first, last = (original_frame_index(p.first_frame_id), original_frame_index(p.last_frame_id))
            ids = list(dict.fromkeys(p.evidence_frame_ids))
            valid = first is not None and last is not None and (first < last) and (len(ids) >= 2) and all((original_frame_index(i) is not None and first <= original_frame_index(i) <= last for i in ids)) and bool(p.explanation.strip()) and bool(p.fixed_background.strip()) and (p.action != '후진' or bool(p.vehicle_orientation.strip()))
            phases.append({**p.model_dump(), 'valid': valid, 'first': first, 'last': last})
        phases.sort(key=lambda p: p['first'] if p['first'] is not None else -1)
        history[who] = phases
        chosen = None
        active = [p for p in phases if p['valid'] and p['support'] != '미확인' and (p['action'] not in ('정지/대기', '주차 중', '미확인', '기타'))]
        if anchor is not None:
            eligible = [p for p in phases if p['valid'] and p['first'] <= anchor and (p['support'] != '미확인')]
            if eligible:
                chosen = max(eligible, key=lambda p: (p['last'] >= anchor, p['first']))
        elif active:
            chosen = active[-1]
        if chosen:
            valid_ids = [i for i in chosen['evidence_frame_ids'] if anchor is None or original_frame_index(i) <= anchor]
            status = 'observed' if chosen['support'] == '관찰' and anchor is not None else 'inferred'
            if len(valid_ids) < 2:
                status = 'unknown'
            action = chosen['action'] if status != 'unknown' else '미확인'
            setattr(scene, who.lower() + '_action', action)
            setattr(scene, who.lower() + '_pre_frame_ids', valid_ids if status != 'unknown' else [])
            scene._evidence_audit[who]['progress'] = {'value': action, 'status': status, 'direct_frame_ids': valid_ids if status == 'observed' else [], 'linked_frame_ids': valid_ids if status == 'inferred' else [], 'sources': ['주차장 구간별 움직임'], 'conflicts': [], 'path_description': chosen['explanation'], 'note': '사건 중심 미확인 시 움직임 구간은 사고 전 진행 후보이며 확정 시점 아님'}
        else:
            action = getattr(scene, who.lower() + '_action')
            checks = [p for p in scene.maneuver_checks if p.vehicle == who]
            text = ' '.join((p.path_description for p in checks))
            conflicts = []
            if who == 'A' and action in ('정지/대기', '주차 중') and any(('A 타임라인의 정지 구간과 배경 이동' in x for x in scene.observation_issues)):
                conflicts.append('내 차의 정지 기록과 배경 변화 단서가 충돌함')
            if action in ('정지/대기', '주차 중') and re.search('(?:초기|처음|전진|후진|이동|주행).{0,30}(?:후|뒤|이후).{0,15}정지', text):
                conflicts.append('이동 후 정지 기록을 전체 구간 정지로 사용할 수 없음: 움직임 구간 확인 필요')
            if conflicts:
                original = action
                setattr(scene, who.lower() + '_action', '미확인')
                scene._evidence_audit[who]['progress'] = {**progress, 'value': '미확인', 'original_value': original, 'status': 'conflicted', 'conflicts': conflicts}
                notes.extend(conflicts)
        setattr(scene, 'pre_contact_' + who.lower() + '_movement', '진행 후보: ' + getattr(scene, who.lower() + '_action'))
    scene._evidence_audit['parking_motion_history'] = history
    scene._evidence_audit['parking_motion_notes'] = list(dict.fromkeys(notes))
    scene.summary = f'도로 형태: {scene.road_shape}. 내 차 진행 후보: {scene.a_action}, 상대 차 진행 후보: {scene.b_action}. 사건 중심: ' + ('미확인' if anchor is None else '영상 근거 시점')
    scene.observation_issues = list(dict.fromkeys(scene.observation_issues + notes))

def collect_match_facts_v2154(scene, raw_scene=None):
    collect_match_facts_v2151(scene, raw_scene)
    if not parking_environment(scene):
        return
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    notes = scene._evidence_audit.setdefault('parking_motion_notes', [])
    for who in ('A', 'B'):
        actor = scene._evidence_audit.setdefault(who, {})
        progress = actor.get('progress', {})
        if progress.get('status') == 'user':
            continue
        phases = scene._evidence_audit.get('parking_motion_history', {}).get(who, [])
        eligible = [p for p in phases if p.get('valid') and p.get('support') != '미확인' and (anchor is not None) and (p['first'] <= anchor)]
        chosen = max(eligible, key=lambda p: (p['last'] >= anchor, p['first'])) if eligible else None
        if chosen and progress.get('status') == 'unknown':
            ids = {i for i in chosen['evidence_frame_ids'] if original_frame_index(i) <= anchor}
            for check in scene.maneuver_checks:
                if check.vehicle != who or check.action != chosen['action'] or check.support == '미확인' or (not check.fixed_background.strip()) or (not check.path_description.strip()):
                    continue
                ids.update((i for i in check.evidence_frame_ids if original_frame_index(i) is not None and chosen['first'] <= original_frame_index(i) <= anchor))
            if len(ids) >= 2:
                ids = sorted(ids, key=original_frame_index)
                actor['progress'] = {**progress, 'value': chosen['action'], 'status': 'inferred', 'direct_frame_ids': [], 'linked_frame_ids': ids, 'sources': ['주차장 구간별 움직임', '같은 구간의 진행 관찰'], 'note': '같은 진행·구간의 사고 전 근거를 병합한 추정; 배경 모순은 해소된 것으로 간주하지 않음'}
                setattr(scene, who.lower() + '_action', chosen['action'])
                setattr(scene, who.lower() + '_pre_frame_ids', ids)
                notes.append(f"{who}의 같은 진행 구간 근거를 병합함: {chosen['action']} 추정")
        action = getattr(scene, who.lower() + '_action')
        if action in ('좌회전', '우회전'):
            checks = [p for p in scene.parking_motion_phases if p.vehicle == who and p.action == action]
            proven = any((p.turn_geometry_evidence.strip() and len(p.evidence_frame_ids) >= 2 and (anchor is not None) and all((original_frame_index(i) is not None and original_frame_index(i) <= anchor for i in p.evidence_frame_ids)) and (p.support == '관찰') for p in checks))
            if not proven:
                current = actor.get('progress', {})
                if current.get('status') == 'observed':
                    actor['progress'] = {**current, 'status': 'inferred', 'linked_frame_ids': current.get('direct_frame_ids', []), 'direct_frame_ids': [], 'note': '화면 횡단과 도로상 회전의 구별 근거 부족: 회전 전후 차체 방향·통로 기준 필요'}
                    for phase in phases:
                        if phase.get('action') == action:
                            phase['original_support'] = phase['support']
                            phase['support'] = '추정'
                            phase['turn_validation'] = '회전 전후 차체 방향·통로 기준 근거 부족'
                    notes.append(f'{who}의 화면 횡단을 도로상 {action} 확정으로 사용하지 않음')
        setattr(scene, 'pre_contact_' + who.lower() + '_movement', '진행 후보: ' + getattr(scene, who.lower() + '_action'))
    scene._evidence_audit['parking_motion_notes'] = list(dict.fromkeys(notes))
    scene.summary = f'도로 형태: {scene.road_shape}. 내 차 진행 후보: {scene.a_action}, 상대 차 진행 후보: {scene.b_action}.'

def collect_match_facts_v2172(scene, raw_scene=None):
    collect_match_facts_v2154(scene, raw_scene)
    if scene.road_shape != '직선 도로':
        return
    r = straight_audit(scene)
    pattern = scene._evidence_audit.setdefault('collision_pattern', {})
    contact_ids = preimpact_ids(scene, scene.contact_frame_ids)
    text = scene.contact_evidence + ' ' + ' '.join(scene.impact_cues)
    valid = scene.b_identity == '구별됨' and r.get('b_vehicle_id') == scene.b_vehicle_id and (r.get('status') in ('observed', 'inferred', 'user')) and (r.get('same_direction') == '같은 방향') and (r.get('b_position') == '앞') and (r.get('b_visible_face') == '후면') and (len(preimpact_ids(scene, r.get('evidence_frame_ids', []))) >= 2) and (len(contact_ids) >= 2) and (scene.contact in ('접촉 관찰', '접촉 추정', '충돌 정황 강함')) and bool(re.search('후면|뒤쪽|뒷범퍼|후방', text)) and bool(re.search('급접근|확대|밀착|겹침|충격|충돌', text))
    if not valid or pattern.get('status') == 'user':
        return
    pattern.update(rear_evidence=True, status='inferred', value='후행 추돌', geometry_basis='같은 방향·상대 앞·후면 관찰과 접촉 근거의 연결 추정; 사고 원인 확정 아님', geometry_frame_ids=contact_ids)
    r['rear_contact_geometry'] = 'inferred'
    if r.get('mechanism') == '미확인':
        r['mechanism'] = '추돌'
        r['mechanism_status'] = '접촉 형태 추정 — 차로변경 원인 미확인'
    r['cause_lane_change_status'] = scene._evidence_audit.get('B', {}).get('lane_change', {}).get('status', 'unknown')

def collect_match_facts(scene, raw_scene=None):
    collect_match_facts_v2172(scene, raw_scene)
    track = next((t for t in scene.tracks if t.vehicle_id == scene.b_vehicle_id), None)
    if scene.accident_object is None and scene.b_identity == '구별됨' and track:
        ids = list(dict.fromkeys(track.evidence_frame_ids))
        vehicle = bool(re.search('픽업|트럭|세단|승용차|승합차|버스|SUV|미니밴|화물차', track.appearance, re.I))
        if vehicle and len(ids) >= 2:
            scene.accident_object = '차대차'
            scene._evidence_audit['accident_object_recovery'] = {'value': '차대차', 'status': 'inferred', 'vehicle_id': track.vehicle_id, 'appearance': track.appearance, 'frame_ids': ids, 'source': '식별된 상대의 자동차 외형 기록; 접촉 여부와 별개'}
    if not parking_environment(scene):
        return
    static = scene._evidence_audit.get('parking_static_background', {})
    current = scene._evidence_audit.setdefault('A', {}).get('progress', {})
    stopped = [p for p in scene.parking_motion_phases if p.vehicle == 'A' and p.action in ('정지/대기', '주차 중') and (p.support != '미확인') and (len(set(p.evidence_frame_ids)) >= 2) and p.fixed_background.strip()]
    if static.get('status') == 'stationary_support' and stopped and (current.get('status') != 'user') and (not any((p.vehicle == 'A' and p.action not in ('정지/대기', '주차 중') and (p.support != '미확인') for p in scene.parking_motion_phases))):
        phase = max(stopped, key=lambda p: original_frame_index(p.last_frame_id) - original_frame_index(p.first_frame_id))
        scene.a_action = '정지/대기'
        scene.a_pre_frame_ids = list(phase.evidence_frame_ids)
        scene._evidence_audit['A']['progress'] = {'value': '정지/대기', 'status': 'inferred', 'direct_frame_ids': [], 'linked_frame_ids': phase.evidence_frame_ids, 'sources': ['고정 벽·천장 다영역 보조 근거', '정지 구간 모델 기록'], 'note': '전체 구간 정지 후보를 보존. 사건 중심 미확인이면 사고 직전 확정 사실로 취급하지 않음'}
    actor = scene._evidence_audit.setdefault('B', {})
    progress = actor.get('progress', {})
    if progress.get('status') != 'user':
        checks = [p for p in scene.parking_motion_phases if p.vehicle == 'B']
        for p in checks:
            text = p.explanation + ' ' + p.vehicle_orientation
            if p.action == '주차 출차' and '후진' in text and (not re.search('후진.{0,8}(?:아님|없|불명)', text)) and (p.support != '미확인') and (len(set(p.evidence_frame_ids)) >= 2) and p.fixed_background.strip() and p.vehicle_orientation.strip():
                scene.b_action = '후진'
                scene.b_pre_frame_ids = list(p.evidence_frame_ids)
                actor['progress'] = {**progress, 'value': '후진', 'status': 'inferred', 'original_value': '주차 출차', 'direct_frame_ids': [], 'linked_frame_ids': p.evidence_frame_ids, 'sources': ['후진 방향·차체 방향을 기록한 주차장 구간'], 'note': '출차 목적과 후진 이동 방향을 분리한 추정; 사고 시점 확정 아님'}
                break
    if scene.accident_object == '차대차' and scene.b_action == '후진':
        scene._evidence_audit['observed_parking_pattern'] = {'title': '주차장 후진 차량 접근', 'ego_motion': scene.a_action, 'other_motion': '후진', 'contact_status': scene.contact, 'csv_limit': '내 차가 정지한 상태라면 CSV127번의 통로 직진 조건과 다름; 동일 유형·비율로 강제 적용하지 않음'}

def civil_fault_number(number):
    number=re.sub(r'\s+', '', str(number))
    if re.search(r'\d(?:고단|고합|고정|고약|도|노|구합|구단|누|두)',number):
        return False
    return bool(re.fullmatch(r'\d{2,4}(?:가단|가합|가소|다카|나|다)\d+',number))

_normalize_tracks_before_recovery = normalize_tracks

def normalize_tracks(observation):
    repairs = []
    if isinstance(observation, Observation):
        relation = observation.straight_relation
        target = observation.b_vehicle_id
        matches = [t for t in observation.tracks if t.vehicle_id.strip() == target]
        if target and target != 'A' and len(matches) == 1:
            track = matches[0]
            overlap = set(track.evidence_frame_ids) & set(relation.evidence_frame_ids)
            external = (relation.b_vehicle_id == target and relation.b_position in ('앞','뒤','옆')
                        and relation.b_visible_face in ('전면','후면','측면') and relation.support != '미확인'
                        and len(overlap) >= 2 and bool(relation.explanation.strip()))
            explicit_ego = bool(re.search(r'^(?:A\s*차량|블랙박스\s*장착\s*차량|카메라\s*차량)(?:\s*자체|\s*본체|$)', track.appearance))
            if track.camera_role == '카메라 차량' and external and not explicit_ego:
                before = track.model_dump()
                track.camera_role = '외부 차량'
                repairs.append({'vehicle_id': target, 'before': before, 'reason': '선택된 상대 ID·보이는 차체 면·서로 다른 근거 프레임을 교차 비교해 역할 모순 수정', 'support': '모델 기록 간 일관성 복구; 독립 영상 검증 아님'})
    notes = _normalize_tracks_before_recovery(observation)
    if repairs:
        observation._evidence_audit.setdefault('identity_repairs', []).extend(repairs)
        notes.append('상대 차량의 카메라 역할 오기 교차 검토·복구')
    return notes
