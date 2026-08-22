#!/usr/bin/env python3
"""Build a contract-gated event history for the CH-004 renewal clock."""

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

from etas_challenge.fault_grid import nearest_fault_sections_for_points
from etas_challenge.readiness_inputs import attach_etas_background_probabilities
from etas_challenge.readiness_inputs import day_number, load_fit_catalog
from etas_challenge.training_matrix import GridDefinition, sha256_file, write_deterministic_npz
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
        default=Path("configs/challenge/ch004-event-history-v1.json"),
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    period = config["period"]
    fit_period = (
        period["scoring_start"] == "2014-01-07T00:00:00Z"
        and period["end_exclusive"] == "2019-01-01T00:00:00Z"
        and period["development_validation_opened"] is False
    )
    validation_period = (
        period["scoring_start"] == "2019-01-01T00:00:00Z"
        and period["end_exclusive"] == "2023-01-01T00:00:00Z"
        and period["development_validation_opened"] is True
        and period.get("locked_retrospective_opened") is False
    )
    retrospective_period = (
        period["scoring_start"] == "2023-01-01T00:00:00Z"
        and period["end_exclusive"] == "2026-08-19T00:00:00Z"
        and period["development_validation_opened"] is True
        and period.get("locked_retrospective_opened") is True
    )
    if (
        period["history_start"] != "2007-01-01T00:00:00Z"
        or period["warmup_scored"] is not False
        or not (fit_period or validation_period or retrospective_period)
    ):
        raise ValueError("CH-004 event-history period violates the frozen contract")
    locked_inputs = [
        ("component_contract", "component_contract_sha256"),
        ("catalog", "catalog_sha256"),
        ("grid", "grid_sha256"),
        ("etas_manifest", "etas_manifest_sha256"),
        ("simulation_config", "simulation_config_sha256"),
        ("fault_sections", "fault_sections_sha256"),
    ]
    if validation_period or retrospective_period:
        locked_inputs.extend(
            (("locked_model", "locked_model_sha256"), ("fit_manifest", "fit_manifest_sha256"))
        )
    if retrospective_period:
        locked_inputs.extend(
            (
                ("validation_manifest", "validation_manifest_sha256"),
                ("challenge_contract", "challenge_contract_sha256"),
                ("retrospective_etas_manifest", "retrospective_etas_manifest_sha256"),
            )
        )
    for path_key, hash_key in locked_inputs:
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-004 locked input changed: {path_key}")
    if retrospective_period:
        validation = json.loads(Path(config["validation_manifest"]).read_text())
        challenge = json.loads(Path(config["challenge_contract"]).read_text())
        retrospective_split = next(
            split for split in challenge["splits"] if split["name"] == "locked_retrospective_test"
        )
        if validation["admission"]["admit_locked_retrospective"] is not True:
            raise ValueError("CH-004 was not admitted to locked retrospective evaluation")
        if (
            retrospective_split["start"] != period["scoring_start"]
            or retrospective_split["end_exclusive"] != period["end_exclusive"]
            or retrospective_split["immutable"] is not True
        ):
            raise ValueError("CH-004 retrospective period differs from challenge contract")

    grid = GridDefinition.load(Path(config["grid"]))
    catalog = load_fit_catalog(
        Path(config["catalog"]),
        grid,
        start=period["history_start"],
        end_exclusive=period["end_exclusive"],
        magnitude_rounding=config["magnitude_rounding"],
        magnitude_threshold=config["magnitude_threshold"],
    )
    etas_manifest = json.loads(Path(config["etas_manifest"]).read_text())
    if retrospective_period:
        retrospective_etas = json.loads(
            Path(config["retrospective_etas_manifest"]).read_text()
        )
        if (
            etas_manifest["period"]["end_exclusive"]
            != retrospective_etas["period"]["start"]
            or retrospective_etas["period"]["start"] != "2023-01-01"
            or retrospective_etas["period"]["end_exclusive"] != "2026-08-19"
        ):
            raise ValueError("CH-004 ETAS manifests are not contiguous")
        etas_manifest = {
            **etas_manifest,
            "outputs": {
                "shards": [
                    *etas_manifest["outputs"]["shards"],
                    *retrospective_etas["outputs"]["shards"],
                ]
            },
        }
    simulation = json.loads(Path(config["simulation_config"]).read_text())
    inputs = attach_etas_background_probabilities(
        catalog,
        grid=grid,
        etas_manifest=etas_manifest,
        repository_root=ROOT,
        mu_per_km2_day=10.0 ** simulation["parameters"]["log10_mu"],
        earth_radius_km=simulation["earth_radius_km"],
    )
    fault_payload = json.loads(Path(config["fault_sections"]).read_text())
    sections = [FaultSection(**item) for item in fault_payload["sections"]]
    nearest_ids, nearest_distances = nearest_fault_sections_for_points(
        inputs.catalog.latitudes,
        inputs.catalog.longitudes,
        sections,
        neighbors=config["nearest_fault_sections_per_event"],
    )
    issue_days = np.arange(
        day_number(period["history_start"]),
        day_number(period["end_exclusive"]),
        dtype=np.int32,
    )
    scoring_start_day = day_number(period["scoring_start"])
    output = Path(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    write_deterministic_npz(
        output,
        {
            "all_issue_days": issue_days,
            "scoring_start_day": np.asarray(scoring_start_day, dtype=np.int32),
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
    warmup = inputs.catalog.issue_days < scoring_start_day
    scoring = ~warmup
    probability = inputs.etas_background_probabilities
    manifest = {
        "schema_version": 1,
        "dataset_id": config["dataset_id"],
        "status": f"completed_warmup_and_{period.get('scoring_role', 'fit_development')}",
        "tool": {
            "name": "scripts/prepare_ch004_event_history.py",
            "script_sha256": sha256_file(Path(__file__)),
            "input_module_sha256": sha256_file(ROOT / "src/etas_challenge/readiness_inputs.py"),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "inputs": {key: config[key] for key in config if key.endswith("_sha256")},
        "period": {
            **period,
            "issue_days": int(len(issue_days)),
            "warmup_days": int(scoring_start_day - issue_days[0]),
            "fit_development_days": int(issue_days[-1] - scoring_start_day + 1),
            "scoring_days": int(issue_days[-1] - scoring_start_day + 1),
            "scoring_role": period.get("scoring_role", "fit_development"),
        },
        "protocol": {
            "history_boundary": "forecast before same-day observations",
            "warmup_targets_scored": False,
            "magnitude_rounding": config["magnitude_rounding"],
            "magnitude_threshold": config["magnitude_threshold"],
            "background_posterior": "analytical direct background cell rate / frozen total ETAS cell rate",
            "event_fault_geometry": "four nearest UCERF3 trace sections from exact event coordinates",
            "event_magnitudes_retained_for_candidate_dependent_reset_marks": True,
        },
        "output": {
            "path": str(output),
            "git_policy": "ignored_generated_data",
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
        },
        "results": {
            "events": int(len(inputs.catalog.event_ids)),
            "warmup_events": int(np.count_nonzero(warmup)),
            "fit_development_events": int(np.count_nonzero(scoring)),
            "scoring_events": int(np.count_nonzero(scoring)),
            "selected_events_before_grid": inputs.catalog.selected_before_grid,
            "outside_relm_grid": inputs.catalog.outside_grid,
            "warmup_posterior_root_mass": float(np.sum(probability[warmup])),
            "fit_development_posterior_root_mass": float(np.sum(probability[scoring])),
            "scoring_posterior_root_mass": float(np.sum(probability[scoring])),
            "magnitude_gte_3_5": int(np.count_nonzero(inputs.catalog.magnitudes >= 3.5)),
            "magnitude_gte_4_0": int(np.count_nonzero(inputs.catalog.magnitudes >= 4.0)),
            "magnitude_gte_5_0": int(np.count_nonzero(inputs.catalog.magnitudes >= 5.0)),
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(
        f"prepared {len(inputs.catalog.event_ids)} CH-004 events across "
        f"{len(issue_days)} issue days at {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
