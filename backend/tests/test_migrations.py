import unittest

from sqlalchemy import text

from app import db
from tests.helpers import DbTestCase


class MigrationTests(DbTestCase):
    def test_applies_all_files_once_and_in_order(self):
        names = [p.name for p in db.migration_files()]
        self.assertEqual(names, sorted(names))
        with self.engine.connect() as conn:
            done = [r[0] for r in conn.execute(text("SELECT name FROM schema_migration ORDER BY name"))]
        self.assertEqual(done, names)

    def test_running_again_applies_nothing(self):
        self.assertEqual(db.migrate(self.engine), [])

    def test_expected_tables_exist(self):
        with self.engine.connect() as conn:
            tables = {r[0] for r in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))}
        for name in ("accident", "video", "analysis", "survey", "analysis_stage_log", "legal_case", "case_accident_type",
                     "case_lookup", "report", "job", "schema_migration"):
            self.assertIn(name, tables)


class ForeignSchemaTests(DbTestCase):
    def setUp(self):
        from sqlalchemy import text
        with self.engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))

    def test_refuses_to_touch_a_database_that_already_has_foreign_tables(self):
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE accident (id UUID PRIMARY KEY, title TEXT)"))
            conn.execute(text("INSERT INTO accident VALUES (gen_random_uuid(), '남의 데이터')"))
        with self.assertRaises(db.ForeignSchemaError) as ctx:
            db.migrate(self.engine)
        self.assertIn("accident", str(ctx.exception))
        with self.engine.connect() as conn:   # 아무것도 바뀌지 않았다
            self.assertEqual(conn.execute(text("SELECT count(*) FROM accident")).scalar(), 1)
            self.assertFalse(conn.execute(text("SELECT to_regclass('public.schema_migration') IS NOT NULL")).scalar())
            self.assertFalse(conn.execute(text("SELECT to_regclass('public.job') IS NOT NULL")).scalar())

    def test_a_failed_migration_leaves_nothing_behind(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            Path(d, "0001_a.sql").write_text("CREATE TABLE t1 (id INT);")
            Path(d, "0002_b.sql").write_text("CREATE TABLE t2 (id INT); SELECT no_such_function();")
            with self.assertRaises(Exception):
                db.migrate(self.engine, Path(d))
        with self.engine.connect() as conn:
            self.assertFalse(conn.execute(text("SELECT to_regclass('public.t1') IS NOT NULL")).scalar())

    def test_empty_database_migrates_normally(self):
        self.assertEqual(db.migrate(self.engine), [p.name for p in db.migration_files()])


if __name__ == "__main__":
    unittest.main()
