import dataclasses
import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app import status as st
from app import storage
from app.config import settings
from tests.helpers import DbTestCase

CONSENT = {"version": "2026-10-19", "analysis": True, "retention": False}


class ApiTestCase(DbTestCase):
    def setUp(self):
        super().setUp()
        from app import deps
        from main import app
        deps._repository.cache_clear()
        self.client = TestClient(app)
        self.repo = deps.get_repo()

    # 도우미
    def make_accident(self, retention=False):
        r = self.client.post("/api/v1/accidents", json={"title": "테스트 사고", "consent": {**CONSENT, "retention": retention}})
        self.assertEqual(r.status_code, 201, r.text)
        body = r.json()
        return body["id"], {"X-Session-Id": body["session_id"]}

    def upload(self, accident_id, headers, name="a.mp4", data=b"fake-video"):
        return self.client.post(f"/api/v1/accidents/{accident_id}/videos", files={"file": (name, data, "video/mp4")}, headers=headers)

    def make_analysis(self):
        accident_id, headers = self.make_accident()
        self.assertEqual(self.upload(accident_id, headers).status_code, 201)
        r = self.client.post(f"/api/v1/accidents/{accident_id}/analyses", headers=headers)
        self.assertEqual(r.status_code, 202, r.text)
        return accident_id, headers, r.json()["analysis_id"]

    def make_awaiting(self, situation=None, facts=None):
        accident_id, headers, analysis_id = self.make_analysis()
        scene = {"situation": situation or {"candidates": [], "default_index": None}, "adjustment_facts": facts or []}
        self.repo.update_analysis(UUID(analysis_id), status=st.AWAITING_CONFIRMATION, stage=None, scene=scene)
        return accident_id, headers, analysis_id


class AccidentTests(ApiTestCase):
    def test_consent_is_required(self):
        r = self.client.post("/api/v1/accidents", json={"title": "x", "consent": {**CONSENT, "analysis": False}})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "CONSENT_REQUIRED"))
        r = self.client.post("/api/v1/accidents", json={"title": "x"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "VALIDATION_ERROR"))

    def test_create_returns_session_and_records_consent(self):
        r = self.client.post("/api/v1/accidents", json={"title": " 제목 ", "consent": {**CONSENT, "retention": True}})
        body = r.json()
        self.assertEqual((r.status_code, body["title"], body["status"]), (201, "제목", "uploaded"))
        UUID(body["session_id"])
        row = self.repo.get_accident(UUID(body["id"]))
        self.assertEqual(row["consent_version"], "2026-10-19")
        self.assertIsNotNone(row["consent_at"])
        self.assertIsNotNone(row["retention_consent_at"])
        self.assertIsNotNone(row["expires_at"])

    def test_no_retention_consent_leaves_it_empty(self):
        accident_id, _ = self.make_accident(retention=False)
        self.assertIsNone(self.repo.get_accident(UUID(accident_id))["retention_consent_at"])

    def test_session_is_required_and_isolated(self):
        accident_id, headers = self.make_accident()
        r = self.client.get(f"/api/v1/accidents/{accident_id}")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (401, "SESSION_REQUIRED"))
        r = self.client.get(f"/api/v1/accidents/{accident_id}", headers={"X-Session-Id": "not-a-uuid"})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (401, "SESSION_INVALID"))
        r = self.client.get(f"/api/v1/accidents/{accident_id}", headers={"X-Session-Id": str(uuid4())})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (404, "ACCIDENT_NOT_FOUND"))
        self.assertEqual(self.client.get(f"/api/v1/accidents/{accident_id}", headers=headers).status_code, 200)


