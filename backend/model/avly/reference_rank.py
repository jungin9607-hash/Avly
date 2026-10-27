"""참고 후보를 고르는 순서. 영상에 적용된다고 확정하지 못한 과실표 행 중 무엇을, 어떤 순서로 보여 줄지 정한다.

표준 라이브러리만 쓴다. (adjustments.py 의 reference_scenarios 가 불러 쓰고, 서버의 snapshot.py 도 soft_actions 를 쓴다)

정렬 기준 (앞에 있을수록 먼저):
1. 현재 관찰과 진행이 어긋난 수가 적을수록
2. AI 가 가리킨 장소(road_place_codes)의 행일수록. 도로 형태가 '교차로'뿐이면 신호등 있음/없음/T자형이 모두 통과하므로, 장소 코드로 먼저 가른다.
   (필터가 아니라 우선순위다. 코드가 틀려도 후보가 사라지지 않는다)
3. AI 가 기록한 내 차·상대 차 움직임과 표의 진행이 더 많이 맞을수록
   - 검증을 통과하지 못해 '미확인'으로 지워진 움직임도 모델이 기록한 값(maneuver_checks)으로 되살려 참고한다. 확정 값이 아니라 순서를 정하는 용도다.
4. 점수가 높을수록. 단 '신호 조건 미확인'은 감점하지 않는다. 신호 색을 못 읽었다는 이유로 신호 유형이 늘 뒤로 밀리면
   노면표시 위반 같은 유형이 어떤 영상에서든 먼저 나오기 때문이다.
5. 가정이 적을수록, 유형 번호가 작을수록
AI 가 기록한 움직임과 반대인 후보(적합도가 마이너스)는 맞는 후보가 있으면 보여 주지 않는다.
같은 장소·사고 유형(feature)은 한 번씩 먼저 보여 주고, 자리가 남으면 그다음 후보로 채운다.
"""

import re

REFERENCE_LIMIT = 3   # 보여 줄 (유형, 내 차 역할) 개수
UNKNOWN = ('미확인', '기타', '', None)
SIGNAL_NOTE = '신호 조건'
DECORATION = re.compile(r'\[[^\]]*\]|\([^)]*\)')   # [신호색]과 (차로 설명)은 동작이 아니라 조건이다


def _get(item, key):
    return item.get(key) if isinstance(item, dict) else getattr(item, key, None)


def soft_actions(a_action, b_action, maneuver_checks=()):
    """{'A': 내 차 움직임 또는 None, 'B': 상대 차 움직임 또는 None}.

    검증을 통과한 값(a_action, b_action)이 있으면 그것을, 없으면 모델이 기록한 사고 직전 진행을 쓴다. 근거가 '미확인'인 기록은 쓰지 않는다.
    """
    out = {'A': a_action, 'B': b_action}
    for check in maneuver_checks or ():
        who, action, support = _get(check, 'vehicle'), _get(check, 'action'), _get(check, 'support')
        if who in out and out[who] in UNKNOWN and action not in UNKNOWN and support != '미확인':
            out[who] = action
    return {who: (value if value not in UNKNOWN else None) for who, value in out.items()}


def action_fit(option, soft, progress_actions):
    """option 의 a_progress/b_progress(블랙박스 차량 기준)가 AI 가 기록한 움직임과 맞으면 +1, 어긋나면 -1 씩 더한다."""
    fit = 0
    for who, expected in (('A', option['a_progress']), ('B', option['b_progress'])):
        action, choices = soft.get(who), progress_actions(DECORATION.sub('', expected))   # '직진 (좌회전 노면표시차로)' 를 좌회전으로도 읽지 않도록
        if action and choices:
            fit += 1 if action in choices else -1
    return fit


def signal_neutral(assessment):
    """(점수, 가정 수)에서 '신호 조건 미확인' 때문에 깎인 만큼을 되돌린다."""
    pending = sum(1 for note in assessment['unresolved_conditions'] if SIGNAL_NOTE in note)
    return assessment['score'] + 0.5 * pending, assessment['assumption_count'] - pending


def order_references(candidates, soft, progress_actions, preferred_places=(), limit=REFERENCE_LIMIT):
    """candidates: [(row, [(assessment, option), ...]), ...] → 보여 줄 [(row, [option, ...])]. 옵션 수의 합은 limit 이하.

    preferred_places: AI 가 가리킨 장소 번호(accident_place). 비어 있으면 장소로는 순서를 정하지 않는다."""
    scored = []
    for row, options in candidates:
        rated = []
        for assessment, option in options:
            fit = action_fit(option, soft, progress_actions)
            score, assumptions = signal_neutral(assessment)
            rated.append(((assessment['progress_mismatch_count'], -fit, -score, assumptions), option))
        rated.sort(key=lambda item: item[0])   # 같은 점수면 들어온 순서(역할 A, B)를 유지한다
        best = rated[0][0]
        kept = [option for key, option in rated if key[:2] == best[:2]]   # 가장 잘 맞는 역할만 남긴다 (맞지 않는 쪽 역할은 버린다)
        place = 0 if row['accident_place'] in preferred_places else 1
        scored.append(((best[0], place, *best[1:], row['accident_type']), row, kept))
    viable = [item for item in scored if item[0][2] <= 0]   # key[2] = -적합도. AI 가 기록한 움직임과 반대인 후보는, 맞는 후보가 하나라도 있으면 뺀다
    scored = viable or scored
    scored.sort(key=lambda item: item[0])
    first, rest, seen = [], [], set()
    for _, row, kept in scored:
        label = (row['accident_place_name'], row['accident_place_feature_name'])
        (rest if label in seen else first).append((row, kept))
        seen.add(label)
    chosen, count = [], 0
    for row, kept in first + rest:
        if count >= limit:
            break
        take = kept[:limit - count]
        chosen.append((row, take))
        count += len(take)
    return chosen
