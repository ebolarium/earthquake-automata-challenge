#!/usr/bin/env python3
"""Score the fit-locked CH-004 model on 2019-2022 validation data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.challenger import stationary_block_bootstrap_igpe  # noqa: E402
from etas_challenge.grid_forecast import analytical_background_rates  # noqa: E402
from etas_challenge.readiness_fit import sparse_geometry  # noqa: E402
from etas_challenge.readiness_replay import branch_loading_vector  # noqa: E402
from etas_challenge.renewal_fit import RenewalFitEvaluator  # noqa: E402
from etas_challenge.residual_emergence import aggregate_sparse_section_mass  # noqa: E402
from etas_challenge.training_matrix import GridDefinition, sha256_file  # noqa: E402
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES  # noqa: E402

EPOCH = np.datetime64("1970-01-01", "D")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch004-validation-v1.json"),
    )
    return parser.parse_args()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def require_committed_gate(config: dict, config_path: Path) -> str:
    if git_output("status", "--porcelain"):
        raise ValueError("CH-004 validation requires a clean committed repository")
    required = [
        str(config_path),
        config["model"],
        config["fit_manifest"],
        config["fit_config"],
        config["event_history_manifest"],
        "scripts/evaluate_ch004_validation.py",
    ]
    tracked = set(git_output("ls-files", *required).splitlines())
    if tracked != set(required):
        raise ValueError("CH-004 validation protocol and locked inputs must be committed")
    lock_commit = config["model_lock_commit"]
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", lock_commit, "HEAD"],
        cwd=ROOT,
        check=True,
    )
    for path_key, hash_key in (("model", "model_sha256"), ("fit_manifest", "fit_manifest_sha256")):
        committed = subprocess.check_output(
            ["git", "show", f"{lock_commit}:{config[path_key]}"], cwd=ROOT
        )
        if hashlib.sha256(committed).hexdigest() != config[hash_key]:
            raise ValueError(f"{path_key} differs from the pre-validation lock")
    return git_output("rev-parse", "HEAD")


def build_evaluator(config: dict, history: dict) -> RenewalFitEvaluator:
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
        raise ValueError("CH-004 validation grid neighbor count changed")
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
    return RenewalFitEvaluator(
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


def daily_vectors(days: np.ndarray, gains: np.ndarray, mask: np.ndarray, all_days: np.ndarray):
    daily_gain = np.zeros(len(all_days), dtype=float)
    daily_count = np.zeros(len(all_days), dtype=np.int64)
    indexes = np.searchsorted(all_days, days[mask])
    np.add.at(daily_gain, indexes, gains[mask])
    np.add.at(daily_count, indexes, 1)
    return daily_gain, daily_count


def summarize(gain: np.ndarray, count: np.ndarray, bootstrap: dict, seed_offset: int) -> dict:
    event_count = int(np.sum(count))
    total_gain = float(np.sum(gain))
    result = {
        "target_events": event_count,
        "information_gain": total_gain,
        "information_gain_per_event": total_gain / event_count,
        "relative_factor": math.exp(total_gain / event_count),
        "positive_gain_days": int(np.count_nonzero(gain > 0)),
        "negative_gain_days": int(np.count_nonzero(gain < 0)),
        "bootstrap": {},
    }
    for block in bootstrap["mean_block_days"]:
        result["bootstrap"][f"{block}_days"] = stationary_block_bootstrap_igpe(
            gain,
            count,
            replicates=bootstrap["replicates"],
            mean_block_days=block,
            seed=bootstrap["seed"] + seed_offset + block,
            confidence_level=bootstrap["confidence_level"],
        )
    return result


def write_daily(path: Path, days: np.ndarray, vectors: dict[str, tuple[np.ndarray, np.ndarray]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fields = ["issue_date"]
    for name in vectors:
        fields.extend((f"{name}_event_count", f"{name}_paired_gain"))
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for index, day in enumerate(days):
            row = {"issue_date": np.datetime_as_string(EPOCH + np.timedelta64(int(day), "D"))}
            for name, (gain, count) in vectors.items():
                row[f"{name}_event_count"] = int(count[index])
                row[f"{name}_paired_gain"] = format(float(gain[index]), ".12g")
            writer.writerow(row)
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    config_path = args.config.resolve().relative_to(ROOT)
    period = config["period"]
    if (
        period["start"] != "2019-01-01"
        or period["end_exclusive"] != "2023-01-01"
        or period["development_validation_opened"] is not True
        or period["locked_retrospective_opened"] is not False
    ):
        raise ValueError("CH-004 validation period violates the frozen contract")
    evaluation_commit = require_committed_gate(config, config_path)
    for path_key, hash_key in (
        ("model", "model_sha256"),
        ("fit_manifest", "fit_manifest_sha256"),
        ("fit_config", "fit_config_sha256"),
        ("event_history_manifest", "event_history_manifest_sha256"),
        ("event_history", "event_history_sha256"),
        ("fault_graph", "fault_graph_sha256"),
        ("fault_grid", "fault_grid_sha256"),
        ("fault_sections", "fault_sections_sha256"),
        ("grid", "grid_sha256"),
        ("simulation_config", "simulation_config_sha256"),
    ):
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-004 validation locked input changed: {path_key}")

    model = json.loads(Path(config["model"]).read_text())
    fit_manifest = json.loads(Path(config["fit_manifest"]).read_text())
    history_manifest = json.loads(Path(config["event_history_manifest"]).read_text())
    if model["status"] != "fit_locked_validation_unseen":
        raise ValueError("CH-004 model is not validation-unseen")
    if fit_manifest["protocol"]["development_validation_opened"] is not False:
        raise ValueError("CH-004 fit did not preserve the validation gate")
    if history_manifest["period"]["locked_retrospective_opened"] is not False:
        raise ValueError("CH-004 locked retrospective was opened")
    with np.load(config["event_history"], allow_pickle=False) as source:
        history = {name: source[name].copy() for name in source.files}

    parameter_order = list(
        json.loads(Path(config["fit_config"]).read_text())["parameter_order"]
    )
    parameter_values = np.asarray([model["parameters"][name] for name in parameter_order])
    result = build_evaluator(config, history).evaluate(parameter_values)
    scored_start = int(np.searchsorted(history["event_issue_days"], int(history["scoring_start_day"])))
    magnitudes = history["magnitudes"][scored_start:]
    etas_rates = history["etas_rates"][scored_start:]
    all_days = history["all_issue_days"][history["all_issue_days"] >= int(history["scoring_start_day"])]
    low_threshold = float(fit_manifest["result"]["low_etas_threshold"])
    masks = {
        "primary": np.ones(len(result.event_gains), dtype=bool),
        "m_gte_3_5": magnitudes >= 3.5,
        "m_gte_4_0": magnitudes >= 4.0,
        "low_etas": etas_rates <= low_threshold,
    }
    vectors = {
        name: daily_vectors(result.event_days, result.event_gains, mask, all_days)
        for name, mask in masks.items()
    }
    summaries = {
        name: summarize(*vectors[name], config["bootstrap"], index * 1000)
        for index, name in enumerate(vectors)
    }
    annual = {}
    years = (EPOCH + result.event_days.astype("timedelta64[D]")).astype("datetime64[Y]").astype(int) + 1970
    for year in range(2019, 2023):
        annual[str(year)] = float(np.mean(result.event_gains[years == year]))
    primary_igpe = summaries["primary"]["information_gain_per_event"]
    low_igpe = summaries["low_etas"]["information_gain_per_event"]
    daily_path = Path(config["daily_output"])
    write_daily(daily_path, all_days, vectors)
    manifest = {
        "schema_version": 1,
        "evaluation_id": config["evaluation_id"],
        "status": "development_validation_completed",
        "tool": {
            "name": "scripts/evaluate_ch004_validation.py",
            "script_sha256": sha256_file(Path(__file__)),
            "module_sha256": sha256_file(ROOT / "src/etas_challenge/renewal_fit.py"),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "repository": {
            "model_lock_commit": config["model_lock_commit"],
            "evaluation_code_commit": evaluation_commit,
        },
        "inputs": {
            "config_sha256": sha256_file(args.config),
            **{key: config[key] for key in config if key.endswith("_sha256")},
        },
        "period": {**period, "issue_days": len(all_days), "events": len(result.event_gains)},
        "protocol": {
            "baseline": "frozen_etas",
            "low_etas_threshold_rate_per_cell_day": low_threshold,
            "low_etas_threshold_source": "fit_locked_2014_2018_quantile",
            "bootstrap": config["bootstrap"],
            "forecast_boundary": "forecast before same-day observations",
        },
        "count_and_magnitude_invariants": {
            "maximum_daily_expected_count_difference": 0.0,
            "number_test": "identical to frozen ETAS by construction",
            "magnitude_test": "identical to frozen ETAS by construction",
            "pseudolikelihood_gain": "conditional spatial log gain; count and magnitude forecasts unchanged",
        },
        "diagnostics": {
            "active_issue_days": result.active_issue_days,
            "expected_reset_weight": result.expected_reset_weight,
            "changed_event_rates": int(np.count_nonzero(result.challenger_event_rates != etas_rates)),
            "maximum_absolute_event_gain": float(np.max(np.abs(result.event_gains))),
        },
        "results": {**summaries, "annual_primary_igpe": annual},
        "admission": {
            "positive_primary_igpe": primary_igpe > 0,
            "nonnegative_low_etas_igpe": low_igpe >= 0,
            "admit_locked_retrospective": primary_igpe > 0 and low_igpe >= 0,
        },
        "outputs": {
            "daily_paired_scores": str(daily_path),
            "daily_paired_scores_sha256": sha256_file(daily_path),
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(json.dumps({"results": manifest["results"], "admission": manifest["admission"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