class VideoTests(ApiTestCase):
    def test_only_one_video_per_accident(self):
        accident_id, headers = self.make_accident()
        first = self.upload(accident_id, headers)
        self.assertEqual(first.status_code, 201)
        self.assertNotIn("storage_key", first.json())
        second = self.upload(accident_id, headers)
        self.assertEqual((second.status_code, second.json()["error"]["code"]), (409, "VIDEO_ALREADY_UPLOADED"))
        files = [p for p in (settings.upload_dir / accident_id).iterdir()]
        self.assertEqual(len(files), 1)   # 거부된 파일은 저장되지 않는다
        detail = self.client.get(f"/api/v1/accidents/{accident_id}", headers=headers).json()
        self.assertEqual(detail["video"]["id"], first.json()["id"])

    def test_video_expires_with_the_session(self):
        accident_id, headers = self.make_accident()
        self.upload(accident_id, headers)
        accident = self.repo.get_accident(UUID(accident_id))
        video = self.repo.get_video(UUID(accident_id), "original")
        self.assertEqual(video["expires_at"], accident["expires_at"])

    def test_rejects_bad_files(self):
        accident_id, headers = self.make_accident()
        r = self.upload(accident_id, headers, name="a.exe")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (415, "UNSUPPORTED_FILE_TYPE"))
        r = self.upload(accident_id, headers, data=b"")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (400, "EMPTY_FILE"))
        small = dataclasses.replace(settings, max_upload_size_mb=1)
        with mock.patch.object(storage, "settings", small):
            r = self.upload(accident_id, headers, data=b"0" * (2 * 1024 * 1024))
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (413, "FILE_TOO_LARGE"))
        self.assertFalse(list((settings.upload_dir / accident_id).glob("*")) if (settings.upload_dir / accident_id).exists() else [])
        self.assertEqual(self.upload(accident_id, headers).status_code, 201)   # 거부된 뒤에도 올릴 수 있다

    def test_cannot_upload_to_someone_elses_accident(self):
        accident_id, _ = self.make_accident()
        r = self.upload(accident_id, {"X-Session-Id": str(uuid4())})
        self.assertEqual(r.status_code, 404)


class AnalysisStartTests(ApiTestCase):
    def test_requires_video(self):
        accident_id, headers = self.make_accident()
        r = self.client.post(f"/api/v1/accidents/{accident_id}/analyses", headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "VIDEO_REQUIRED"))

    def test_start_queues_a_job_and_blocks_a_second_run(self):
        accident_id, headers, analysis_id = self.make_analysis()
        job = self.repo.claim_job()
        self.assertEqual((str(job["analysis_id"]), job["kind"], job["status"]), (analysis_id, "analyze", "running"))
        r = self.client.post(f"/api/v1/accidents/{accident_id}/analyses", headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ANALYSIS_IN_PROGRESS"))
        self.assertEqual(self.client.get(f"/api/v1/accidents/{accident_id}", headers=headers).json()["status"], "analyzing")

    def test_place_is_kept_for_the_worker(self):
        accident_id, headers = self.make_accident()
        self.upload(accident_id, headers)
        r = self.client.post(f"/api/v1/accidents/{accident_id}/analyses", json={"place": "주차장(또는 차도가 아닌 장소)"}, headers=headers)
        self.assertEqual(r.status_code, 202, r.text)
        self.assertEqual(self.repo.claim_job()["payload"]["place"], "주차장(또는 차도가 아닌 장소)")

    def test_unknown_place_is_rejected(self):
        accident_id, headers = self.make_accident()
        self.upload(accident_id, headers)
        r = self.client.post(f"/api/v1/accidents/{accident_id}/analyses", json={"place": "하늘"}, headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "INVALID_PLACE"))

    def test_can_start_again_after_failure(self):
        accident_id, headers, analysis_id = self.make_analysis()
        self.repo.update_analysis(UUID(analysis_id), status=st.FAILED, error_code="X", error_message="실패")
        r = self.client.post(f"/api/v1/accidents/{accident_id}/analyses", headers=headers)
        self.assertEqual(r.status_code, 202)
        self.assertEqual(self.repo.get_analysis(UUID(r.json()["analysis_id"]))["attempt"], 2)

    def test_status_view(self):
        accident_id, headers, analysis_id = self.make_analysis()
        view = self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()
        self.assertEqual((view["status"], view["stage"], view["situation"], view["result"], view["error"]), ("queued", None, None, None, None))
        self.repo.update_analysis(UUID(analysis_id), status=st.PROCESSING, stage="overview")
        view = self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()
        self.assertEqual(view["stage"], {"id": "overview", "index": 2, "total": 5, "label": "전체 흐름 분석"})
        self.repo.update_analysis(UUID(analysis_id), status=st.FAILED, error_code="VIDEO_TOO_LONG", error_message="영상이 깁니다")
        view = self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()
        self.assertEqual((view["stage"], view["error"]), (None, {"code": "VIDEO_TOO_LONG", "message": "영상이 깁니다"}))

    def test_view_identifies_the_engine_that_actually_created_the_result(self):
        _, headers, analysis_id = self.make_analysis()
        self.repo.update_analysis(UUID(analysis_id), status=st.AWAITING_CONFIRMATION, scene={"engine": "fake"})
        view = self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()
        self.assertEqual(view["engine"], "fake")

    def test_unsupported_view_and_accident_status(self):
        accident_id, headers, analysis_id = self.make_analysis()
        self.repo.update_analysis(UUID(analysis_id), status=st.UNSUPPORTED, unsupported_reason="차대보행자 사고는 지원하지 않습니다.")
        view = self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()
        self.assertEqual((view["status"], view["unsupported_reason"], view["error"]), ("unsupported", "차대보행자 사고는 지원하지 않습니다.", None))
        self.assertEqual(self.client.get(f"/api/v1/accidents/{accident_id}", headers=headers).json()["status"], "unsupported")

    def test_analysis_is_isolated_by_session(self):
        _, _, analysis_id = self.make_analysis()
        r = self.client.get(f"/api/v1/analyses/{analysis_id}", headers={"X-Session-Id": str(uuid4())})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (404, "ANALYSIS_NOT_FOUND"))


