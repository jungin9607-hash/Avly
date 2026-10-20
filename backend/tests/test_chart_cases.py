"""협회 도표의 참고 판례를 사고 유형에 붙이는 도구(tools/build_chart_cases.py)와 서버의 읽기 방식 시험."""

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import build_chart_cases as bcc   # noqa: E402

from app.worker import cases as case_module   # noqa: E402
from avly.tables import VERIFIED_CASES   # noqa: E402

TEXT = """⊙ 대법원 1986.12 9. 선고 86다카1551 판결
모든 차는 진로를 변경할 때 거리를 확보해야 한다.
⊙ 서울중앙지방법원 2018.5.29. 선고 2018나1901 판결,
2021. 7 . 8. 선고 2020나56904판결
무리하게 진로변경한 차와 제동하지 않은 차의 사고: A과실 30%
⊙ 인천지방법원 1998.10.23. 97가단8474 판결 신호위반 좌회전 사고: B과실 65%
⊙ 대법원 2015. 11. 12. 선고 2015도3107 판결
형사 사건이다."""


class ParseTests(unittest.TestCase):
    def test_headers_are_read_even_with_odd_spacing_and_missing_words(self):
        cases = bcc.parse_cases(TEXT, "차43-2")
        got = [(c["court"], c["date"], c["case_number"]) for c in cases]
        self.assertIn(("대법원", "1986-12-09", "86다카1551"), got)
        self.assertIn(("서울중앙지방법원", "2018-05-29", "2018나1901"), got)
        self.assertIn(("서울중앙지방법원", "2021-07-08", "2020나56904"), got)     # 한 요약을 공유하는 두 번째 사건
        self.assertIn(("인천지방법원", "1998-10-23", "97가단8474"), got)          # '선고'가 빠진 머리글
        self.assertEqual(len(got), 5)

    def test_a_shared_summary_is_kept_for_both_cases(self):
        shared = [c for c in bcc.parse_cases(TEXT, "차43-2") if c["case_number"] in ("2018나1901", "2020나56904")]
        self.assertEqual(len({c["summary"] for c in shared}), 1)
        self.assertIn("A과실 30%", shared[0]["summary"])

    def test_criminal_and_administrative_case_numbers_are_not_used(self):
        self.assertFalse(bcc.civil_fault_number("2015도3107"))
        self.assertFalse(bcc.civil_fault_number("2018고단123"))
        for ok in ("86다카1551", "2018나1901", "97가단8474", "2001다40732"):
            self.assertTrue(bcc.civil_fault_number(ok), ok)

    def test_cases_with_a_fault_ratio_come_first(self):
        cases = bcc.parse_cases(TEXT, "차43-2")
        ranked = sorted(cases, key=bcc.rank)
        self.assertTrue(bcc.FAULT.search(ranked[0]["summary"]))


class DataTests(unittest.TestCase):
    def test_registered_cases_are_civil_and_complete(self):
        self.assertGreaterEqual(len(VERIFIED_CASES), 90)
        for type_id, group in VERIFIED_CASES.items():
            self.assertLessEqual(len(group), 3, type_id)
            seen = set()
            for c in group:
                self.assertTrue(bcc.civil_fault_number(c["case_number"]), (type_id, c["case_number"]))
                self.assertTrue(c["court"] and c["summary"] and re.fullmatch(r"\d{4}-\d{2}-\d{2}", c["date"]), (type_id, c["case_number"]))
                self.assertNotIn(c["case_number"], seen, type_id)
                seen.add(c["case_number"])

    def test_chart_cases_are_marked_as_from_the_chart_and_not_as_human_verified(self):
        chart = next(c for g in VERIFIED_CASES.values() for c in g if c.get("chart_reference"))
        self.assertNotIn("verified_date", chart)
        self.assertIn("판결문 원문 조회 아님", chart["source_kind"])
        self.assertIn("accident.knia.or.kr", chart["source"])


class ServerReadTests(unittest.TestCase):
    CHART = {"court": "서울중앙지방법원", "date": "2018-05-29", "case_number": "2018나1901", "summary": "요약", "chart_reference": True,
             "source": "https://accident.knia.or.kr/x", "comparison_limit": "한계"}

    def test_chart_cases_are_same_type_references_that_are_not_marked_verified(self):
        row, link = case_module._db_case(self.CHART)
        self.assertEqual((row["source_kind"], row["verified"], row["fetched_at"]), ("knia_chart", False, None))
        self.assertEqual(link["relevance_status"], "registered_chart_reference")   # 화면에서 '같은 사고 유형'으로 보인다

    def test_human_verified_registered_cases_keep_their_verified_mark(self):
        row, link = case_module._db_case({**self.CHART, "verified_date": "2026-10-14"})
        self.assertEqual((row["verified"], row["source_kind"]), (True, "knia_chart"))

    def test_searched_cases_are_unchanged(self):
        row, link = case_module._db_case({"court": "서울중앙지방법원", "date": "2019-01-01", "case_number": "2018나1", "summary": "s"})
        self.assertEqual((row["source_kind"], row["verified"], link["relevance_status"]), ("law_api", False, "civil_traffic_context_reference"))


if __name__ == "__main__":
    unittest.main()
