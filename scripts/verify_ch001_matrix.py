#!/usr/bin/env python3
"""Verify all generated CH-001 matrix shards against the committed manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.training_matrix import verify_matrix_artifacts  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/manifests/ch001-matrix-v1.json"),
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    verify_matrix_artifacts(manifest, ROOT)
    print(
        f"valid CH-001 matrix: {manifest['results']['issue_days']} days, "
        f"{len(manifest['outputs']['shards'])} shards"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
