"""가감산 비율까지 지원하는 사고 유형을 정리한 문서(docs/review/supported-types.md)를 만든다.

    python tools/make_supported_types.py            # 문서를 새로 쓴다
    python tools/make_supported_types.py --stdout   # 화면에만 보여 준다

서비스가 가감요소를 실제로 묻고 계산하는 조건(avly/tables.py 와 같은 기준)으로 계산한다.
1. 가감요소 규칙(숫자)을 사람이 확인한 유형이고
2. 그 안에서 쉬운 말(제목·설명·질문)까지 확인한 가감요소만 쓴다.
검수가 진행되면 다시 실행해서 문서를 갱신한다.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "model"))

from avly.tables import ALL_ADJUSTMENT_RULES, REVIEWED_FACTOR_WORDING, active_rules, wording_gate   # noqa: E402

DATA = BACKEND / "model" / "avly" / "data"
OUT = BACKEND.parent / "docs" / "review" / "supported-types.md"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def easy(labels, kind, name):
    name = name.replace("출자", "출차") if "주차구역" in name else name
    return (labels.get(kind, {}).get(name) or {}).get("easy") or name


def build() -> str:
    factors = load(DATA / "adjustment_explanations.json")["factors"]
    labels = load(BACKEND / "app" / "data" / "accident_labels.json")
    rows = {r["accident_type"]: r for r in csv.DictReader((DATA / "fault_table_car_to_car.csv").open(encoding="utf-8-sig", newline=""))}
    reviewed = active_rules(ALL_ADJUSTMENT_RULES, True)
    asked, held = wording_gate(reviewed, REVIEWED_FACTOR_WORDING)

    def title(config_rule):
        t = factors.get(config_rule["factor"], {}).get("title") or config_rule["factor"]
        return f"{t} ({config_rule['delta_pp']:+d}%p)"

    lines = ["# 가감산 비율까지 지원하는 사고 유형", "",
             "이 문서는 `python tools/make_supported_types.py`로 만든 것입니다. 검수가 진행되면 다시 실행해서 갱신하세요. 직접 고치지 마세요.", "",
             "**서비스가 가감요소를 실제로 묻고 계산하는 조건**: ① 가감요소 규칙(숫자)을 사람이 확인한 유형이고, ② 그 안에서 **쉬운 말(제목·설명·질문)까지 확인한 가감요소**만 씁니다. "
             "그 밖의 유형과 가감요소는 반영하지 않고, 기본 과실비율만 안내하거나 '확인한 요소만 반영한 비율'로 안내합니다.", ""]
    total = len(rows)
    COMMON = ("gross_negligence", "serious_negligence")   # 모든 유형에 공통인 '현저한/중대한 과실'
    situation = sorted((k for k in asked if any(r["factor"] not in COMMON for r in asked[k]["rules"])), key=int)
    only_common = sorted((k for k in asked if k not in situation), key=int)
    lines += [f"- 차대차 사고 유형 전체: **{total}개** (모두 기본 과실비율은 안내합니다)",
              f"- **가감요소를 묻는 유형: {len(asked)}개**",
              f"  - **사고 상황에 따른 가감요소까지 지원하는 유형: {len(situation)}개** (서행, 신호 위반처럼 영상 속 상황을 묻는 질문이 있음)",
              f"  - **'음주·무면허·약물운전' 같은 공통 질문만 나오는 유형: {len(only_common)}개** (거의 모두 '아니요'라서 비율이 실제로 달라지는 일은 드뭄)",
              f"- 기본 비율만 안내하는 유형: {total - len(asked)}개", ""]

    lines += ["## 사고 상황에 따른 가감요소까지 지원하는 유형", "",
              "표의 A·B는 과실표의 차량 구분입니다(화면에서는 '내 차/상대 차'로 보여 줍니다). 가감요소는 쉬운 말까지 확인된 것만 적었습니다.", "",
              "| 유형 | 사고 장소 · 사고 유형 | 표의 A 차량 / B 차량 | 기본 비율(A:B) | 지원하는 가감요소 | 반영하지 않는 가감요소 |",
              "| --- | --- | --- | --- | --- | --- |"]
    for key in situation:
        r = rows[key]
        sup = "<br>".join(f"{rule['actor']}: {title(rule)}" for rule in asked[key]["rules"])
        lines.append(f"| {key} | {easy(labels, 'places', r['accident_place_name'])} · {easy(labels, 'features', r['accident_place_feature_name'])} "
                     f"| {easy(labels, 'progress', r['vehicle_a_progress_info_name'])} / {easy(labels, 'progress', r['vehicle_b_progress_info_name'])} "
                     f"| {r['negligence_a']}:{r['negligence_b']} | {sup} | {held.get(key, 0)}개 |")
    lines += ["", "## 공통 질문(음주·무면허·약물운전)만 나오는 유형", "",
              "이 유형들은 사고 상황에 따른 가감요소의 쉬운 말이 아직 검수되지 않아 공통 질문만 묻습니다. 결과는 '확인한 요소만 반영한 비율'로 안내합니다.", "",
              ", ".join(only_common) or "-", ""]

    no_rules = sorted((k for k in rows if k not in ALL_ADJUSTMENT_RULES), key=int)
    not_reviewed = sorted((k for k in ALL_ADJUSTMENT_RULES if k not in reviewed), key=int)
    no_wording = sorted((k for k in reviewed if k not in asked), key=int)
    lines += ["", "## 기본 비율만 안내하는 유형과 이유", "",
              "| 이유 | 유형 번호 |", "| --- | --- |",
              f"| 가감요소 규칙을 넣지 않았거나 검수 결정으로 삭제했다 (PDF와 과실표의 기본값이 달라 일부러 뺌, PDF에 가감요소가 없어 삭제 등) | {', '.join(no_rules) or '-'} ({len(no_rules)}개) |",
              f"| 가감요소 규칙(숫자) 검수가 끝나지 않았다 | {', '.join(not_reviewed) or '-'} ({len(not_reviewed)}개) |",
              f"| 규칙은 확인했지만 쉬운 말이 검수 전이라 쓸 수 있는 가감요소가 없다 | {', '.join(no_wording) or '-'} ({len(no_wording)}개) |", ""]
    done = len(REVIEWED_FACTOR_WORDING)
    lines += [f"쉬운 말 검수가 끝난 가감요소는 전체 {len(factors)}개 중 {done}개입니다. 나머지 문장을 검수하면 지원하는 유형과 가감요소가 늘어납니다. "
              "검수가 필요한 항목은 [pending-review-requests.md](pending-review-requests.md)에 모아 두었습니다.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args(argv)
    text = build()
    if args.stdout:
        print(text)
    else:
        OUT.write_text(text, encoding="utf-8")
        print("저장했습니다:", OUT)


if __name__ == "__main__":
    main()
