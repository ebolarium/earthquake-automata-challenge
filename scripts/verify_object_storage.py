#!/usr/bin/env python3
"""Verify prospective object storage with a temporary write/read/delete probe."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.object_storage import ObjectStorageConfig  # noqa: E402
from etas_challenge.object_storage import write_read_delete_probe  # noqa: E402


def main() -> int:
    result = write_read_delete_probe(ObjectStorageConfig.from_environment())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
