"""Discovery and integrity helpers for prospective database migrations."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re


MIGRATION_NAME = re.compile(r"^[0-9]{3}_[a-z0-9_]+\.sql$")


def discover_migrations(directory: Path) -> list[Path]:
    migrations = sorted(directory.glob("*.sql"))
    invalid = [path.name for path in migrations if not MIGRATION_NAME.fullmatch(path.name)]
    if invalid:
        raise ValueError(f"invalid migration names: {', '.join(invalid)}")
    versions = [path.name.split("_", 1)[0] for path in migrations]
    if len(versions) != len(set(versions)):
        raise ValueError("duplicate migration version")
    return migrations


def migration_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
