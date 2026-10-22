"""사용자가 확정한 사고 상황과 AI 가 영상에서 본 움직임이 어긋나는지 살핀다. AI 를 호출하지 않는다.

AI 가 본 움직임(avly 의 Action)과 과실표의 진행 문구를 같은 '동작 묶음'으로 바꿔서 겹치는지 본다.
어느 한쪽이라도 알아볼 수 없으면(미확인, 기타, 교차로 진입, 표에 없는 표현, 여러 동작이 섞인 문구) 판단하지 않는다.
어긋난다고 잘못 단정하는 것보다 말없이 두는 쪽이 안전하기 때문이다.
"""

import re

AI_GROUP = {
    "직진": "straight", "진로변경": "lane_change", "좌회전": "left", "우회전": "right",
    "정지/대기": "stopped", "주차 중": "stopped", "후진": "reverse",
}

# 과실표 진행 문구에서 동작을 찾는 말. 신호색 같은 [대괄호]와 (괄호) 안의 설명은 지우고 본다.
TABLE_WORDS = {
    "lane_change": re.compile(r"진로변경|차로변경|합류"),
    "left": re.compile(r"좌회전"),
    "right": re.compile(r"우회전"),
    "uturn": re.compile(r"유턴"),
    "straight": re.compile(r"직진|추돌"),   # 추돌은 앞차를 향해 직진하다 부딪힌 쪽이다
    "stopped": re.compile(r"주차|정차"),
    "reverse": re.compile(r"후진"),
    "start": re.compile(r"출발"),
    "overtake": re.compile(r"추월"),
}

# 어긋난 것으로 보지 않는 짝: 앞차가 서 있거나 감속하는 것도 '직진 중인 차'로 적힌다(추돌 사고 등)
COMPATIBLE = {frozenset(("straight", "stopped"))}


def table_group(phrase: str) -> str | None:
    """과실표 진행 문구의 동작 묶음. 정확히 한 가지로 읽히지 않으면 None."""
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", phrase or "")
    found = {group for group, word in TABLE_WORDS.items() if word.search(text)}
    return found.pop() if len(found) == 1 else None


def situation_check(my_action: str | None, other_action: str | None, option: dict) -> dict:
    """option: catalog.orient() 가 만든, 사용자가 확정한 유형(내 차 기준). conflict 가 true 면 items 에 어긋난 쪽이 담긴다."""
    items = []
    for who, key, action in (("me", "my_progress", my_action), ("other", "other_progress", other_action)):
        seen, chosen = AI_GROUP.get(action or ""), table_group(option[key])
        if seen and chosen and seen != chosen and frozenset((seen, chosen)) not in COMPATIBLE:
            items.append({"who": who, "ai_action": action, "chosen": option["easy"][key]})
    return {"conflict": bool(items), "items": items}
