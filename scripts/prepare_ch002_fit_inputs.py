#!/usr/bin/env python3
"""Generate fit-only CH-002 events with frozen ETAS background posteriors."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.readiness_inputs import (
    attach_etas_background_probabilities,
    day_number,
    load_fit_catalog,
)
from etas_challenge.fault_grid import nearest_fault_sections_for_points
from etas_challenge.training_matrix import (
    GridDefinition,
    sha256_file,
    write_deterministic_npz,
)
from etas_challenge.ucerf3_faults import FaultSection


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch002-fit-inputs-v1.json"),
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["fit_end_exclusive"] != "2019-01-01T00:00:00Z":
        raise ValueError("CH-002 fit inputs cannot reach validation")
    if config.get("validation_opened") is not False:
        raise ValueError("CH-002 fit input contract must keep validation closed")
    for path_key, hash_key in (
        ("catalog_path", "catalog_sha256"),
        ("grid_path", "grid_sha256"),
        ("etas_manifest", "etas_manifest_sha256"),
        ("simulation_config", "simulation_config_sha256"),
        ("fault_sections_path", "fault_sections_sha256"),
        ("challenge_contract", "challenge_contract_sha256"),
    ):
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-002 locked input changed: {path_key}")

    grid = GridDefinition.load(Path(config["grid_path"]))
    catalog = load_fit_catalog(
        Path(config["catalog_path"]),
        grid,
        start=config["fit_start"],
        end_exclusive=config["fit_end_exclusive"],
        magnitude_rounding=config["magnitude_rounding"],
        magnitude_threshold=config["magnitude_threshold"],
    )
    etas_manifest = json.loads(Path(config["etas_manifest"]).read_text())
    simulation = json.loads(Path(config["simulation_config"]).read_text())
    inputs = attach_etas_background_probabilities(
        catalog,
        grid=grid,
        etas_manifest=etas_manifest,
        repository_root=ROOT,
        mu_per_km2_day=10.0 ** simulation["parameters"]["log10_mu"],
        earth_radius_km=simulation["earth_radius_km"],
    )
    fault_payload = json.loads(Path(config["fault_sections_path"]).read_text())
    sections = [FaultSection(**item) for item in fault_payload["sections"]]
    nearest_ids, nearest_distances = nearest_fault_sections_for_points(
        inputs.catalog.latitudes,
        inputs.catalog.longitudes,
        sections,
        neighbors=config["nearest_fault_sections_per_event"],
    )
    all_issue_days = np.arange(
        day_number(config["fit_start"]),
        day_number(config["fit_end_exclusive"]),
        dtype=np.int32,
    )
    output = Path(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    write_deterministic_npz(
        output,
        {
            "all_issue_days": all_issue_days,
            "event_ids": inputs.catalog.event_ids,
            "origin_time_ns": inputs.catalog.origin_time_ns,
            "event_issue_days": inputs.catalog.issue_days,
            "longitudes": inputs.catalog.longitudes,
            "latitudes": inputs.catalog.latitudes,
            "depths_km": inputs.catalog.depths_km,
            "magnitudes": inputs.catalog.magnitudes,
            "cell_indexes": inputs.catalog.cell_indexes,
            "etas_rates": inputs.etas_rates,
            "direct_background_rates": inputs.direct_background_rates,
            "etas_background_probabilities": inputs.etas_background_probabilities,
            "nearest_fault_section_ids": nearest_ids,
            "nearest_fault_distances_km": nearest_distances,
            "config_sha256": np.asarray(sha256_file(args.config)),
        },
    )
    probability = inputs.etas_background_probabilities
    manifest = {
        "schema_version": 1,
        "dataset_id": config["dataset_id"],
        "status": "completed_fit_only",
        "tool": {
            "name": "scripts/prepare_ch002_fit_inputs.py",
            "script_sha256": sha256_file(Path(__file__)),
            "module_sha256": sha256_file(
                ROOT / "src/etas_challenge/readiness_inputs.py"
            ),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "inputs": {
            "config_sha256": sha256_file(args.config),
            "catalog_sha256": config["catalog_sha256"],
            "grid_sha256": config["grid_sha256"],
            "etas_manifest_sha256": config["etas_manifest_sha256"],
            "simulation_config_sha256": config["simulation_config_sha256"],
            "fault_sections_sha256": config["fault_sections_sha256"],
        },
        "period": {
            "start": config["fit_start"],
            "end_exclusive": config["fit_end_exclusive"],
            "validation_opened": False,
        },
        "protocol": {
            "history_boundary": "forecast before same-day observations",
            "magnitude_rounding": config["magnitude_rounding"],
            "magnitude_threshold": config["magnitude_threshold"],
            "background_posterior": "analytical direct background cell rate / frozen total ETAS cell rate",
            "event_fault_geometry": "eight nearest UCERF3 trace sections from exact event coordinates",
        },
        "output": {
            "path": str(output),
            "git_policy": "ignored_generated_data",
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
        },
        "results": {
            "issue_days": int(len(all_issue_days)),
            "selected_events_before_grid": inputs.catalog.selected_before_grid,
            "outside_relm_grid": inputs.catalog.outside_grid,
            "fit_events": int(len(inputs.catalog.event_ids)),
            "event_days": int(len(np.unique(inputs.catalog.issue_days))),
            "verified_etas_monthly_shards": int(
                len(np.unique(inputs.catalog.issue_days.astype("datetime64[D]").astype("datetime64[M]")))
            ),
            "magnitude_min": float(np.min(inputs.catalog.magnitudes)),
            "magnitude_max": float(np.max(inputs.catalog.magnitudes)),
            "magnitude_gte_3_5": int(np.count_nonzero(inputs.catalog.magnitudes >= 3.5)),
            "magnitude_gte_4_0": int(np.count_nonzero(inputs.catalog.magnitudes >= 4.0)),
            "posterior_background_event_mass": float(np.sum(probability)),
            "etas_background_probability_min": float(np.min(probability)),
            "etas_background_probability_median": float(np.median(probability)),
            "etas_background_probability_mean": float(np.mean(probability)),
            "etas_background_probability_max": float(np.max(probability)),
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(
        f"prepared {len(inputs.catalog.event_ids)} fit events across "
        f"{len(all_issue_days)} issue days at {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
