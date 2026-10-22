"""라벨(정답) 영상의 분석 결과를 정답과 나란히 보고 확인하는 검수 페이지를 만든다. 더블클릭 또는 http://localhost:5173/label-review.html 로 연다.

    docker compose exec -T worker python tools/make_label_review_page.py --results /app/labels/_eval_openai > docs/review/label-review.html

- 먼저 tools/evaluate_labels.py 로 영상을 분석해 --results 폴더에 결과를 만들어 둔다.
- 영상마다 정답(라벨)과 AI 결과, 사고 흐름·타임라인, 판례(정답 유형과 AI가 고른 유형)를 한 카드에 모아 보여 준다.
- 판례는 서비스가 쓰는 코드(CaseService)로 DB 와 판례 API 에서 읽는다. 그래서 DB 에 접속되는 worker 컨테이너에서 실행한다.
"""
import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BACKEND), str(BACKEND / "model"), str(Path(__file__).resolve().parent)]

import evaluate_labels as ev  # noqa: E402
from app import catalog  # noqa: E402
from app.worker import snapshot  # noqa: E402

CASES_PER_TYPE = 3


def type_view(type_id: int | None) -> dict | None:
    """과실표 유형 하나를 쉬운 말과 원래 표기로."""
    row = catalog.get_row(type_id) if type_id is not None else None
    if row is None:
        return None
    opt = catalog.orient(row, "A")   # 표의 A 기준(블랙박스 차량이 A)
    return {"id": row.id, "place": opt["easy"]["place"], "feature": opt["easy"]["feature"], "a": opt["easy"]["my_progress"], "b": opt["easy"]["other_progress"],
            "official": f"{row.place} · {row.feature} · A {row.a_progress} / B {row.b_progress}", "base_a": row.negligence_a, "base_b": row.negligence_b}


def cases_view(service, type_id: int | None) -> list[dict]:
    if type_id is None:
        return []
    try:
        rows = service.related_for(type_id)
    except Exception as exc:   # 판례 조회가 실패해도 페이지는 만든다
        return [{"error": f"{type(exc).__name__}: {str(exc)[:120]}"}]
    return [{"court": c["court"], "date": c["date"], "case_number": c["case_number"], "summary": (c["summary"] or "")[:420], "source": c["source_label"],
             "verified": bool(c["verified"]), "relevance": c["relevance_status"], "limit": c.get("comparison_limit") or ""} for c in rows[:CASES_PER_TYPE]]


def build(results: Path, labels: Path) -> dict:
    from app.repository import Repository
    from app.worker.cases import make_cases
    service = make_cases(Repository())
    evaluation = {r["video"]: r for r in json.loads((results / "evaluation.json").read_text(encoding="utf-8"))}
    videos = []
    for case in ev.load_cases(labels, set(evaluation)):
        row = evaluation[case["name"]]
        if row.get("error") or not row.get("result_file"):
            videos.append({"name": case["name"], "category": case["category"], "error": row.get("error") or "결과 파일 없음"})
            continue
        data = json.loads((results / row["result_file"]).read_text(encoding="utf-8"))
        snap = snapshot.from_model_result(data, "eval")
        situation = snap["situation"]
        default = situation["candidates"][situation["default_index"]] if situation["default_index"] is not None else None
        ai_type = default["accident_type_id"] if default else None
        label = case["label"]
        scene = data["scene"]
        flow_issues = [i for i in scene.get("observation_issues", []) if str(i).startswith("사고 흐름")]
        videos.append({
            "name": case["name"], "category": case["category"], "file": f"backend/labels/{case['category']}/{case['name']}.mp4",
            "label": {"type": type_view(case["type"]), "place": label["사고 장소"]["명칭"], "feature": label["사고 장소 특성"]["명칭"], "a": case["a"], "b": case["b"],
                      "ratio_a": label.get("차량 A 과실비율"), "ratio_b": label.get("차량 B 과실비율"), "ratio_any": label.get("과실비율(원본에 차량 구분 없음)"), "date": label.get("영상 날짜(원본)")},
            "ai": {"road_shape": scene["road_shape"], "a_action": scene["a_action"], "b_action": scene["b_action"], "contact": scene["contact"], "object": scene["accident_object"],
                   "summary": scene.get("summary") or "", "no_match": data.get("no_match_reason") or "", "needs_check": situation.get("needs_check", []),
                   "top": type_view(ai_type), "top_role": default["role"] if default else None,
                   "candidates": [{"id": c["accident_type_id"], "role": c["role"], "feature": c["easy"]["feature"], "a": c["easy"]["my_progress"], "b": c["easy"]["other_progress"], "source": c["source"]} for c in situation["candidates"][:5]],
                   "models": row.get("models", []), "tokens": row.get("tokens"), "detail_review": row.get("detail_review")},
            "auto": {k: row.get(k) for k in ("object_ok", "place_ok", "a_ok", "b_ok", "any_ok", "top1_ok", "blackbox_is", "top1_role")},
            "timeline": {"events": [{"kind": e["kind"], "stage": e.get("stage"), "actor": e.get("actor"), "start": e["start_sec"], "end": e["end_sec"], "text": e.get("description") or "",
                                     "certainty": e.get("certainty") or ""} for e in snap["timeline"]], "note": snap.get("timeline_note") or "", "flow_issues": flow_issues},
            "cases": {"label_type": cases_view(service, case["type"]), "ai_type": cases_view(service, ai_type) if ai_type not in (None, case["type"]) else None, "ai_type_id": ai_type},
        })
    order = {"사거리 교차로": 0, "주차장": 1, "차도와 차도가 아닌 장소": 2}
    videos.sort(key=lambda v: (order.get(v["category"], 9), v["name"]))
    return {"videos": videos, "generated_from": results.name}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--labels", type=Path, default=BACKEND / "labels")
    args = parser.parse_args(argv)
    template = (Path(__file__).resolve().parent / "label_review_template.html").read_text(encoding="utf-8")
    payload = json.dumps(build(args.results, args.labels), ensure_ascii=False).replace("</", "<\\/")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(template.replace("__DATA__", payload))


if __name__ == "__main__":
    main()
