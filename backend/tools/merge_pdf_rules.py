"""PDF(손해보험협회 과실비율 인정기준 2023.06)에서 뽑은 가감요소 규칙을 avly/data 에 합친다.

    python tools/merge_pdf_rules.py assets/pdf_survey_rules.json [--replace-existing] [--dry-run]

- 입력: 팀원이 PDF 에서 뽑은 규칙 파일(`version: pdf-survey-v1`). 유형별 규칙(types)과 요소 이름(factor_labels)이 들어 있다.
- 출력: model/avly/data/adjustment_rules.json (유형 추가), factor_labels.json (요소 이름 추가). 다른 파일은 바꾸지 않는다.
- 이미 등록된 유형은 기본으로 **그대로 둔다**(영상 관찰로 자동 적용되는 기존 규칙을 보존). --replace-existing 이면 PDF 규칙으로 바꾼다.
- 합치기 전에 과실표(CSV)와 대조한다: 유형 번호, 진행 이름, 기본 비율이 하나라도 다르면 멈춘다.
- 쉬운 말 설명(adjustment_explanations.json)은 별도 작업이다. 설명이 없는 요소는 합친 뒤 test_catalog 가 알려 준다.
"""
import argparse
import csv
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "model" / "avly" / "data"
KEEP_RULE_FIELDS = ("id", "actor", "factor", "delta_pp", "group", "manual_only", "label", "pdf_source", "reviewed")
KEEP_TYPE_FIELDS = ("official_chart", "source", "coverage", "expected_a_progress", "expected_b_progress", "expected_base",
                    "exclusive_groups", "source_review_pending", "reviewed")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_against_csv(types: dict) -> None:
    rows = {int(r["accident_type"]): r for r in csv.DictReader((DATA / "fault_table_car_to_car.csv").open(encoding="utf-8-sig", newline=""))}
    fix = lambda name: name.replace("출자", "출차") if "주차구역" in name else name   # app/catalog.py 와 같은 오탈자 보정
    problems = []
    for key, t in types.items():
        row = rows.get(int(key))
        if row is None:
            problems.append(f"{key}: 과실표에 없는 유형")
            continue
        if t["expected_base"] != [int(row["negligence_a"]), int(row["negligence_b"])]:
            problems.append(f"{key}: 기본 비율 불일치 {t['expected_base']}")
        if (t["expected_a_progress"], t["expected_b_progress"]) != (fix(row["vehicle_a_progress_info_name"]), fix(row["vehicle_b_progress_info_name"])):
            problems.append(f"{key}: 진행 이름 불일치")
    if problems:
        raise SystemExit("과실표와 맞지 않아 합치지 않습니다:\n  " + "\n  ".join(problems))


def to_engine_type(t: dict) -> dict:
    """엔진이 읽는 모양으로 줄인다. 원문 추출에 쓴 부가 정보(source_csv_row 등)는 넣지 않는다."""
    merged = {k: t[k] for k in KEEP_TYPE_FIELDS if k in t}
    merged["reviewed_by"] = ""   # 검수 완료로 바꿀 때 이름과 날짜를 적는다 (app/review_status.py 가 누가 얼마나 했는지 보여 준다)
    merged["reviewed_at"] = ""
    merged["rules"] = [{k: r[k] for k in KEEP_RULE_FIELDS if k in r} | ({"requires_B_adjustment": True} if r.get("requires_B_adjustment") else {})
                       for r in t["rules"]]
    return merged


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rules", type=Path, help="PDF 규칙 파일 (version: pdf-survey-v1)")
    parser.add_argument("--replace-existing", action="store_true", help="이미 등록된 유형도 PDF 규칙으로 바꾼다")
    parser.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 보여 준다")
    args = parser.parse_args(argv)

    source = load(args.rules)
    if source.get("version") != "pdf-survey-v1":
        raise SystemExit("알 수 없는 규칙 파일 버전입니다: " + str(source.get("version")))
    check_against_csv(source["types"])

    existing = load(DATA / "adjustment_rules.json")
    labels = load(DATA / "factor_labels.json")
    merged = dict(existing)
    added = replaced = 0
    for key in sorted(source["types"], key=int):   # 기존 항목의 순서는 그대로 두고 새 유형을 번호순으로 뒤에 붙인다
        if key in existing and not args.replace_existing:
            continue
        replaced += key in existing
        added += key not in existing
        merged[key] = to_engine_type(source["types"][key])
    new_labels = {f: l for f, l in source["factor_labels"].items() if f not in labels}
    labels.update(new_labels)

    print(f"유형 {len(existing)}개 → {len(merged)}개 (추가 {added}, 교체 {replaced}), 요소 이름 +{len(new_labels)}개, 막힌 유형 {len(source.get('blocked_types', {}))}개는 넣지 않음")
    if not args.dry_run:
        (DATA / "adjustment_rules.json").write_text(json.dumps(merged, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (DATA / "factor_labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        # 규칙을 넣지 않은 유형과 그 이유(검수용). 큰 원문 파일 없이도 왜 뺐는지 볼 수 있게 저장소에 남긴다.
        blocked = {k: [x["reason"] for x in v] for k, v in sorted(source.get("blocked_types", {}).items(), key=lambda kv: int(kv[0]))}
        (DATA / "pdf_rules_blocked.json").write_text(json.dumps({"source": source.get("source_pdf_sha256"), "blocked_types": blocked}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("저장했습니다.")


if __name__ == "__main__":
    main()
