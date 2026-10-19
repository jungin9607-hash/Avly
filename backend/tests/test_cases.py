import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from app.worker import cases
from tests.helpers import DbTestCase


def api_case(number="2020다1111", court="대법원", **extra):
    return {"court": court, "date": "20200304", "case_number": number, "summary": "주차장 출차 중 충돌한 사고의 과실을 따졌다.",
            "comparison_limit": "검색 일치 조건: 주차장 / 출차; 별도 검토 필요", "source": "https://www.law.go.kr/x", "case_api_id": "1",
            "case_name": "손해배상(자)", "relevance_status": "civil_traffic_context_reference", **extra}


class FakeFetcher:
    def __init__(self, result=None, status="ok", error=None):
        self.result, self.status, self.error, self.calls = result or [], status, error, []

    def fetch(self, accident_type_id):
        self.calls.append(accident_type_id)
        if self.error:
            raise self.error
        return self.result, self.status


class DateTests(unittest.TestCase):
    def test_parse_date(self):
        for raw in ("2015-12-18", "20151218", "2015.12.18", "2015. 12. 18.", "선고 2015년 12월 18일"):
            self.assertEqual(cases.parse_date(raw), "2015-12-18", raw)
        for raw in (None, "", "언제인지 모름", "2015-13-45"):
            self.assertIsNone(cases.parse_date(raw), raw)


