#!/usr/bin/env python3
"""Export the pinned pyCSEP New Zealand testing mask without event data."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from csep.core.regions import nz_csep_region

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/regions/nz-csep-v1.npz"
MANIFEST = ROOT / "data/manifests/nz-csep-region-v1.json"
PROTOCOL = ROOT / "configs/regions/new-zealand-csep-v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    region = nz_csep_region(use_midpoint=True)
    origins = np.asarray(region.origins(), dtype=np.float64)
    expected = protocol["region"]["published_node_count"]
    if origins.shape != (expected, 2) or not np.all(np.isfinite(origins)):
        raise ValueError("pinned pyCSEP New Zealand region changed")
    order = np.lexsort((origins[:, 0], origins[:, 1]))
    origins = origins[order]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUTPUT,
        origins=origins,
        spacing_degrees=np.asarray(protocol["region"]["mask_spacing_degrees"]),
    )
    payload = {
        "schema_version": 1,
        "region_id": "nz-csep-v1",
        "pycsep_version": protocol["source"]["pycsep_version"],
        "source_resource": protocol["source"]["region_resource"],
        "protocol_sha256": sha256(PROTOCOL),
        "output": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256(OUTPUT),
        "nodes": int(len(origins)),
        "longitude_origin_bounds": [float(origins[:, 0].min()), float(origins[:, 0].max())],
        "latitude_origin_bounds": [float(origins[:, 1].min()), float(origins[:, 1].max())],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
