#!/usr/bin/env python3
"""Compare zero and equilibrium-ensemble initialization for locked CH-004."""

from __future__ import annotations

import argparse
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

from etas_challenge.emergence_fit import annual_robust_score  # noqa: E402
from etas_challenge.renewal_quiescence import equilibrium_hazard_age_ensemble  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402
from scripts.evaluate_ch004_validation import build_evaluator  # noqa: E402

EPOCH = np.datetime64("1970-01-01", "D")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch005-equilibrium-fit-v1.json"),
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
        raise ValueError("CH-005 evaluation requires a clean committed repository")
    required = {
        str(config_path),
        config["parent_model"],
        config["parent_fit_manifest"],
        config["event_history_manifest"],
        "scripts/evaluate_ch005_equilibrium_ablation.py",
    }
    if set(git_output("ls-files", *sorted(required)).splitlines()) != required:
        raise ValueError("CH-005 protocol and locked inputs must be committed")
    lock_commit = config["parent_model_lock_commit"]
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", lock_commit, "HEAD"],
        cwd=ROOT,
        check=True,
    )
    committed = subprocess.check_output(
        ["git", "show", f"{lock_commit}:{config['parent_model']}"], cwd=ROOT
    )
    if hashlib.sha256(committed).hexdigest() != config["parent_model_sha256"]:
        raise ValueError("CH-005 parent model differs from its lock commit")
    return git_output("rev-parse", "HEAD")


def summarize(gains: np.ndarray, masks: dict[str, np.ndarray]) -> dict:
    return {
        name: {
            "events": int(np.count_nonzero(mask)),
            "igpe": float(np.mean(gains[mask])),
            "relative_factor": math.exp(float(np.mean(gains[mask]))),
        }
        for name, mask in masks.items()
    }


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    config_path = args.config.resolve().relative_to(ROOT)
    if (
        config["stage"] != "fit_ablation"
        or config["period"]["scoring_start"] != "2014-01-07"
        or config["period"]["end_exclusive"] != "2019-01-01"
        or config["period"]["development_validation_opened"] is not False
        or config["period"]["locked_retrospective_opened"] is not False
    ):
        raise ValueError("CH-005 fit ablation violates the frozen split")
    evaluation_commit = require_committed_gate(config, config_path)
    for path_key, hash_key in config["locked_files"]:
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-005 locked input changed: {path_key}")

    model = json.loads(Path(config["parent_model"]).read_text())
    fit_manifest = json.loads(Path(config["parent_fit_manifest"]).read_text())
    fit_config = json.loads(Path(config["parent_fit_config"]).read_text())
    with np.load(config["event_history"], allow_pickle=False) as source:
        history = {name: source[name].copy() for name in source.files}
    evaluator = build_evaluator(config, history)
    parameter_values = np.asarray(
        [model["parameters"][name] for name in fit_config["parameter_order"]]
    )
    zero = evaluator.evaluate(parameter_values)
    initialization = config["initialization"]
    initial_ages = equilibrium_hazard_age_ensemble(
        evaluator.active,
        initialization["ensemble_size"],
        initialization["seed"],
    )
    ensemble = evaluator.evaluate_initial_age_ensemble(parameter_values, initial_ages)
    difference = ensemble.event_gains - zero.event_gains

    scoring_start = int(history["scoring_start_day"])
    event_start = int(np.searchsorted(history["event_issue_days"], scoring_start))
    magnitudes = history["magnitudes"][event_start:]
    etas_rates = history["etas_rates"][event_start:]
    low_threshold = float(fit_manifest["result"]["low_etas_threshold"])
    masks = {
        "primary": np.ones(len(zero.event_gains), dtype=bool),
        "low_etas": etas_rates <= low_threshold,
        "m_gte_3_5": magnitudes >= 3.5,
        "m_gte_4_0": magnitudes >= 4.0,
    }
    zero_summary = summarize(zero.event_gains, masks)
    ensemble_summary = summarize(ensemble.event_gains, masks)
    difference_summary = summarize(difference, masks)
    robust_difference, annual_difference = annual_robust_score(
        difference, zero.event_days
    )
    _, annual_zero = annual_robust_score(zero.event_gains, zero.event_days)
    _, annual_ensemble = annual_robust_score(
        ensemble.event_gains, ensemble.event_days
    )
    admission = {
        "positive_primary_delta": difference_summary["primary"]["igpe"] > 0,
        "nonnegative_robust_annual_delta": robust_difference >= 0,
        "nonnegative_low_etas_delta": difference_summary["low_etas"]["igpe"] >= 0,
    }
    admission["admit_development_validation"] = all(admission.values())
    manifest = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "status": "fit_ablation_completed",
        "tool": {
            "name": "scripts/evaluate_ch005_equilibrium_ablation.py",
            "script_sha256": sha256_file(Path(__file__)),
            "renewal_fit_sha256": sha256_file(ROOT / "src/etas_challenge/renewal_fit.py"),
            "renewal_quiescence_sha256": sha256_file(
                ROOT / "src/etas_challenge/renewal_quiescence.py"
            ),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "repository": {
            "parent_model_lock_commit": config["parent_model_lock_commit"],
            "evaluation_code_commit": evaluation_commit,
        },
        "inputs": {
            "config_sha256": sha256_file(args.config),
            **{key: config[key] for key in config if key.endswith("_sha256")},
        },
        "period": config["period"],
        "initialization": {
            **initialization,
            "distribution": "unit_exponential_stationary_memoryless_hazard_age",
            "stratification": "mid_quantiles_with_section_specific_cyclic_phases",
            "mean_initial_age": float(np.mean(initial_ages[:, evaluator.active])),
        },
        "results": {
            "zero_initialization": zero_summary,
            "equilibrium_ensemble": ensemble_summary,
            "paired_delta_ensemble_minus_zero": difference_summary,
            "annual_primary_igpe": {
                "zero": {str(key): value for key, value in annual_zero.items()},
                "ensemble": {str(key): value for key, value in annual_ensemble.items()},
                "delta": {str(key): value for key, value in annual_difference.items()},
            },
            "robust_annual_delta": robust_difference,
        },
        "diagnostics": {
            "member_active_issue_days": ensemble.member_active_issue_days.tolist(),
            "changed_mixture_event_rates": int(
                np.count_nonzero(
                    ensemble.challenger_event_rates != zero.challenger_event_rates
                )
            ),
            "maximum_absolute_paired_delta": float(np.max(np.abs(difference))),
        },
        "admission": admission,
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(json.dumps({"results": manifest["results"], "admission": admission}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
