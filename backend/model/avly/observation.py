"""관찰 결과 검증과 보정."""
from .dataio import prompt_text
import cv2
import json
import numpy as np
import re
from .constants import ACCURACY_RULES, VISION_MODEL
from .tables import CONFIRMED_ROAD_CONTEXT, CONFIRMED_VIDEO_CONTEXT, SUPPORT_LABELS
from .context import ctx
from .schemas import AdjustmentObservation, FrameReferenceError, LaneCauseReview, Observation, SignalCheck, Track, unknown_state
from .facts import collect_match_facts, original_frame_index, preimpact_ids, progress_actions, straight_audit
from .vision import call
from .video import get_frames, image_content, uniform_pick


def validate(observation, frames):
    indices = {f['id']: f['index'] for f in frames}
    invalid = []

    def inspect_ids(value, field=''):
        if isinstance(value, dict):
            for key, child in value.items():
                name = f'{field}.{key}' if field else key
                if key.endswith('frame_id') and child is not None:
                    if child not in indices:
                        invalid.append({'field': name, 'id': child})
                elif key.endswith('frame_ids') and isinstance(child, list):
                    for n, frame_id in enumerate(child):
                        if frame_id not in indices:
                            invalid.append({'field': f'{name}[{n}]', 'id': frame_id})
                else:
                    inspect_ids(child, name)
        elif isinstance(value, list):
            for n, child in enumerate(value):
                inspect_ids(child, f'{field}[{n}]')
    inspect_ids(observation.model_dump())
    if invalid:
        raise FrameReferenceError(invalid, indices)
    if isinstance(observation, Observation):
        maneuver_actors = [x.vehicle for x in observation.maneuver_checks]
        if len(set(maneuver_actors)) != len(maneuver_actors):
            raise ValueError('차량별 진행 검토 기록 중복')
        parking_actors = [x.vehicle for x in observation.parking_route_checks]
        if len(set(parking_actors)) != len(parking_actors):
            raise ValueError('주차장 차량별 경로 기록 중복')
        pairs = [(x.vehicle, x.condition) for x in observation.special_conditions]
        if len(set(pairs)) != len(pairs):
            raise ValueError('특수 조건 기록 중복')

    def check(ids):
        bad = [{'field': 'frame_reference', 'id': i} for i in ids if i not in indices]
        if bad:
            raise FrameReferenceError(bad, indices)
    vehicle_ids = [v.vehicle_id for v in observation.tracks]
    if len(set(vehicle_ids)) != len(vehicle_ids) or 'A' in vehicle_ids:
        raise ValueError('상대 차량 ID 중복 또는 A 사용')
    b_id = getattr(observation, 'b_vehicle_id', None)
    if b_id is not None and b_id not in vehicle_ids:
        raise ValueError('B 차량 ID가 관찰 차량 목록에 없음')
    for obj in observation.tracks + observation.a_phases:
        check([obj.first_frame_id, obj.last_frame_id])
        if indices[obj.first_frame_id] > indices[obj.last_frame_id]:
            raise ValueError('관찰 구간 순서 오류')
        if isinstance(obj, Track):
            check(obj.evidence_frame_ids)
    check(observation.contact_frame_ids + getattr(observation, 'pre_contact_evidence_frame_ids', []))
    if observation.impact_anchor_frame_id:
        check([observation.impact_anchor_frame_id])
    if isinstance(observation, Observation):
        check(observation.lane_count_frame_ids)
        check(observation.signal_check.evidence_frame_ids)
        for state in (observation.a_state, observation.b_state):
            check(state.motion_frame_ids + state.position_frame_ids + state.lane_change_frame_ids)
        check(observation.a_pre_frame_ids + observation.b_pre_frame_ids + observation.road_shape_evidence_frame_ids)
        check([p.frame_id for p in observation.b_screen_points])
        if len({p.frame_id for p in observation.b_screen_points}) != len(observation.b_screen_points):
            raise ValueError('B 좌표 프레임 중복')
        for crossing in observation.lane_crossings:
            check([crossing.before_frame_id, crossing.after_frame_id])
            if indices[crossing.before_frame_id] >= indices[crossing.after_frame_id]:
                raise ValueError('차로 경계 통과 근거 순서 오류')
    review_first = getattr(observation, 'review_first_frame_id', None)
    review_last = getattr(observation, 'review_last_frame_id', None)
    for i in (review_first, review_last):
        if i is not None:
            check([i])
    if review_first and review_last:
        if indices[review_first] > indices[review_last]:
            raise ValueError('재검토 구간 순서 오류')
    if any((i not in ctx.places for i in observation.road_place_codes)):
        raise ValueError('없는 장소 코드')

