import tempfile
from pathlib import Path
import unittest

from etas_challenge.database_migrations import discover_migrations
from etas_challenge.database_migrations import migration_checksum


class DatabaseMigrationTest(unittest.TestCase):
    def test_repository_migrations_are_ordered_and_unique(self):
        root = Path(__file__).resolve().parents[1]
        migrations = discover_migrations(root / "db" / "migrations")
        self.assertEqual(
            [path.name for path in migrations],
            [
                "001_prospective_core.sql",
                "002_optional_region_depth.sql",
                "003_catalog_snapshot_identity.sql",
            ],
        )
        self.assertEqual(len(migration_checksum(migrations[0])), 64)

    def test_duplicate_versions_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")
            (root / "001_second.sql").write_text("SELECT 2;", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate migration version"):
                discover_migrations(root)

    def test_invalid_names_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "migration.sql").write_text("SELECT 1;", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid migration names"):
                discover_migrations(root)


if __name__ == "__main__":
    unittest.main()
