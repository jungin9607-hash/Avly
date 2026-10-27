"""손해보험협회 과실비율 인정기준(2023.06) PDF 의 도표마다 실린 '참고 판례'를 사고 유형별 판례(verified_cases.json)로 옮긴다.

    python tools/build_chart_cases.py assets/install_data.json assets/csv_pdf_links.json [--dry-run]

- 입력 1: PDF 에서 뽑은 통합 원문(charts[].sections.reference_cases), 입력 2: 과실표 유형 ↔ PDF 도표 연결표(entries[].source_document_link).
- 도표에 실린 판례는 그 도표의 사고 유형에 해당하는 협회 자료이므로 검색 없이 유형에 바로 붙인다.
- 유형마다 최대 3건: 민사 과실 사건번호(가단·가합·나·다 등)만 쓰고 형사·행정 사건은 뺀다. 과실 비율이 소개된 것, 최근 것을 먼저 고른다. 이미 등록된 판례는 그대로 두고 부족한 만큼만 채운다.
- 협회 도표의 판례 요약이지 판결문 원문이 아니다. 요약을 파싱한 것이므로 verified_date 는 적지 않는다(검수 전).
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote

DATA = Path(__file__).resolve().parent.parent / "model" / "avly" / "data"
TARGET = 3
ENTRY = re.compile(r"\s*(?P<y>\d{4})\s*\.\s*(?P<m>\d{1,2})\s*[\.\s]\s*(?P<d>\d{1,2})\s*\.?\s*(?:선고)?\s*(?P<no>\d{2,4}[가-힣]{1,4}\s*\d+)\s*(?:판결)?\s*,?")
FAULT = re.compile(r"[AB]\s*과실\s*\d{1,3}\s*%")
def civil_fault_number(number: str) -> bool:
    """민사 과실 참고 사건번호인지. 서비스의 판례 목록 규칙(avly.facts.civil_fault_number)과 같다: 형사·행정 사건은 쓰지 않는다."""
    number = re.sub(r"\s+", "", str(number))
    if re.search(r"\d(?:고단|고합|고정|고약|도|노|구합|구단|누|두)", number):
        return False
    return bool(re.fullmatch(r"\d{2,4}(?:가단|가합|가소|다카|나|다)\d+", number))


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_cases(text: str, chart: str) -> list[dict]:
    """도표의 reference_cases 문단에서 판례 목록을 만든다.

    한 줄에 '법원 날짜 선고 사건번호 판결' 머리글이 나오고 그 뒤가 요약이다. 선고나 판결이라는 글자가 빠진 경우와
    사건이 둘 이상 같은 요약을 공유하는 경우(쉼표로 이어진 머리글)도 읽는다.
    """
    cases = []
    for block in re.split(r"(?=⊙)", text or ""):
        block = clean(block)
        if not block.startswith("⊙"):
            continue
        head = re.match(r"⊙\s*(?P<court>[^\d⊙]+?)\s*(?=\d{4}\s*\.)", block)
        if not head:
            continue
        court, pos, entries = clean(head["court"]), head.end(), []
        while True:
            m = ENTRY.match(block, pos)
            if not m:
                break
            entries.append(m)
            pos = m.end()
        body = block[pos:].strip(" ,")
        if not entries or not body:
            continue
        for e in entries:
            cases.append({"court": court, "date": f"{int(e['y']):04d}-{int(e['m']):02d}-{int(e['d']):02d}", "case_number": clean(e["no"]).replace(" ", ""),
                          "summary": body, "chart": chart})
    return cases


def rank(case: dict):
    """과실 비율이 소개된 판례를 먼저, 그다음 최근 판례를 먼저."""
    return (0 if FAULT.search(case["summary"]) else 1, -int(case["date"][:4]))


def to_entry(case: dict) -> dict:
    chart = case["chart"]
    return {"court": case["court"], "date": case["date"], "case_number": case["case_number"], "summary": case["summary"][:600],
            "comparison_limit": "협회 도표에 실린 판례 요약이며 판결문 원문을 조회한 것이 아닙니다. 사건의 사실관계가 달라서 같은 비율을 적용하지 않습니다.",
            "source": f"https://accident.knia.or.kr/myaccident-content?chartNo={quote(chart)}&chartType=1",
            "source_kind": "손해보험협회 도표의 참고 판례 요약(2023.06); 판결문 원문 조회 아님", "chart_reference": True, "chart": chart}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("reference", type=Path)
    parser.add_argument("links", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    ref = json.loads(args.reference.read_text(encoding="utf-8"))
    links = json.loads(args.links.read_text(encoding="utf-8"))
    by_chart = {c["official_chart_id"]: parse_cases(c["sections"].get("reference_cases", ""), c["official_chart_id"]) for c in ref["charts"]}
    existing = json.loads((DATA / "verified_cases.json").read_text(encoding="utf-8"))
    out = dict(existing)
    stats = {"types_with_cases": 0, "full": 0, "partial": 0, "none": [], "added": 0}
    for entry in sorted(links["entries"], key=lambda e: e["csv_accident_type"]):
        type_id = str(entry["csv_accident_type"])
        chart = entry["source_document_link"]["official_chart_id"]
        have = list(existing.get(type_id, []))
        seen = {c["case_number"] for c in have}
        pool = [c for c in sorted(by_chart.get(chart, []), key=rank) if c["case_number"] not in seen and civil_fault_number(c["case_number"])]
        # 같은 사건번호가 도표에서 여러 번 나오면 하나만
        unique, keys = [], set()
        for c in pool:
            if c["case_number"] not in keys:
                keys.add(c["case_number"]); unique.append(c)
        fill = [to_entry(c) for c in unique[: max(0, TARGET - len(have))]]
        merged = have + fill
        stats["added"] += len(fill)
        if merged:
            out[type_id] = merged
            stats["types_with_cases"] += 1
            stats["full" if len(merged) >= TARGET else "partial"] += 1
        else:
            stats["none"].append(int(type_id))
    out = {k: out[k] for k in sorted(out, key=int)}
    print(f"판례가 붙은 유형 {stats['types_with_cases']}개 / 133 (3건 채움 {stats['full']}개, 1~2건 {stats['partial']}개), 새로 붙인 판례 {stats['added']}건")
    print("판례를 못 붙인 유형:", stats["none"])
    if not args.dry_run:
        (DATA / "verified_cases.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("저장했습니다.")
    return out


if __name__ == "__main__":
    main()
