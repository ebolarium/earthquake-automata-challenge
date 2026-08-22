#!/usr/bin/env python3
"""Run the pre-registered CH-004 marked-renewal fit experiment."""

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

from etas_challenge.emergence_fit import annual_robust_score, candidate_is_admissible
from etas_challenge.grid_forecast import analytical_background_rates
from etas_challenge.readiness_fit import sparse_geometry
from etas_challenge.readiness_replay import branch_loading_vector
from etas_challenge.renewal_fit import RenewalFitEvaluator
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.training_matrix import GridDefinition, sha256_file
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES


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
        raise RuntimeError("CH-004 fit requires a clean committed worktree")
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


def main() -> int:
    config_path = Path("configs/challenge/ch004-fit-v1.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    period = config["period"]
    if (
        period["warmup_scored"] is not False
        or period["development_validation_opened"] is not False
        or period["locked_retrospective_opened"] is not False
        or period["end_exclusive"] != "2019-01-01"
    ):
        raise ValueError("CH-004 fit period violates the frozen contract")
    lock_commit = clean_lock_commit()
    for path_key, hash_key in (
        ("component_contract", "component_contract_sha256"),
        ("event_history_manifest", "event_history_manifest_sha256"),
        ("event_history", "event_history_sha256"),
        ("warmup_diagnostic_manifest", "warmup_diagnostic_manifest_sha256"),
        ("fault_graph", "fault_graph_sha256"),
        ("fault_grid", "fault_grid_sha256"),
        ("fault_sections", "fault_sections_sha256"),
        ("grid", "grid_sha256"),
        ("simulation_config", "simulation_config_sha256"),
    ):
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-004 fit locked input changed: {path_key}")

    with np.load(config["event_history"], allow_pickle=False) as source:
        history = {name: source[name].copy() for name in source.files}
    with np.load(config["fault_graph"], allow_pickle=False) as source:
        section_ids = source["section_ids"].copy()
        adjacency = source["adjacency"].astype(float)
    with np.load(config["fault_grid"], allow_pickle=False) as source:
        grid_ids = source["nearest_section_ids"].copy()
        grid_distances = source["nearest_trace_distances_km"].copy()
    fault_payload = json.loads(Path(config["fault_sections"]).read_text())
    sections = sorted(
        (FaultSection(**item) for item in fault_payload["sections"]),
        key=lambda section: section.section_id,
    )
    grid = GridDefinition.load(Path(config["grid"]))
    simulation = json.loads(Path(config["simulation_config"]).read_text())
    background = analytical_background_rates(
        grid,
        10.0 ** simulation["parameters"]["log10_mu"],
        simulation["earth_radius_km"],
    )
    fixed = config["fixed_contract"]
    if grid_ids.shape[1] != fixed["grid_neighbors"]:
        raise ValueError("CH-004 fit grid neighbor count changed")
    active_sections = []
    expected_background = []
    grid_geometries = []
    event_geometries = []
    for branch in SLIP_RATE_BRANCHES:
        _, active = branch_loading_vector(sections, branch)
        active_sections.append(active)
        grid_geometry = sparse_geometry(
            grid_ids,
            grid_distances,
            section_ids,
            active,
            bandwidth_km=fixed["grid_bandwidth_km"],
            cutoff_km=fixed["grid_cutoff_km"],
            fault_prior_odds=fixed["fault_prior_odds"],
        )
        grid_geometries.append(grid_geometry)
        section_mass, _ = aggregate_sparse_section_mass(
            background, grid_geometry, len(section_ids)
        )
        expected_background.append(section_mass)
        event_geometries.append(
            sparse_geometry(
                history["nearest_fault_section_ids"],
                history["nearest_fault_distances_km"],
                section_ids,
                active,
                bandwidth_km=fixed["grid_bandwidth_km"],
                cutoff_km=fixed["grid_cutoff_km"],
                fault_prior_odds=fixed["fault_prior_odds"],
            )
        )
    evaluator = RenewalFitEvaluator(
        issue_days=history["all_issue_days"],
        scoring_start_day=int(history["scoring_start_day"]),
        event_days=history["event_issue_days"],
        event_cells=history["cell_indexes"],
        event_magnitudes=history["magnitudes"],
        event_etas_rates=history["etas_rates"],
        event_background_probabilities=history["etas_background_probabilities"],
        event_geometries=event_geometries,
        expected_section_background=np.asarray(expected_background),
        adjacency=adjacency,
        active_sections=np.asarray(active_sections),
        grid_geometries=grid_geometries,
        background_grid=background,
        beta=simulation["beta"],
        magnitude_reference=simulation["m_ref"],
        graph_neighbors=fixed["graph_neighbors"],
        maximum_log_tilt=fixed["maximum_log_tilt"],
    )

    protocol = config["candidate_protocol"]
    bounds = np.asarray(config["parameter_bounds"], dtype=float)
    sampler = qmc.Sobol(d=len(bounds), scramble=True, seed=protocol["seed"])
    candidates = qmc.scale(
        sampler.random_base2(m=protocol["sobol_power"]), bounds[:, 0], bounds[:, 1]
    )
    if protocol["include_etas_control"]:
        candidates = np.vstack((np.asarray(config["etas_control_parameters"]), candidates))
    scored_etas = history["etas_rates"][
        history["event_issue_days"] >= int(history["scoring_start_day"])
    ]
    low_threshold = float(np.quantile(scored_etas, protocol["low_etas_quantile"]))
    low_mask = scored_etas <= low_threshold
    parameter_names = config["parameter_order"]
    rows: list[dict] = []
    evaluations = []
    annual_fields = [f"igpe_{year}" for year in range(2014, 2019)]
    for candidate_id, values in enumerate(candidates):
        started = time.monotonic()
        result = evaluator.evaluate(values)
        mean_igpe = float(np.mean(result.event_gains))
        robust_score, annual = annual_robust_score(result.event_gains, result.event_days)
        low_igpe = float(np.mean(result.event_gains[low_mask]))
        admissible = candidate_id > 0 and candidate_is_admissible(
            mean_igpe, robust_score, annual, low_igpe, protocol["annual_loss_floor"]
        )
        elapsed = time.monotonic() - started
        row = {
            "candidate_id": candidate_id,
            **{
                name: format(float(value), ".12g")
                for name, value in zip(parameter_names, values)
            },
            "expected_reset_weight": format(result.expected_reset_weight, ".12g"),
            "mean_igpe": format(mean_igpe, ".12g"),
            "robust_annual_igpe": format(robust_score, ".12g"),
            "low_etas_igpe": format(low_igpe, ".12g"),
            "active_issue_days": result.active_issue_days,
            "changed_events": int(
                np.count_nonzero(result.challenger_event_rates != scored_etas)
            ),
            "maximum_absolute_event_gain": format(
                float(np.max(np.abs(result.event_gains))), ".12g"
            ),
            **{f"igpe_{year}": format(annual[year], ".12g") for year in range(2014, 2019)},
            "admissible": str(admissible).lower(),
            "elapsed_seconds": format(elapsed, ".6f"),
        }
        rows.append(row)
        evaluations.append((robust_score, mean_igpe, low_igpe, annual, admissible, result))
        print(
            f"candidate={candidate_id:02d} mean={mean_igpe:+.6f} "
            f"robust={robust_score:+.6f} low={low_igpe:+.6f} "
            f"active_days={result.active_issue_days} admissible={admissible} "
            f"elapsed={elapsed:.2f}s",
            flush=True,
        )

    admissible_indexes = [index for index, item in enumerate(evaluations) if item[4]]
    selected_index = (
        max(admissible_indexes, key=lambda index: evaluations[index][0])
        if admissible_indexes
        else 0
    )
    robust_score, mean_igpe, low_igpe, annual, admitted, selected_result = evaluations[
        selected_index
    ]
    selected_values = candidates[selected_index]
    candidate_path = Path(config["candidate_output"])
    fields = [
        "candidate_id",
        *parameter_names,
        "expected_reset_weight",
        "mean_igpe",
        "robust_annual_igpe",
        "low_etas_igpe",
        "active_issue_days",
        "changed_events",
        "maximum_absolute_event_gain",
        *annual_fields,
        "admissible",
        "elapsed_seconds",
    ]
    write_candidates(candidate_path, rows, fields)

    model = {
        "schema_version": 1,
        "model_id": "ch004-marked-renewal-v1",
        "status": "fit_locked_validation_unseen",
        "fit_lock_commit": lock_commit,
        "selected_candidate_id": selected_index,
        "selected_nonzero_candidate": bool(admitted),
        "parameters": {
            name: float(value) for name, value in zip(parameter_names, selected_values)
        },
        "fit_scores": {
            "mean_igpe": mean_igpe,
            "relative_factor": math.exp(mean_igpe),
            "robust_annual_igpe": robust_score,
            "low_etas_igpe": low_igpe,
            "annual_igpe": {str(year): value for year, value in annual.items()},
            "active_issue_days": selected_result.active_issue_days,
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
            "name": "scripts/fit_ch004_renewal.py",
            "script_sha256": sha256_file(Path(__file__)),
            "module_sha256": sha256_file(ROOT / "src/etas_challenge/renewal_fit.py"),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "protocol": {
            **protocol,
            "candidate_count": len(candidates),
            "fit_lock_commit": lock_commit,
            "warmup_scored": False,
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
            "events": int(len(scored_etas)),
            "low_etas_events": int(np.count_nonzero(low_mask)),
            "low_etas_threshold": low_threshold,
            "mean_igpe": mean_igpe,
            "robust_annual_igpe": robust_score,
            "low_etas_igpe": low_igpe,
            "annual_igpe": {str(year): value for year, value in annual.items()},
            "active_issue_days": selected_result.active_issue_days,
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