class ConfirmTests(ApiTestCase):
    def test_not_awaiting_is_rejected(self):
        accident_id, headers, analysis_id = self.make_analysis()
        r = self.client.post(f"/api/v1/analyses/{analysis_id}/confirm", json={"accident_type_id": 11, "role": "A"}, headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ANALYSIS_NOT_AWAITING"))

    def test_adjustment_questions_with_suggestions(self):
        facts = [{"actor": "B", "factor": "signal_delay", "value": "있음", "status": "observed", "reason": "깜빡이 없음"}]
        _, headers, analysis_id = self.make_awaiting(facts=facts)
        r = self.client.get(f"/api/v1/analyses/{analysis_id}/adjustment-questions", params={"accident_type_id": 11, "role": "A"}, headers=headers)
        body = r.json()
        self.assertEqual((r.status_code, body["registered"]), (200, True))
        by = {q["key"]: q for q in body["questions"]}
        self.assertEqual(by["other.signal_delay"]["suggested"]["answer"], "예")
        r = self.client.get(f"/api/v1/analyses/{analysis_id}/adjustment-questions", params={"accident_type_id": 2, "role": "A"}, headers=headers)
        self.assertEqual((r.json()["registered"], r.json()["questions"]), (False, []))
        r = self.client.get(f"/api/v1/analyses/{analysis_id}/adjustment-questions", params={"accident_type_id": 99999, "role": "A"}, headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (404, "ACCIDENT_TYPE_NOT_FOUND"))

    def test_confirm_validation(self):
        _, headers, analysis_id = self.make_awaiting()
        url = f"/api/v1/analyses/{analysis_id}/confirm"
        r = self.client.post(url, json={"accident_type_id": 11}, headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "ROLE_REQUIRED"))
        r = self.client.post(url, json={"accident_type_id": 99999, "role": "A"}, headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (404, "ACCIDENT_TYPE_NOT_FOUND"))
        r = self.client.post(url, json={"accident_type_id": 11, "role": "A", "answers": [{"key": "other.no_such", "answer": "예"}]}, headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "INVALID_ANSWER"))
        dup = [{"key": "other.signal_delay", "answer": "예"}, {"key": "other.signal_delay", "answer": "아니요"}]
        r = self.client.post(url, json={"accident_type_id": 11, "role": "A", "answers": dup}, headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "INVALID_ANSWER"))
        r = self.client.post(url, json={"accident_type_id": 11, "role": "A", "answers": [{"key": "other.signal_delay", "answer": "네"}]}, headers=headers)
        self.assertEqual(r.status_code, 422)
        r = self.client.post(url, json={"accident_type_id": None, "answers": [{"key": "other.signal_delay", "answer": "예"}]}, headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "INVALID_ANSWER"))
        # 모든 요청이 거부됐으므로 아직 확인 대기 상태다
        self.assertEqual(self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).json()["status"], "awaiting_confirmation")

    def test_confirm_queues_finalize_once(self):
        _, headers, analysis_id = self.make_awaiting()
        self.repo.claim_job()  # 처음의 analyze 작업을 치운다
        body = {"accident_type_id": 11, "role": "A", "answers": [{"key": "other.signal_delay", "answer": "예"}]}
        r = self.client.post(f"/api/v1/analyses/{analysis_id}/confirm", json=body, headers=headers)
        self.assertEqual(r.status_code, 202, r.text)
        view = r.json()
        self.assertEqual((view["status"], view["stage"]["id"]), ("processing", "finalize"))
        row = self.repo.get_analysis(UUID(analysis_id))
        self.assertEqual(row["confirmed"], {"accident_type_id": 11, "role": "A", "answers": {"other.signal_delay": "예"}})
        job = self.repo.claim_job()
        self.assertEqual((job["kind"], str(job["analysis_id"])), ("finalize", analysis_id))
        again = self.client.post(f"/api/v1/analyses/{analysis_id}/confirm", json=body, headers=headers)
        self.assertEqual((again.status_code, again.json()["error"]["code"]), (409, "ANALYSIS_NOT_AWAITING"))

    def test_confirm_without_a_type_is_allowed(self):
        _, headers, analysis_id = self.make_awaiting()
        r = self.client.post(f"/api/v1/analyses/{analysis_id}/confirm", json={"accident_type_id": None}, headers=headers)
        self.assertEqual(r.status_code, 202)
        self.assertEqual(self.repo.get_analysis(UUID(analysis_id))["confirmed"], {"accident_type_id": None, "role": None, "answers": {}})

    def test_report_is_not_implemented(self):
        _, headers, analysis_id = self.make_analysis()
        r = self.client.post(f"/api/v1/analyses/{analysis_id}/reports", headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ANALYSIS_NOT_COMPLETED"))
        self.repo.update_analysis(UUID(analysis_id), status=st.COMPLETED, result={"state": "final"})
        r = self.client.post(f"/api/v1/analyses/{analysis_id}/reports", headers=headers)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (501, "REPORT_NOT_IMPLEMENTED"))


