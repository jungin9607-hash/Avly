"""판례 검수 결과를 자료에 반영하는 도구(tools/apply_case_review.py)와 검수 페이지 시험."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import apply_case_review as acr   # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent


def cases():
    return {"11": [{"court": "대법원", "case_number": "86다카1551", "summary": "요약", "source": "x"}],
            "126": [{"court": "서울중앙지방법원", "case_number": "2015나37411", "summary": "후진 출차", "source": "x"}]}


def export(key, reviewer="김검수", date="2026-10-21", **checks):
    return {"reviewer": reviewer, "date": date, "cases": {key: checks}}


ALL_OK = {"exists": "ok", "summary": "ok", "fits": "ok"}


class ApplyCaseReviewTests(unittest.TestCase):
    def test_all_ok_marks_the_case_verified(self):
        data = cases()
        summary, issues = acr.apply(data, [export("11|86다카1551", **ALL_OK)])
        self.assertEqual((summary["verified"], issues), (["11|86다카1551"], []))
        self.assertEqual((data["11"][0]["verified_date"], data["11"][0]["reviewed_by"]), ("2026-10-21", "김검수"))

    def test_a_wrong_type_link_is_removed_when_everyone_says_it_does_not_fit(self):
        data = cases()
        summary, issues = acr.apply(data, [export("126|2015나37411", exists="ok", summary="ok", fits="bad", note="후진 출차 사례")])
        self.assertEqual((summary["removed"], data["126"]), (["126|2015나37411"], []))
        self.assertIn("후진 출차 사례", issues[0][2])

    def test_other_problems_change_nothing_and_become_issues(self):
        data = cases()
        summary, issues = acr.apply(data, [export("11|86다카1551", exists="ok", summary="bad", fits="skip")])
        self.assertEqual((summary, "verified_date" in data["11"][0]), ({"verified": [], "removed": []}, False))
        self.assertIn("요약이 출처와 같은가", issues[0][2])
        self.assertIn("확인하지 못함", issues[0][2])

    def test_disagreement_and_missing_name_are_not_applied(self):
        data = cases()
        summary, issues = acr.apply(data, [export("11|86다카1551", **ALL_OK), export("11|86다카1551", reviewer="이검수", exists="ok", summary="ok", fits="bad")])
        self.assertEqual((summary["verified"], summary["removed"], len(issues)), ([], [], 1))
        summary, issues = acr.apply(cases(), [export("11|86다카1551", reviewer="", **ALL_OK)])
        self.assertIn("이름이 없는", issues[0][2])
        self.assertEqual(summary["verified"], [])

    def test_unknown_case_is_an_issue(self):
        _, issues = acr.apply(cases(), [export("11|없는번호", **ALL_OK)])
        self.assertIn("찾지 못했습니다", issues[0][2])


class CaseReviewPageTests(unittest.TestCase):
    def test_every_registered_case_has_a_card_and_the_export_script_works(self):
        page = Path(BACKEND.parent / "docs" / "review" / "case-review.html")
        if not page.is_file():
            self.skipTest("검수 페이지가 아직 만들어지지 않았습니다 (tools/make_case_review_page.py)")
        html = page.read_text(encoding="utf-8")
        data = json.loads(html.split('<script id="data" type="application/json">')[1].split("</script>")[0])
        registered = json.loads((BACKEND / "model" / "avly" / "data" / "verified_cases.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(len(t["cases"]) for t in data["types"]), sum(len(v) for v in registered.values()))


if __name__ == "__main__":
    unittest.main()
