#!/usr/bin/env python3
"""Prepare ignored, region-specific ETAS inversion workspaces for FERN-001."""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.training_matrix import sha256_file  # noqa: E402

PROTOCOL = ROOT / "configs/regions/fern-japan-v1.json"
CATALOG_MANIFEST = ROOT / "data/manifests/fern-japan-catalog-v1.json"
UPSTREAM_ETAS = ROOT / "reference/upstream/EarthquakeNPP/Experiments/ETAS"
WORKSPACE = ROOT / "artifacts/fern-japan-etas/workspace/Experiments/ETAS"


def write_catalog(source: Path, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    count = 0
    with source.open(encoding="utf-8", newline="") as input_handle, temporary.open(
        "w", encoding="utf-8", newline=""
    ) as output_handle:
        reader = csv.DictReader(input_handle)
        writer = csv.writer(output_handle, lineterminator="\n")
        writer.writerow(("id", "latitude", "longitude", "time", "magnitude"))
        for count, row in enumerate(reader, start=1):
            writer.writerow(
                (
                    count - 1,
                    row["latitude"],
                    row["longitude"],
                    row["time_utc"].replace("T", " ").replace("+00:00", ""),
                    row["magnitude"],
                )
            )
    temporary.replace(destination)
    return count


def main() -> int:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    manifest = json.loads(CATALOG_MANIFEST.read_text(encoding="utf-8"))
    if sha256_file(PROTOCOL) != manifest["config_sha256"]:
        raise ValueError("FERN catalog manifest does not match the protocol")
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(UPSTREAM_ETAS / "invert_etas.py", WORKSPACE / "invert_etas.py")
    shutil.copy2(UPSTREAM_ETAS / "predict_etas.py", WORKSPACE / "predict_etas.py")
    prepared = {}
    for region in protocol["regions"]:
        name = region["name"]
        source = ROOT / manifest["outputs"][name]["target_path"]
        if sha256_file(source) != manifest["outputs"][name]["target_sha256"]:
            raise ValueError(f"Region {name} target catalog hash changed")
        dataset_dir = WORKSPACE / "Datasets" / f"FERN_{name}"
        catalog_path = dataset_dir / "catalog.csv"
        event_count = write_catalog(source, catalog_path)
        lon_min, lon_max = region["longitude"]
        lat_min, lat_max = region["latitude"]
        shape = np.asarray(
            [
                [lat_min, lon_min],
                [lat_min, lon_max],
                [lat_max, lon_max],
                [lat_max, lon_min],
                [lat_min, lon_min],
            ],
            dtype=float,
        )
        shape_path = dataset_dir / "shape.npy"
        np.save(shape_path, shape, allow_pickle=False)
        config = {
            "fn_catalog": f"Datasets/FERN_{name}/catalog.csv",
            "data_path": f"output_data_FERN_{name}/",
            "auxiliary_start": "1967-01-01 00:00:00",
            "timewindow_start": "1978-12-31 15:00:00",
            "timewindow_end": "1995-12-31 15:00:00",
            "testwindow_end": "2011-03-11 05:46:18",
            "theta_0": {
                "log10_mu": -5.8,
                "log10_k0": -2.6,
                "a": 1.8,
                "log10_c": -2.5,
                "omega": -0.02,
                "log10_tau": 3.5,
                "log10_d": -0.85,
                "gamma": 1.3,
                "rho": 0.66,
            },
            "mc": region["target_magnitude"],
            "delta_m": 0.1,
            "coppersmith_multiplier": 100,
            "shape_coords": f"Datasets/FERN_{name}/shape.npy",
            "id": "0",
        }
        config_path = WORKSPACE / "config" / f"FERN_{name}.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        prepared[name] = {
            "events": event_count,
            "catalog_sha256": sha256_file(catalog_path),
            "shape_sha256": sha256_file(shape_path),
            "config_sha256": sha256_file(config_path),
        }
    print(json.dumps(prepared, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
