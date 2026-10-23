"""검수 페이지에서 내보낸 결과를 데이터에 반영하는 도구(tools/apply_review.py) 시험."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import apply_review as ar   # noqa: E402


def make_rules():
    return {"60": {"reviewed": False, "reviewed_by": "", "reviewed_at": "", "rules": [{"id": "60_A_x", "reviewed": False}, {"id": "60_B_y", "reviewed": False}]},
            "61": {"reviewed": False, "reviewed_by": "", "reviewed_at": "", "rules": [{"id": "61_A_x", "reviewed": False}]}}


def make_factors():
    return {"pdf_a": {"title": "제목", "easy": "설명이에요.", "question": "{who}가 했나요?", "reviewed": False}}


def export(reviewer="김검수", date="2026-10-21", types=None, wording=None):
    return {"reviewer": reviewer, "date": date, "types": types or {}, "wording": wording or {}}


ALL_OK = {"decision": "ok", "rules": {"60_A_x": {"ok": True}, "60_B_y": {"ok": True}}}


class TypeTests(unittest.TestCase):
    def test_a_fully_confirmed_type_is_turned_on_with_the_reviewer(self):
        rules, factors = make_rules(), make_factors()
        summary, issues = ar.apply(rules, factors, [export(types={"60": ALL_OK})])
        self.assertEqual((summary["types_on"], issues), (["60"], []))
        self.assertEqual((rules["60"]["reviewed"], rules["60"]["reviewed_by"], rules["60"]["reviewed_at"]), (True, "김검수", "2026-10-21"))
        self.assertTrue(all(r["reviewed"] for r in rules["60"]["rules"]))
        self.assertFalse(rules["61"]["reviewed"])   # 결과에 없는 유형은 그대로

    def test_one_wrong_rule_keeps_the_type_off_and_is_collected_as_an_issue(self):
        rules = make_rules()
        bad = {"decision": "ok", "rules": {"60_A_x": {"ok": True}, "60_B_y": {"ok": False, "note": "원문은 +20 입니다"}}}
        summary, issues = ar.apply(rules, make_factors(), [export(types={"60": bad})])
        self.assertEqual((summary["types_on"], summary["types_issue"]), ([], ["60"]))
        self.assertFalse(rules["60"]["reviewed"])
        self.assertIn("원문은 +20 입니다", issues[0][3])

    def test_missing_rule_decisions_do_not_turn_the_type_on(self):
        rules = make_rules()
        partial = {"decision": "ok", "rules": {"60_A_x": {"ok": True}}}
        summary, issues = ar.apply(rules, make_factors(), [export(types={"60": partial})])
        self.assertFalse(rules["60"]["reviewed"])
        self.assertIn("결정이 없는 규칙 1개", issues[0][3])

    def test_skipped_types_are_ignored(self):
        rules = make_rules()
        summary, issues = ar.apply(rules, make_factors(), [export(types={"60": {"decision": "skip"}})])
        self.assertEqual((summary["types_on"], summary["types_issue"], issues), ([], [], []))

    def test_two_reviewers_who_agree_are_fine_and_who_disagree_are_flagged(self):
        rules = make_rules()
        ar.apply(rules, make_factors(), [export("김", types={"60": ALL_OK}), export("이", types={"60": ALL_OK})])
        self.assertTrue(rules["60"]["reviewed"])
        rules = make_rules()
        no = {"decision": "issue", "rules": {"60_A_x": {"ok": False, "note": "다름"}}}
        summary, issues = ar.apply(rules, make_factors(), [export("김", types={"60": ALL_OK}), export("이", types={"60": no})])
        self.assertFalse(rules["60"]["reviewed"])
        self.assertIn("결정이 달라", issues[0][3])

    def test_results_without_a_reviewer_name_are_not_applied(self):
        rules = make_rules()
        summary, issues = ar.apply(rules, make_factors(), [export("", types={"60": ALL_OK})])
        self.assertFalse(rules["60"]["reviewed"])
        self.assertIn("이름이 없는", issues[0][3])


class WordingTests(unittest.TestCase):
    def test_ok_marks_the_sentence_reviewed(self):
        factors = make_factors()
        summary, _ = ar.apply(make_rules(), factors, [export(wording={"pdf_a": {"decision": "ok"}})])
        self.assertEqual(summary["words_ok"], ["pdf_a"])
        self.assertTrue(factors["pdf_a"]["reviewed"])

    def test_a_good_edit_is_applied_and_marked_reviewed(self):
        factors = make_factors()
        edit = {"decision": "edit", "title": "새 제목", "easy": "새 설명이에요.", "question": "{who}가 새로 했나요?"}
        summary, issues = ar.apply(make_rules(), factors, [export(wording={"pdf_a": edit})])
        self.assertEqual((summary["words_edited"], issues), (["pdf_a"], []))
        self.assertEqual((factors["pdf_a"]["title"], factors["pdf_a"]["question"], factors["pdf_a"]["reviewed"]), ("새 제목", "{who}가 새로 했나요?", True))

    def test_bad_edits_are_rejected_with_the_reason(self):
        for bad, reason in (({"title": "t", "easy": "e", "question": "했나요?"}, "{who}"), ({"title": "t", "easy": "e", "question": "{who}가 했어요"}, "?로 끝"),
                            ({"title": "t", "easy": "과실이 늘어요", "question": "{who}가 했나요?"}, "방향"), ({"title": "", "easy": "e", "question": "{who}가 했나요?"}, "비어")):
            factors = make_factors()
            summary, issues = ar.apply(make_rules(), factors, [export(wording={"pdf_a": {"decision": "edit", **bad}})])
            self.assertEqual(factors["pdf_a"]["title"], "제목")
            self.assertIn(reason, issues[0][3])

    def test_issue_decisions_are_collected_with_the_note(self):
        summary, issues = ar.apply(make_rules(), make_factors(), [export(wording={"pdf_a": {"decision": "issue", "note": "뜻이 달라요"}})])
        self.assertEqual((summary["words_issue"], issues[0][3]), (["pdf_a"], "뜻이 달라요"))


class IssueFileTests(unittest.TestCase):
    def test_issue_list_is_readable(self):
        text = ar.render_issues([("type", "60", "김", "원문은 +20 입니다")])
        self.assertIn("| 가감요소 유형 | 60 | 김 | 원문은 +20 입니다 |", text)
        self.assertIn("문제 없음", ar.render_issues([]))


if __name__ == "__main__":
    unittest.main()


class ReviewPageTests(unittest.TestCase):
    def test_the_page_data_covers_every_pdf_type_and_every_sentence(self):
        import make_review_page
        data = make_review_page.build_data()
        from avly.tables import ALL_ADJUSTMENT_RULES   # 지운 유형이 있어도 맞도록 숫자를 고정하지 않고 데이터와 비교한다
        pdf = [t for t in ALL_ADJUSTMENT_RULES.values() if any("pdf_source" in r for r in t["rules"])]
        self.assertEqual(len(data["types"]), len(pdf))
        self.assertEqual(sum(len(t["rules"]) for t in data["types"]), sum(len(t["rules"]) for t in pdf))
        self.assertGreaterEqual(len(data["factors"]), 68)
        for t in data["types"]:
            for r in t["rules"]:
                self.assertTrue(r["title"] and r["raw"] and r["chart"], r["id"])   # 모든 규칙에 쉬운 제목과 PDF 원문이 붙는다
        self.assertNotIn("11", {t["id"] for t in data["types"]})   # 사람이 먼저 입력한 기존 7개 유형은 제외한다
