#!/usr/bin/env python3
"""Prepare train-only academic ETAS inversion for the Chile corridor."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.fern_ch008 import regional_grid  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402

PROTOCOL = ROOT / "configs/regions/chile-subduction-v1.json"
CATALOG_MANIFEST = ROOT / "data/manifests/chile-subduction-catalog-v1.json"
WORKSPACE = ROOT / "artifacts/chile-etas/workspace/Experiments/ETAS"


def write_catalog(source: Path, destination: Path) -> int:
    rows = list(csv.DictReader(source.open(encoding="utf-8", newline="")))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("id", "latitude", "longitude", "time", "magnitude"))
        for index, row in enumerate(rows):
            writer.writerow((row["event_id"] or index, row["latitude"], row["longitude"], row["time_utc"].replace("T", " ").replace("+00:00", ""), row["magnitude"]))
    return len(rows)


def main() -> int:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    manifest = json.loads(CATALOG_MANIFEST.read_text(encoding="utf-8"))
    if sha256_file(PROTOCOL) != manifest["protocol_sha256"]:
        raise ValueError("Chile protocol changed after catalog lock")
    catalog_path = ROOT / manifest["output_path"]
    if sha256_file(catalog_path) != manifest["output_sha256"]:
        raise ValueError("Chile catalog changed")
    region = protocol["region"]
    grid = regional_grid(tuple(region["longitude"]), tuple(region["latitude"]), region["spacing_degrees"])
    area = float(np.sum(grid.areas_km2))
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "scripts/invert_etas_exact_area.py", WORKSPACE / "invert_etas_exact_area.py")
    dataset = WORKSPACE / "Datasets/CHILE"
    event_count = write_catalog(catalog_path, dataset / "catalog.csv")
    lon_min, lon_max = region["longitude"]
    lat_min, lat_max = region["latitude"]
    epsilon = 1e-6
    shape = np.asarray([[lat_min - epsilon, lon_min - epsilon], [lat_min - epsilon, lon_max + epsilon], [lat_max + epsilon, lon_max + epsilon], [lat_max + epsilon, lon_min - epsilon], [lat_min - epsilon, lon_min - epsilon]])
    np.save(dataset / "shape.npy", shape, allow_pickle=False)
    fit_start, fit_end = protocol["periods"]["fit"]
    config = {
        "fn_catalog": "Datasets/CHILE/catalog.csv",
        "data_path": "output_data_CHILE/",
        "auxiliary_start": fit_start.replace("T", " ").replace("+00:00", ""),
        "timewindow_start": fit_start.replace("T", " ").replace("+00:00", ""),
        "timewindow_end": fit_end.replace("T", " ").replace("+00:00", ""),
        "testwindow_end": protocol["periods"]["external_evaluation"][1].replace("T", " ").replace("+00:00", ""),
        "theta_0": {"log10_mu": -5.8, "log10_k0": -2.6, "a": 1.8, "log10_c": -2.5, "omega": -0.02, "log10_tau": 3.5, "log10_d": -0.85, "gamma": 1.3, "rho": 0.66},
        "mc": region["minimum_magnitude"],
        "delta_m": 0.1,
        "coppersmith_multiplier": 100,
        "shape_coords": "Datasets/CHILE/shape.npy",
        "exact_area_km2": area,
        "id": "0"
    }
    config_path = WORKSPACE / "config/CHILE.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"events": event_count, "area_km2": area, "grid_cells": len(grid.areas_km2), "config": str(config_path.relative_to(ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
