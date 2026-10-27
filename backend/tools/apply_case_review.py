"""판례 검수 페이지(docs/review/case-review.html)에서 내보낸 결과 파일을 판례 자료에 반영한다.

    python tools/apply_case_review.py 김검수.json 이검수.json [--dry-run]

- 세 가지(실제로 있음 / 요약이 출처와 같음 / 이 유형과 맞음)를 모두 '맞아요'로 확인한 판례만 verified_date 와 검수자 이름을 적는다.
  그 판례는 화면에서 '검수 전' 표시가 사라진다.
- '이 유형과 맞나요?'를 모든 검수자가 '아니에요'로 답하면 그 유형에서 판례를 뺀다. (126번에 후진 출차 사례가 붙어 있던 경우처럼 잘못 붙인 연결)
- 그 밖의 문제('실제로 있는지', '요약이 같은지'가 아니에요, 모르겠어요, 사람마다 답이 다름, 이름 없음)는 파일을 바꾸지 않고
  docs/review/case-review-issues.md 에 메모와 함께 모은다. 사람이 직접 확인해야 한다.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "model" / "avly" / "data" / "verified_cases.json"
ISSUES = BACKEND.parent / "docs" / "review" / "case-review-issues.md"
CHECKS = ("exists", "summary", "fits")
CHECK_NAMES = {"exists": "실제로 있는 판례인가", "summary": "요약이 출처와 같은가", "fits": "이 사고 유형과 맞는가"}


def collect(exports: list[dict]) -> dict:
    merged = defaultdict(list)
    for e in exports:
        who = (e.get("reviewer") or "").strip()
        for key, record in (e.get("cases") or {}).items():
            merged[key].append((who, record, e.get("date", "")))
    return merged


def apply(cases_by_type: dict, exports: list[dict]):
    """판례 자료를 제자리에서 고친다. 반환: (요약 {'verified': [...], 'removed': [...]}, 이슈 [(키, 검수자들, 이유)])"""
    summary, issues = {"verified": [], "removed": []}, []
    for key, decisions in sorted(collect(exports).items()):
        type_id, _, number = key.partition("|")
        names = " / ".join(sorted({w or "(이름 없음)" for w, _, _ in decisions}))
        notes = " ".join(r.get("note", "") for _, r, _ in decisions if r.get("note")).strip()
        if any(not w for w, _, _ in decisions):
            issues.append((key, names, "검수자 이름이 없는 결과라 반영하지 않았습니다. 이름을 입력하고 다시 내보내 주세요."))
            continue
        entries = cases_by_type.get(type_id, [])
        entry = next((c for c in entries if c["case_number"] == number), None)
        if entry is None:
            issues.append((key, names, "자료에서 이 판례를 찾지 못했습니다. 이미 빠졌거나 번호가 바뀌었을 수 있습니다."))
            continue
        verdicts = {c: {r.get(c) for _, r, _ in decisions} for c in CHECKS}
        if verdicts["fits"] == {"bad"}:
            entries.remove(entry)
            summary["removed"].append(key)
            issues.append((key, names, f"이 유형과 맞지 않아 유형에서 뺐습니다. {notes}".strip()))
            continue
        if all(verdicts[c] == {"ok"} for c in CHECKS):
            entry["verified_date"] = max(d for _, _, d in decisions) or entry.get("verified_date", "")
            entry["reviewed_by"] = " / ".join(sorted({w for w, _, _ in decisions}))
            summary["verified"].append(key)
            continue
        reasons = []
        for c in CHECKS:
            got = verdicts[c] - {None}
            if "bad" in got:
                reasons.append(f"'{CHECK_NAMES[c]}'에 아니에요")
            elif len(got - {"skip"}) > 1:
                reasons.append(f"'{CHECK_NAMES[c]}' 사람마다 답이 다름")
            elif not got or got == {"skip"}:
                reasons.append(f"'{CHECK_NAMES[c]}' 확인하지 못함")
        issues.append((key, names, ("; ".join(reasons) or "일부 항목이 비어 있음") + (f". 메모: {notes}" if notes else "")))
    return summary, issues


def render_issues(issues: list) -> str:
    lines = ["# 판례 검수 이슈", "", "도구가 자동으로 반영하지 않은 항목입니다. 사람이 출처를 다시 확인해 주세요.", ""]
    if not issues:
        lines.append("(없음)")
    lines += [f"- **{key}** ({names}): {reason}" for key, names, reason in issues]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("exports", nargs="+", type=Path, help="판례 검수 페이지에서 내보낸 결과 파일")
    parser.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 보여 준다")
    args = parser.parse_args(argv)
    exports = [json.loads(p.read_text(encoding="utf-8")) for p in args.exports]
    cases = json.loads(DATA.read_text(encoding="utf-8"))
    summary, issues = apply(cases, exports)
    print(f"검수 완료로 표시 {len(summary['verified'])}개, 유형에서 뺌 {len(summary['removed'])}개, 이슈 {len(issues)}개")
    if not args.dry_run:
        DATA.write_text(json.dumps(cases, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        ISSUES.write_text(render_issues(issues), encoding="utf-8")
        print("저장했습니다. 이슈 목록:", ISSUES)


if __name__ == "__main__":
    main()
