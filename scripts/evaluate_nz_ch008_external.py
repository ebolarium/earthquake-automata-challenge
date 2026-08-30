#!/usr/bin/env python3
"""Evaluate frozen exposure-normalized CH-008 in the NZ CSEP region once."""

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
from etas_challenge.fern_ch008_normalized import evaluate_exposure_normalized_ch008  # noqa: E402
from etas_challenge.masked_grid import masked_grid  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402

CONFIG = ROOT / "configs/challenge/nz-ch008-normalized-external-v1.json"
PARAMETERS = ROOT / "artifacts/nz-csep-etas/workspace/Experiments/ETAS/output_data_NZ_CSEP/parameters_0.json"
OUTPUT = ROOT / "data/manifests/nz-ch008-normalized-external-v1.json"
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
    if not len(gains):
        raise ValueError("New Zealand evaluation period has no events")
    first_day = utc_day(timestamp(evaluation["period"][0]))
    last_day = utc_day(timestamp(evaluation["period"][1]))
    daily_gain = np.zeros(last_day - first_day, dtype=float)
    daily_count = np.zeros(last_day - first_day, dtype=np.int64)
    np.add.at(daily_gain, days - first_day, gains)
    np.add.at(daily_count, days - first_day, 1)
    result = {
        "events": int(len(gains)),
        "mean_igpe": float(np.mean(gains)),
        "relative_factor": float(np.exp(np.mean(gains))),
        "total_log_likelihood_gain": float(np.sum(gains)),
        "positive_event_fraction": float(np.mean(gains > 0)),
        "bootstrap": {},
    }
    for block in evaluation["bootstrap_mean_block_days"]:
        result["bootstrap"][f"{block}_days"] = stationary_block_bootstrap_igpe(
            daily_gain,
            daily_count,
            replicates=evaluation["bootstrap_replicates"],
            mean_block_days=block,
            seed=evaluation["bootstrap_seed"] + block,
            confidence_level=evaluation["confidence_level"],
        )
    return result


def epoch_scores(catalog: dict[str, np.ndarray], gains: np.ndarray, start: datetime, end: datetime) -> dict:
    result = {}
    cursor = start
    while cursor < end:
        stop = min(cursor.replace(year=min(cursor.year + 3, end.year)), end)
        selected = np.asarray([cursor <= value < stop for value in catalog["times"]])
        values = gains[selected]
        result[f"{cursor.year}-{stop.year - 1}"] = {
            "events": int(len(values)),
            "mean_igpe": float(np.mean(values)) if len(values) else None,
        }
        cursor = stop
    return result


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    protocol_path = ROOT / config["region_protocol"]
    region_manifest_path = ROOT / config["region_manifest"]
    catalog_manifest_path = ROOT / config["catalog_manifest"]
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    region_manifest = json.loads(region_manifest_path.read_text(encoding="utf-8"))
    catalog_manifest = json.loads(catalog_manifest_path.read_text(encoding="utf-8"))
    region_path = ROOT / region_manifest["output"]
    catalog_path = ROOT / catalog_manifest["output_path"]
    for path, expected in ((region_path, region_manifest["output_sha256"]), (catalog_path, catalog_manifest["output_sha256"])):
        if sha256_file(path) != expected:
            raise ValueError(f"locked input changed: {path}")
    metadata = json.loads(PARAMETERS.read_text(encoding="utf-8"))
    if not metadata.get("inversion_done"):
        raise ValueError("New Zealand ETAS inversion is incomplete")
    evaluation_start, evaluation_end = (timestamp(value) for value in config["evaluation"]["period"])
    if timestamp(metadata["timewindow_end"]) != evaluation_start:
        raise ValueError("ETAS fit does not end at the external evaluation boundary")
    archive = np.load(region_path, allow_pickle=False)
    region = protocol["region"]
    grid = masked_grid(archive["origins"], region["mask_spacing_degrees"], region["latent_spacing_degrees"])
    catalog = read_catalog(catalog_path)
    cells = grid.cells(catalog["latitudes"], catalog["longitudes"])
    if np.any(cells < 0):
        raise ValueError("catalog contains events outside the exact CSEP mask")
    etas_parameters = metadata["final_parameters"]
    rates = event_rates(catalog["time_days"], catalog["latitudes"], catalog["longitudes"], catalog["magnitudes"], magnitude_reference=metadata["m_ref"], parameters=etas_parameters)
    parent_path = ROOT / config["parent_model"]
    model_path = ROOT / config["source_model"]
    replay, renewal_scale = evaluate_exposure_normalized_ch008(
        event_days=catalog["days"],
        event_cells=cells,
        event_magnitudes=catalog["magnitudes"],
        etas_rates=rates,
        etas_mu=10.0 ** etas_parameters["log10_mu"],
        beta=metadata["beta"],
        magnitude_reference=metadata["m_ref"],
        grid=grid,
        issue_day_start=utc_day(timestamp(metadata["auxiliary_start"])),
        issue_day_end_exclusive=utc_day(evaluation_end),
        prevalidation_days=(evaluation_start - timestamp(metadata["auxiliary_start"])).total_seconds() / 86400.0,
        parent_parameters=json.loads(parent_path.read_text(encoding="utf-8"))["parameters"],
        ch008_parameters=json.loads(model_path.read_text(encoding="utf-8"))["parameters"],
        target_mean_cell_exposure=config["adaptation"]["target_mean_cell_prefit_exposure"],
    )
    selected = np.asarray([evaluation_start <= value < evaluation_end for value in catalog["times"]])
    gains = replay.event_gains[selected]
    summary = summarize(gains, catalog["days"][selected], config["evaluation"])
    summary["three_year_epochs"] = epoch_scores({key: value[selected] for key, value in catalog.items()}, gains, evaluation_start, evaluation_end)
    gates = {
        "mean_igpe_positive": summary["mean_igpe"] > 0,
        "30_day_lower_bound_positive": summary["bootstrap"]["30_days"]["lower"] > 0,
        "90_day_lower_bound_nonnegative": summary["bootstrap"]["90_days"]["lower"] >= 0,
    }
    admitted = all(gates[key] for key, required in config["admission_rule"].items() if required)
    payload = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "status": "completed_admitted" if admitted else "completed_not_admitted",
        "config_sha256": sha256_file(CONFIG),
        "protocol_sha256": sha256_file(protocol_path),
        "region_manifest_sha256": sha256_file(region_manifest_path),
        "catalog_manifest_sha256": sha256_file(catalog_manifest_path),
        "etas_parameters_sha256": sha256_file(PARAMETERS),
        "source_model_sha256": sha256_file(model_path),
        "parent_model_sha256": sha256_file(parent_path),
        "evaluation_script_sha256": sha256_file(Path(__file__)),
        "renewal_exposure_scale": renewal_scale,
        "grid": {"fine_cells": int(len(archive["origins"])), "latent_cells": int(len(grid.areas_km2)), "area_km2": float(np.sum(grid.areas_km2))},
        "external_evaluation": summary,
        "admission_gates": gates,
        "admitted": admitted,
        "claim_boundary": config["claim_boundary"],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"external_evaluation": summary, "admission_gates": gates, "admitted": admitted}, indent=2))
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