class CaseServiceTests(DbTestCase):
    def setUp(self):
        super().setUp()
        from app.repository import Repository
        self.repo = Repository(self.engine)

    def service(self, fetcher=None, target=3):
        return cases.CaseService(self.repo, fetcher or FakeFetcher(), target)

    def test_seeding_registered_cases_is_idempotent_and_marks_them_verified(self):
        s = self.service()
        first = s.seed_registered()
        self.assertGreater(first, 0)
        self.assertEqual(s.seed_registered(), first)
        rows = self.repo.cases_for_type(126)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["court"], r["case_number"], r["source_kind"], r["verified"]), ("서울중앙지방법원", "2015나37411", "knia_chart", True))
        self.assertEqual(r["decided_on"].isoformat(), "2015-12-18")
        self.assertEqual(r["relevance_status"], "registered_chart_reference")
        self.assertIn("후진 출차", r["comparison_limit"])
        with self.engine.connect() as conn:
            from sqlalchemy import text
            from avly.tables import VERIFIED_CASES
            distinct = {(c["court"], c["case_number"]) for v in VERIFIED_CASES.values() for c in v}
            self.assertEqual(conn.execute(text("SELECT count(*) FROM legal_case")).scalar(), len(distinct))   # 같은 판례를 두 번 넣지 않는다

    def test_enough_cases_in_the_db_means_no_api_call(self):
        s = self.service(FakeFetcher())
        s.seed_registered()
        self.assertEqual(len(s.related_for(11)), 3)   # 11번 유형은 등록 판례가 3개
        self.assertEqual(s.fetcher.calls, [])

    def test_too_few_cases_are_topped_up_from_the_api_and_saved(self):
        fetcher = FakeFetcher([api_case("2020다1111"), api_case("2020다2222")])
        s = self.service(fetcher)
        s.seed_registered()
        result = s.related_for(126)   # 등록 판례 1개 + API 2개
        self.assertEqual(fetcher.calls, [126])
        self.assertEqual({c["case_number"] for c in result}, {"2015나37411", "2020다1111", "2020다2222"})
        fetched = next(c for c in result if c["case_number"] == "2020다1111")
        self.assertFalse(fetched["verified"])   # API 로 가져온 판례는 검수 전
        self.assertEqual((fetched["source_kind"], fetched["date"]), ("law_api", "2020-03-04"))
        self.assertEqual(fetched["source_label"], "법령정보 API의 판례")
        self.assertEqual(self.repo.get_case_lookup(126)["status"], "found")
        self.assertEqual(result[0]["case_number"], "2015나37411")   # 검수된 판례가 먼저
        s.related_for(126)
        self.assertEqual(fetcher.calls, [126])   # 쉬는 시간 안에는 다시 부르지 않는다

    def test_empty_result_is_remembered_and_not_asked_again(self):
        fetcher = FakeFetcher([])
        s = self.service(fetcher)
        self.assertEqual(s.related_for(5), [])
        self.assertEqual(s.related_for(5), [])
        self.assertEqual(fetcher.calls, [5])
        lookup = self.repo.get_case_lookup(5)
        self.assertEqual((lookup["status"], lookup["case_count"]), ("empty", 0))
        self.assertGreater(lookup["retry_after"], datetime.now(timezone.utc) + timedelta(hours=20))

    def test_api_error_never_breaks_the_analysis_and_retries_soon(self):
        fetcher = FakeFetcher(error=RuntimeError("API 장애"))
        s = self.service(fetcher)
        self.assertEqual(s.related_for(5), [])
        lookup = self.repo.get_case_lookup(5)
        self.assertEqual(lookup["status"], "error")
        self.assertLess(lookup["retry_after"], datetime.now(timezone.utc) + timedelta(minutes=11))
        # 쉬는 시간이 지나면 다시 시도하고 성공하면 저장한다
        self.repo.set_case_lookup(5, "error", 0, datetime.now(timezone.utc) - timedelta(seconds=1))
        fetcher.error, fetcher.result = None, [api_case()]
        self.assertEqual(len(s.related_for(5)), 1)
        self.assertEqual(self.repo.get_case_lookup(5)["status"], "found")

    def test_unavailable_api_is_not_recorded_as_no_cases(self):
        fetcher = FakeFetcher([], status="unavailable")
        s = self.service(fetcher)
        s.related_for(5)
        self.assertEqual(self.repo.get_case_lookup(5)["status"], "error")   # '판례 없음'으로 굳히지 않는다

    def test_a_case_shared_by_two_types_is_stored_once(self):
        s = self.service(FakeFetcher([api_case("2020다3333")]))
        s.related_for(5)
        s.related_for(6)
        self.assertEqual([c["case_number"] for c in s.related_for(5)], ["2020다3333"])
        self.assertEqual([c["case_number"] for c in s.related_for(6)], ["2020다3333"])
        with self.engine.connect() as conn:
            from sqlalchemy import text
            self.assertEqual(conn.execute(text("SELECT count(*) FROM legal_case")).scalar(), 1)
            self.assertEqual(conn.execute(text("SELECT count(*) FROM case_accident_type")).scalar(), 2)

    def test_upsert_never_lowers_a_verified_case(self):
        s = self.service()
        s.save(5, [api_case("2020다4444", verified_date="2026-10-14", relevance_status="registered_chart_reference")])
        s.save(5, [api_case("2020다4444")])   # 같은 판례를 검수 전 상태로 다시 저장해도
        row = self.repo.cases_for_type(5)[0]
        self.assertTrue(row["verified"])

    def test_view_shape(self):
        s = self.service()
        s.seed_registered()
        v = s.related_for(126)[0]
        self.assertEqual(set(v), {"_text", "case_id", "court", "date", "case_number", "title", "summary", "comparison_limit",
                                  "source_url", "source_kind", "source_label", "verified", "relevance_status"})
        self.assertTrue(v["_text"])   # AI 비교용 본문. 결과를 만들 때 빠진다 (등록 판례는 요약문)
        self.assertEqual(v["source_label"], "손해보험협회 도표에 소개된 판례 요약")


class FetcherTests(unittest.TestCase):
    def test_avly_fetcher_builds_a_csv_style_row_and_returns_the_status(self):
        from avly import law
        seen = {}

        def fake(row, client=None):
            seen.update(row)
            return [api_case()], {"status": "ok"}
        with mock.patch.object(law, "related_cases_for_row", fake):
            found, status = cases.AvlyCaseFetcher().fetch(126)
        self.assertEqual(status, "ok")
        self.assertEqual((seen["accident_type"], seen["accident_object_name"]), (126, "차대차"))
        self.assertEqual(seen["vehicle_b_progress_info_name"], "주차구역에서 직진 출차")
        self.assertEqual(len(found), 1)

    def test_without_an_api_key_the_fetcher_reports_unavailable_but_keeps_registered_cases(self):
        import os
        from avly import law
        with mock.patch.dict(os.environ, {}, clear=False):
            for name in ("law_api", "LAW_API_OC", "LAW_API_KEY"):
                os.environ.pop(name, None)
            found, status = cases.AvlyCaseFetcher().fetch(126)
        self.assertEqual(status, "unavailable")
        self.assertEqual([c["case_number"] for c in found], ["2015나37411"])   # 등록 자료만 돌려준다


if __name__ == "__main__":
    unittest.main()
