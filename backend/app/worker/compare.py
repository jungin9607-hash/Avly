"""판례와 내 사고의 공통점·차이점을 규칙으로 만든다. AI 를 쓰지 않는다.

비교하는 것은 판례 요약문(약 400자)과, 사용자가 확정한 사고 유형의 장소·사고 유형·진행 이름이다.
요약만 보므로 얕다. 그래서 퍼센트가 아니라 단계(match_level)로만 표시하고, 항상 한계를 함께 알려 준다.
"""
import re

MATCH_LABEL = {
    "same_type": "같은 사고 유형",
    "partial": "조건 일부 일치",
}
NOTE = "판례 요약문만 비교한 결과예요. 실제 사고와 같은 비율이 나온다는 뜻이 아니에요."
MAX_ITEMS = 4

# 판례 요약과 사고 유형 이름에서 서로 맞춰 볼 상황 단어
KEYWORDS = ["후진", "전진", "출차", "직진", "좌회전", "우회전", "진로변경", "차로변경", "추돌", "정차", "주차",
            "회전교차로", "교차로", "합류", "역주행", "중앙선", "추월", "급정지", "신호", "방향지시등"]


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))[:MAX_ITEMS]


def _matched_conditions(comparison_limit: str | None) -> list[str]:
    """모델이 API 판례에 적어 둔 '검색 일치 조건: 주차장 / 출차; ...' 에서 조건 이름을 꺼낸다."""
    match = re.search(r"검색 일치 조건:\s*([^;]+)", comparison_limit or "")
    return [c.strip() for c in match.group(1).split("/") if c.strip()] if match else []


def compare_case(case: dict, option: dict) -> dict:
    """case: 판례 한 건, option: 사용자가 확정한 유형(catalog.orient 결과)."""
    registered = case.get("relevance_status") == "registered_chart_reference"
    mine = " ".join(str(option.get(k) or "") for k in ("place", "feature", "my_progress", "other_progress"))
    summary = case.get("summary") or ""

    common, differences = [], []
    if registered:
        common.append(f"같은 사고 유형({option['place']} · {option['feature']})을 설명하는 손해보험협회 도표에 소개된 판례예요.")
    else:
        common += [f"판결 본문에서 '{c}' 조건이 확인돼요." for c in _matched_conditions(case.get("comparison_limit"))]
        if not common:
            common.append("교통사고 판결 본문에서 관련 조건이 확인된 판례예요.")
    for word in KEYWORDS:
        in_case, in_mine = word in summary, word in mine
        if in_case and in_mine:
            common.append(f"'{word}' 상황이 판례와 내 사고에 모두 있어요.")
        elif in_case:
            differences.append(f"판례에는 '{word}' 상황이 나오지만 내 사고 유형에는 없어요.")
        elif in_mine and summary:
            differences.append(f"내 사고의 '{word}' 상황은 이 판례 요약에서 확인되지 않아요.")
    limit = (case.get("comparison_limit") or "").strip()
    if registered and limit:
        differences.insert(0, limit)
    elif not registered:
        differences.insert(0, "신호, 진행 방식, 접촉 위치가 실제 영상과 같은지는 별도 확인이 필요해요.")
    if not differences:
        differences.append("요약문만으로는 뚜렷한 차이를 찾지 못했어요. 판결 원문과 실제 사고 상황을 함께 확인해 주세요.")
    level = "same_type" if registered else "partial"
    return {"match_level": level, "match_label": MATCH_LABEL[level], "common": _dedupe(common),
            "differences": _dedupe(differences), "note": NOTE}