def scan_as_observation(scan):
    return Observation.model_validate({**scan.model_dump(), 'b_vehicle_id': None, 'b_identity': '판단 불가', 'impact_cues': [], 'pre_contact_a_movement': '미확인', 'pre_contact_b_movement': '미확인', 'pre_contact_evidence_frame_ids': [], 'a_action': '미확인', 'b_action': '미확인', 'a_state': unknown_state().model_dump(), 'b_state': unknown_state().model_dump(), 'roundabout_lane_count': '미확인', 'lane_count_frame_ids': [], 'observation_issues': [], 'b_screen_points': [], 'a_pre_frame_ids': [], 'b_pre_frame_ids': [], 'lane_crossings': [], 'road_shape': scan.road_shape, 'road_shape_evidence_frame_ids': list(scan.road_shape_evidence_frame_ids), 'review_needed': False, 'review_first_frame_id': None, 'review_last_frame_id': None, 'review_reason': '', 'unknowns': [], 'signal_check': SignalCheck().model_dump()})

def neutral_context(scan):
    return [{'id': t.vehicle_id, 'appearance': t.appearance, 'first': t.first_frame_id, 'last': t.last_frame_id, 'exit_observation': t.exit_observation} for t in scan.tracks]

def compact_observation(scene):
    compact = {k: scene.model_dump()[k] for k in ('summary', 'b_vehicle_id', 'b_identity', 'accident_object', 'road_place_codes', 'road_evidence', 'pre_contact_a_movement', 'pre_contact_b_movement', 'pre_contact_evidence_frame_ids', 'a_pre_frame_ids', 'b_pre_frame_ids', 'road_shape', 'a_action', 'b_action', 'a_state', 'b_state', 'roundabout_lane_count', 'contact', 'observation_issues', 'unknowns')}
    compact['evidence_support'] = {who: {field: item.get('status') for field, item in fields.items()} for who, fields in scene._evidence_audit.items() if who in ('A', 'B')}
    compact['lane_count_support'] = scene._evidence_audit.get('lane_count', {}).get('status', 'unknown')
    compact['route_geometry'] = {who: scene._evidence_audit.get(who, {}).get('roundabout_position', {}).get('geometry_check', {}) for who in ('A', 'B')}
    compact['signal_check'] = scene.signal_check.model_dump()
    compact['accident_input_context'] = scene._evidence_audit.get('accident_input_context', {})
    compact['straight_relation'] = straight_audit(scene)
    compact['parking_motion_history'] = scene._evidence_audit.get('parking_motion_history', {})
    compact['camera_view'] = scene.camera_view
    compact['parking_route_checks'] = [x.model_dump() for x in scene.parking_route_checks]
    compact['maneuver_checks'] = [x.model_dump() for x in scene.maneuver_checks]
    compact['special_conditions'] = [x.model_dump() for x in scene.special_conditions]
    compact['collision_pattern'] = scene._evidence_audit.get('collision_pattern', {})
    compact['place_search'] = scene._evidence_audit.get('place_search', {})
    return compact

def screen_direction(scene, frame_lookup):
    points = sorted((p for p in scene.b_screen_points if p.visibility == '차량 중심 식별 가능'), key=lambda p: frame_lookup[p.frame_id])
    if len(points) < 3:
        return '판단 불가'
    delta = float(np.median([p.x_center for p in points[-2:]]) - np.median([p.x_center for p in points[:2]]))
    if abs(delta) < 0.1:
        return '뚜렷한 좌우 이동 미확인'
    return '왼쪽→오른쪽' if delta > 0 else '오른쪽→왼쪽'

FLOW_STAGE_ORDER = {'접근': 0, '사고 직전': 1, '접촉': 2, '접촉 이후': 3}
FLOW_BANNED = re.compile(r'과실|책임|잘못|위반|가해|피해|\d+(?:\.\d+)?\s*(?:km|㎞|미터|m\b|초|%)')   # 판단 표현과 수치(속도·거리·시간)는 쓰지 않는다
FLOW_CONTACT_CLAIM = re.compile(r'부딪혔|충돌했|접촉했|추돌했|들이받')
FLOW_CONFIRMED_CONTACT = ('접촉 관찰', '충돌 정황 강함')


def clean_accident_flow(scene, frames):
    """AI 가 쓴 사고 흐름(accident_flow)에서 믿기 어려운 단계를 뺀다. 분석을 실패시키지 않고 단계만 버리고, 이유는 observation_issues 에 남긴다.

    버리는 경우: 시간순이 아니거나 같은 단계가 반복됨 / 시작이 끝보다 늦음 / 판단 표현·수치가 들어 있음 /
    직접 접촉이 확인되지 않았는데 부딪혔다고 단정함. 최대 4단계.
    """
    index = {f['id']: f['index'] for f in frames}
    kept, dropped = [], []
    last_index = -1
    seen = set()
    for step in sorted(scene.accident_flow, key=lambda s: (FLOW_STAGE_ORDER[s.stage], index.get(s.first_frame_id, 0))):
        first, last = index.get(step.first_frame_id), index.get(step.last_frame_id)
        reason = None
        if step.stage in seen:
            reason = '같은 단계 반복'
        elif first is None or last is None or first > last:
            reason = '시작·끝 장면 순서 오류'
        elif first < last_index:
            reason = '앞 단계보다 시간이 앞섬'
        elif FLOW_BANNED.search(step.description):
            reason = '판단 표현 또는 수치 포함'
        elif FLOW_CONTACT_CLAIM.search(step.description) and scene.contact not in FLOW_CONFIRMED_CONTACT:
            reason = '접촉이 확인되지 않았는데 접촉을 단정'
        if reason:
            dropped.append(f'사고 흐름 {step.stage} 단계 제외: {reason}')
            continue
        seen.add(step.stage)
        last_index = first
        kept.append(step)
    scene.accident_flow = kept[:4]
    scene.observation_issues = list(scene.observation_issues) + dropped[:4]
    return len(scene.accident_flow)

