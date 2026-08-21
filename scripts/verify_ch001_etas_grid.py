#!/usr/bin/env python3
"""Verify generated CH-001 frozen-ETAS grid shards and their hashes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.grid_forecast import verify_grid_forecast_artifacts  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifests/ch001-etas-grid-v1.json"),
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    verify_grid_forecast_artifacts(manifest, ROOT)
    print(
        f"verified {manifest['results']['issue_days']} issue days across "
        f"{len(manifest['outputs']['shards'])} shards"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
