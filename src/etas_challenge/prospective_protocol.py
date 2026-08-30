"""Validation for operational prospective protocol files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPECTED_REGIONS = {"california-relm", "new-zealand-csep", "chile-subduction"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_protocol(path: Path, root: Path) -> dict:
    protocol = json.loads(path.read_text(encoding="utf-8"))
    if protocol.get("mode") != "dry_run" or protocol.get("duration_days") != 14:
        raise ValueError("expected a 14-day dry-run protocol")
    if protocol.get("counts_toward_prospective_claim") is not False:
        raise ValueError("dry-run must not count toward the prospective claim")
    if protocol["issue_contract"].get("backfill_permitted") is not False:
        raise ValueError("forecast backfill must be prohibited")

    regions = protocol.get("regions", [])
    region_ids = [region.get("region_id") for region in regions]
    if len(region_ids) != len(set(region_ids)) or set(region_ids) != EXPECTED_REGIONS:
        raise ValueError("protocol must contain exactly the three admitted regions")

    locked_files = [
        (protocol["challenger"]["model_path"], protocol["challenger"]["model_sha256"]),
        (
            protocol["challenger"]["california_runtime_path"],
            protocol["challenger"]["california_runtime_sha256"],
        ),
        (
            protocol["challenger"]["normalized_runtime_path"],
            protocol["challenger"]["normalized_runtime_sha256"],
        ),
        (
            protocol["baseline_runtime"]["path"],
            protocol["baseline_runtime"]["sha256"],
        ),
    ]
    for region in regions:
        locked_files.append((region["etas_model_path"], region["etas_model_sha256"]))
        geometry = region["geometry"]
        if "path" in geometry:
            locked_files.append((geometry["path"], geometry["sha256"]))
        if "protocol_path" in geometry:
            locked_files.append((geometry["protocol_path"], geometry["protocol_sha256"]))

    for relative, expected in locked_files:
        actual = sha256_file(root / relative)
        if actual != expected:
            raise ValueError(f"locked file changed: {relative}")
    return protocol
