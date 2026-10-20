"""사용자가 확정한 사고 유형과 가감요소 답변으로 결과를 만든다. 이 모듈은 AI 를 호출하지 않는다 (판례 AI 비교는 ai_compare 가 미리 만들어 넘긴다).

규칙 계산은 avly 의 evaluate_rule_input 을 그대로 쓰고, 설명 문장은 avly.explain 이 미리 써 둔 문장으로 조립한다.
"""

from app import catalog
from app.worker import compare
from avly import explain
from avly.pdf_reference import web_pdf_reference
from avly.constants import REPORT_NOTICE
from avly.tables import LAW_ARTICLES_BY_TYPE

STATUS_TEXT = {
    "final": "등록된 가감요소를 모두 확인해서 계산한 예상 비율이에요.",
    "partial": "확인된 가감요소만 반영했어요. 확인하지 못한 요소가 있어서 실제 비율은 달라질 수 있어요.",
    "base_only": "이 사고 유형은 가감요소가 아직 등록되지 않아 기본 비율만 안내해요.",
    "unresolved": "과실표에서 맞는 사고 유형을 찾지 못해 과실비율을 안내할 수 없어요. 상황 설명만 참고해 주세요.",
}
WHO = {"A": "내 차", "B": "상대 차"}   # 규칙 엔진의 A = 블랙박스 차량 = 내 차


def _article_label(article) -> str:
    parts = str(article).split("의")
    return "도로교통법 제" + parts[0] + "조" + ("의" + parts[1] if len(parts) > 1 else "")


def _laws(accident_type_id: int) -> list[dict]:
    laws = []
    for article in LAW_ARTICLES_BY_TYPE.get(accident_type_id, []):
        e = explain.explain_law(article)
        laws.append({"article": str(article), "label": _article_label(article), "name": e["name"], "easy": e["easy"],
                     "missing": e["missing"], "reviewed": e["reviewed"]})
    return laws


def _pair(fault: dict | None) -> dict | None:
    return None if fault is None else {"me": fault["A"], "other": fault["B"]}


def _item(entry: dict, **extra) -> dict:
    who = WHO[entry["actor"]]
    e = entry.get("display", {}).get(who) or explain.explain_factor(entry["factor"], entry["delta_pp"], who)
    return {"factor": entry["factor"], "who": who, "title": e["title"], "easy": e["easy"], "effect": e["effect"],
            "delta_pp": entry["delta_pp"], "reviewed": e["reviewed"], **extra}


def _state(config_registered: bool, out: dict) -> str:
    if not config_registered:
        return "base_only"
    if out.get("final_fault") is not None:
        return "final"
    if out.get("adjusted_fault") is not None:
        return "partial"
    return "base_only"   # 규칙표와 CSV 가 달라 가감을 적용하지 못한 경우


def _with_comparison(case: dict, option: dict, ai: dict | None) -> dict:
    """AI 비교가 있으면 그것을, 없으면 규칙 비교를 붙인다."""
    if ai is None:
        return {**case, "comparison": {**compare.compare_case(case, option), "source": "rule"}}
    return {**case, "comparison": ai["comparison"], "digest": ai["digest"]}


def build_result(snapshot: dict, confirmed: dict, related_cases: list[dict], comparisons: dict | None = None) -> dict:
    from avly.adjustments import evaluate_rule_input   # 무거운 모듈이라 worker 에서만 불러온다

    situation = snapshot["situation"]
    comparisons = comparisons or {}
    related_cases = [{k: v for k, v in c.items() if k != "_text"} for c in related_cases]   # AI 비교용 본문은 결과에 싣지 않는다
    common = {
        "summary": situation.get("summary"),
        "situation": {k: situation.get(k) for k in ("road_shape", "my_action", "other_action", "contact")},
        "timeline": snapshot["timeline"],
        "impact": snapshot["impact"],
        "related_cases": related_cases,
        "reference_candidates": [c for c in situation.get("candidates", [])],
        "notice": REPORT_NOTICE,
        "pdf_reference": web_pdf_reference(confirmed.get("accident_type_id"), confirmed.get("role"), catalog.settings.fault_table_path),
    }
    type_id, role = confirmed.get("accident_type_id"), confirmed.get("role")
    if type_id is None:
        return {**common, "state": "unresolved", "accident_type": None, "fault": None, "steps": [], "laws": [],
                "adjustments": {"registered": False, "applied": [], "not_applied": [], "pending": []},
                "explanation": {"base": None, "situation": None, "status": STATUS_TEXT["unresolved"]}}

    row = catalog.get_row(type_id)
    option = catalog.orient(row, role)
    common["related_cases"] = [_with_comparison(c, option, comparisons.get(c.get("case_id"))) for c in related_cases]
    scenario = {
        "scenario_id": f"{type_id}:{role}:confirmed", "accident_type": type_id, "dashcam_table_role": role,
        "eligible_for_adjustment": True,   # 사용자가 유형과 역할을 확정했다
        "base_fault": {"A": option["base_me"], "B": option["base_other"]},   # 엔진은 내 차(A) 기준으로 읽는다
        "table_progress": {"A": row.a_progress, "B": row.b_progress},       # 표의 A/B 순서
    }
    out = evaluate_rule_input({"scenarios": [scenario], "factors": catalog.answers_to_facts(confirmed.get("answers", {}))}, csv_path=catalog.settings.fault_table_path)["results"][0]
    registered = bool(out.get("source"))
    state = _state(registered, out)

    base_text = explain.explain_base(option["base_me"], option["base_other"], option["place"],
                                     option["my_progress"], option["other_progress"])
    steps = [{"kind": "base", "title": base_text["text"], "easy": base_text["situation"], "effect": None, "who": None,
              "factor": None, "delta_pp": None, "me": option["base_me"], "other": option["base_other"]}]
    me = option["base_me"]
    applied = []
    for entry in out["applied_adjustments"]:
        item = _item(entry)
        me = max(0, min(100, me + entry["delta_pp"] if entry["actor"] == "A" else me - entry["delta_pp"]))
        steps.append({"kind": "adjustment", "title": item["title"], "easy": item["easy"], "effect": item["effect"],
                      "who": item["who"], "factor": item["factor"], "delta_pp": item["delta_pp"], "me": me, "other": 100 - me})
        applied.append(item)

    return {
        **common,
        "state": state,
        "accident_type": {k: option[k] for k in ("accident_type_id", "role", "place", "feature", "my_progress", "other_progress")},
        "fault": {"base": {"me": option["base_me"], "other": option["base_other"]}, "adjusted": _pair(out.get("adjusted_fault")),
                  "final": _pair(out.get("final_fault")), "bounds_applied": bool(out.get("bounds_applied"))},
        "steps": steps,
        "adjustments": {
            "registered": registered, "applied": applied,
            "not_applied": [_item(e, reason=e.get("reason")) for e in out["not_applied"]],
            "pending": [_item(e, question=(e.get("display", {}).get(WHO[e["actor"]]) or explain.explain_factor(e["factor"], e["delta_pp"], WHO[e["actor"]]))["question"])
                        for e in out["pending"]],
        },
        "laws": _laws(type_id),
        "explanation": {"base": base_text["text"], "situation": base_text["situation"], "status": STATUS_TEXT[state]},
    }