class MediaTests(ApiTestCase):
    def masked_video(self, accident_id, data=b"0123456789" * 100):
        key = f"{accident_id}/masked-test.mp4"
        path = storage.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.repo.add_video(UUID(accident_id), "masked", key, size_bytes=len(data),
                            source_video_id=self.repo.get_video(UUID(accident_id), "original")["id"])
        return data

    def test_video_url_is_unavailable_until_a_masked_video_exists(self):
        accident_id, headers = self.make_accident()
        self.upload(accident_id, headers)
        r = self.client.get(f"/api/v1/accidents/{accident_id}/video-url", headers=headers)
        self.assertEqual(r.json(), {"available": False, "url": None, "expires_at": None})

    def test_masked_video_streams_with_range_and_original_never_does(self):
        accident_id, headers = self.make_accident()
        self.upload(accident_id, headers)
        data = self.masked_video(accident_id)
        body = self.client.get(f"/api/v1/accidents/{accident_id}/video-url", headers=headers).json()
        self.assertTrue(body["available"])
        r = self.client.get(body["url"])   # 서명 URL 은 헤더 없이 열린다
        self.assertEqual((r.status_code, r.content), (200, data))
        r = self.client.get(body["url"], headers={"Range": "bytes=10-19"})
        self.assertEqual((r.status_code, r.content), (206, data[10:20]))
        from app.security import sign_media
        token, _ = sign_media(UUID(accident_id), "original")
        self.assertEqual(self.client.get(f"/api/v1/media/{token}").status_code, 403)

    def test_bad_or_expired_links_are_rejected(self):
        accident_id, headers = self.make_accident()
        self.upload(accident_id, headers)
        self.masked_video(accident_id)
        url = self.client.get(f"/api/v1/accidents/{accident_id}/video-url", headers=headers).json()["url"]
        self.assertEqual(self.client.get(url[:-1] + ("0" if url[-1] != "0" else "1")).status_code, 403)
        from app.security import sign_media
        token, _ = sign_media(UUID(accident_id), "masked", ttl=-5)
        self.assertEqual(self.client.get(f"/api/v1/media/{token}").status_code, 403)

    def test_deleted_file_is_not_available(self):
        accident_id, headers = self.make_accident()
        self.upload(accident_id, headers)
        self.masked_video(accident_id)
        storage.delete(f"{accident_id}/masked-test.mp4")
        r = self.client.get(f"/api/v1/accidents/{accident_id}/video-url", headers=headers)
        self.assertFalse(r.json()["available"])


