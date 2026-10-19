import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from uuid import UUID

from app import status as st
from app import storage
from app.worker import cleanup, finalize, runner
from app.worker.engines import AvlyEngine, EngineNotConfigured, FakeEngine, ReplayEngine, make_engine
from app.worker.redaction import DevCopyRedaction, make_redaction
from tests.helpers import DbTestCase

FIXTURES = Path(__file__).parent / "fixtures"


class StubRedaction:
    name = "stub"

    def __init__(self, stats=None, fail=None):
        self.stats, self.fail, self.calls = stats or {}, fail, 0

    def redact(self, source, destination):
        self.calls += 1
        if self.fail:
            raise self.fail
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = Path(source).read_bytes()
        destination.write_bytes(data if data.startswith(b"FAKE") else b"masked:" + data)   # FAKE 지시는 그대로 넘긴다
        return self.stats


class WorkerTestCase(DbTestCase):
    def setUp(self):
        super().setUp()
        from app.repository import Repository
        self.repo = Repository(self.engine)

    def make_analysis(self, content=b"video", retention=False):
        accident = self.repo.create_accident("테스트", "v1", retention, 24)
        key = f"{accident['id']}/original-test.mp4"
        path = storage.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        video = self.repo.add_video(accident["id"], "original", key, size_bytes=len(content), expires_at=accident["expires_at"])
        analysis = self.repo.create_analysis(accident["id"], video["id"])
        return accident, video, analysis

    def worker(self, engine=None, redaction=None, cases=None):
        return runner.Worker(self.repo, engine or ReplayEngine(directory=FIXTURES), redaction or StubRedaction(), cases)

    def analysis(self, analysis):
        return self.repo.get_analysis(analysis["id"])


