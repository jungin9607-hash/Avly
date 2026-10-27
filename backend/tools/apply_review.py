"""검수 페이지(docs/review/review.html)에서 내보낸 결과 파일을 JSON 데이터에 반영한다.

    python tools/apply_review.py 김검수.json 이검수.json [--dry-run]

- 검수 페이지에서 각자 '내보내기'를 눌러 받은 파일을 모아서 한꺼번에 넣으면 된다. JSON 을 직접 고칠 필요가 없다.
- 가감요소 유형: 모든 규칙을 '맞아요'로 확인한 유형만 reviewed: true + 검수자 이름·날짜를 적는다(그 유형이 서비스에 켜진다).
  '틀려요'나 '모르겠어요'가 하나라도 있으면 켜지 않고 docs/review/review-issues.md 에 메모와 함께 모은다.
- 쉬운 문장: '괜찮아요'면 reviewed: true. 문구를 고쳤으면 검사(질문은 ?로 끝나고 {who}가 있어야 함 등)를 통과할 때만 반영한다.
- 두 사람의 결정이 서로 다르면 어느 쪽도 반영하지 않고 이슈로 남긴다.
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "model" / "avly" / "data"
ISSUES = BACKEND.parent / "docs" / "review" / "review-issues.md"
DIRECTION = re.compile(r"과실이 (더해|늘|줄|커|무거워)")   # 과실이 늘고 주는 방향은 설명에 쓰지 않는다 (tests/test_explain 과 같은 규칙)


def wording_problem(title: str, easy: str, question: str) -> str | None:
    """고친 쉬운 문장이 규칙을 지키는지. 문제가 있으면 이유를, 없으면 None."""
    if not (title.strip() and easy.strip() and question.strip()):
        return "제목, 설명, 질문 중 비어 있는 것이 있습니다."
    if "{who}" not in question:
        return "질문에는 {who}(내 차/상대 차가 들어갈 자리)가 있어야 합니다."
    if not question.strip().endswith("?"):
        return "질문은 ?로 끝나야 합니다."
    if "{" in title + easy:
        return "제목과 설명에는 { } 를 쓰지 않습니다."
    if DIRECTION.search(easy):
        return "설명에는 과실이 늘고 주는 방향을 쓰지 않습니다(방향은 +n%p/-n%p로 따로 붙습니다)."
    return None


def collect(exports: list[dict]):
    """사람별 결과를 항목별로 모은다. 반환: {('type', 번호): [(검수자, 결정)], ('word', 요소): [...]}"""
    merged = defaultdict(list)
    for e in exports:
        who = (e.get("reviewer") or "").strip()
        for key, d in (e.get("types") or {}).items():
            merged[("type", key)].append((who, d, e.get("date", "")))
        for key, d in (e.get("wording") or {}).items():
            merged[("word", key)].append((who, d, e.get("date", "")))
    return merged


def apply(rules: dict, factors: dict, exports: list[dict]):
    """규칙과 설명 데이터에 검수 결과를 반영한다. (rules, factors 는 제자리에서 고친다) 반환: (반영 요약, 이슈 목록)"""
    summary = {"types_on": [], "types_issue": [], "words_ok": [], "words_edited": [], "words_issue": []}
    issues = []
    for (kind, key), decisions in sorted(collect(exports).items(), key=lambda kv: (kv[0][0], kv[0][1])):
        names = " / ".join(sorted({w or "(이름 없음)" for w, _, _ in decisions}))
        if any(not w for w, _, _ in decisions):
            issues.append((kind, key, names, "검수자 이름이 없는 결과라 반영하지 않았습니다. 검수 페이지에서 이름을 입력하고 다시 내보내 주세요."))
            continue
        verdicts = {d.get("decision") for _, d, _ in decisions} - {"skip", None}
        if not verdicts:
            continue
        if len(verdicts) > 1:
            issues.append((kind, key, names, "검수자마다 결정이 달라 반영하지 않았습니다: " + ", ".join(f"{w} {d.get('decision')}" for w, d, _ in decisions)))
            continue
        who, d, date = next((w, d, dt) for w, d, dt in decisions if d.get("decision") in verdicts)
        if kind == "type":
            t = rules.get(key)
            if t is None:
                issues.append((kind, key, who, "규칙 파일에 없는 유형입니다."))
            elif d["decision"] == "ok" and all(r.get("ok") for r in d.get("rules", {}).values()) and set(d.get("rules", {})) == {r["id"] for r in t["rules"]}:
                t.update(reviewed=True, reviewed_by=who, reviewed_at=date)
                for r in t["rules"]:
                    r["reviewed"] = True
                summary["types_on"].append(key)
            else:
                bad = [f"{rid}: {r.get('note') or '메모 없음'}" for rid, r in d.get("rules", {}).items() if not r.get("ok")]
                missing = len({r["id"] for r in t["rules"]} - set(d.get("rules", {})))
                note = "; ".join(bad) or ("전체 메모: " + (d.get("note") or "없음"))
                if missing:
                    note += f" (결정이 없는 규칙 {missing}개)"
                issues.append((kind, key, who, note))
                summary["types_issue"].append(key)
        else:
            e = factors.get(key)
            if e is None:
                issues.append((kind, key, who, "설명 파일에 없는 요소입니다."))
            elif d["decision"] == "ok":
                e["reviewed"] = True
                summary["words_ok"].append(key)
            elif d["decision"] == "edit":
                title, easy, question = [(d.get(f) or "").strip() for f in ("title", "easy", "question")]
                problem = wording_problem(title, easy, question)
                if problem:
                    issues.append((kind, key, who, "고친 문장을 반영하지 못했습니다: " + problem))
                else:
                    e.update(title=title, easy=easy, question=question, reviewed=True)
                    summary["words_edited"].append(key)
            else:
                issues.append((kind, key, who, d.get("note") or "메모 없음"))
                summary["words_issue"].append(key)
    return summary, issues


def render_issues(issues: list) -> str:
    lines = ["# 검수에서 나온 문제 모음", "", "`tools/apply_review.py`가 반영하지 않고 남긴 항목입니다. 해결한 뒤 검수 페이지에서 다시 확인하고 내보내 주세요.", ""]
    if not issues:
        return "\n".join(lines + ["문제 없음"]) + "\n"
    lines += ["| 종류 | 번호/요소 | 검수자 | 내용 |", "| --- | --- | --- | --- |"]
    for kind, key, who, note in issues:
        lines.append(f"| {'가감요소 유형' if kind == 'type' else '쉬운 문장'} | {key} | {who} | {note.replace('|', '/').replace(chr(10), ' ')} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("exports", nargs="+", type=Path, help="검수 페이지에서 내보낸 결과 파일")
    parser.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 결과만 보여 준다")
    args = parser.parse_args(argv)
    exports = [json.loads(p.read_text(encoding="utf-8")) for p in args.exports]
    rules = json.loads((DATA / "adjustment_rules.json").read_text(encoding="utf-8"))
    explanations = json.loads((DATA / "adjustment_explanations.json").read_text(encoding="utf-8"))
    summary, issues = apply(rules, explanations["factors"], exports)
    print(f"켜진 유형 {len(summary['types_on'])}개, 문제가 있어 보류한 유형 {len(summary['types_issue'])}개, "
          f"쉬운 문장 확인 {len(summary['words_ok'])}개 + 고침 {len(summary['words_edited'])}개, 문제 {len(summary['words_issue'])}개, 이슈 {len(issues)}개")
    if not args.dry_run:
        (DATA / "adjustment_rules.json").write_text(json.dumps(rules, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        (DATA / "adjustment_explanations.json").write_text(json.dumps(explanations, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        ISSUES.write_text(render_issues(issues), encoding="utf-8")
        print("저장했습니다. 이슈 목록:", ISSUES)


if __name__ == "__main__":
    main()