class CatalogAndHealthTests(ApiTestCase):
    def test_catalog(self):
        first = self.client.get("/api/v1/catalog/accident-types")
        self.assertEqual(first.headers["cache-control"], "no-cache")
        again = self.client.get("/api/v1/catalog/accident-types", headers={"If-None-Match": first.headers["etag"]})
        self.assertEqual((again.status_code, again.content), (304, b""))   # 같으면 본문 없이 확인만
        body = first.json()
        self.assertEqual(body["count"], 261)
        self.assertEqual({i["role"] for i in body["items"]}, {"A", "B"})

    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/health/db").json()["status"], "ok")

    def test_cors_allows_the_frontend_and_session_header(self):
        r = self.client.options("/api/v1/accidents", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                                                                "Access-Control-Request-Headers": "x-session-id,content-type"})
        self.assertEqual(r.headers["access-control-allow-origin"], "http://localhost:5173")
        self.assertIn("x-session-id", r.headers["access-control-allow-headers"].lower())


class JobTests(ApiTestCase):
    def test_jobs_are_claimed_once_in_order(self):
        _, _, first = self.make_analysis()
        _, _, second = self.make_analysis()
        j1, j2 = self.repo.claim_job(), self.repo.claim_job()
        self.assertEqual((str(j1["analysis_id"]), str(j2["analysis_id"])), (first, second))
        self.assertIsNone(self.repo.claim_job())

    def test_stale_running_jobs_are_requeued_then_failed(self):
        self.make_analysis()
        job = self.repo.claim_job()
        time.sleep(1.1)
        self.assertEqual(self.repo.requeue_stale_jobs(max_age_seconds=1, max_attempts=2), (1, 0))
        again = self.repo.claim_job()
        self.assertEqual((again["id"], again["attempts"]), (job["id"], 2))
        time.sleep(1.1)
        self.assertEqual(self.repo.requeue_stale_jobs(max_age_seconds=1, max_attempts=2), (0, 1))
        row = self.repo.get_analysis(job["analysis_id"])
        self.assertEqual((row["status"], row["stage"], row["error_code"]), ("failed", None, "WORKER_TIMEOUT"))
        self.assertEqual(self.repo.get_accident(row["accident_id"])["status"], "failed")
        self.assertIsNone(self.repo.claim_job())


if __name__ == "__main__":
    unittest.main()


