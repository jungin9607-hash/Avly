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


if __name__ == "__main__":
    unittest.main()