def ground_observation(scene, frames, anchor, cues, visual_frame_ids=None):
    lookup = {f['id']: f['index'] for f in frames}
    visual = set(lookup) if visual_frame_ids is None else set(visual_frame_ids)
    issues = list(scene.observation_issues)
    previous_audit = scene._evidence_audit
    audit = {}
    route_actions = {'진입': '교차로 진입', '내부 회전': '교차로 내 회전', '진출': '진출', '진입 전 대기': '정지/대기'}

    def before(ids):
        return sorted(set((i for i in ids if i in visual and lookup[i] <= anchor)), key=lookup.get)
    for who in ('A', 'B'):
        state = getattr(scene, who.lower() + '_state')
        pre_ids = before(getattr(scene, who.lower() + '_pre_frame_ids'))
        b_track = next((t for t in scene.tracks if t.vehicle_id == scene.b_vehicle_id), None) if who == 'B' else None

        def vehicle_frames(ids):
            ids = before(ids)
            if b_track is not None:
                track_first = original_frame_index(b_track.first_frame_id)
                track_last = original_frame_index(b_track.last_frame_id)
                if track_first is None or track_last is None or track_first > track_last:
                    return []
                ids = [i for i in ids if track_first <= lookup[i] <= track_last]
            return ids
        pre_ids = vehicle_frames(pre_ids)
        narrative = getattr(scene, 'pre_contact_' + who.lower() + '_movement')
        old_action = getattr(scene, who.lower() + '_action')
        audit[who] = {}
        for field, label in (('motion_frame_ids', 'motion'), ('position_frame_ids', 'roundabout_position'), ('lane_change_frame_ids', 'lane_change')):
            value = getattr(state, label)
            direct = vehicle_frames(getattr(state, field))
            linked, sources, conflicts = ([], [], [])
            previous = previous_audit.get(who, {}).get(label, {})
            if previous.get('value') == value:
                linked = vehicle_frames(previous.get('linked_frame_ids', []))
                direct = [i for i in direct if i not in linked]
                sources = list(previous.get('sources', []))
                conflicts = list(previous.get('conflicts', []))
            if label == 'motion' and value == '이동' and (len(direct) < 2):
                if who == 'A':
                    for phase in scene.a_phases:
                        if phase.state == '이동 추정' and lookup[phase.first_frame_id] <= anchor and (lookup[phase.last_frame_id] >= anchor - round(ctx.fps)):
                            linked += before([phase.first_frame_id, phase.last_frame_id])
                    if linked:
                        sources.append('A 배경 이동 타임라인 (같은 모델의 연결 추정)')
                elif re.search('이동|진입|가로지|진행', narrative):
                    linked += pre_ids
                    sources.append('B 사고 직전 진행 설명 (같은 모델의 연결 추정)')
            if label == 'roundabout_position':
                expected = route_actions.get(value)
                narrated = progress_actions(narrative)
                if expected and expected in narrated and (len(direct) < 2):
                    linked += pre_ids
                    sources.append('해당 차량의 사고 직전 설명과 일치하는 근거 목록')
                if expected and old_action in ('교차로 진입', '교차로 내 회전') and (old_action != expected):
                    conflicts.append(f'{who} 원래 action({old_action})과 교차로 위치({value}) 불일치')
                if expected and narrated.intersection({'교차로 진입', '교차로 내 회전'}) and (expected not in narrated):
                    conflicts.append(f'{who} 진행 설명과 교차로 위치 불일치')
            if label == 'lane_change' and value == '있음' and (len(direct) < 2):
                for crossing in scene.lane_crossings:
                    pair = vehicle_frames([crossing.before_frame_id, crossing.after_frame_id])
                    if crossing.vehicle == who and crossing.visible_lane_boundary.strip() and (len(pair) == 2) and (lookup[crossing.before_frame_id] < lookup[crossing.after_frame_id] <= anchor):
                        linked += pair
                        sources.append('해당 차량의 차로 경계 통과 기록 (연결 추정)')
            linked = vehicle_frames(linked)
            combined = vehicle_frames(direct + linked)
            status = 'observed' if len(direct) >= 2 else 'inferred' if len(combined) >= 2 else 'unknown'
            if value == '미확인':
                status = 'unknown'
            if label == 'lane_change' and value == '없음' and (status == 'observed'):
                status = 'inferred'
            if conflicts:
                status = 'conflicted'
                issues.extend(conflicts)
            audit[who][label] = {'value': value, 'status': status, 'direct_frame_ids': direct, 'linked_frame_ids': linked, 'sources': list(dict.fromkeys(sources)), 'conflicts': list(dict.fromkeys(conflicts))}
            setattr(state, field, combined)
    scene._evidence_audit = audit
    for who, state in (('A', scene.a_state), ('B', scene.b_state)):
        for field, label in (('motion_frame_ids', 'motion'), ('position_frame_ids', 'roundabout_position'), ('lane_change_frame_ids', 'lane_change')):
            ids = sorted(set((i for i in getattr(state, field) if i in visual and lookup[i] <= anchor)), key=lookup.get)
            setattr(state, field, ids)
            if len(ids) < 2 and getattr(state, label) != '미확인':
                setattr(state, label, '미확인')
                audit[who][label]['status'] = 'unknown'
                issues.append(f'{who} {label}: 사고 전 근거 부족')
        if state.lane_change == '있음':
            crossed = [c for c in scene.lane_crossings if c.vehicle == who and c.visible_lane_boundary.strip() and (c.before_frame_id in visual) and (c.after_frame_id in visual) and (lookup[c.before_frame_id] < lookup[c.after_frame_id] <= anchor) and (c.before_frame_id in state.lane_change_frame_ids) and (c.after_frame_id in state.lane_change_frame_ids)]
            if not crossed:
                state.lane_change = '미확인'
                audit[who]['lane_change']['status'] = 'unknown'
                issues.append(f'{who} 차로변경: 검토 이미지의 전후 차로 경계 근거 부족')
        if who == 'A' and state.motion == '정지':
            ids = state.motion_frame_ids
            span = (lookup[ids[-1]] - lookup[ids[0]]) / ctx.fps if len(ids) >= 2 else 0
            changing = [c for c in cues if ids and lookup[ids[0]] <= lookup[c[0]] < lookup[c[1]] <= lookup[ids[-1]] and (abs(c[2]) + abs(c[3]) >= 6)]
            if span < 0.75 or len(changing) >= 2:
                state.motion = '미확인'
                audit[who]['motion']['status'] = 'unknown'
                issues.append('A 정지 상태와 배경 변화가 불일치: 정지 확정 보류')
        action = '진로변경' if state.lane_change == '있음' else {'진입': '교차로 진입', '내부 회전': '교차로 내 회전', '진입 전 대기': '정지/대기'}.get(state.roundabout_position, '미확인')
        if scene.road_shape == '회전교차로':
            setattr(scene, who.lower() + '_action', action)
            setattr(scene, who.lower() + '_pre_frame_ids', sorted(set(state.lane_change_frame_ids if action == '진로변경' else state.position_frame_ids), key=lookup.get))
    scene.lane_count_frame_ids = list(dict.fromkeys((i for i in scene.lane_count_frame_ids if i in visual)))
    if len(scene.lane_count_frame_ids) < 2:
        scene.roundabout_lane_count = '미확인'
    audit['lane_count'] = {'value': scene.roundabout_lane_count, 'status': 'inferred' if scene.roundabout_lane_count != '미확인' else 'unknown', 'frame_ids': scene.lane_count_frame_ids, 'note': '모델의 차로 수는 추정 조건: 프레임 수만으로 실제 차로 경계를 확인할 수 없음'}
    for phase in scene.a_phases:
        changing = [c for c in cues if lookup[phase.first_frame_id] <= lookup[c[0]] < lookup[c[1]] <= lookup[phase.last_frame_id] and abs(c[2]) + abs(c[3]) >= 6]
        if phase.state == '정지 추정' and len(changing) >= 2:
            phase.state = '판단 불가'
            phase.background_evidence += ' / 배경 이동 단서와 모순: 이동·카메라 회전 구분 필요'
            issues.append('A 타임라인의 정지 구간과 배경 이동 단서 불일치')
    for who, field in (('A', 'a_pre_frame_ids'), ('B', 'b_pre_frame_ids')):
        valid = sorted(set((i for i in getattr(scene, field) if i in visual and lookup[i] <= anchor)), key=lookup.get)
        setattr(scene, field, valid)
        action_field = 'a_action' if who == 'A' else 'b_action'
        if getattr(scene, action_field) not in ('미확인', '기타') and len(valid) < 2:
            setattr(scene, action_field, '미확인')
            issues.append(f'{who} 사고 직전 행동의 유효 근거 프레임이 2장 미만')
        if getattr(scene, action_field) == '진로변경':
            crossed = [c for c in scene.lane_crossings if c.vehicle == who and c.visible_lane_boundary.strip() and (lookup[c.after_frame_id] <= anchor) and (c.before_frame_id in visual) and (c.after_frame_id in visual)]
            if not crossed:
                setattr(scene, action_field, '미확인')
                issues.append(f'{who} 진로변경 주장에 차로 경계 통과 근거가 없어 미확인 처리')
    if scene.a_action == '정지/대기':
        ids = scene.a_pre_frame_ids
        span = (lookup[ids[-1]] - lookup[ids[0]]) / ctx.fps if len(ids) >= 2 else 0
        changes = [c for c in cues if anchor - round(2 * ctx.fps) <= lookup[c[0]] < lookup[c[1]] <= anchor and abs(c[2]) + abs(c[3]) >= 6]
        if span < 0.75 or len(changes) >= 2:
            scene.a_action = '미확인'
            issues.append('정지 판단의 시간 범위가 짧거나 사고 직전 배경 변동이 반복됨: A 이동/카메라 변동 구분 필요')
    scene.pre_contact_evidence_frame_ids = sorted(set(scene.a_pre_frame_ids + scene.b_pre_frame_ids), key=lookup.get)
    scene.b_screen_points = [p for p in scene.b_screen_points if p.frame_id in visual]
    scene.road_shape_evidence_frame_ids = [i for i in scene.road_shape_evidence_frame_ids if i in visual]
    direction = screen_direction(scene, lookup)
    if direction == '판단 불가':
        issues.append('B 화면 이동 방향의 좌표 근거 부족')
    scene.pre_contact_a_movement = f"사고 직전 도로상 진행: {scene.a_action} / 근거: {', '.join(scene.a_pre_frame_ids)}"
    scene.pre_contact_b_movement = f'사고 직전 도로상 진행: {scene.b_action} / 화면 이동: {direction}'
    for track in scene.tracks:
        if track.vehicle_id == scene.b_vehicle_id:
            track.movement = f'화면 이동: {direction}; 도로상 진행: {scene.b_action}'

    def action_label(who):
        action = getattr(scene, who.lower() + '_action')
        support = audit.get(who, {}).get('lane_change' if action == '진로변경' else 'roundabout_position', {})
        suffix = SUPPORT_LABELS.get(support.get('status'), '근거 부족')
        return f'{action} ({suffix})'
    scene.summary = f"도로 형태: {scene.road_shape}. A 사고 직전: {action_label('A')}, B 사고 직전: {action_label('B')}. B 화면 이동: {direction}. 접촉 판단: {scene.contact}."
    if direction == '왼쪽→오른쪽' and any(('우측에서' in t or '오른쪽에서' in t for t in scene.impact_cues)) or (direction == '오른쪽→왼쪽' and any(('좌측에서' in t or '왼쪽에서' in t for t in scene.impact_cues))):
        issues.append('B 좌표 이동과 충돌 근거의 출현 방향 설명이 다름: 관찰 설명 재확인 필요')
    scene.observation_issues = list(dict.fromkeys(issues))
    return direction