class AnalyzeTests(WorkerTestCase):
    def test_analyze_reaches_awaiting_confirmation_with_a_masked_video(self):
        accident, original, analysis = self.make_analysis()
        redaction = StubRedaction(stats={"duration": 10.0, "fps": 30.0, "width": 1280, "height": 720, "frames": 300,
                                         "frames_with_plates": 40, "plate_detections": 55, "frames_with_people": 12, "person_detections": 20})
        w = self.worker(redaction=redaction)
        self.assertTrue(w.run_once())
        self.assertFalse(w.run_once())   # 더 처리할 작업이 없다
        row = self.analysis(analysis)
        self.assertEqual((row["status"], row["stage"]), (st.AWAITING_CONFIRMATION, None))
        self.assertEqual(row["scene"]["situation"]["candidates"][0]["accident_type_id"], 11)
        self.assertEqual(row["scene"]["engine"], "replay")
        masked = self.repo.get_video(accident["id"], "masked")
        self.assertEqual(row["video_id"], masked["id"])   # 이후 분석은 비식별 영상만 가리킨다
        self.assertEqual(masked["source_video_id"], original["id"])
        self.assertTrue(storage.path_for(masked["storage_key"]).read_bytes().startswith(b"masked:"))
        self.assertEqual((masked["redact_frames_total"], masked["plate_frames_detected"], masked["person_detections"]), (300, 40, 20))
        self.assertEqual(float(masked["duration"]), 10.0)
        self.assertIsNotNone(row["started_at"])
        self.assertEqual(self.repo.get_accident(accident["id"])["status"], "analyzing")

    def test_masked_video_follows_the_retention_consent(self):
        for retention in (False, True):
            accident, _, _ = self.make_analysis(retention=retention)
            self.worker().run_once()
            masked = self.repo.get_video(accident["id"], "masked")
            self.assertEqual(masked["expires_at"], None if retention else accident["expires_at"])
            original = self.repo.get_video(accident["id"], "original")
            self.assertEqual(original["expires_at"], accident["expires_at"])   # 원본은 동의와 상관없이 세션이 끝나면 삭제

    def test_stage_logs_are_saved(self):
        _, _, analysis = self.make_analysis()
        self.worker().run_once()
        with self.engine.connect() as conn:
            from sqlalchemy import text
            rows = conn.execute(text("SELECT stage, provider FROM analysis_stage_log WHERE analysis_id = :a"), {"a": analysis["id"]}).all()
        self.assertGreaterEqual(len(rows), 1)

    def test_unsupported_accident_stops_the_analysis(self):
        accident, _, analysis = self.make_analysis(content="FAKE unsupported 차대보행자\n".encode())
        self.worker(engine=FakeEngine(directory=FIXTURES)).run_once()
        row = self.analysis(analysis)
        self.assertEqual((row["status"], row["unsupported_reason"]), (st.UNSUPPORTED, "차대보행자 사고는 지원하지 않습니다. 현재는 차대차 사고만 분석합니다."))
        self.assertEqual(self.repo.get_accident(accident["id"])["status"], "unsupported")

    def test_unsupported_videos_expire_in_a_day_even_with_retention_consent(self):
        accident, _, analysis = self.make_analysis(content="FAKE unsupported 차대보행자\n".encode(), retention=True)
        self.worker(engine=FakeEngine(directory=FIXTURES)).run_once()
        from datetime import datetime, timedelta, timezone
        with self.engine.connect() as conn:
            from sqlalchemy import text
            rows = conn.execute(text("SELECT kind, expires_at FROM video WHERE accident_id = :a"), {"a": accident["id"]}).all()
        self.assertEqual({r.kind for r in rows}, {"original", "masked"})
        limit = datetime.now(timezone.utc) + timedelta(hours=24, minutes=1)
        self.assertTrue(all(r.expires_at is not None and r.expires_at <= limit for r in rows), rows)

    def test_too_long_video_fails_with_a_clear_code(self):
        _, _, analysis = self.make_analysis(content=b"FAKE too_long 42.5\n")
        self.worker(engine=FakeEngine(directory=FIXTURES)).run_once()
        row = self.analysis(analysis)
        self.assertEqual((row["status"], row["error_code"]), (st.FAILED, "VIDEO_TOO_LONG"))
        self.assertIn("42.5", row["error_message"])

    def test_long_video_is_stopped_before_calling_the_engine(self):
        _, _, analysis = self.make_analysis()
        engine = mock.Mock()
        self.worker(engine=engine, redaction=StubRedaction(stats={"duration": 99.0})).run_once()
        engine.analyze.assert_not_called()
        self.assertEqual((self.analysis(analysis)["status"], self.analysis(analysis)["error_code"]), (st.FAILED, "VIDEO_TOO_LONG"))

    def test_engine_failure_hides_details_from_the_user(self):
        _, _, analysis = self.make_analysis(content=b"FAKE fail\n")
        self.worker(engine=FakeEngine(directory=FIXTURES)).run_once()
        row = self.analysis(analysis)
        self.assertEqual((row["status"], row["error_code"]), (st.FAILED, "ANALYSIS_FAILED"))
        self.assertNotIn("FAKE", row["error_message"])
        with self.engine.connect() as conn:
            from sqlalchemy import text
            self.assertEqual(conn.execute(text("SELECT status FROM job WHERE analysis_id = :a"), {"a": analysis["id"]}).scalar(), "done")

    def test_missing_ai_key_is_reported_as_not_configured(self):
        _, _, analysis = self.make_analysis()
        engine = mock.Mock()
        engine.analyze.side_effect = RuntimeError("OPENAI_API_KEY가 없습니다. backend/.env에 설정하고 프로그램을 다시 실행하세요.")
        self.worker(engine=engine).run_once()
        row = self.analysis(analysis)
        self.assertEqual(row["error_code"], "AI_NOT_CONFIGURED")
        self.assertNotIn("OPENAI", row["error_message"])
        engine.analyze.side_effect = EngineNotConfigured("재생 파일 없음")
        _, _, other = self.make_analysis()
        self.worker(engine=engine).run_once()
        self.assertEqual(self.analysis(other)["error_code"], "AI_NOT_CONFIGURED")

    def test_redaction_failure_never_reaches_the_engine(self):
        accident, _, analysis = self.make_analysis()
        engine = mock.Mock()
        self.worker(engine=engine, redaction=StubRedaction(fail=RuntimeError("탐지 모델 오류"))).run_once()
        engine.analyze.assert_not_called()
        row = self.analysis(analysis)
        self.assertEqual((row["status"], row["error_code"]), (st.FAILED, "ANALYSIS_FAILED"))
        self.assertIsNone(self.repo.get_video(accident["id"], "masked"))   # 가리지 못한 영상은 남기지 않는다

    def test_progress_stages_are_reported(self):
        _, _, analysis = self.make_analysis()
        seen = []
        original = self.repo.update_analysis

        def spy(analysis_id, **fields):
            if fields.get("stage"):
                seen.append(fields["stage"])
            return original(analysis_id, **fields)

        with mock.patch.object(self.repo, "update_analysis", side_effect=spy):
            self.worker().run_once()
        self.assertEqual(seen[0], "plate_masking")
        self.assertIn("overview", seen)
        self.assertEqual(seen[-1], "case_matching")


