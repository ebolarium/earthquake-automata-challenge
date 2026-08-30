#!/usr/bin/env python3
"""Evaluate frozen exposure-normalized CH-008 in Chile once."""

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
from etas_challenge.fern_ch008 import regional_grid  # noqa: E402
from etas_challenge.fern_ch008_normalized import evaluate_exposure_normalized_ch008  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402

CONFIG = ROOT / "configs/challenge/chile-ch008-normalized-external-v1.json"
PARAMETERS = ROOT / "artifacts/chile-etas/workspace/Experiments/ETAS/output_data_CHILE/parameters_0.json"
OUTPUT = ROOT / "data/manifests/chile-ch008-normalized-external-v1.json"
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def utc_day(value: datetime) -> int:
    return math.floor(value.timestamp() / 86400)


def read_catalog(path: Path) -> dict[str, np.ndarray]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    times = [timestamp(row["time_utc"]) for row in rows]
    seconds = np.asarray([(value - EPOCH).total_seconds() for value in times])
    return {
        "times": np.asarray(times, dtype=object),
        "time_days": seconds / 86400.0,
        "days": np.asarray([utc_day(value) for value in times], dtype=np.int64),
        "latitudes": np.asarray([float(row["latitude"]) for row in rows]),
        "longitudes": np.asarray([float(row["longitude"]) for row in rows]),
        "magnitudes": np.asarray([float(row["magnitude"]) for row in rows]),
    }


def summarize(gains: np.ndarray, days: np.ndarray, evaluation: dict) -> dict:
    first = utc_day(timestamp(evaluation["period"][0]))
    last = utc_day(timestamp(evaluation["period"][1]))
    daily_gain = np.zeros(last - first, dtype=float)
    daily_count = np.zeros(last - first, dtype=np.int64)
    np.add.at(daily_gain, days - first, gains)
    np.add.at(daily_count, days - first, 1)
    result = {
        "events": int(len(gains)),
        "mean_igpe": float(np.mean(gains)),
        "relative_factor": float(np.exp(np.mean(gains))),
        "total_log_likelihood_gain": float(np.sum(gains)),
        "positive_event_fraction": float(np.mean(gains > 0)),
        "bootstrap": {},
    }
    for block in evaluation["bootstrap_mean_block_days"]:
        result["bootstrap"][f"{block}_days"] = stationary_block_bootstrap_igpe(daily_gain, daily_count, replicates=evaluation["bootstrap_replicates"], mean_block_days=block, seed=evaluation["bootstrap_seed"] + block, confidence_level=evaluation["confidence_level"])
    return result


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    protocol_path = ROOT / config["region_protocol"]
    catalog_manifest_path = ROOT / config["catalog_manifest"]
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    catalog_manifest = json.loads(catalog_manifest_path.read_text(encoding="utf-8"))
    if sha256_file(protocol_path) != catalog_manifest["protocol_sha256"]:
        raise ValueError("Chile catalog does not match locked protocol")
    catalog_path = ROOT / catalog_manifest["output_path"]
    if sha256_file(catalog_path) != catalog_manifest["output_sha256"]:
        raise ValueError("Chile catalog changed")
    metadata = json.loads(PARAMETERS.read_text(encoding="utf-8"))
    if not metadata.get("inversion_done"):
        raise ValueError("Chile ETAS inversion is incomplete")
    evaluation_start, evaluation_end = (timestamp(value) for value in config["evaluation"]["period"])
    if timestamp(metadata["timewindow_end"]) != evaluation_start:
        raise ValueError("ETAS fit boundary disagrees with Chile evaluation")
    region = protocol["region"]
    grid = regional_grid(tuple(region["longitude"]), tuple(region["latitude"]), config["adaptation"]["spacing_degrees"])
    catalog = read_catalog(catalog_path)
    cells = grid.cells(catalog["latitudes"], catalog["longitudes"])
    etas_parameters = metadata["final_parameters"]
    rates = event_rates(catalog["time_days"], catalog["latitudes"], catalog["longitudes"], catalog["magnitudes"], magnitude_reference=metadata["m_ref"], parameters=etas_parameters)
    parent_path = ROOT / config["parent_model"]
    model_path = ROOT / config["source_model"]
    replay, renewal_scale = evaluate_exposure_normalized_ch008(
        event_days=catalog["days"], event_cells=cells, event_magnitudes=catalog["magnitudes"], etas_rates=rates,
        etas_mu=10.0 ** etas_parameters["log10_mu"], beta=metadata["beta"], magnitude_reference=metadata["m_ref"], grid=grid,
        issue_day_start=utc_day(timestamp(metadata["auxiliary_start"])), issue_day_end_exclusive=utc_day(evaluation_end),
        prevalidation_days=(evaluation_start - timestamp(metadata["auxiliary_start"])).total_seconds() / 86400.0,
        parent_parameters=json.loads(parent_path.read_text(encoding="utf-8"))["parameters"],
        ch008_parameters=json.loads(model_path.read_text(encoding="utf-8"))["parameters"],
        target_mean_cell_exposure=config["adaptation"]["target_mean_cell_prefit_exposure"],
    )
    selected = np.asarray([evaluation_start <= value < evaluation_end for value in catalog["times"]])
    summary = summarize(replay.event_gains[selected], catalog["days"][selected], config["evaluation"])
    annual = {}
    for year in range(evaluation_start.year, evaluation_end.year):
        start, end = datetime(year, 1, 1, tzinfo=timezone.utc), datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        chosen = selected & np.asarray([start <= value < end for value in catalog["times"]])
        values = replay.event_gains[chosen]
        annual[str(year)] = {"events": int(len(values)), "mean_igpe": float(np.mean(values)) if len(values) else None}
    summary["annual"] = annual
    gates = {
        "mean_igpe_positive": summary["mean_igpe"] > 0,
        "30_day_lower_bound_positive": summary["bootstrap"]["30_days"]["lower"] > 0,
        "90_day_lower_bound_nonnegative": summary["bootstrap"]["90_days"]["lower"] >= 0,
    }
    admitted = all(gates[key] for key, required in config["admission_rule"].items() if required)
    payload = {
        "schema_version": 1, "experiment_id": config["experiment_id"], "status": "completed_admitted" if admitted else "completed_not_admitted",
        "config_sha256": sha256_file(CONFIG), "protocol_sha256": sha256_file(protocol_path), "catalog_manifest_sha256": sha256_file(catalog_manifest_path),
        "etas_parameters_sha256": sha256_file(PARAMETERS), "source_model_sha256": sha256_file(model_path), "parent_model_sha256": sha256_file(parent_path),
        "evaluation_script_sha256": sha256_file(Path(__file__)), "renewal_exposure_scale": renewal_scale,
        "grid": {"cells": int(len(grid.areas_km2)), "area_km2": float(np.sum(grid.areas_km2))},
        "external_evaluation": summary, "admission_gates": gates, "admitted": admitted, "claim_boundary": config["claim_boundary"],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"external_evaluation": summary, "admission_gates": gates, "admitted": admitted}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