class SessionEndTests(ApiTestCase):
    """세션이 끝나면 결과가 사라지고, '결과 지우기'로 바로 지울 수도 있다."""

    def end_session(self, accident_id):
        from sqlalchemy import text
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE accident SET expires_at = now() - interval '1 minute' WHERE id = :a"), {"a": accident_id})

    def test_results_are_hidden_after_the_session_ends_even_before_cleanup(self):
        accident_id, headers, analysis_id = self.make_awaiting()
        self.assertEqual(self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).status_code, 200)
        self.end_session(accident_id)
        for path in (f"/api/v1/analyses/{analysis_id}", f"/api/v1/accidents/{accident_id}", f"/api/v1/accidents/{accident_id}/video-url",
                     f"/api/v1/analyses/{analysis_id}/adjustment-questions?accident_type_id=1&role=A"):
            r = self.client.get(path, headers=headers)
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (410, "SESSION_EXPIRED"), path)
        r = self.client.post(f"/api/v1/analyses/{analysis_id}/confirm", headers=headers, json={"accident_type_id": None})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (410, "SESSION_EXPIRED"))

    def test_someone_elses_expired_result_is_still_not_found(self):
        accident_id, _, analysis_id = self.make_awaiting()
        self.end_session(accident_id)
        r = self.client.get(f"/api/v1/analyses/{analysis_id}", headers={"X-Session-Id": str(uuid4())})
        self.assertEqual(r.status_code, 404)   # 남의 분석은 만료 여부도 알려 주지 않는다

    def test_expired_masked_video_cannot_be_played(self):
        accident_id, headers = self.make_accident()
        self.upload(accident_id, headers)
        key = f"{accident_id}/masked-test.mp4"
        (settings.upload_dir / accident_id).mkdir(parents=True, exist_ok=True)
        storage.path_for(key).write_bytes(b"x" * 20)
        self.repo.add_video(UUID(accident_id), "masked", key, size_bytes=20, source_video_id=self.repo.get_video(UUID(accident_id), "original")["id"])
        from app.security import sign_media
        token, _ = sign_media(UUID(accident_id), "masked")
        self.assertEqual(self.client.get(f"/api/v1/media/{token}").status_code, 200)
        self.end_session(accident_id)
        self.assertEqual(self.client.get(f"/api/v1/media/{token}").status_code, 404)

    def test_delete_clears_the_result_and_videos_at_once(self):
        accident_id, headers, analysis_id = self.make_awaiting(situation={"summary": "비밀 요약", "candidates": [], "default_index": None})
        self.repo.update_analysis(UUID(analysis_id), status=st.COMPLETED, result={"state": "final"}, fault_me=30, fault_other=70)
        r = self.client.delete(f"/api/v1/accidents/{accident_id}", headers=headers)
        self.assertEqual((r.status_code, r.content), (204, b""))
        row = self.repo.get_analysis(UUID(analysis_id))
        self.assertEqual([row["scene"], row["result"], row["fault_me"]], [None, {}, None])   # 정리 작업을 기다리지 않고 지운다
        self.assertEqual(self.repo.get_accident(UUID(accident_id))["title"], "삭제됨")
        self.assertEqual(self.client.get(f"/api/v1/analyses/{analysis_id}", headers=headers).status_code, 410)
        video = self.repo.get_video(UUID(accident_id), "original")
        self.assertLessEqual(video["expires_at"], datetime.now(timezone.utc))   # 영상 파일은 worker 가 곧 지운다

    def test_delete_needs_the_owner_session(self):
        accident_id, _ = self.make_accident()
        self.assertEqual(self.client.delete(f"/api/v1/accidents/{accident_id}").status_code, 401)
        self.assertEqual(self.client.delete(f"/api/v1/accidents/{accident_id}", headers={"X-Session-Id": str(uuid4())}).status_code, 404)

    def test_defaults_are_two_hours_and_ninety_days(self):
        from app.config import load_settings
        with mock.patch.dict(os.environ):
            os.environ.pop("SESSION_TTL_HOURS", None)
            os.environ.pop("RETENTION_DAYS", None)
            loaded = load_settings()
        self.assertEqual((loaded.session_ttl_hours, loaded.retention_days), (2, 90))
