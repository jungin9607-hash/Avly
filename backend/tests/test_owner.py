import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from uuid import uuid4

from app import config, db, migrate
from app.repository import Repository
from tests.helpers import DbTestCase


class OwnerIsolationTests(DbTestCase):
    """같은 DB 를 여러 PC 가 쓸 때 서로의 작업과 영상을 건드리지 않는다."""

    def setUp(self):
        super().setUp()
        self.mine = Repository(self.engine, owner="mine")
        self.theirs = Repository(self.engine, owner="theirs")

    def make(self, repo):
        accident = repo.create_accident("t", "v", False, 24)
        video = repo.add_video(accident["id"], "original", f"{accident['id']}/o.mp4", size_bytes=1,
                               expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
        analysis = repo.create_analysis(accident["id"], video["id"])
        return accident, video, analysis

    def test_a_worker_only_claims_jobs_registered_by_the_same_owner(self):
        _, _, analysis = self.make(self.theirs)
        self.assertIsNone(self.mine.claim_job())
        job = self.theirs.claim_job()
        self.assertEqual(job["analysis_id"], analysis["id"])
        self.assertEqual(job["payload"], {"owner": "theirs"})

    def test_finalize_job_keeps_the_owner(self):
        _, _, analysis = self.make(self.mine)
        self.mine.claim_job()
        self.mine.update_analysis(analysis["id"], status="awaiting_confirmation")
        self.mine.request_confirm(analysis["id"], {"role": "A", "accident_type_id": 11, "answers": {}})
        self.assertIsNone(self.theirs.claim_job())
        self.assertEqual(self.mine.claim_job()["kind"], "finalize")

    def test_jobs_without_an_owner_can_be_claimed_by_anyone(self):
        _, _, analysis = self.make(self.mine)
        with self.engine.begin() as conn:
            from sqlalchemy import text
            conn.execute(text("UPDATE job SET payload = NULL"))   # 소유자 표시가 생기기 전의 작업
        self.assertEqual(self.theirs.claim_job()["analysis_id"], analysis["id"])

    def test_stale_jobs_are_requeued_only_by_their_owner(self):
        self.make(self.theirs)
        self.theirs.claim_job()
        with self.engine.begin() as conn:
            from sqlalchemy import text
            conn.execute(text("UPDATE job SET locked_at = now() - interval '2 hours'"))
        self.assertEqual(self.mine.requeue_stale_jobs(60, 5), (0, 0))
        self.assertEqual(self.theirs.requeue_stale_jobs(60, 5), (1, 0))

    def test_expired_videos_of_other_owners_are_left_alone(self):
        _, mine_video, _ = self.make(self.mine)
        _, their_video, _ = self.make(self.theirs)
        ids = {v["id"] for v in self.mine.videos_to_delete()}
        self.assertEqual(ids, {mine_video["id"]})
        self.assertEqual({v["id"] for v in self.theirs.videos_to_delete()}, {their_video["id"]})


class InstanceIdTests(unittest.TestCase):
    def test_id_is_created_once_and_reused(self):
        from app import instance
        with TemporaryDirectory() as d:
            fake = mock.Mock(upload_dir=Path(d))
            with mock.patch.object(instance, "settings", fake), mock.patch.object(instance, "_cached", None):
                first = instance.instance_id()
                instance._cached = None
                self.assertEqual(instance.instance_id(), first)
                self.assertEqual((Path(d) / ".instance_id").read_text(), first)


class AutoMigrateDefaultTests(unittest.TestCase):
    def test_only_the_compose_local_db_migrates_by_default(self):
        self.assertTrue(config._default_auto_migrate("postgresql://postgres:avly@db:5432/avly"))
        self.assertFalse(config._default_auto_migrate("postgresql://u:p@aws-0.pooler.supabase.com:5432/postgres"))
        self.assertFalse(config._default_auto_migrate(None))


class MigrateCommandTests(DbTestCase):
    def test_shows_pending_without_changing_the_database_and_applies_only_when_asked(self):
        with self.engine.begin() as conn:
            from sqlalchemy import text
            conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
        with mock.patch.object(db, "get_engine", return_value=self.engine):
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(migrate.main([]), 0)
            self.assertIn("0001_initial.sql", out.getvalue())
            self.assertIn("--apply", out.getvalue())
            self.assertEqual(db.pending_migrations(self.engine)[0], "0001_initial.sql")   # 확인만 했으므로 그대로
            with redirect_stdout(io.StringIO()):
                migrate.main(["--apply"])
            self.assertEqual(db.pending_migrations(self.engine), [])
            out = io.StringIO()
            with redirect_stdout(out):
                migrate.main([])
            self.assertIn("최신 상태", out.getvalue())

    def test_the_password_is_never_printed(self):
        self.assertNotIn("secret", migrate.describe("postgresql://user:secret@host.example:5432/postgres"))


if __name__ == "__main__":
    unittest.main()
