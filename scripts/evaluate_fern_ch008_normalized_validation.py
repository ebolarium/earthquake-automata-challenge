#!/usr/bin/env python3
"""Run the single-candidate exposure-normalized CH-008 validation experiment."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fern_ch008 import CATALOG_MANIFEST, ETAS_ROOT  # noqa: E402
from evaluate_fern_ch008 import jst_day, read_catalog, timestamp  # noqa: E402
from etas_challenge.challenger import stationary_block_bootstrap_igpe  # noqa: E402
from etas_challenge.etas_native import event_rates  # noqa: E402
from etas_challenge.fern_ch008 import regional_grid  # noqa: E402
from etas_challenge.fern_ch008_normalized import (  # noqa: E402
    evaluate_exposure_normalized_ch008,
)
from etas_challenge.training_matrix import sha256_file  # noqa: E402

CONFIG = ROOT / "configs/challenge/fern-ch008-normalized-validation-v1.json"
OUTPUT = ROOT / "data/manifests/fern-ch008-exposure-normalized-validation-v1.json"


def truncate_catalog(catalog: dict[str, np.ndarray], end) -> dict[str, np.ndarray]:
    selected = np.asarray([value < end for value in catalog["times"]])
    result = {key: value[selected] for key, value in catalog.items()}
    if not len(result["times"]) or any(value >= end for value in result["times"]):
        raise ValueError("validation catalog truncation failed")
    return result


def summarize(gains: np.ndarray, days: np.ndarray, evaluation: dict, seed: int) -> dict:
    unique_days, inverse = np.unique(days, return_inverse=True)
    calendar_days = np.arange(unique_days[0], unique_days[-1] + 1, dtype=np.int64)
    daily_gain = np.zeros(len(calendar_days), dtype=float)
    daily_count = np.zeros(len(calendar_days), dtype=np.int64)
    positions = unique_days[inverse] - calendar_days[0]
    np.add.at(daily_gain, positions, gains)
    np.add.at(daily_count, positions, 1)
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
            seed=seed + block,
            confidence_level=evaluation["confidence_level"],
        )
    return result


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    protocol_path = ROOT / config["regions"]
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    catalog_manifest = json.loads(CATALOG_MANIFEST.read_text(encoding="utf-8"))
    parent_path = ROOT / config["parent_model"]
    model_path = ROOT / config["source_model"]
    adapter_path = ROOT / config["normalized_adapter_module"]
    parent = json.loads(parent_path.read_text(encoding="utf-8"))["parameters"]
    challenger = json.loads(model_path.read_text(encoding="utf-8"))["parameters"]
    validation_start = timestamp(config["evaluation"]["period"][0])
    validation_end = timestamp(config["evaluation"]["period"][1])
    forbidden_start = timestamp(config["evaluation"]["forbidden_period_start"])
    if validation_end != forbidden_start:
        raise ValueError("validation must end exactly at the forbidden boundary")

    results = {}
    for region_index, region in enumerate(protocol["regions"]):
        name = region["name"]
        catalog_path = ROOT / catalog_manifest["outputs"][name]["target_path"]
        if sha256_file(catalog_path) != catalog_manifest["outputs"][name]["target_sha256"]:
            raise ValueError(f"region {name} catalog hash changed")
        catalog = truncate_catalog(read_catalog(catalog_path), forbidden_start)
        parameter_path = ETAS_ROOT / f"output_data_FERN_{name}" / "parameters_0.json"
        metadata = json.loads(parameter_path.read_text(encoding="utf-8"))
        if timestamp(metadata["timewindow_end"]) != validation_start:
            raise ValueError(f"region {name} ETAS was not fit at the validation boundary")
        rates = event_rates(
            catalog["time_days"], catalog["latitudes"], catalog["longitudes"],
            catalog["magnitudes"], magnitude_reference=metadata["m_ref"],
            parameters=metadata["final_parameters"],
        )
        grid = regional_grid(
            tuple(region["longitude"]), tuple(region["latitude"]),
            0.5,
        )
        prevalidation_days = (
            validation_start - timestamp(metadata["auxiliary_start"])
        ).total_seconds() / 86400.0
        replay, renewal_scale = evaluate_exposure_normalized_ch008(
            event_days=catalog["days"],
            event_cells=grid.cells(catalog["latitudes"], catalog["longitudes"]),
            event_magnitudes=catalog["magnitudes"],
            etas_rates=rates,
            etas_mu=10.0 ** metadata["final_parameters"]["log10_mu"],
            beta=metadata["beta"],
            magnitude_reference=metadata["m_ref"],
            grid=grid,
            issue_day_start=jst_day(timestamp(metadata["auxiliary_start"])),
            issue_day_end_exclusive=jst_day(validation_end),
            prevalidation_days=prevalidation_days,
            parent_parameters=parent,
            ch008_parameters=challenger,
            target_mean_cell_exposure=config["normalization"][
                "target_mean_cell_prevalidation_exposure"
            ],
        )
        selected = np.asarray(
            [validation_start <= value < validation_end for value in catalog["times"]]
        )
        summary = summarize(
            replay.event_gains[selected],
            catalog["days"][selected],
            config["evaluation"],
            config["evaluation"]["bootstrap_seed"] + 1000 * region_index,
        )
        results[name] = {
            "renewal_exposure_scale": renewal_scale,
            "prevalidation_days": prevalidation_days,
            "etas_parameters_sha256": sha256_file(parameter_path),
            "catalog_sha256": sha256_file(catalog_path),
            "validation": summary,
        }
        print(name, json.dumps(results[name], indent=2))

    rule = config["admission_rule"]
    all_mean = all(value["validation"]["mean_igpe"] > 0 for value in results.values())
    all_lower_30 = all(
        value["validation"]["bootstrap"]["30_days"]["lower"] > 0
        for value in results.values()
    )
    all_lower_90 = all(
        value["validation"]["bootstrap"]["90_days"]["lower"] >= 0
        for value in results.values()
    )
    gates = {
        "all_three_region_mean_igpe_positive": all_mean,
        "all_three_region_30_day_lower_bound_positive": all_lower_30,
        "all_three_region_90_day_lower_bound_nonnegative": all_lower_90,
    }
    admitted = all(gates[key] for key, required in rule.items() if required)
    payload = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "status": "completed_admitted" if admitted else "completed_not_admitted",
        "config_sha256": sha256_file(CONFIG),
        "protocol_sha256": sha256_file(protocol_path),
        "catalog_manifest_sha256": sha256_file(CATALOG_MANIFEST),
        "source_experiment_sha256": sha256_file(ROOT / config["source_experiment"]),
        "source_model_sha256": sha256_file(model_path),
        "parent_model_sha256": sha256_file(parent_path),
        "normalized_adapter_module_sha256": sha256_file(adapter_path),
        "evaluation_script_sha256": sha256_file(Path(__file__)),
        "forbidden_period_accessed": False,
        "results": results,
        "admission_gates": gates,
        "admitted": admitted,
        "claim_boundary": config["claim_boundary"],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"admitted={admitted}")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
