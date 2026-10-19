"""타임라인 생성과 저장."""
import math
from pathlib import Path
from .constants import TIMELINE_NOTICE


def build_timeline(scene, frames):
    data = scene.model_dump() if hasattr(scene, 'model_dump') else scene
    times = {}
    for frame in frames:
        frame_id, sec = (frame.get('id'), frame.get('sec'))
        if not frame_id or sec is None:
            continue
        try:
            sec = float(sec)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(sec) or sec < 0:
            continue
        if frame_id in times and (not math.isclose(times[frame_id], sec, abs_tol=1e-08)):
            raise ValueError(f'같은 프레임의 시간값이 다릅니다: {frame_id}')
        times[frame_id] = sec
    events, warnings = ([], [])

    def append_event(kind, actor, ids, description, certainty, evidence='', interval=False):
        ids = list(dict.fromkeys((i for i in ids if i)))
        if not ids:
            warnings.append(f'{kind}: 시간을 연결할 근거 프레임이 없어 표시하지 않음')
            return
        missing = [i for i in ids if i not in times]
        if missing:
            warnings.append(f'{kind}: 시간값이 없는 프레임 때문에 표시하지 않음: ' + ', '.join(missing))
            return
        if interval and times[ids[0]] > times[ids[-1]]:
            warnings.append(f'{kind}: 시작과 끝 순서가 맞지 않아 표시하지 않음')
            return
        ordered = sorted(ids, key=lambda i: times[i])
        events.append({'kind': kind, 'actor': actor, 'start_sec': times[ordered[0]], 'end_sec': times[ordered[-1]], 'description': description, 'certainty': certainty, 'evidence_frame_ids': ordered, 'evidence_text': evidence, 'time_basis': '프레임 이미지의 sec', 'interval_meaning': '기록된 관찰 구간' if interval else '인용된 근거 프레임의 시간 범위'})
    states = {'이동 추정': 'A(블랙박스 차량)가 이동한 것으로 추정됨.', '정지 추정': 'A(블랙박스 차량)가 정지한 것으로 추정됨.', '판단 불가': 'A(블랙박스 차량)의 이동 여부를 판단하기 어려움.'}
    for phase in data.get('a_phases', []):
        state = phase.get('state', '판단 불가')
        append_event('A 움직임', 'A', [phase.get('first_frame_id'), phase.get('last_frame_id')], states.get(state, 'A 차량의 움직임을 확인하기 어려움.'), state, phase.get('background_evidence', ''), interval=True)
    b_id = data.get('b_vehicle_id')
    b_tracks = [t for t in data.get('tracks', []) if b_id and t.get('vehicle_id') == b_id]
    if len(b_tracks) == 1:
        track = b_tracks[0]
        b_identified = data.get('b_identity') == '구별됨'
        append_event('B 확인 구간', 'B', [track.get('first_frame_id'), track.get('last_frame_id')], 'B로 선택된 상대 차량이 확인된 구간.' if b_identified else '접촉 상대 B의 후보 차량이 기록된 구간. 차량 구별은 추가 확인 필요.', data.get('b_identity', '판단 불가'), track.get('appearance', '') + ' / ' + track.get('movement', ''), interval=True)
    elif b_id:
        warnings.append('B 확인 구간: 선택된 차량 기록이 없거나 중복되어 표시하지 않음')
    contact = data.get('contact', '판단 불가')
    contact_descriptions = {'접촉 관찰': 'AI가 A와 상대 차량의 접촉으로 판단한 장면이 관찰됨.', '충돌 정황 강함': 'A와 상대 차량 사이에 충돌 정황이 강하게 관찰됨. 직접 접촉 확정과는 구분됨.', '접촉 추정': 'A와 상대 차량의 접촉이 의심되는 정황이 관찰됨.', '근접만 관찰': 'A와 상대 차량의 근접이 관찰됨. 접촉 여부는 확인되지 않음.', '판단 불가': '접촉 여부를 판단하기 어려운 구간.'}
    contact_ids = data.get('contact_frame_ids', [])
    if contact_ids:
        append_event('접촉 근거 구간', 'A/B' if data.get('b_identity') == '구별됨' and b_id else 'A/상대 후보', contact_ids, contact_descriptions.get(contact, contact_descriptions['판단 불가']), contact, data.get('contact_evidence', ''))
    elif data.get('impact_anchor_frame_id'):
        warnings.append('접촉 근거 구간: 직접 연결된 근거 프레임 없음. 분석 중심 시각은 충돌 시각으로 표시하지 않음')
    unique = {}
    for event in events:
        key = (event['kind'], event['start_sec'], event['end_sec'], event['description'])
        unique[key] = event
    events = sorted(unique.values(), key=lambda e: (e['start_sec'], e['end_sec'], e['kind']))
    frame_times = [{'id': i, 'sec': s} for i, s in sorted(times.items(), key=lambda p: (p[1], p[0]))]
    return {'timeline': events, 'timeline_warnings': list(dict.fromkeys(warnings)), 'timeline_notice': TIMELINE_NOTICE, 'frame_times': frame_times}