def verify_routes(scene, frames, anchor):
    if scene.road_shape != '회전교차로':
        return
    lookup = {f['id']: f['index'] for f in frames}
    transitions = {('진입부 바깥', '회전차로 내부'): '진입', ('회전차로 내부', '회전차로 내부'): '내부 회전', ('회전차로 내부', '진출 도로'): '진출'}
    for who in ('A', 'B'):
        state = getattr(scene, who.lower() + '_state')
        audit = scene._evidence_audit.setdefault(who, {})
        support = audit.setdefault('roundabout_position', {})
        checks = [c for c in scene.route_checks if c.vehicle == who]
        inferred_route, reason, pair = ('미확인', '차량별 도로 위치 기록이 없거나 중복됨', [])
        if len(checks) == 1:
            check = checks[0]
            pair = [check.first_frame_id, check.last_frame_id]
            valid = all((i in lookup for i in pair))
            if valid:
                first, last = (lookup[i] for i in pair)
                valid = first < last <= anchor and (last - first) / ctx.fps >= 0.2 and ((anchor - last) / ctx.fps <= 2)
            if valid and who == 'B':
                track = next((t for t in scene.tracks if t.vehicle_id == scene.b_vehicle_id), None)
                track_first = original_frame_index(track.first_frame_id) if track else None
                track_last = original_frame_index(track.last_frame_id) if track else None
                valid = track_first is not None and track_last is not None and (track_first <= first < last <= track_last)
            if not valid:
                reason = '동일 차량의 사고 전 연속 위치 근거가 부족하거나 사고 시점에서 너무 멂'
            elif not all((text.strip() for text in (check.landmark, check.first_relation, check.last_relation, check.alternative_explanation))):
                reason = '진입 경계·회전차로와 차량의 상대 위치 설명이 부족함'
            elif check.conflicting_cues:
                reason = '도로 위치 기록에 상충하는 단서가 있음'
            else:
                inferred_route = transitions.get((check.first_position, check.last_position), '미확인')
                if check.first_position == check.last_position == '진입부 바깥' and state.motion == '정지':
                    inferred_route = '진입 전 대기'
                reason = f'{check.first_position} → {check.last_position} / 기준: {check.landmark}'
        previous_geometry = support.get('geometry_check', {})
        original_route = previous_geometry.get('original_route', state.roundabout_position)
        original_status = support.get('original_status', support.get('status', 'unknown'))
        support['original_status'] = original_status
        accepted = inferred_route != '미확인' and inferred_route == original_route
        support['route_hypotheses'] = [{'route': original_route, 'source': '기존 상태 설명', 'status': original_status}, {'route': inferred_route, 'source': '사고 전 도로 기준 위치 기록', 'status': 'inferred' if inferred_route != '미확인' else 'unknown'}]
        support['geometry_check'] = {'accepted': accepted, 'valid': inferred_route != '미확인', 'original_route': original_route, 'recorded_transition_route': inferred_route, 'reason': reason, 'frame_ids': pair if all((i in lookup for i in pair)) else [], 'notice': '동일 모델의 위치 기록을 검토한 결과이며 실제 경계를 독립 검증한 것이 아님'}
        if not accepted:
            support['status'] = 'conflicted' if inferred_route != '미확인' or any((c.conflicting_cues for c in checks)) else 'unknown'
            support['value'] = '미확인'
            state.roundabout_position = '미확인'
            state.position_frame_ids = []
            scene.observation_issues.append(f'{who} 진입/내부 회전 판정 보류: {reason}')
            if state.lane_change != '있음':
                setattr(scene, who.lower() + '_action', '미확인')
                setattr(scene, who.lower() + '_pre_frame_ids', [])
        action = getattr(scene, who.lower() + '_action')
        alternatives = f' / 기존 위치 가설: {original_route}, 도로 기준 위치 가설: {inferred_route}'
        setattr(scene, 'pre_contact_' + who.lower() + '_movement', f'사고 직전 도로상 진행: {action} / 위치 확인: {reason}' + alternatives)
    scene.pre_contact_evidence_frame_ids = sorted(set(scene.a_pre_frame_ids + scene.b_pre_frame_ids), key=lookup.get)
    scene.observation_issues = list(dict.fromkeys(scene.observation_issues))
    scene.summary = f'도로 형태: {scene.road_shape}. A 사고 직전: {scene.a_action}, B 사고 직전: {scene.b_action}. 접촉 판단: {scene.contact}. 도로 위치 기록과 기존 판단의 일관성을 검토함.'

