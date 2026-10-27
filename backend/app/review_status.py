"""검수가 어디까지 됐는지, 누가 했는지, 표시가 잘못된 곳은 없는지 한눈에 보여 준다.

    docker compose exec backend python -m app.review_status          # 사람이 읽는 요약
    docker compose exec backend python -m app.review_status --json   # 다른 도구에 넘길 때

검수 표시 방법(가감요소): backend/model/avly/data/adjustment_rules.json 에서 유형 하나를 다 확인했으면 그 유형에
    "reviewed": true, "reviewed_by": "이름", "reviewed_at": "2026-10-21"
을 적는다. 이렇게 확인한 유형만 서비스에 켜진다(기본값. 개발에서 전부 보려면 AVLY_REQUIRE_RULE_REVIEW=0).
그중에서도 쉬운 말(adjustment_explanations.json 의 reviewed)까지 확인한 가감요소만 묻고 계산한다(개발에서 전부 보려면 AVLY_REQUIRE_WORDING_REVIEW=0).
"""
import argparse
import json
import sys

from app import catalog
from avly.tables import active_rules, type_is_reviewed, wording_gate


def summarize(all_rules: dict, factors: dict, labels: dict) -> dict:
    pdf_types = {k: t for k, t in all_rules.items() if any("pdf_source" in r for r in t["rules"])}
    by_person: dict[str, list[str]] = {}
    warnings: list[str] = []
    done, partial = [], []
    for key, t in sorted(pdf_types.items(), key=lambda kv: int(kv[0])):
        rules = t["rules"]
        marked = sum(1 for r in rules if r.get("reviewed"))
        if type_is_reviewed(t):
            done.append(key)
            who, when = (t.get("reviewed_by") or "").strip(), (t.get("reviewed_at") or "").strip()
            by_person.setdefault(who or "(이름 없음)", []).append(key)
            if not who or not when:
                warnings.append(f"{key}번 유형: 확인 완료인데 검수자 이름이나 날짜(reviewed_by, reviewed_at)가 비어 있습니다.")
            if not t.get("reviewed") and marked == len(rules):
                warnings.append(f"{key}번 유형: 규칙은 모두 확인 표시인데 유형 자체에는 reviewed: true 가 없습니다. 유형에도 표시해 주세요.")
        elif marked:
            partial.append((key, marked, len(rules)))
        if (t.get("reviewed_by") or t.get("reviewed_at")) and not type_is_reviewed(t):
            warnings.append(f"{key}번 유형: 검수자 이름은 있는데 아직 확인 완료(reviewed: true)가 아닙니다.")
    text_done = [f for f, e in factors.items() if e.get("reviewed")]
    label_done = sum(1 for kind in ("places", "features", "progress") for e in labels.get(kind, {}).values() if e.get("reviewed"))
    label_total = sum(len(labels.get(kind, {})) for kind in ("places", "features", "progress"))
    # 규칙을 확인한 유형 중, 쉬운 말까지 확인한 가감요소가 하나라도 있어서 서비스가 실제로 묻는 유형
    asked, _ = wording_gate(active_rules(all_rules, True), set(text_done))
    return {
        "rules": {
            "types_total": len(all_rules), "pdf_types": len(pdf_types), "pdf_types_done": len(done), "partial": partial,
            "on_in_service": sorted(int(k) for k in active_rules(all_rules, True)), "by_person": by_person,
            "asked_in_service": sorted(int(k) for k in asked),
        },
        "easy_words": {"total": len(factors), "done": len(text_done)},
        "accident_labels": {"total": label_total, "done": label_done},
        "warnings": warnings,
    }


def render(s: dict) -> str:
    r = s["rules"]
    pct = lambda a, b: f"{a * 100 // b}%" if b else "-"
    lines = ["가감요소 규칙 (PDF에서 합친 유형)",
             f"  확인 완료 {r['pdf_types_done']} / {r['pdf_types']}개 유형 ({pct(r['pdf_types_done'], r['pdf_types'])})  ← 이 유형만 서비스에 켜집니다",
             f"  서비스에 켜진 유형: {len(r['on_in_service'])}개 / 133개 (기존 7개 + 확인 완료 {r['pdf_types_done']}개)",
             f"  그중 쉬운 말까지 확인돼서 가감요소를 실제로 묻는 유형: {len(r['asked_in_service'])}개 (나머지는 기본 비율만 안내)"]
    if r["partial"]:
        lines.append("  확인 중(일부 규칙만 표시): " + ", ".join(f"{k}번 {a}/{b}" for k, a, b in r["partial"]))
    if r["by_person"]:
        lines.append("  사람별: " + ", ".join(f"{who} {len(types)}개" for who, types in sorted(r["by_person"].items())))
    e, a = s["easy_words"], s["accident_labels"]
    lines += ["", f"쉬운 말(가감요소 설명): 확인 {e['done']} / {e['total']}개", f"사고 유형 이름(쉬운 말): 확인 {a['done']} / {a['total']}개", ""]
    if s["warnings"]:
        lines.append(f"점검할 것 {len(s['warnings'])}개")
        lines += ["  - " + w for w in s["warnings"]]
    else:
        lines.append("점검할 것 없음 (표시가 빠지거나 어긋난 곳이 없습니다)")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data_dir = catalog.BASE_DIR / "model" / "avly" / "data"
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    summary = summarize(load(data_dir / "adjustment_rules.json"), load(data_dir / "adjustment_explanations.json")["factors"],
                        load(catalog.LABELS_PATH))
    print(json.dumps(summary, ensure_ascii=False, indent=1) if args.json else render(summary))
    return 1 if summary["warnings"] else 0


if __name__ == "__main__":
    sys.exit(main())
