"""정답(라벨)이 있는 영상으로 사고 분석이 얼마나 맞는지 잰다. AI 를 실제로 부르므로 비용(또는 무료 한도)이 든다.

    python tools/evaluate_labels.py --results /tmp/eval [--only 주차장1,주차장2] [--labels labels]

- 영상: <labels>/<종류>/*.mp4, 정답: <labels>/labels_<종류>_한국어/*.json (CSV 과실표 번호와 A/B 진행 정보). 종류는 주차장, 사거리 교차로, 차도와 차도가 아닌 장소
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
# 영상 종류(폴더 이름) → 정답 폴더 이름. 정답 폴더 이름의 띄어쓰기가 폴더마다 달라서 직접 적는다.
CATEGORIES = {"주차장": "labels_주차장_한국어", "사거리 교차로": "labels_사거리 교차로_한국어", "차도와 차도가 아닌 장소": "labels_차도와차도가아닌장소_한국어"}
# 정답 장소에 대해 모델의 road_shape 로 맞다고 볼 값
PLACE_SHAPES = {"주차장": PARKING_SHAPES, "사거리 교차로": {"교차로"}, "차도와 차도가 아닌 장소": {"기타", "주차장/기타", "직선 도로", "교차로"}}


def load_cases(labels_dir: Path, only: set[str] | None):
    cases = []
    for category, label_folder in CATEGORIES.items():
        for path in sorted((labels_dir / label_folder).glob("*.json")):
            info = json.loads(path.read_text(encoding="utf-8"))["영상"]
            name = info["영상 이름"]
            if only and name not in only:
                continue
            cases.append({"name": name, "category": category, "video": labels_dir / category / f"{name}.mp4", "type": info["사고 유형 코드"],
                          "place_code": info["사고 장소"]["코드"], "a": info["차량 A 진행 정보"]["명칭"], "b": info["차량 B 진행 정보"]["명칭"],
                          "ratio_a": info.get("차량 A 과실비율") or info.get("과실비율(원본에 차량 구분 없음)"), "label": info})
    return cases


def analyze(video: Path, results: Path, place_codes: list[int] | None = None) -> dict:
    """영상 하나를 분석하고 모델이 저장한 결과 JSON 을 돌려준다."""
    from avly import pipeline
    from avly.context import ctx
    pipeline.run({"BACKEND_DIR": str(BACKEND), "VIDEO_FILE": str(video), "PICK_VIDEO": False,
                  "CSV_FILE": str(BACKEND / "model" / "avly" / "data" / "fault_table_car_to_car.csv"), "RESULTS_DIR": str(results),
                  "SHOW_PROCESS_LOGS": False, "USE_CACHE": True, "no_survey": True,
                  **({"PLACE_CODES": place_codes} if place_codes else {})})
    data = json.loads(Path(ctx.output_path).read_text(encoding="utf-8"))
    data["_result_path"] = str(ctx.output_path)   # 검수 페이지 도구가 이 결과 파일을 다시 읽는다
    return data


def _actions_match(case: dict, scene: dict):
    """(내 차 행동 일치, 상대 차 행동 일치, 블랙박스 차량이 라벨의 A/B 중 어느 쪽인지). 대응표가 없으면 (None, None, None)."""
    def ok(action, label):
        return (action in EXPECTED_ACTIONS[label]) if label in EXPECTED_ACTIONS else None
    direct = (ok(scene["a_action"], case["a"]), ok(scene["b_action"], case["b"]))
    swapped = (ok(scene["a_action"], case["b"]), ok(scene["b_action"], case["a"]))
    if direct[0] is None and direct[1] is None:
        return None, None, None
    if swapped.count(True) > direct.count(True):
        return swapped[0], swapped[1], "B"
    return direct[0], direct[1], "A"


def judge(case: dict, data: dict) -> dict:
    from app.worker import snapshot
    scene, snap = data["scene"], snapshot.from_model_result(data, "eval")
    situation = snap["situation"]
    candidates = [(c["accident_type_id"], c["role"], c["source"]) for c in situation["candidates"]]
    default = situation["candidates"][situation["default_index"]] if situation["default_index"] is not None else None
    mine = _actions_match(case, scene)
    return {
        "video": case["name"], "label_type": case["type"],
        "object_ok": scene["accident_object"] == "차대차",
        "category": case["category"], "place_ok": scene["road_shape"] in PLACE_SHAPES[case["category"]],
        # 행동 대응표는 주차장만 만들어 두었다. 다른 종류는 사람이 정답과 나란히 보고 판단한다(None = 자동 판정 안 함)
        # 정답 라벨의 A/B 는 블랙박스 차량과 상관없이 도표 기준이라, 내 차 = 라벨 A 인 경우와 라벨 B 인 경우 중 맞는 쪽으로 본다
        "a_ok": mine[0], "b_ok": mine[1], "blackbox_is": mine[2],
        "result_file": Path(data["_result_path"]).name if data.get("_result_path") else None,
        "top1_ok": bool(default and default["accident_type_id"] == case["type"]),
        "any_ok": any(t == case["type"] for t, _, _ in candidates),
        "top1_role": default["role"] if default else None,
        "road_shape": scene["road_shape"], "a_action": scene["a_action"], "b_action": scene["b_action"], "contact": scene["contact"],
        "candidates": candidates[:4], "no_match_reason": data.get("no_match_reason") or "",
        "tokens": data.get("current_run_usage", {}).get("total_tokens"),
        "models": sorted({s.get("model") for s in data.get("stages", []) if s.get("model") and s.get("usage")}),
        "detail_review": data["pipeline"]["detail_review_required"],
    }


def table(rows: list[dict]) -> str:
    mark = lambda ok: "-" if ok is None else ("O" if ok else "X")
    out = ["| 영상 | 정답 유형 | 대상 | 장소 | 내 차 행동 | 상대 차 행동 | 후보에 정답 | 1순위 정답 | AI가 본 장소 / 내 차 / 상대 차 / 접촉 | 후보(유형, 역할) |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        out.append(f"| {r['video']} | {r['label_type']} | {mark(r['object_ok'])} | {mark(r['place_ok'])} | {mark(r['a_ok'])} | {mark(r['b_ok'])} | {mark(r['any_ok'])} | {mark(r['top1_ok'])} | "
                   f"{r['road_shape']} / {r['a_action']} / {r['b_action']} / {r['contact']} | {', '.join(f'{t}{role}' for t, role, _ in r['candidates']) or '없음'} |")
    n = len(rows) or 1
    out.append("")
    out.append(f"**{len(rows)}개 중** 차대차 {sum(r['object_ok'] for r in rows)}, 장소 {sum(r['place_ok'] for r in rows)}, 내 차 행동 {sum(bool(r['a_ok']) for r in rows)}, "
               f"상대 차 행동 {sum(bool(r['b_ok']) for r in rows)}, 후보에 정답 {sum(r['any_ok'] for r in rows)}, 1순위 정답 {sum(r['top1_ok'] for r in rows)} ({sum(r['top1_ok'] for r in rows) * 100 // n}%), "
               f"후보 없음 {sum(not r['candidates'] for r in rows)}")
    return "\n".join(out)


def place_codes_for(category: str) -> list[int]:
    """라벨 영상의 종류(폴더 이름)를 사용자가 고른 장소로 보고 과실표 장소 번호로 바꾼다."""
    from avly.constants import PLACE_GROUPS
    return PLACE_GROUPS[category]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--labels", type=Path, default=BACKEND / "labels")
    parser.add_argument("--place-hint", action="store_true", help="사용자가 장소를 골랐다고 보고 그 장소의 유형만 비교한다")
    parser.add_argument("--results", type=Path, required=True, help="분석 결과와 응답 캐시를 저장할 폴더")
    parser.add_argument("--only", default="", help="쉼표로 구분한 영상 이름 (예: 주차장1,주차장2)")
    args = parser.parse_args(argv)
    args.results.mkdir(parents=True, exist_ok=True)
    cases = load_cases(args.labels, set(filter(None, args.only.split(","))) or None)
    rows = []
    for case in cases:
        started = time.time()
        try:
            rows.append(judge(case, analyze(case["video"], args.results, place_codes_for(case["category"]) if args.place_hint else None)))
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
