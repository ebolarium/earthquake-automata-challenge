#!/usr/bin/env python3
"""Run the pre-registered CH-003 residual-emergence fit experiment."""

from __future__ import annotations

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

from etas_challenge.emergence_fit import EmergenceFitEvaluator
from etas_challenge.emergence_fit import annual_robust_score
from etas_challenge.emergence_fit import candidate_is_admissible
from etas_challenge.grid_forecast import analytical_background_rates
from etas_challenge.readiness_fit import sparse_geometry
from etas_challenge.training_matrix import GridDefinition, sha256_file


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def clean_lock_commit() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    if status:
        raise RuntimeError("CH-003 fit requires a clean committed worktree")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def write_candidates(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def generate_candidates(config: dict) -> np.ndarray:
    protocol = config["candidate_protocol"]
    bounds = np.asarray(config["parameter_bounds"], dtype=float)
    sampler = qmc.Sobol(d=len(bounds), scramble=True, seed=protocol["seed"])
    unit = sampler.random_base2(m=protocol["sobol_power"])
    candidates = qmc.scale(unit, bounds[:, 0], bounds[:, 1])
    lower, upper = bounds[0]
    candidates[:, 0] = np.exp(np.log(lower) + unit[:, 0] * (np.log(upper) - np.log(lower)))
    if protocol["include_etas_control"]:
        candidates = np.vstack((np.asarray(config["etas_control_parameters"]), candidates))
    return candidates


def main() -> int:
    config_path = Path("configs/challenge/ch003-fit-v1.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    period = config["period"]
    if period["end_exclusive"] != "2019-01-01" or period["development_validation_opened"] is not False:
        raise ValueError("CH-003 fit must not open development validation")
    if period["locked_retrospective_opened"] is not False:
        raise ValueError("CH-003 fit must keep the retrospective test closed")
    lock_commit = clean_lock_commit()
    for path_key, hash_key in (
        ("component_contract", "component_contract_sha256"),
        ("compensator_manifest", "compensator_manifest_sha256"),
        ("compensator", "compensator_sha256"),
        ("fit_inputs", "fit_inputs_sha256"),
        ("fault_grid", "fault_grid_sha256"),
        ("grid", "grid_sha256"),
        ("simulation_config", "simulation_config_sha256"),
    ):
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-003 locked input changed: {path_key}")

    grid = GridDefinition.load(Path(config["grid"]))
    simulation = json.loads(Path(config["simulation_config"]).read_text())
    background = analytical_background_rates(
        grid,
        10.0 ** simulation["parameters"]["log10_mu"],
        simulation["earth_radius_km"],
    )
    with np.load(config["compensator"], allow_pickle=False) as source:
        compensator = {name: source[name].copy() for name in source.files}
    with np.load(config["fit_inputs"], allow_pickle=False) as source:
        fit = {name: source[name].copy() for name in source.files}
    with np.load(config["fault_grid"], allow_pickle=False) as source:
        grid_ids = source["nearest_section_ids"].copy()
        grid_distances = source["nearest_trace_distances_km"].copy()

    fixed = config["fixed_contract"]
    geometries = [
        sparse_geometry(
            grid_ids,
            grid_distances,
            compensator["section_ids"],
            active,
            bandwidth_km=fixed["grid_bandwidth_km"],
            cutoff_km=fixed["grid_cutoff_km"],
            fault_prior_odds=fixed["fault_prior_odds"],
        )
        for active in compensator["active_sections"]
    ]
    evaluator = EmergenceFitEvaluator(
        issue_days=compensator["issue_days"],
        observed_root_mass=compensator["observed_root_mass"],
        expected_daily_root_mass=compensator["expected_daily_root_mass"],
        adjacency=compensator["adjacency"],
        active_sections=compensator["active_sections"],
        grid_geometries=geometries,
        background_grid=background,
        event_days=fit["event_issue_days"],
        event_cells=fit["cell_indexes"],
        event_etas_rates=fit["etas_rates"],
        event_background_rates=fit["direct_background_rates"],
        graph_neighbors=fixed["graph_neighbors"],
        variance_floor=fixed["variance_floor"],
        maximum_log_tilt=fixed["maximum_log_tilt"],
    )

    parameters = config["parameter_order"]
    candidates = generate_candidates(config)
    low_threshold = float(
        np.quantile(fit["etas_rates"], config["candidate_protocol"]["low_etas_quantile"])
    )
    low_mask = fit["etas_rates"] <= low_threshold
    rows: list[dict] = []
    evaluations = []
    annual_fields = [f"igpe_{year}" for year in range(2014, 2019)]
    protocol = config["candidate_protocol"]
    for candidate_id, values in enumerate(candidates):
        started = time.monotonic()
        result = evaluator.evaluate(values)
        mean_igpe = float(np.mean(result.event_gains))
        robust_score, annual = annual_robust_score(result.event_gains, result.event_days)
        low_igpe = float(np.mean(result.event_gains[low_mask]))
        admissible = candidate_id > 0 and candidate_is_admissible(
            mean_igpe,
            robust_score,
            annual,
            low_igpe,
            protocol["annual_loss_floor"],
        )
        elapsed = time.monotonic() - started
        row = {
            "candidate_id": candidate_id,
            **{name: format(float(value), ".12g") for name, value in zip(parameters, values)},
            "mean_igpe": format(mean_igpe, ".12g"),
            "robust_annual_igpe": format(robust_score, ".12g"),
            "low_etas_igpe": format(low_igpe, ".12g"),
            **{f"igpe_{year}": format(annual[year], ".12g") for year in range(2014, 2019)},
            "admissible": str(admissible).lower(),
            "elapsed_seconds": format(elapsed, ".6f"),
        }
        rows.append(row)
        evaluations.append((robust_score, mean_igpe, low_igpe, annual, admissible, result))
        print(
            f"candidate={candidate_id:02d} mean={mean_igpe:+.6f} "
            f"robust={robust_score:+.6f} low={low_igpe:+.6f} "
            f"admissible={admissible} elapsed={elapsed:.2f}s",
            flush=True,
        )

    admissible_indexes = [index for index, item in enumerate(evaluations) if item[4]]
    selected_index = (
        max(admissible_indexes, key=lambda index: evaluations[index][0])
        if admissible_indexes
        else 0
    )
    robust_score, mean_igpe, low_igpe, annual, admitted, _ = evaluations[selected_index]
    selected_values = candidates[selected_index]
    candidate_path = Path(config["candidate_output"])
    fields = [
        "candidate_id",
        *parameters,
        "mean_igpe",
        "robust_annual_igpe",
        "low_etas_igpe",
        *annual_fields,
        "admissible",
        "elapsed_seconds",
    ]
    write_candidates(candidate_path, rows, fields)

    model = {
        "schema_version": 1,
        "model_id": "ch003-residual-emergence-v1",
        "status": "fit_locked_validation_unseen",
        "fit_lock_commit": lock_commit,
        "selected_candidate_id": selected_index,
        "selected_nonzero_candidate": bool(admitted),
        "parameters": {
            name: float(value) for name, value in zip(parameters, selected_values)
        },
        "fit_scores": {
            "mean_igpe": mean_igpe,
            "relative_factor": math.exp(mean_igpe),
            "robust_annual_igpe": robust_score,
            "low_etas_igpe": low_igpe,
            "annual_igpe": {str(year): value for year, value in annual.items()},
            "development_validation_admitted": bool(admitted),
        },
        "claim_boundary": config["claim_boundary"],
    }
    model_path = Path(config["model_output"])
    atomic_json(model_path, model)
    manifest = {
        "schema_version": 1,
        "fit_id": config["fit_id"],
        "status": "fit_locked_validation_unseen",
        "tool": {
            "name": "scripts/fit_ch003_emergence.py",
            "script_sha256": sha256_file(Path(__file__)),
            "module_sha256": sha256_file(ROOT / "src/etas_challenge/emergence_fit.py"),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "protocol": {
            **protocol,
            "candidate_count": len(candidates),
            "fit_lock_commit": lock_commit,
            "development_validation_opened": False,
            "locked_retrospective_opened": False,
        },
        "inputs": {
            "config_sha256": sha256_file(config_path),
            **{key: config[key] for key in config if key.endswith("_sha256")},
        },
        "outputs": {
            "model": str(model_path),
            "model_sha256": sha256_file(model_path),
            "candidates": str(candidate_path),
            "candidates_sha256": sha256_file(candidate_path),
        },
        "result": {
            "selected_candidate_id": selected_index,
            "selected_nonzero_candidate": bool(admitted),
            "events": int(len(fit["event_issue_days"])),
            "low_etas_events": int(np.count_nonzero(low_mask)),
            "low_etas_threshold": low_threshold,
            "mean_igpe": mean_igpe,
            "robust_annual_igpe": robust_score,
            "low_etas_igpe": low_igpe,
            "annual_igpe": {str(year): value for year, value in annual.items()},
            "admit_development_validation": bool(admitted),
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["fit_manifest"]), manifest)
    print(
        f"selected candidate {selected_index}: mean={mean_igpe:+.6f}, "
        f"robust={robust_score:+.6f}, low={low_igpe:+.6f}, "
        f"validation_admitted={admitted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