def timeline_lines(events):
    lines = []
    for event in events:
        start, end = (event['start_sec'], event['end_sec'])
        label = f'{start:.2f}초' if abs(end - start) < 1e-08 else f'{start:.2f}~{end:.2f}초'
        lines.append(f"{label}: {event['description']}")
    return lines

def print_timeline(payload):
    print('\n[사고 진행 타임라인 — 기록된 관찰 구간]')
    lines = timeline_lines(payload['timeline'])
    print('\n'.join(lines) if lines else '시간을 연결할 관찰 기록이 없습니다.')
    print('안내:', payload['timeline_notice'])
    if payload['timeline_warnings']:
        print('[시간 연결 확인]', ' / '.join(payload['timeline_warnings']))

def save_timeline_text(result_path, payload, video_name=None):
    destination = Path(result_path).with_name(Path(result_path).stem + '_timeline.txt')
    lines = ['에블리 | 사고 진행 타임라인']
    if video_name:
        lines.append('영상: ' + str(video_name))
    lines.extend(['A: 블랙박스 차량 / B: 접촉 상대 차량', '', *timeline_lines(payload['timeline'])])
    if not payload['timeline']:
        lines.append('시간을 연결할 관찰 기록이 없습니다.')
    lines.extend(['', payload['timeline_notice']])
    if payload['timeline_warnings']:
        lines.extend(['', '시간 연결 확인:', *payload['timeline_warnings']])
    destination.write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')
    return destination

def major_accident_timeline(payload, limit=4):
    events = list((payload or {}).get('timeline') or [])
    candidates = []
    for event in events:
        kind = event.get('kind', '')
        start, end = (event.get('start_sec'), event.get('end_sec'))
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            continue
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or (end < start):
            continue
        if not event.get('evidence_frame_ids'):
            continue
        if kind == '접촉 근거 구간':
            certainty = event.get('certainty', '판단 불가')
            if certainty == '접촉 관찰':
                label = '접촉 장면 관찰'
            elif certainty in ('충돌 정황 강함', '접촉 추정'):
                label = '충돌 의심 장면 (접촉 확인 필요)'
            elif certainty == '근접만 관찰':
                label = '차량 근접 장면 (접촉 미확인)'
            else:
                label = '접촉 여부 확인이 필요한 장면'
            priority = 0
        elif kind == 'B 확인 구간':
            label = '상대 차량 확인' if event.get('certainty') == '구별됨' else '상대 차량 후보 확인 (식별 필요)'
            priority = 1
        elif kind == 'A 움직임':
            certainty = event.get('certainty', '판단 불가')
            if certainty == '이동 추정':
                label = '내 차 이동 추정'
            elif certainty == '정지 추정':
                label = '내 차 정지 추정'
            else:
                continue
            priority = 2
        else:
            continue
        candidates.append((priority, float(start), float(end), label, event))
    contact = sorted((e for e in candidates if e[0] == 0), key=lambda e: (e[1], e[2]))
    others = sorted((e for e in candidates if e[0] != 0), key=lambda e: (e[1], e[0], e[2]))
    selected = contact[:1]
    seen = {(e[0], e[3]) for e in selected}
    for e in others:
        key = (e[0], e[3])
        if key in seen:
            continue
        selected.append(e)
        seen.add(key)
        if len(selected) >= limit:
            break
    selected.sort(key=lambda e: (e[1], e[2], e[0]))
    lines = []
    for _, start, end, label, _ in selected:
        timestamp = f'{start:.2f}초' if abs(end - start) < 1e-08 else f'{start:.2f}~{end:.2f}초'
        lines.append(f'• {timestamp} | {label}')
    return lines