class FinalizeTests(WorkerTestCase):
    def awaiting(self, content=b"video"):
        accident, _, analysis = self.make_analysis(content=content)
        w = self.worker(engine=FakeEngine(directory=FIXTURES))
        w.run_once()
        return accident, analysis, w

    def confirm(self, analysis, type_id, role, answers=None):
        self.repo.request_confirm(analysis["id"], {"accident_type_id": type_id, "role": role, "answers": answers or {}})

    def test_final_result_when_all_registered_factors_are_answered(self):
        from app import catalog
        accident, analysis, w = self.awaiting()
        answers = {q["key"]: "아니요" for q in catalog.adjustment_questions(11, "A")}
        answers["other.signal_delay"] = "예"
        self.confirm(analysis, 11, "A", answers)
        self.assertTrue(w.run_once())
        row = self.analysis(analysis)
        r = row["result"]
        self.assertEqual((row["status"], r["state"]), (st.COMPLETED, "final"))
        self.assertEqual(r["fault"]["base"], {"me": 30, "other": 70})
        self.assertEqual(r["fault"]["final"], {"me": 20, "other": 80})
        self.assertEqual([(s["me"], s["other"]) for s in r["steps"]], [(30, 70), (20, 80)])
        self.assertEqual(r["steps"][1]["effect"], "상대 차 과실 +10%p")
        self.assertEqual((float(row["fault_me"]), float(row["fault_other"]), row["accident_type_id"]), (20.0, 80.0, 11))
        self.assertEqual(self.repo.get_accident(accident["id"])["status"], "completed")
        self.assertEqual(r["timeline"], row["scene"]["timeline"])
        self.assertTrue(r["notice"].startswith("※"))
        self.assertEqual(r["accident_type"]["my_progress"], "후행 직진")

    def test_unanswered_factors_make_the_result_partial_without_a_final_ratio(self):
        accident, analysis, w = self.awaiting()
        self.confirm(analysis, 11, "A", {"other.signal_delay": "예"})
        w.run_once()
        row = self.analysis(analysis)
        r = row["result"]
        self.assertEqual(r["state"], "partial")
        self.assertIsNone(r["fault"]["final"])
        self.assertEqual(r["fault"]["adjusted"], {"me": 20, "other": 80})
        self.assertTrue(r["adjustments"]["pending"])
        self.assertIn("question", r["adjustments"]["pending"][0])
        self.assertEqual((row["fault_me"], row["fault_other"]), (None, None))   # 확정하지 못했으면 비워 둔다

    def test_type_without_rules_gives_base_only(self):
        accident, analysis, w = self.awaiting()
        self.confirm(analysis, 0, "A")
        w.run_once()
        r = self.analysis(analysis)["result"]
        self.assertEqual(r["state"], "base_only")
        self.assertEqual(r["fault"], {"base": {"me": 80, "other": 20}, "adjusted": None, "final": None, "bounds_applied": False})
        self.assertFalse(r["adjustments"]["registered"])
        self.assertEqual(len(r["steps"]), 1)

    def test_no_type_is_unresolved(self):
        accident, analysis, w = self.awaiting()
        self.confirm(analysis, None, None)
        w.run_once()
        row = self.analysis(analysis)
        r = row["result"]
        self.assertEqual((row["status"], r["state"], r["fault"], r["accident_type"]), (st.COMPLETED, "unresolved", None, None))
        self.assertTrue(r["reference_candidates"])
        self.assertEqual((row["fault_me"], row["accident_type_id"]), (None, None))

    def test_my_role_swaps_who_gets_the_adjustment(self):
        accident, analysis, w = self.awaiting()
        # 내 차가 표의 B(선행 진로변경)인 경우: 방향지시등 미점등은 내 차 과실을 늘린다
        self.confirm(analysis, 11, "B", {"me.signal_delay": "예"})
        w.run_once()
        r = self.analysis(analysis)["result"]
        self.assertEqual(r["fault"]["base"], {"me": 70, "other": 30})
        self.assertEqual(r["fault"]["adjusted"], {"me": 80, "other": 20})
        self.assertEqual(r["steps"][1]["who"], "내 차")

    def test_finalize_failure_is_reported(self):
        accident, analysis, w = self.awaiting()
        self.confirm(analysis, 11, "A")
        with mock.patch.object(finalize, "build_result", side_effect=RuntimeError("boom")):
            w.run_once()
        row = self.analysis(analysis)
        self.assertEqual((row["status"], row["error_code"]), (st.FAILED, "FINALIZE_FAILED"))
        self.assertNotIn("boom", row["error_message"])

    def test_cases_are_looked_up_for_the_confirmed_type_and_compared(self):
        accident, analysis, w = self.awaiting()
        cases = mock.Mock()
        cases.related_for.return_value = [{"court": "서울", "case_number": "1", "relevance_status": "registered_chart_reference",
                                           "summary": "진로변경 중 충돌", "comparison_limit": "한계"}]
        w.cases = cases
        self.confirm(analysis, 11, "A")
        w.run_once()
        cases.related_for.assert_called_once_with(11)
        related = self.analysis(analysis)["result"]["related_cases"]
        self.assertEqual(related[0]["court"], "서울")
        self.assertEqual(related[0]["comparison"]["match_level"], "same_type")
        self.assertEqual(related[0]["comparison"]["differences"][0], "한계")
        accident2, analysis2, _ = self.awaiting()
        cases.related_for.reset_mock()
        self.confirm(analysis2, None, None)
        w.run_once()
        cases.related_for.assert_not_called()   # 유형이 없으면 판례를 찾지 않는다
        self.assertEqual(self.analysis(analysis2)["result"]["related_cases"], [])