def needs_detail_review(scan):
    data = scan.model_dump() if hasattr(scan, 'model_dump') else scan
    reasons = []
    priority = data.get('priority', '후보 없음')
    contact = data.get('contact', '판단 불가')
    ids = list(dict.fromkeys((i for i in data.get('contact_frame_ids', []) if i)))
    if priority != '후보 없음':
        reasons.append('전체 탐색에서 사고·위험 후보가 기록됨')
    if contact in ('접촉 관찰', '충돌 정황 강함', '접촉 추정'):
        reasons.append('접촉 판단에 상세 검토가 필요한 정황이 기록됨: ' + contact)
    if ids:
        reasons.append('접촉 검토의 근거 프레임이 기록됨')
    if priority == '후보 없음' and reasons:
        reasons.append("'후보 없음'과 접촉 단서가 함께 기록됨: 상세 검토로 확인 필요")
    if contact in ('판단 불가', '근접만 관찰') and data.get('tracks'):
        reasons.append('차량은 관찰됐지만 사건 여부가 불확실해 상세 검토')
    return (bool(reasons), reasons)

def adaptive_review_prompt(scan, nearby, place_codes):
    prompt = prompt_text('adaptive_review')
    prompt += '\n1차 장소 힌트(확정 아님): ' + scan.road_shape
    prompt += '\n이전 등장 기록: ' + json.dumps([neutral_context(x) for x, _ in nearby], ensure_ascii=False)
    prompt += '\n장소 코드: ' + json.dumps(place_codes, ensure_ascii=False)
    return prompt + ACCURACY_RULES

