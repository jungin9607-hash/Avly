"""모델 결과 JSON(avly 가 만든 것)을 서비스가 저장하는 '스냅샷'으로 줄인다.

원본은 2MB 가 넘고 내부 용어가 많아서 DB 에 그대로 넣지 않는다. 스냅샷에는 화면에 필요한 것만 담는다.
- situation: 사용자에게 보여줄 AI 의 사고 상황 판단과 과실표 후보 (my/other_action_hint: 검증은 못 통과했지만 모델이 기록한 움직임)
- timeline: 사고 타임라인 (구간 단위). kind 가 '사고 흐름'인 이벤트는 AI 가 쓴 사고 진행 단계다
- timeline_note: 상대 차가 처음 보인 뒤 접촉 장면까지의 시간 관계 한 문장 (없으면 None)
- impact: 충돌(접촉) 시점과 확실도
- adjustment_facts: 영상에서 관찰·추정한 가감요소 (질문의 AI 제안에 쓴다)
"""

from app import catalog
from avly.reference_rank import UNKNOWN, soft_actions

CONTACT_CONFIRMED = ("접촉 관찰", "충돌 정황 강함")
ACTOR = {"A": "me", "B": "other", "A/B": "both"}   # 모델의 A = 블랙박스 차량 = 내 차. A/B 는 두 차량의 접촉 구간


def _candidates(rule_input: dict) -> list[dict]:
    seen, out = set(), []
    for s in rule_input.get("scenarios", []):
        row = catalog.get_row(int(s["accident_type"]))
        role = s.get("dashcam_table_role")
        if row is None or role not in ("A", "B") or (row.id, role) in seen:
            continue
        seen.add((row.id, role))
        out.append({
            **catalog.orient(row, role),
            "source": "reference" if s.get("reference_only") else "matched",
            "eligible": bool(s.get("eligible_for_adjustment")),
            "note": s.get("scenario_status"),
        })
    order = {"matched": 0, "reference": 1}
    return sorted(out, key=lambda c: (order[c["source"]], not c["eligible"]))   # 정렬은 안정적이라 나머지 순서는 유지된다


def _timeline(events: list[dict]) -> list[dict]:
    return [{
        "kind": e["kind"],
        "stage": e.get("stage"),   # 사고 흐름 단계(접근/사고 직전/접촉/접촉 이후). 다른 종류의 이벤트는 None
        "actor": ACTOR.get(e.get("actor")),
        "start_sec": round(float(e["start_sec"]), 2),
        "end_sec": round(float(e["end_sec"]), 2),
        "description": e.get("description"),
        "certainty": e.get("certainty"),
        "evidence_text": e.get("evidence_text"),
    } for e in events]


def from_model_result(data: dict, engine: str) -> dict:
    scene = data["scene"]
    frames = {f["id"]: f["sec"] for f in data.get("overview_frames", []) + data.get("review_frames", [])}
    contact = scene.get("contact")
    confirmed_contact = contact in CONTACT_CONFIRMED
    candidates = _candidates(data.get("rule_engine_input", {}))
    default_index = 0 if candidates and candidates[0]["source"] == "matched" else None
    soft = soft_actions(scene.get("a_action"), scene.get("b_action"), scene.get("maneuver_checks"))
    needs_check = [] if confirmed_contact else ["직접 접촉 장면은 영상에서 확인되지 않았습니다."]
    if not candidates:
        needs_check.append("과실표에서 맞는 유형을 찾지 못했습니다. 아래에서 직접 골라 주세요.")
    return {
        "engine": engine,
        "model_version": data.get("version"),
        "accident_object": scene.get("accident_object"),
        "situation": {
            "summary": scene.get("summary"),
            "road_shape": scene.get("road_shape"),
            "my_action": scene.get("a_action"),
            "other_action": scene.get("b_action"),
            # 근거 검증을 통과하지 못해 '미확인'이 된 움직임도 모델이 기록한 값이 있으면 '추정'으로 알려 준다 (확정 값이 아니다)
            "my_action_hint": soft["A"] if scene.get("a_action") in UNKNOWN else None,
            "other_action_hint": soft["B"] if scene.get("b_action") in UNKNOWN else None,
            "contact": contact,
            "needs_check": needs_check,
            "technical_notes": list(scene.get("observation_issues", []))[:10],
            "candidates": candidates,
            "default_index": default_index,
        },
        "timeline": _timeline(data.get("timeline", [])),
        "timeline_note": data.get("timeline_relation"),   # 상대 차가 처음 보인 뒤 접촉 장면까지의 영상 속 시간 관계(AI 없이 만든 한 문장)
        "impact": {"sec": frames.get(scene.get("impact_anchor_frame_id")), "contact": contact, "confirmed": confirmed_contact},
        "adjustment_facts": [
            {"actor": f["actor"], "factor": f["factor"], "value": f["value"], "status": f["status"], "reason": f.get("reason")}
            for f in data.get("rule_engine_input", {}).get("factors", []) if f.get("status") in ("observed", "inferred")
        ],
        "video_sha256": data.get("video_sha256"),
        "csv_sha256": data.get("csv_sha256"),
    }


def stage_logs(data: dict) -> list[dict]:
    """모델 결과의 단계별 호출 기록을 analysis_stage_log 에 넣을 형태로 바꾼다."""
    logs = []
    for s in data.get("stages", []):
        usage = s.get("usage") or {}
        logs.append({
            "stage": s.get("stage"), "provider": "openai", "model": s.get("model"), "cached": bool(s.get("cached")),
            "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
        })
    return logs