class CleanupTests(WorkerTestCase):
    def test_expired_videos_are_deleted_but_their_rows_remain(self):
        accident, original, _ = self.make_analysis()
        path = storage.path_for(original["storage_key"])
        self.assertTrue(path.is_file())
        self.assertEqual(cleanup.delete_expired(self.repo), 0)   # 아직 만료 전
        later = datetime.now(timezone.utc) + timedelta(hours=25)
        self.assertEqual(cleanup.delete_expired(self.repo, later), 1)
        self.assertFalse(path.exists())
        row = self.repo.get_video_by_id(original["id"])
        self.assertIsNotNone(row["deleted_at"])
        self.assertEqual(cleanup.delete_expired(self.repo, later), 0)   # 두 번 지우지 않는다

    def test_videos_without_expiry_are_kept(self):
        accident, _, _ = self.make_analysis(retention=True)
        self.worker().run_once()
        masked = self.repo.get_video(accident["id"], "masked")
        self.assertIsNone(masked["expires_at"])
        cleanup.delete_expired(self.repo, datetime.now(timezone.utc) + timedelta(days=365))
        self.assertTrue(storage.path_for(masked["storage_key"]).is_file())
        self.assertIsNone(self.repo.get_video(accident["id"], "original"))   # 원본은 지워졌다

    def test_maintenance_runs_cleanup_and_requeue(self):
        accident, original, _ = self.make_analysis()
        w = self.worker()
        w._last_maintenance = 0
        with mock.patch.object(cleanup, "delete_expired", return_value=0) as deleted:
            w.maintenance(interval=0)
        deleted.assert_called_once()