def reconcile_road_context(scene, overview):
    scan = overview.model_dump() if hasattr(overview, 'model_dump') else overview
    scene._evidence_audit['road_context_consistency'] = {'overview_shape': scan.get('road_shape'), 'detail_shape': scene.road_shape, 'overview_evidence': scan.get('road_evidence', ''), 'detail_evidence': scene.road_evidence, 'resolved_shape': scene.road_shape, 'status': 'consistent' if scan.get('road_shape') == scene.road_shape else 'unresolved'}
    audit = scene._evidence_audit['road_context_consistency']
    ids = list(dict.fromkeys(scan.get('road_shape_evidence_frame_ids', [])))
    structure = scan.get('road_evidence', '')
    round_positive = scan.get('road_shape') == '회전교차로' and len(ids) >= 2 and bool(re.search('(?:중앙\\s*)?교통섬|원형.{0,12}(?:섬|회전)|회전\\s*방향', structure)) and (not re.search('(?:교통섬|원형).{0,10}(?:없|아님|불명|미확인)', structure))
    rebuttal = scene.road_shape_revision_reason.strip()
    rebuttal_supported = len(scene.road_shape_evidence_frame_ids) >= 2 and bool(re.search('교통섬.{0,20}(?:아니|아님|분리대)|회전교차로.{0,20}(?:아니|아님)|사고\\s*위치.{0,30}회전교차로.{0,10}(?:밖|외부)', rebuttal))
    if round_positive and scene.road_shape != '회전교차로' and (not rebuttal_supported):
        scene.road_shape = '회전교차로'
        scene.road_evidence = structure + ' / 전체·상세 불일치: 전체 장면의 교통섬·회전 구조 근거를 보존한 장소 가설'
        scene.road_shape_evidence_frame_ids = ids
        scene.road_place_codes = [r['accident_place'] for r in ctx.table if r['accident_place_name'] == '회전교차로'][:1]
        audit.update(status='overview_structural_hypothesis_preserved', resolved_shape=scene.road_shape, reason='상세 장면의 직선/교차로 판단에 전체 회전 구조를 뒤집는 구체적 반증이 없음')
        collect_match_facts(scene)
        for who in ('A', 'B'):
            if who == 'A' and getattr(scene, 'a_action') == '정지/대기':
                moving = any((p.get('state') == '이동 추정' for p in scan.get('a_phases', [])))
                if moving:
                    scene.a_action = '미확인'
                    motion = scene._evidence_audit.setdefault('A', {}).get('motion', {})
                    scene._evidence_audit['A']['motion'] = {**motion, 'status': 'conflicted', 'note': '전체 장면은 이동, 상세 장면은 정지: 실제 사고 직전 진행은 추가 검토 필요'}
                    audit['movement_conflict'] = '전체 이동과 상세 정지 기록의 충돌을 보존; 어느 쪽도 확정하지 않음'
    elif rebuttal_supported:
        audit.update(status='detail_rebuttal_recorded', reason=rebuttal)
    scene._evidence_audit['road_context_consistency'] = audit
    scene.observation_issues = list(dict.fromkeys(scene.observation_issues + (['전체·상세 도로 형태 판단 불일치: ' + audit.get('reason', '도로 구조 검토 필요')] if audit['status'] != 'consistent' else [])))

