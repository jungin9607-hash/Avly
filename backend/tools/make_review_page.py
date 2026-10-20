"""검수 페이지(docs/review/review.html)를 만든다. 더블클릭하면 브라우저에서 열리고 인터넷이 필요 없다.

    docker compose exec -T backend python tools/make_review_page.py > docs/review/review.html

가감요소 규칙(PDF에서 합친 유형)과 쉬운 문장을 사람이 읽기 쉬운 카드로 보여 주고 '맞아요/틀려요'를 누르게 한다.
결과는 '내보내기'로 파일을 받아 tools/apply_review.py 로 데이터에 반영한다. 규칙이나 문장이 바뀌면 다시 만든다.
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BACKEND), str(BACKEND / "model")]

from app import catalog  # noqa: E402

DATA = BACKEND / "model" / "avly" / "data"


def build_data() -> dict:
    rules = json.loads((DATA / "adjustment_rules.json").read_text(encoding="utf-8"))
    explanations = json.loads((DATA / "adjustment_explanations.json").read_text(encoding="utf-8"))["factors"]
    labels = json.loads((DATA / "factor_labels.json").read_text(encoding="utf-8"))
    types, usage = [], {}
    for key in sorted(rules, key=int):
        t = rules[key]
        if not any("pdf_source" in r for r in t["rules"]):
            continue   # 사람이 먼저 입력해 둔 기존 7개 유형은 이 페이지에서 확인하지 않는다
        row = catalog.get_row(int(key))
        converted = []
        for r in t["rules"]:
            e = explanations[r["factor"]]
            src = r["pdf_source"]
            converted.append({"id": r["id"], "actor": r["actor"], "factor": r["factor"], "delta": r["delta_pp"], "title": e["title"], "easy": e["easy"],
                              "raw": src["raw_text"], "chart": src["chart"], "pages": src.get("pdf_pages") or []})
            u = usage.setdefault(r["factor"], {"types": [], "deltas": set()})
            u["types"].append(int(key))
            u["deltas"].add(r["delta_pp"])
        types.append({"id": key, "place": catalog.easy_label("place", row.place), "feature": catalog.easy_label("feature", row.feature),
                      "a": catalog.easy_label("my_progress", row.a_progress), "b": catalog.easy_label("other_progress", row.b_progress),
                      "base_a": row.negligence_a, "base_b": row.negligence_b, "chart": t["official_chart"], "reviewed": bool(t.get("reviewed")),
                      "reviewed_by": t.get("reviewed_by", ""), "rules": converted})
    factors = []
    for key, e in explanations.items():
        u = usage.get(key, {"types": [], "deltas": set()})
        factors.append({"key": key, "label": labels.get(key, key), "title": e["title"], "easy": e["easy"], "question": e["question"], "note": e.get("note", ""),
                        "reviewed": bool(e.get("reviewed")), "n_types": len(u["types"]), "types": sorted(set(u["types"]))[:6], "deltas": [f"{d:+d}" for d in sorted(u["deltas"])]})
    factors.sort(key=lambda f: (f["reviewed"], -f["n_types"]))
    return {"types": types, "factors": factors}


def main():
    template = (Path(__file__).resolve().parent / "review_page_template.html").read_text(encoding="utf-8")
    payload = json.dumps(build_data(), ensure_ascii=False).replace("</", "<\\/")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(template.replace("__DATA__", payload))


if __name__ == "__main__":
    main()
