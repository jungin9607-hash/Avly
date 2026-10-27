"""테스트 공통 도구. 실제 PostgreSQL 을 쓴다 (환경변수 TEST_DATABASE_URL)."""

import os
import unittest

SKIP_REASON = "TEST_DATABASE_URL 이 없어 DB 테스트를 건너뜁니다. 예: postgresql://postgres:x@localhost:5432/postgres"


class DbTestCase(unittest.TestCase):
    """테스트마다 새 스키마를 만든다 (public 스키마를 비우고 마이그레이션을 다시 적용)."""

    @classmethod
    def setUpClass(cls):
        if not os.environ.get("TEST_DATABASE_URL"):
            raise unittest.SkipTest(SKIP_REASON)
        from app import db
        cls.engine = db.get_engine()

    def setUp(self):
        from sqlalchemy import text
        from app import db
        with self.engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        db.migrate(self.engine)
