#!/usr/bin/env python3
"""Run the pre-registered fit-only CH-002 Sobol candidate experiment."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import qmc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.grid_forecast import analytical_background_rates
from etas_challenge.readiness_fit import ReadinessFitEvaluator
from etas_challenge.readiness_inputs import day_number
from etas_challenge.training_matrix import GridDefinition, sha256_file
from etas_challenge.ucerf3_faults import FaultSection


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def clean_lock_commit() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status:
        raise ValueError("CH-002 fit requires a clean committed repository")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def write_candidates(path: Path, rows: list[dict], parameter_names: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fields = ["candidate_id", *parameter_names, "selection_igpe", "holdout_igpe", "elapsed_seconds"]
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch002-fit-v1.json"),
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if config["status"] != "pre_registered_unrun":
        raise ValueError("CH-002 fit config is not in its pre-run state")
    if config["period"].get("validation_opened") is not False:
        raise ValueError("CH-002 fit cannot open development validation")
    lock_commit = clean_lock_commit()

    locked = (
        ("fit_inputs_manifest", "fit_inputs_manifest_sha256"),
        ("fit_inputs", "fit_inputs_sha256"),
        ("initial_state_manifest", "initial_state_manifest_sha256"),
        ("initial_state", "initial_state_sha256"),
        ("fault_grid_manifest", "fault_grid_manifest_sha256"),
        ("fault_grid", "fault_grid_sha256"),
        ("fault_sections", "fault_sections_sha256"),
        ("grid", "grid_sha256"),
        ("simulation_config", "simulation_config_sha256"),
        ("state_contract", "state_contract_sha256"),
    )
    for path_key, hash_key in locked:
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-002 fit locked input changed: {path_key}")

    fault_payload = json.loads(Path(config["fault_sections"]).read_text())
    sections = [FaultSection(**item) for item in fault_payload["sections"]]
    grid = GridDefinition.load(Path(config["grid"]))
    simulation = json.loads(Path(config["simulation_config"]).read_text())
    background_grid = analytical_background_rates(
        grid,
        10.0 ** simulation["parameters"]["log10_mu"],
        simulation["earth_radius_km"],
    )
    with np.load(config["initial_state"], allow_pickle=False) as graph:
        section_ids = graph["section_ids"].copy()
        initial_state = graph["criticality_margin"].astype(float)
        particle_branches = graph["particle_loading_branch"].copy()
    with np.load(config["fault_grid"], allow_pickle=False) as fault_grid:
        grid_nearest_ids = fault_grid["nearest_section_ids"].copy()
        grid_nearest_distances = fault_grid["nearest_trace_distances_km"].copy()
    with np.load(config["fit_inputs"], allow_pickle=False) as fit:
        fit_arrays = {name: fit[name].copy() for name in fit.files}

    geometry = config["fixed_geometry"]
    evaluator = ReadinessFitEvaluator(
        sections=sections,
        section_ids=section_ids,
        initial_state=initial_state,
        particle_branches=particle_branches,
        grid_nearest_ids=grid_nearest_ids,
        grid_nearest_distances_km=grid_nearest_distances,
        event_nearest_ids=fit_arrays["nearest_fault_section_ids"],
        event_nearest_distances_km=fit_arrays["nearest_fault_distances_km"],
        background_grid=background_grid,
        all_issue_days=fit_arrays["all_issue_days"],
        event_days=fit_arrays["event_issue_days"],
        event_cells=fit_arrays["cell_indexes"],
        event_magnitudes=fit_arrays["magnitudes"],
        event_etas_rates=fit_arrays["etas_rates"],
        event_background_rates=fit_arrays["direct_background_rates"],
        event_background_probabilities=fit_arrays["etas_background_probabilities"],
        bandwidth_km=geometry["grid_projection_bandwidth_km"],
        cutoff_km=geometry["grid_projection_cutoff_km"],
        fault_prior_odds=geometry["fault_prior_odds"],
    )

    protocol = config["candidate_protocol"]
    bounds = np.asarray(config["parameter_bounds"], dtype=float)
    sampler = qmc.Sobol(
        d=len(bounds), scramble=True, seed=protocol["seed"]
    )
    unit = sampler.random_base2(m=protocol["sobol_power"])
    candidates = qmc.scale(unit, bounds[:, 0], bounds[:, 1])
    if protocol["include_zero_candidate"]:
        candidates = np.vstack((np.zeros(len(bounds)), candidates))

    selection_start = day_number(config["period"]["start"])
    selection_end = day_number(config["period"]["selection_end_exclusive"])
    holdout_start = day_number(config["period"]["fit_holdout_start"])
    holdout_end = day_number(config["period"]["end_exclusive"])
    rows = []
    evaluations = []
    for candidate_id, values in enumerate(candidates):
        started = time.monotonic()
        result = evaluator.evaluate(values)
        elapsed = time.monotonic() - started
        selection_igpe = result.igpe(selection_start, selection_end)
        holdout_igpe = result.igpe(holdout_start, holdout_end)
        row = {
            "candidate_id": candidate_id,
            **{
                name: format(float(value), ".12g")
                for name, value in zip(config["parameter_order"], values)
            },
            "selection_igpe": format(selection_igpe, ".12g"),
            "holdout_igpe": format(holdout_igpe, ".12g"),
            "elapsed_seconds": format(elapsed, ".6f"),
        }
        rows.append(row)
        evaluations.append((selection_igpe, holdout_igpe, result))
        print(
            f"candidate={candidate_id:02d} selection={selection_igpe:+.6f} "
            f"holdout={holdout_igpe:+.6f} elapsed={elapsed:.2f}s",
            flush=True,
        )

    best_index = int(np.argmax([item[0] for item in evaluations]))
    best_selection, best_holdout, best_result = evaluations[best_index]
    best_values = candidates[best_index]
    candidate_output = Path(config["candidate_output"])
    write_candidates(candidate_output, rows, config["parameter_order"])

    model = {
        "schema_version": 1,
        "model_id": "ch002-readiness-v1",
        "status": "fit_locked_validation_unseen",
        "fit_lock_commit": lock_commit,
        "selected_candidate_id": best_index,
        "parameters": {
            name: float(value)
            for name, value in zip(config["parameter_order"], best_values)
        },
        "fit_scores": {
            "selection_2014_2017_igpe": best_selection,
            "selection_2014_2017_relative_factor": math.exp(best_selection),
            "holdout_2018_igpe": best_holdout,
            "holdout_2018_relative_factor": math.exp(best_holdout),
            "holdout_positive": best_holdout > 0,
        },
        "forecast_contract": {
            "preserve_triggered_etas": True,
            "preserve_daily_expected_count": True,
            "directional_transfer": 0.0,
        },
        "claim_boundary": config["claim_boundary"],
    }
    model_output = Path(config["model_output"])
    atomic_json(model_output, model)
    manifest = {
        "schema_version": 1,
        "fit_id": config["fit_id"],
        "status": "fit_locked_validation_unseen",
        "tool": {
            "name": "scripts/fit_ch002_readiness.py",
            "script_sha256": sha256_file(Path(__file__)),
            "module_sha256": sha256_file(
                ROOT / "src/etas_challenge/readiness_fit.py"
            ),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "protocol": {
            **protocol,
            "candidate_count": len(candidates),
            "validation_opened": False,
            "locked_retrospective_opened": False,
            "fit_lock_commit": lock_commit,
        },
        "inputs": {
            "config_sha256": sha256_file(args.config),
            **{hash_key: config[hash_key] for _, hash_key in locked},
        },
        "outputs": {
            "model": str(model_output),
            "model_sha256": sha256_file(model_output),
            "candidates": str(candidate_output),
            "candidates_sha256": sha256_file(candidate_output),
        },
        "result": {
            "selected_candidate_id": best_index,
            "selection_events": int(np.count_nonzero(best_result.event_days < selection_end)),
            "holdout_events": int(np.count_nonzero(best_result.event_days >= holdout_start)),
            "selection_igpe": best_selection,
            "holdout_igpe": best_holdout,
            "admit_development_validation": best_holdout > 0,
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["fit_manifest"]), manifest)
    print(
        f"selected candidate {best_index}: selection={best_selection:+.6f}, "
        f"holdout={best_holdout:+.6f}, validation_admitted={best_holdout > 0}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
