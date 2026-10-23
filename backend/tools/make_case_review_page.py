"""유형에 붙은 판례를 사람이 확인하는 검수 페이지를 만든다. 더블클릭 또는 http://localhost:5173/case-review.html 로 연다.

    docker compose exec -T worker python tools/make_case_review_page.py > docs/review/case-review.html

- 대상은 model/avly/data/verified_cases.json 에 적어 둔 (사고 유형, 판례) 연결이다.
- 법률 지식이 없어도 되는 세 가지만 확인한다: 판례가 실제로 있는지 / 우리 요약이 출처와 같은지 / 그 사고 유형과 맞는지.
- 결과는 검수 페이지의 '내보내기' 파일로 받아 tools/apply_case_review.py 로 반영한다.
"""
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(BACKEND), str(BACKEND / "model")]

from app import catalog  # noqa: E402

DATA = BACKEND / "model" / "avly" / "data" / "verified_cases.json"
TEMPLATE = Path(__file__).with_name("case_review_template.html")


def build(cases_by_type: dict) -> dict:
    types = []
    for key in sorted(cases_by_type, key=int):
        row = catalog.get_row(int(key))
        if row is None:
            continue
        opt = catalog.orient(row, "A")
        types.append({
            "id": row.id, "place": opt["easy"]["place"], "feature": opt["easy"]["feature"],
            "a": opt["easy"]["my_progress"], "b": opt["easy"]["other_progress"],
            "original": f"{row.place} · {row.feature} · A {row.a_progress} / B {row.b_progress}",
            "cases": [{"key": f"{row.id}|{c['case_number']}", "court": c["court"], "date": c["date"], "case_number": c["case_number"],
                       "summary": c["summary"], "limit": c.get("comparison_limit", ""), "source": c.get("source", ""),
                       "source_kind": c.get("source_kind", ""), "verified": bool(c.get("verified_date"))} for c in cases_by_type[key]],
        })
    return {"format": "avly-case-review-v1", "types": types}


def main() -> None:
    data = build(json.loads(DATA.read_text(encoding="utf-8")))
    html = TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
    sys.stdout.buffer.write(html.encode("utf-8"))


if __name__ == "__main__":
    main()
