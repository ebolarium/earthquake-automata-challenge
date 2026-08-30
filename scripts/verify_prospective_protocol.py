#!/usr/bin/env python3
"""Verify the three-region dry-run protocol and all locked files."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.prospective_protocol import sha256_file  # noqa: E402
from etas_challenge.prospective_protocol import validate_protocol  # noqa: E402


PROTOCOL = ROOT / "configs/prospective/three-region-dry-run-v1.json"


def main() -> int:
    protocol = validate_protocol(PROTOCOL, ROOT)
    print(
        json.dumps(
            {
                "status": "ok",
                "protocol_id": protocol["protocol_id"],
                "protocol_sha256": sha256_file(PROTOCOL),
                "regions": [region["region_id"] for region in protocol["regions"]],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
