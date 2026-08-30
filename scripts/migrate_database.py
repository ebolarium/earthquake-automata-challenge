#!/usr/bin/env python3
"""Apply checksum-locked PostgreSQL migrations in order."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.database_migrations import discover_migrations  # noqa: E402
from etas_challenge.database_migrations import migration_checksum  # noqa: E402


DEFAULT_MIGRATIONS = ROOT / "db" / "migrations"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--migrations", type=Path, default=DEFAULT_MIGRATIONS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required")

    try:
        import psycopg
    except ImportError as exc:
        raise SystemExit('install the prospective extra: pip install ".[prospective]"') from exc

    migrations = discover_migrations(args.migrations)
    with psycopg.connect(args.database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("etas-challenge-migrations",))
            cursor.execute("CREATE SCHEMA IF NOT EXISTS prospective")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS prospective.schema_migrations (
                    version text PRIMARY KEY,
                    filename text NOT NULL UNIQUE,
                    sha256 char(64) NOT NULL,
                    applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            cursor.execute("SELECT version, sha256 FROM prospective.schema_migrations")
            applied = dict(cursor.fetchall())

            for path in migrations:
                version = path.name.split("_", 1)[0]
                checksum = migration_checksum(path)
                if version in applied:
                    if applied[version] != checksum:
                        raise RuntimeError(f"migration checksum changed: {path.name}")
                    print(f"already applied {path.name}")
                    continue
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute(
                    """
                    INSERT INTO prospective.schema_migrations (version, filename, sha256)
                    VALUES (%s, %s, %s)
                    """,
                    (version, path.name, checksum),
                )
                print(f"applied {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