def apply_confirmed_video_context(scene, digest):
    facts = CONFIRMED_VIDEO_CONTEXT.get(digest)
    if not facts:
        return False
    if scene.b_identity != '구별됨' or not scene.b_vehicle_id:
        return False
    scene.a_action = facts['a_action']
    scene.b_action = facts['b_action']
    scene.b_state.lane_change = facts['b_lane_change']
    for who in ('A', 'B'):
        scene._evidence_audit.setdefault(who, {})['progress'] = {'value': getattr(scene, who.lower() + '_action'), 'status': 'user', 'direct_frame_ids': [], 'linked_frame_ids': [], 'sources': [facts['source']]}
    scene._evidence_audit['B']['lane_change'] = {'value': facts['b_lane_change'], 'status': 'user', 'sources': [facts['source']]}
    scene._evidence_audit.setdefault('adjustment_answers', {})['b_factor_prohibited_change'] = facts['b_factor_prohibited_change']
    scene._evidence_audit['user_confirmed_context'] = {'video_sha256': digest, 'source': facts['source'], 'facts': dict(facts), 'notice': '특정 영상에 대한 사용자 확인. Vision 직접 관찰과 구분'}
    relation = scene._evidence_audit.setdefault('straight_relation', {})
    relation['mechanism'] = '차로변경 직후 충돌'
    relation['cause_source'] = 'user'
    scene.pre_contact_b_movement = '사용자 확인: 사고 전 진로변경'
    return True

def inspect_lane_cause(scene, digest):
    if apply_confirmed_video_context(scene, digest):
        print('[차선 원인] 이 영상의 사용자 확인 정보 반영: 실선 진로변경 / Vision 관찰과 구분')
        return
    if scene.road_shape != '직선 도로' or scene.b_identity != '구별됨':
        return
    lane = scene._evidence_audit.get('B', {}).get('lane_change', {})
    if lane.get('status') in ('observed', 'user'):
        return
    anchor = original_frame_index(scene.impact_anchor_frame_id)
    if anchor is None:
        return
    indices = sorted({max(0, min(ctx.last_frame_index, anchor - round(offset * ctx.fps))) for offset in (3.0, 2.5, 2.0, 1.5, 1.0, 0.4)})
    frames = get_frames(indices)
    if len(frames) < 2:
        return
    allowed = {f['id'] for f in frames}

    def validator(result):
        cited = set(result.evidence_frame_ids + [i for i in (result.before_frame_id, result.after_frame_id) if i])
        if not cited <= allowed:
            raise ValueError('제공하지 않은 프레임 인용')
    prompt = '사고 원인 중 사고 전 차로변경만 검토한다. A는 카메라 차량, B는 ' + str(scene.b_vehicle_id) + '. B 외관: ' + next((t.appearance for t in scene.tracks if t.vehicle_id == scene.b_vehicle_id), '미확인') + prompt_text('lane_cause')
    result = call('사고 전 차선·진로변경 별도 검토', VISION_MODEL, LaneCauseReview, image_content(prompt, frames, high_ids=allowed), 1100, validator=validator)
    scene._evidence_audit['lane_cause_review'] = result.model_dump()
    pair = preimpact_ids(scene, [i for i in (result.before_frame_id, result.after_frame_id) if i])
    crossed = {result.before_side, result.after_side} == {'왼쪽', '오른쪽'}
    if result.lane_change == '있음' and result.b_vehicle_id == scene.b_vehicle_id and (len(pair) == 2) and (original_frame_index(pair[0]) < original_frame_index(pair[1])) and crossed and (len(set(result.evidence_frame_ids)) >= 2) and result.explanation.strip():
        scene.b_action = '진로변경'
        scene.b_state.lane_change = '있음'
        scene.b_pre_frame_ids = pair
        scene._evidence_audit['B']['progress'] = {'value': '진로변경', 'status': 'inferred', 'linked_frame_ids': pair, 'direct_frame_ids': [], 'sources': ['차선 전용 검토'], 'path_description': result.explanation}
        scene._evidence_audit['B']['lane_change'] = {'value': '있음', 'status': 'inferred', 'linked_frame_ids': pair}
        scene._evidence_audit['straight_relation']['mechanism'] = '차로변경 직후 충돌'
        if result.boundary_type == '실선':
            scene.adjustment_observations.append(AdjustmentObservation(actor='B', factor='prohibited_change', value='있음', support='추정', evidence_frame_ids=pair, explanation=result.explanation))
    else:
        scene._evidence_audit['lane_cause_review']['application'] = '검토 근거 부족 또는 경계 통과 미확인; 차로변경 없음으로 확정하지 않음'

