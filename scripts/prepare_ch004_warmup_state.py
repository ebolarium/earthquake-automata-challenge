#!/usr/bin/env python3
"""Build unscored CH-004 renewal-age anchors at the fit scoring boundary."""

from __future__ import annotations

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
from etas_challenge.readiness_replay import branch_loading_vector
from etas_challenge.renewal_quiescence import bpt_overdue_score
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight
from etas_challenge.renewal_quiescence import update_expected_hazard_age
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.training_matrix import GridDefinition, sha256_file, write_deterministic_npz
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    config_path = Path("configs/challenge/ch004-warmup-state-v1.json")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for path_key, hash_key in (
        ("component_contract", "component_contract_sha256"),
        ("event_history_manifest", "event_history_manifest_sha256"),
        ("event_history", "event_history_sha256"),
        ("fault_graph", "fault_graph_sha256"),
        ("fault_grid", "fault_grid_sha256"),
        ("fault_sections", "fault_sections_sha256"),
        ("grid", "grid_sha256"),
        ("simulation_config", "simulation_config_sha256"),
    ):
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-004 warmup locked input changed: {path_key}")

    with np.load(config["event_history"], allow_pickle=False) as source:
        history = {name: source[name].copy() for name in source.files}
    with np.load(config["fault_graph"], allow_pickle=False) as source:
        section_ids = source["section_ids"].copy()
    with np.load(config["fault_grid"], allow_pickle=False) as source:
        grid_ids = source["nearest_section_ids"].copy()
        grid_distances = source["nearest_trace_distances_km"].copy()
    scoring_start = int(history["scoring_start_day"])
    warmup_days = history["all_issue_days"][history["all_issue_days"] < scoring_start]
    event_end = int(np.searchsorted(history["event_issue_days"], scoring_start, side="left"))
    if np.any(history["event_issue_days"][:event_end] >= scoring_start):
        raise ValueError("warmup event boundary is not strict")

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
    geometry = config["geometry"]
    if grid_ids.shape[1] != geometry["neighbors"]:
        raise ValueError("CH-004 grid neighbor count changed")
    branch_active = []
    expected_background = []
    event_geometries = []
    for branch in SLIP_RATE_BRANCHES:
        _, active = branch_loading_vector(sections, branch)
        branch_active.append(active)
        grid_geometry = sparse_geometry(
            grid_ids,
            grid_distances,
            section_ids,
            active,
            bandwidth_km=geometry["bandwidth_km"],
            cutoff_km=geometry["cutoff_km"],
            fault_prior_odds=geometry["fault_prior_odds"],
        )
        section_mass, _ = aggregate_sparse_section_mass(
            background, grid_geometry, len(section_ids)
        )
        expected_background.append(section_mass)
        event_geometries.append(
            sparse_geometry(
                history["nearest_fault_section_ids"][:event_end],
                history["nearest_fault_distances_km"][:event_end],
                section_ids,
                active,
                bandwidth_km=geometry["bandwidth_km"],
                cutoff_km=geometry["cutoff_km"],
                fault_prior_odds=geometry["fault_prior_odds"],
            )
        )
    branch_active = np.asarray(branch_active)
    expected_background = np.asarray(expected_background)

    anchor_ages = []
    anchor_scores = []
    anchor_expectations = []
    for anchor in config["anchors"]:
        expected_mark = expected_reset_weight_gr(
            simulation["beta"],
            simulation["m_ref"],
            anchor["full_reset_magnitude"],
            anchor["magnitude_exponent"],
        )
        expected_hazard = expected_background * expected_mark
        marks = magnitude_reset_weight(
            history["magnitudes"][:event_end],
            anchor["full_reset_magnitude"],
            anchor["magnitude_exponent"],
        )
        marked_roots = history["etas_background_probabilities"][:event_end] * marks
        age = np.zeros_like(expected_hazard)
        for day in warmup_days:
            start = int(np.searchsorted(history["event_issue_days"][:event_end], day, side="left"))
            end = int(np.searchsorted(history["event_issue_days"][:event_end], day, side="right"))
            observed = np.zeros_like(age)
            if end > start:
                for branch, event_geometry in enumerate(event_geometries):
                    day_geometry = SparseGeometry(
                        event_geometry.section_indexes[start:end],
                        event_geometry.probabilities[start:end],
                    )
                    observed[branch], _ = aggregate_sparse_section_mass(
                        marked_roots[start:end], day_geometry, len(section_ids)
                    )
            age = update_expected_hazard_age(age, expected_hazard, observed)
        anchor_expectations.append(expected_mark)
        anchor_ages.append(age)
        anchor_scores.append(bpt_overdue_score(age, config["diagnostic_bpt_aperiodicity"]))

    anchor_ages = np.asarray(anchor_ages)
    anchor_scores = np.asarray(anchor_scores)
    output = Path(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    write_deterministic_npz(
        output,
        {
            "section_ids": section_ids,
            "branch_names": np.asarray(SLIP_RATE_BRANCHES),
            "active_sections": branch_active,
            "anchor_full_reset_magnitude": np.asarray(
                [item["full_reset_magnitude"] for item in config["anchors"]]
            ),
            "anchor_magnitude_exponent": np.asarray(
                [item["magnitude_exponent"] for item in config["anchors"]]
            ),
            "anchor_expected_reset_weight": np.asarray(anchor_expectations),
            "warmup_end_hazard_age": anchor_ages,
            "warmup_end_overdue_score": anchor_scores,
            "scoring_start_day": np.asarray(scoring_start, dtype=np.int32),
            "config_sha256": np.asarray(sha256_file(config_path)),
        },
    )
    diagnostics = []
    for anchor_index, anchor in enumerate(config["anchors"]):
        selected_age = anchor_ages[anchor_index][branch_active]
        selected_score = anchor_scores[anchor_index][branch_active]
        diagnostics.append(
            {
                **anchor,
                "expected_reset_weight": anchor_expectations[anchor_index],
                "active_age_percentiles": {
                    str(percentile): float(np.percentile(selected_age, percentile))
                    for percentile in (0, 25, 50, 75, 90, 95, 99, 100)
                },
                "active_overdue_fraction": float(np.mean(selected_score > 0)),
                "active_overdue_score_max": float(np.max(selected_score)),
            }
        )
    manifest = {
        "schema_version": 1,
        "dataset_id": config["dataset_id"],
        "status": "completed_unscored_warmup_anchors",
        "tool": {
            "name": "scripts/prepare_ch004_warmup_state.py",
            "script_sha256": sha256_file(Path(__file__)),
            "renewal_module_sha256": sha256_file(ROOT / "src/etas_challenge/renewal_quiescence.py"),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "inputs": {key: config[key] for key in config if key.endswith("_sha256")},
        "protocol": {
            "warmup_start_day": int(warmup_days[0]),
            "warmup_end_exclusive_day": scoring_start,
            "warmup_days": int(len(warmup_days)),
            "warmup_events": event_end,
            "forecast_before_same_day_reset": True,
            "anchors_selected": False,
            "diagnostic_bpt_aperiodicity": config["diagnostic_bpt_aperiodicity"],
            "geometry": geometry,
        },
        "output": {
            "path": str(output),
            "git_policy": "ignored_generated_data",
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
        },
        "results": {"anchor_diagnostics": diagnostics},
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(f"prepared {len(config['anchors'])} CH-004 warmup anchors at {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