class EngineTests(unittest.TestCase):
    def test_replay_engine_snapshot(self):
        snap, logs = ReplayEngine(directory=FIXTURES).analyze(Path("x.mp4"), lambda stage: None)
        self.assertEqual(snap["engine"], "replay")
        self.assertEqual(snap["situation"]["default_index"], 0)

    def test_replay_can_load_another_fixture(self):
        snap, _ = ReplayEngine(fixture="parking", directory=FIXTURES).analyze(Path("x.mp4"), lambda stage: None)
        self.assertIsNone(snap["situation"]["default_index"])

    def test_missing_fixture_is_a_configuration_error(self):
        with self.assertRaises(EngineNotConfigured):
            ReplayEngine(fixture="none", directory=FIXTURES).analyze(Path("x.mp4"), lambda stage: None)

    def test_fake_engine_ignores_ordinary_videos(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
            f.write(b"\x00\x00\x00 ftypmp42 binary")
            f.flush()
            snap, _ = FakeEngine(directory=FIXTURES).analyze(Path(f.name), lambda stage: None)
        self.assertEqual(snap["situation"]["candidates"][0]["accident_type_id"], 11)

    def test_a_fixture_directive_applies_only_to_that_video(self):
        import tempfile
        engine = FakeEngine(directory=FIXTURES)
        with tempfile.NamedTemporaryFile(suffix=".mp4") as special, tempfile.NamedTemporaryFile(suffix=".mp4") as ordinary:
            special.write(b"FAKE fixture parking\n")
            special.flush()
            ordinary.write(b"ordinary")
            ordinary.flush()
            first, _ = engine.analyze(Path(special.name), lambda stage: None)
            second, _ = engine.analyze(Path(ordinary.name), lambda stage: None)
        self.assertIsNone(first["situation"]["default_index"])           # 주차장 결과
        self.assertEqual(second["situation"]["candidates"][0]["accident_type_id"], 11)   # 다음 영상은 기본 결과로 돌아간다

    def test_make_engine(self):
        self.assertEqual(make_engine("replay").name, "replay")
        self.assertEqual(make_engine("FAKE").name, "fake")
        self.assertEqual(make_engine("avly").name, "avly")
        with self.assertRaises(ValueError):
            make_engine("gemini")

    def test_make_redaction(self):
        self.assertEqual(make_redaction("dev_copy").name, "dev_copy")
        self.assertEqual(make_redaction("yolo").name, "yolo")
        with self.assertRaises(ValueError):
            make_redaction("off")

    def test_dev_copy_copies_and_reports_no_stats(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d, "a.mp4"), Path(d, "sub", "b.mp4")
            src.write_bytes(b"abc")
            self.assertEqual(DevCopyRedaction().redact(src, dst), {})
            self.assertEqual(dst.read_bytes(), b"abc")


class AvlyEngineTests(unittest.TestCase):
    """실제 AI 를 부르지 않고 avly 파이프라인을 가짜로 바꿔서 연결부(단계 알림, 결과 변환, 원래대로 되돌리기)를 확인한다."""

    def run_engine(self, fake_run):
        import tempfile
        from avly import observation, pipeline
        from avly.context import ctx
        reported = []
        original_calls = (pipeline.call, observation.call)
        with tempfile.TemporaryDirectory() as d:
            result = Path(d, "analysis.json")
            result.write_text((FIXTURES / "model_result_lane_change.json").read_text(encoding="utf-8"), encoding="utf-8")
            pipeline.call = lambda stage, *a, **k: "pipeline-call"
            observation.call = lambda stage, *a, **k: "observation-call"
            patched_calls = (pipeline.call, observation.call)

            def run(settings):
                ctx.output_path = result
                fake_run(settings, pipeline, observation)

            try:
                with mock.patch.object(pipeline, "run", run):
                    try:
                        outcome = AvlyEngine(results_dir=Path(d, "results")).analyze(Path(d, "x.mp4"), reported.append)
                    except Exception as exc:
                        outcome = exc
                restored = (pipeline.call, observation.call) == patched_calls
            finally:
                pipeline.call, observation.call = original_calls
        return outcome, reported, restored

    def test_reports_stages_converts_the_result_and_restores_hooks(self):
        def fake_run(settings, pipeline, observation):
            self.assertTrue(settings["no_survey"] and not settings["PICK_VIDEO"])
            self.assertTrue(settings["CSV_FILE"].endswith("fault_table_car_to_car.csv"))
            self.assertEqual(pipeline.call("1/3 전체 흐름 분석"), "pipeline-call")   # 원래 함수의 값을 그대로 돌려준다
            pipeline.call("2/3 사고 전후 상세 확인")
            self.assertEqual(observation.call("사고 전 차선·진로변경 별도 검토"), "observation-call")
            pipeline.call("3/3 CSV 연결·과실 시나리오")
        (snap, logs), reported, restored = self.run_engine(fake_run)
        self.assertEqual(reported, ["overview", "detail_review", "detail_review", "case_matching"])
        self.assertEqual(snap["engine"], "avly")
        self.assertEqual(snap["situation"]["candidates"][0]["accident_type_id"], 11)
        self.assertTrue(restored)

    def test_exceptions_pass_through_and_hooks_are_restored(self):
        from avly import scope

        def boom(settings, pipeline, observation):
            raise scope.UnsupportedAccident("차대이륜차")
        outcome, _, restored = self.run_engine(boom)
        self.assertIsInstance(outcome, scope.UnsupportedAccident)
        self.assertTrue(restored)


if __name__ == "__main__":
    unittest.main()
