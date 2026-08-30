#!/usr/bin/env python3
"""Evaluate the zero-refit CH-008 transport in the three FERN regions."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.challenger import stationary_block_bootstrap_igpe  # noqa: E402
from etas_challenge.etas_native import event_rates  # noqa: E402
from etas_challenge.fern_ch008 import evaluate_frozen_ch008, regional_grid  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402

CONFIG = ROOT / "configs/challenge/fern-ch008-transfer-v1.json"
PROTOCOL = ROOT / "configs/regions/fern-japan-v1.json"
CATALOG_MANIFEST = ROOT / "data/manifests/fern-japan-catalog-v1.json"
ETAS_ROOT = ROOT / "artifacts/fern-japan-etas/workspace/Experiments/ETAS"
OUTPUT = ROOT / "data/manifests/fern-ch008-zero-refit-transfer-v1.json"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def jst_day(value: datetime) -> int:
    return math.floor((value.timestamp() + 9 * 3600) / 86400)


def read_catalog(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    times = [timestamp(row["time_utc"]) for row in rows]
    seconds = np.asarray([(value - EPOCH).total_seconds() for value in times], dtype=float)
    return {
        "times": np.asarray(times, dtype=object),
        "time_days": seconds / 86400.0,
        "days": np.asarray([jst_day(value) for value in times], dtype=np.int64),
        "latitudes": np.asarray([float(row["latitude"]) for row in rows]),
        "longitudes": np.asarray([float(row["longitude"]) for row in rows]),
        "magnitudes": np.asarray([float(row["magnitude"]) for row in rows]),
    }


def summarize(gains: np.ndarray, days: np.ndarray, config: dict, seed_offset: int) -> dict:
    unique_days, inverse = np.unique(days, return_inverse=True)
    daily_gain = np.zeros(len(unique_days), dtype=float)
    daily_count = np.zeros(len(unique_days), dtype=np.int64)
    np.add.at(daily_gain, inverse, gains)
    np.add.at(daily_count, inverse, 1)
    calendar_days = np.arange(unique_days[0], unique_days[-1] + 1, dtype=np.int64)
    expanded_gain = np.zeros(len(calendar_days), dtype=float)
    expanded_count = np.zeros(len(calendar_days), dtype=np.int64)
    positions = unique_days - calendar_days[0]
    expanded_gain[positions] = daily_gain
    expanded_count[positions] = daily_count
    result = {
        "events": int(len(gains)),
        "mean_igpe": float(np.mean(gains)),
        "relative_factor": float(np.exp(np.mean(gains))),
        "total_log_likelihood_gain": float(np.sum(gains)),
        "positive_event_fraction": float(np.mean(gains > 0)),
        "bootstrap": {},
    }
    evaluation = config["evaluation"]
    for block in evaluation["bootstrap_mean_block_days"]:
        result["bootstrap"][f"{block}_days"] = stationary_block_bootstrap_igpe(
            expanded_gain,
            expanded_count,
            mean_block_days=block,
            replicates=evaluation["bootstrap_replicates"],
            seed=evaluation["bootstrap_seed"] + seed_offset + block,
            confidence_level=evaluation["confidence_level"],
        )
    return result


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    catalog_manifest = json.loads(CATALOG_MANIFEST.read_text(encoding="utf-8"))
    parent_path = ROOT / config["parent_model"]
    model_path = ROOT / config["source_model"]
    native_etas_path = ROOT / config["native_etas_module"]
    adapter_path = ROOT / config["regional_adapter_module"]
    parent = json.loads(parent_path.read_text(encoding="utf-8"))["parameters"]
    challenger = json.loads(model_path.read_text(encoding="utf-8"))["parameters"]
    results = {}
    for region_index, region in enumerate(protocol["regions"]):
        name = region["name"]
        catalog_path = ROOT / catalog_manifest["outputs"][name]["target_path"]
        if sha256_file(catalog_path) != catalog_manifest["outputs"][name]["target_sha256"]:
            raise ValueError(f"region {name} catalog hash changed")
        parameter_path = ETAS_ROOT / f"output_data_FERN_{name}" / "parameters_0.json"
        metadata = json.loads(parameter_path.read_text(encoding="utf-8"))
        if not metadata.get("inversion_done"):
            raise ValueError(f"region {name} ETAS inversion is incomplete")
        catalog = read_catalog(catalog_path)
        etas_parameters = metadata["final_parameters"]
        rates = event_rates(
            catalog["time_days"],
            catalog["latitudes"],
            catalog["longitudes"],
            catalog["magnitudes"],
            magnitude_reference=metadata["m_ref"],
            parameters=etas_parameters,
        )
        grid = regional_grid(
            tuple(region["longitude"]),
            tuple(region["latitude"]),
            config["adaptation"]["spacing_degrees"],
        )
        evaluation = evaluate_frozen_ch008(
            event_days=catalog["days"],
            event_cells=grid.cells(catalog["latitudes"], catalog["longitudes"]),
            event_magnitudes=catalog["magnitudes"],
            etas_rates=rates,
            etas_mu=10.0 ** etas_parameters["log10_mu"],
            beta=metadata["beta"],
            magnitude_reference=metadata["m_ref"],
            grid=grid,
            issue_day_start=jst_day(timestamp(metadata["auxiliary_start"])),
            issue_day_end_exclusive=jst_day(timestamp(config["evaluation"]["locked_test"][1])) + 1,
            parent_parameters=parent,
            ch008_parameters=challenger,
        )
        periods = {}
        for period_name in ("development_validation", "locked_test"):
            start, end = (timestamp(value) for value in config["evaluation"][period_name])
            selected = np.asarray([(value >= start and value < end) for value in catalog["times"]])
            periods[period_name] = summarize(
                evaluation.event_gains[selected],
                catalog["days"][selected],
                config,
                1000 * region_index + (0 if period_name == "development_validation" else 500),
            )
        results[name] = {
            "etas_parameters_sha256": sha256_file(parameter_path),
            "etas_train_events": metadata["n_target_events"],
            "etas_beta": metadata["beta"],
            "etas_final_parameters": etas_parameters,
            "catalog_sha256": sha256_file(catalog_path),
            "grid_cells": int(np.prod(grid.shape)),
            "periods": periods,
        }
        print(name, periods)
    manifest = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "status": "completed",
        "config_sha256": sha256_file(CONFIG),
        "protocol_sha256": sha256_file(PROTOCOL),
        "catalog_manifest_sha256": sha256_file(CATALOG_MANIFEST),
        "source_model_sha256": sha256_file(model_path),
        "parent_model_sha256": sha256_file(parent_path),
        "native_etas_module_sha256": sha256_file(native_etas_path),
        "regional_adapter_module_sha256": sha256_file(adapter_path),
        "evaluation_script_sha256": sha256_file(Path(__file__)),
        "results": results,
        "claim_boundary": config["claim_boundary"],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