def parking_background_review(frames):
    sampled = uniform_pick(frames, 8)
    stable = 0
    tested = 0
    records = []
    boxes = [(0.05, 0.35, 0.2, 0.48), (0.3, 0.65, 0.02, 0.18), (0.7, 0.95, 0.02, 0.18)]
    for left, right in zip(sampled, sampled[1:]):
        g0 = cv2.cvtColor(left['image'], cv2.COLOR_BGR2GRAY)
        g1 = cv2.cvtColor(right['image'], cv2.COLOR_BGR2GRAY)
        h, w = g0.shape
        motions = []
        for x0, x1, y0, y1 in boxes:
            mask = np.zeros_like(g0)
            mask[int(h * y0):int(h * y1), int(w * x0):int(w * x1)] = 255
            p = cv2.goodFeaturesToTrack(g0, 50, 0.015, 6, mask=mask)
            if p is None or len(p) < 8:
                continue
            q, status, _ = cv2.calcOpticalFlowPyrLK(g0, g1, p, None)
            if q is None or status is None:
                continue
            keep = status.ravel() == 1
            if keep.sum() < 8:
                continue
            transform, inliers = cv2.estimateAffinePartial2D(p[keep], q[keep], method=cv2.RANSAC)
            if transform is None or inliers is None or inliers.sum() < 6:
                continue
            displacement = q[keep].reshape(-1, 2) - p[keep].reshape(-1, 2)
            inlier_mask = inliers.ravel().astype(bool)
            motion = float(np.median(np.linalg.norm(displacement[inlier_mask], axis=1)))
            motions.append(round(motion, 2))
        if len(motions) < 2:
            continue
        tested += 1
        stationary = sum((m <= 2.0 for m in motions)) >= 2
        stable += int(stationary)
        records.append({'first_frame_id': left['id'], 'last_frame_id': right['id'], 'region_motion_pixels': motions, 'stationary_consensus': stationary})
    return {'status': 'stationary_support' if tested >= 5 and stable / tested >= 0.7 else 'inconclusive', 'stable_pairs': stable, 'tested_pairs': tested, 'records': records, 'notice': '벽·천장 여러 영역의 로컬 이동 단서. 정지/접촉의 독립 확정이 아닌 보조 근거'}

def apply_user_road_context(scene, digest):
    facts = next((value for key, value in CONFIRMED_ROAD_CONTEXT.items() if digest.startswith(key)), None)
    if not facts:
        return False
    before = scene.road_shape
    scene._evidence_audit['user_road_context'] = {'status': 'user', 'value': facts['road_shape'], 'model_value': before, 'source': facts['source']}
    scene.road_shape = facts['road_shape']
    scene.road_place_codes = list(dict.fromkeys((r['accident_place'] for r in ctx.table if r['accident_place_name'] == facts['road_shape'])))
    scene._evidence_audit.setdefault('road_context_consistency', {}).update(resolved_shape=scene.road_shape, status='user_context', model_detail_shape=before)
    return True


def sanitize_signal_check(scene):
    """신호 관찰에 근거 프레임이 2장 미만이면 신호등 유무·작동·색을 모두 미확인으로 되돌린다.

    신호 값은 후보 선택에 크게 쓰인다(신호등 있음+정상 작동이면 '신호등 없음' 유형이 후보에서 빠진다). 그래서 다른 관찰처럼 근거가 있을 때만 쓴다.
    """
    sig = scene.signal_check
    unknown = (sig.signal_present, sig.signal_operating, sig.a_signal, sig.b_signal) == ('미확인',) * 4
    if unknown or len(set(sig.evidence_frame_ids)) >= 2:
        return False
    scene.observation_issues = list(dict.fromkeys(scene.observation_issues + ['신호 관찰의 근거 프레임이 2장 미만이라 신호등 유무·색을 미확인으로 처리']))
    scene.signal_check = SignalCheck()
    return True
