#!/usr/bin/env python3
"""Build branch-aware observed and expected CH-003 section root masses."""

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

from etas_challenge.grid_forecast import analytical_background_rates
from etas_challenge.readiness_fit import SparseGeometry, sparse_geometry
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.training_matrix import GridDefinition, sha256_file, write_deterministic_npz
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES
from etas_challenge.readiness_replay import branch_loading_vector


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
        default=Path("configs/challenge/ch003-compensator-v1.json"),
    )
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    period = config["period"]
    if period["end_exclusive"] != "2019-01-01" or period["development_validation_opened"] is not False:
        raise ValueError("CH-003 compensator must remain inside fit development data")
    for path_key, hash_key in (
        ("component_contract", "component_contract_sha256"),
        ("fit_inputs", "fit_inputs_sha256"),
        ("fault_graph", "fault_graph_sha256"),
        ("fault_grid", "fault_grid_sha256"),
        ("fault_sections", "fault_sections_sha256"),
        ("grid", "grid_sha256"),
        ("simulation_config", "simulation_config_sha256"),
    ):
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-003 locked input changed: {path_key}")

    fault_payload = json.loads(Path(config["fault_sections"]).read_text())
    sections = sorted(
        (FaultSection(**item) for item in fault_payload["sections"]),
        key=lambda section: section.section_id,
    )
    grid = GridDefinition.load(Path(config["grid"]))
    simulation = json.loads(Path(config["simulation_config"]).read_text())
    background_grid = analytical_background_rates(
        grid,
        10.0 ** simulation["parameters"]["log10_mu"],
        simulation["earth_radius_km"],
    )
    with np.load(config["fault_graph"], allow_pickle=False) as graph:
        section_ids = graph["section_ids"].copy()
        adjacency = graph["adjacency"].astype(np.float32)
    with np.load(config["fault_grid"], allow_pickle=False) as fault_grid:
        grid_ids = fault_grid["nearest_section_ids"].copy()
        grid_distances = fault_grid["nearest_trace_distances_km"].copy()
    with np.load(config["fit_inputs"], allow_pickle=False) as fit:
        issue_days = fit["all_issue_days"].copy()
        event_days = fit["event_issue_days"].copy()
        event_probabilities = fit["etas_background_probabilities"].astype(float)
        event_ids = fit["nearest_fault_section_ids"].copy()
        event_distances = fit["nearest_fault_distances_km"].copy()

    geometry_config = config["geometry"]
    neighbors = int(geometry_config["neighbors"])
    if grid_ids.shape[1] != neighbors or event_ids.shape[1] < neighbors:
        raise ValueError("grid and event fault-neighbor contracts disagree")
    event_ids = event_ids[:, :neighbors]
    event_distances = event_distances[:, :neighbors]
    branch_count = len(SLIP_RATE_BRANCHES)
    section_count = len(section_ids)
    observed = np.zeros((len(issue_days), branch_count, section_count), dtype=np.float64)
    expected = np.zeros((branch_count, section_count), dtype=np.float64)
    observed_off_fault = np.zeros((len(issue_days), branch_count), dtype=np.float64)
    expected_off_fault = np.zeros(branch_count, dtype=np.float64)
    active_sections = np.zeros((branch_count, section_count), dtype=bool)
    loading = np.zeros((branch_count, section_count), dtype=np.float32)

    for branch_index, branch in enumerate(SLIP_RATE_BRANCHES):
        branch_loading, active = branch_loading_vector(sections, branch)
        active_sections[branch_index] = active
        loading[branch_index] = branch_loading
        grid_geometry = sparse_geometry(
            grid_ids,
            grid_distances,
            section_ids,
            active,
            bandwidth_km=geometry_config["bandwidth_km"],
            cutoff_km=geometry_config["cutoff_km"],
            fault_prior_odds=geometry_config["fault_prior_odds"],
        )
        expected[branch_index], expected_off_fault[branch_index] = (
            aggregate_sparse_section_mass(background_grid, grid_geometry, section_count)
        )
        event_geometry = sparse_geometry(
            event_ids,
            event_distances,
            section_ids,
            active,
            bandwidth_km=geometry_config["bandwidth_km"],
            cutoff_km=geometry_config["cutoff_km"],
            fault_prior_odds=geometry_config["fault_prior_odds"],
        )
        for day_index, day in enumerate(issue_days):
            start = int(np.searchsorted(event_days, day, side="left"))
            end = int(np.searchsorted(event_days, day, side="right"))
            if end == start:
                continue
            day_geometry = SparseGeometry(
                event_geometry.section_indexes[start:end],
                event_geometry.probabilities[start:end],
            )
            section_mass, off_fault = aggregate_sparse_section_mass(
                event_probabilities[start:end], day_geometry, section_count
            )
            observed[day_index, branch_index] = section_mass
            observed_off_fault[day_index, branch_index] = off_fault

    output = Path(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    write_deterministic_npz(
        output,
        {
            "issue_days": issue_days,
            "branch_names": np.asarray(SLIP_RATE_BRANCHES),
            "section_ids": section_ids,
            "observed_root_mass": observed,
            "expected_daily_root_mass": expected,
            "observed_off_fault_mass": observed_off_fault,
            "expected_daily_off_fault_mass": expected_off_fault,
            "active_sections": active_sections,
            "loading": loading,
            "adjacency": adjacency,
            "config_sha256": np.asarray(sha256_file(args.config)),
        },
    )
    observed_total = np.sum(observed, axis=(0, 2)) + np.sum(observed_off_fault, axis=0)
    expected_total = np.sum(expected, axis=1) + expected_off_fault
    posterior_total = float(np.sum(event_probabilities))
    background_total = float(np.sum(background_grid))
    if not np.allclose(observed_total, posterior_total, rtol=0.0, atol=1e-10):
        raise ValueError("observed section plus off-fault mass is not conserved")
    if not np.allclose(expected_total, background_total, rtol=0.0, atol=1e-12):
        raise ValueError("expected section plus off-fault mass is not conserved")
    manifest = {
        "schema_version": 1,
        "dataset_id": config["dataset_id"],
        "status": "completed_fit_development_only",
        "tool": {
            "name": "scripts/prepare_ch003_compensator.py",
            "script_sha256": sha256_file(Path(__file__)),
            "module_sha256": sha256_file(ROOT / "src/etas_challenge/residual_emergence.py"),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "inputs": {
            key: config[key]
            for key in config
            if key.endswith("_sha256")
        },
        "period": {**period, "issue_days": int(len(issue_days))},
        "protocol": {
            "branches": list(SLIP_RATE_BRANCHES),
            "observed_mass": "event ETAS-background posterior times branch-aware fault probability",
            "expected_mass": "analytical direct-background cell rate times the same branch-aware fault probability",
            "off_fault_mass_retained": True,
            "geometry": geometry_config,
        },
        "output": {
            "path": str(output),
            "git_policy": "ignored_generated_data",
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
        },
        "results": {
            "sections": section_count,
            "branches": branch_count,
            "observed_total_root_mass_by_branch": observed_total.tolist(),
            "expected_daily_total_root_mass_by_branch": expected_total.tolist(),
            "expected_period_total_root_mass_by_branch": (expected_total * len(issue_days)).tolist(),
            "observed_mass_conservation_max_abs_error": float(
                np.max(np.abs(observed_total - posterior_total))
            ),
            "expected_mass_conservation_max_abs_error": float(
                np.max(np.abs(expected_total - background_total))
            ),
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(f"prepared {len(issue_days)} CH-003 compensator days at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
