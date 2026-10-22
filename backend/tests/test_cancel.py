"""분석 취소: API 와 worker 가 함께 지켜야 하는 규칙.

- 대기 중이거나 분석 중인 분석만 취소할 수 있고, 취소하면 failed + CANCELLED 로 남는다.
- 취소한 분석은 worker 가 시작하지 않고, 진행 중이었다면 다음 단계에 들어가기 전에 멈추며, 끝난 뒤에도 되살리지 않는다.
- 취소해도 같은 영상으로 다시 분석할 수 있다.
"""

import unittest
from pathlib import Path
from uuid import UUID, uuid4

from app import status as st
from app.worker import runner
from app.worker.engines import ReplayEngine
from tests.test_api import ApiTestCase
from tests.test_worker import FIXTURES, StubRedaction, WorkerTestCase


class CancelApiTests(ApiTestCase):
    def cancel(self, analysis_id, headers):
        return self.client.post(f"/api/v1/analyses/{analysis_id}/cancel", headers=headers)

    def view(self, analysis_id, headers):
        return self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()

    def test_queued_analysis_is_cancelled_and_its_job_is_dropped(self):
        accident_id, headers, analysis_id = self.make_analysis()
        r = self.cancel(analysis_id, headers)
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual((body["status"], body["error"]["code"]), ("failed", "CANCELLED"))
        self.assertIsNone(self.repo.claim_job(), "취소한 분석의 작업은 worker 가 가져가지 못한다")
        # 같은 사고(같은 영상)로 다시 분석을 시작할 수 있다
        again = self.client.post(f"/api/v1/accidents/{accident_id}/analyses", headers=headers)
        self.assertEqual(again.status_code, 202, again.text)
        self.assertNotEqual(again.json()["analysis_id"], analysis_id)

    def test_processing_analysis_can_be_cancelled(self):
        _, headers, analysis_id = self.make_analysis()
        self.repo.update_analysis(UUID(analysis_id), status=st.PROCESSING, stage="overview")
        self.assertEqual(self.cancel(analysis_id, headers).json()["error"]["code"], "CANCELLED")

    def test_cancelling_twice_is_harmless(self):
        _, headers, analysis_id = self.make_analysis()
        first = self.cancel(analysis_id, headers)
        second = self.cancel(analysis_id, headers)
        self.assertEqual((first.status_code, second.status_code), (200, 200))
        self.assertEqual(second.json()["error"]["code"], "CANCELLED")

    def test_finished_or_confirming_analyses_cannot_be_cancelled(self):
        for status in (st.AWAITING_CONFIRMATION, st.UNSUPPORTED):
            _, headers, analysis_id = self.make_analysis()
            fields = {"unsupported_reason": "차대보행자"} if status == st.UNSUPPORTED else {}
            self.repo.update_analysis(UUID(analysis_id), status=status, stage=None, **fields)
            r = self.cancel(analysis_id, headers)
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ANALYSIS_NOT_CANCELLABLE"), status)
            self.assertEqual(self.view(analysis_id, headers)["status"], status, "취소하지 못했으면 상태를 건드리지 않는다")

    def test_a_failure_that_is_not_a_cancellation_is_not_reported_as_one(self):
        _, headers, analysis_id = self.make_analysis()
        self.repo.update_analysis(UUID(analysis_id), status=st.FAILED, stage=None, error_code="ANALYSIS_FAILED", error_message="x")
        r = self.cancel(analysis_id, headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ANALYSIS_NOT_CANCELLABLE"))

    def test_only_the_owner_can_cancel(self):
        _, _, analysis_id = self.make_analysis()
        other = {"X-Session-Id": str(uuid4())}
        r = self.cancel(analysis_id, other)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/analyses/{analysis_id}/cancel").status_code, 401)


class CancelWorkerTests(WorkerTestCase):
    def cancel(self, analysis):
        self.assertEqual(self.repo.cancel_analysis(analysis["id"]), "cancelled")

    def test_a_cancelled_analysis_is_never_started(self):
        _, _, analysis = self.make_analysis()
        redaction = StubRedaction()
        w = self.worker(redaction=redaction)
        w.repo.claim_job()   # worker 가 작업을 가져온 직후에 취소된 경우를 흉내 낸다
        self.cancel(analysis)
        w.analyze(analysis["id"])
        self.assertEqual(redaction.calls, 0, "취소된 분석은 비식별화도 하지 않는다")
        self.assertEqual(self.analysis(analysis)["error_code"], "CANCELLED")

    def test_cancellation_during_the_analysis_stops_it_at_the_next_stage(self):
        _, _, analysis = self.make_analysis()
        calls = []

        class CancellingEngine(ReplayEngine):
            def analyze(inner, video_path, report, place=None):
                report("overview")
                calls.append("overview")
                self.cancel(analysis)          # 첫 단계가 끝난 뒤에 사용자가 취소한다
                report("detail_review")        # 다음 단계에 들어가려는 순간 멈춰야 한다
                calls.append("detail_review")  # 여기까지 오면 안 된다
                return super().analyze(video_path, report, place=place)

        w = self.worker(engine=CancellingEngine(directory=FIXTURES))
        w.analyze(analysis["id"])
        self.assertEqual(calls, ["overview"])
        row = self.analysis(analysis)
        self.assertEqual((row["status"], row["error_code"]), (st.FAILED, "CANCELLED"))
        self.assertIsNone(row["scene"], "취소된 분석에는 결과를 저장하지 않는다")

    def test_an_analysis_cancelled_after_its_last_stage_is_not_revived(self):
        _, _, analysis = self.make_analysis()

        class LateCancelEngine(ReplayEngine):
            def analyze(inner, video_path, report, place=None):
                result = super().analyze(video_path, report, place=place)
                self.cancel(analysis)          # 마지막 단계 보고 뒤, 결과를 저장하기 직전에 취소
                return result

        self.worker(engine=LateCancelEngine(directory=FIXTURES)).analyze(analysis["id"])
        row = self.analysis(analysis)
        self.assertEqual((row["status"], row["error_code"]), (st.FAILED, "CANCELLED"))
        self.assertIsNone(row["scene"])

    def test_a_later_failure_does_not_overwrite_the_cancellation(self):
        _, _, analysis = self.make_analysis()

        class FailingAfterCancel(ReplayEngine):
            def analyze(inner, video_path, report, place=None):
                self.cancel(analysis)
                raise RuntimeError("boom")

        self.worker(engine=FailingAfterCancel(directory=FIXTURES)).analyze(analysis["id"])
        self.assertEqual(self.analysis(analysis)["error_code"], "CANCELLED")

    def test_uncancelled_analysis_still_reaches_confirmation(self):
        _, _, analysis = self.make_analysis()
        self.worker().analyze(analysis["id"])
        self.assertEqual(self.analysis(analysis)["status"], st.AWAITING_CONFIRMATION)

    def test_worker_moves_on_to_the_next_analysis_after_one_is_cancelled(self):
        _, _, first = self.make_analysis()
        _, _, second = self.make_analysis()
        self.cancel(first)
        w = self.worker()
        self.assertTrue(w.run_once())
        self.assertEqual(self.analysis(second)["status"], st.AWAITING_CONFIRMATION, "취소된 분석이 줄을 막지 않는다")
        self.assertEqual(self.analysis(first)["error_code"], "CANCELLED")


if __name__ == "__main__":
    unittest.main()
