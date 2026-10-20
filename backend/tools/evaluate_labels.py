"""정답(라벨)이 있는 영상으로 사고 분석이 얼마나 맞는지 잰다. AI 를 실제로 부르므로 비용(또는 무료 한도)이 든다.

    python tools/evaluate_labels.py --results /tmp/eval [--only 주차장1,주차장2] [--labels labels]

- 영상: <labels>/주차장/*.mp4, 정답: <labels>/labels_주차장_한국어/*_한국어.json (CSV 과실표 번호와 A/B 진행 정보)
- 블랙박스 차량(영상 주인)은 항상 A 로 본다. 그래서 '맞았다'는 정답 유형 번호이면서 내 차 역할이 A 인 후보가 있다는 뜻이다.
- 같은 영상은 응답 캐시(--results 폴더)를 써서 두 번 부르지 않는다.
- 출력: 영상별로 AI 가 본 것과 정답을 나란히 보여 주는 표(마크다운)와 JSON. 어디서 틀렸는지(장소 / 행동 / 후보 걸러짐 / 후보 선택) 볼 수 있다.
"""
import argparse
import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BACKEND), str(BACKEND / "model")]

# 정답의 B 진행 정보를 모델의 행동 이름(Action)으로 옮긴 것. 모델의 표현이 정답 문구와 다르므로 '참고' 용도다.
EXPECTED_ACTIONS = {
    "통로 직진": {"직진"},
    "주차구역에서 직진 출자": {"주차 출차", "출발", "직진"},
    "주차구역에서 후진 출자": {"후진", "주차 출차"},
}
PARKING_SHAPES = {"주차장", "주차장/기타"}


def load_cases(labels_dir: Path, only: set[str] | None):
    cases = []
    for path in sorted((labels_dir / "labels_주차장_한국어").glob("*_한국어.json")):
        info = json.loads(path.read_text(encoding="utf-8"))["영상"]
        name = info["영상 이름"]
        video = labels_dir / "주차장" / f"{name}.mp4"
        if only and name not in only:
            continue
        cases.append({"name": name, "video": video, "type": info["사고 유형 코드"], "place_code": info["사고 장소"]["코드"],
                      "a": info["차량 A 진행 정보"]["명칭"], "b": info["차량 B 진행 정보"]["명칭"]})
    return cases


def analyze(video: Path, results: Path) -> dict:
    """영상 하나를 분석하고 모델이 저장한 결과 JSON 을 돌려준다."""
    from avly import pipeline
    from avly.context import ctx
    pipeline.run({"BACKEND_DIR": str(BACKEND), "VIDEO_FILE": str(video), "PICK_VIDEO": False,
                  "CSV_FILE": str(BACKEND / "model" / "avly" / "data" / "fault_table_car_to_car.csv"), "RESULTS_DIR": str(results),
                  "SHOW_PROCESS_LOGS": False, "USE_CACHE": True, "no_survey": True})
    return json.loads(Path(ctx.output_path).read_text(encoding="utf-8"))


def judge(case: dict, data: dict) -> dict:
    from app.worker import snapshot
    scene, snap = data["scene"], snapshot.from_model_result(data, "eval")
    situation = snap["situation"]
    candidates = [(c["accident_type_id"], c["role"], c["source"]) for c in situation["candidates"]]
    default = situation["candidates"][situation["default_index"]] if situation["default_index"] is not None else None
    return {
        "video": case["name"], "label_type": case["type"],
        "object_ok": scene["accident_object"] == "차대차",
        "place_ok": scene["road_shape"] in PARKING_SHAPES,
        "a_ok": scene["a_action"] in EXPECTED_ACTIONS.get(case["a"], set()),
        "b_ok": scene["b_action"] in EXPECTED_ACTIONS.get(case["b"], set()),
        "top1_ok": bool(default and default["accident_type_id"] == case["type"] and default["role"] == "A"),
        "any_ok": any(t == case["type"] and r == "A" for t, r, _ in candidates),
        "road_shape": scene["road_shape"], "a_action": scene["a_action"], "b_action": scene["b_action"], "contact": scene["contact"],
        "candidates": candidates[:4], "no_match_reason": data.get("no_match_reason") or "",
        "tokens": data.get("current_run_usage", {}).get("total_tokens"),
        "models": sorted({s.get("model") for s in data.get("stages", []) if s.get("model") and s.get("usage")}),
        "detail_review": data["pipeline"]["detail_review_required"],
    }


def table(rows: list[dict]) -> str:
    mark = lambda ok: "O" if ok else "X"
    out = ["| 영상 | 정답 유형 | 대상 | 장소 | 내 차 행동 | 상대 차 행동 | 후보에 정답 | 1순위 정답 | AI가 본 장소 / 내 차 / 상대 차 / 접촉 | 후보(유형, 역할) |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        out.append(f"| {r['video']} | {r['label_type']} | {mark(r['object_ok'])} | {mark(r['place_ok'])} | {mark(r['a_ok'])} | {mark(r['b_ok'])} | {mark(r['any_ok'])} | {mark(r['top1_ok'])} | "
                   f"{r['road_shape']} / {r['a_action']} / {r['b_action']} / {r['contact']} | {', '.join(f'{t}{role}' for t, role, _ in r['candidates']) or '없음'} |")
    n = len(rows) or 1
    out.append("")
    out.append(f"**{len(rows)}개 중** 차대차 {sum(r['object_ok'] for r in rows)}, 장소 {sum(r['place_ok'] for r in rows)}, 내 차 행동 {sum(r['a_ok'] for r in rows)}, "
               f"상대 차 행동 {sum(r['b_ok'] for r in rows)}, 후보에 정답 {sum(r['any_ok'] for r in rows)}, 1순위 정답 {sum(r['top1_ok'] for r in rows)} ({sum(r['top1_ok'] for r in rows) * 100 // n}%), "
               f"후보 없음 {sum(not r['candidates'] for r in rows)}")
    return "\n".join(out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--labels", type=Path, default=BACKEND / "labels")
    parser.add_argument("--results", type=Path, required=True, help="분석 결과와 응답 캐시를 저장할 폴더")
    parser.add_argument("--only", default="", help="쉼표로 구분한 영상 이름 (예: 주차장1,주차장2)")
    args = parser.parse_args(argv)
    args.results.mkdir(parents=True, exist_ok=True)
    cases = load_cases(args.labels, set(filter(None, args.only.split(","))) or None)
    rows = []
    for case in cases:
        started = time.time()
        try:
            rows.append(judge(case, analyze(case["video"], args.results)))
            print(f"{case['name']}: 완료 {time.time() - started:.0f}초", flush=True)
        except Exception as exc:   # 한 영상이 실패해도 나머지는 계속한다
            rows.append({"video": case["name"], "label_type": case["type"], "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                         **{k: False for k in ("object_ok", "place_ok", "a_ok", "b_ok", "top1_ok", "any_ok")}, "road_shape": "-", "a_action": "-",
                         "b_action": "-", "contact": "-", "candidates": []})
            print(f"{case['name']}: 실패 {rows[-1]['error']}", flush=True)
    (args.results / "evaluation.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (args.results / "evaluation.md").write_text(table(rows) + "\n", encoding="utf-8")
    print("\n" + table(rows))
    for r in rows:
        if r.get("error"):
            print("오류:", r["video"], r["error"])


if __name__ == "__main__":
    main()
