#!/usr/bin/env python3
"""Fit the pre-registered CH-006 discounted frailty-renewal challenger."""

from __future__ import annotations

import csv
import argparse
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
sys.path.insert(0, str(ROOT / "scripts"))

from etas_challenge.emergence_fit import annual_robust_score  # noqa: E402
from etas_challenge.frailty_renewal_fit import FrailtyRenewalFitEvaluator  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402
from evaluate_ch004_validation import build_evaluator  # noqa: E402


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def clean_lock_commit(challenger_name: str) -> str:
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    )
    if status:
        raise RuntimeError(f"{challenger_name} fit requires a clean committed worktree")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def transformed_candidates(config: dict) -> np.ndarray:
    protocol = config["candidate_protocol"]
    bounds = np.asarray(config["parameter_bounds"], dtype=float)
    sampler = qmc.Sobol(d=len(bounds), scramble=True, seed=protocol["seed"])
    unit = sampler.random_base2(m=protocol["sobol_power"])
    values = np.empty_like(unit)
    for column, scale in enumerate(config["parameter_scales"]):
        low, high = bounds[column]
        if scale == "linear":
            values[:, column] = low + unit[:, column] * (high - low)
        elif scale == "log10":
            values[:, column] = 10.0 ** (
                math.log10(low) + unit[:, column] * (math.log10(high) - math.log10(low))
            )
        else:
            raise ValueError(f"unsupported CH-006 parameter scale: {scale}")
    return np.vstack((np.asarray(config["parent_control_parameters"], dtype=float), values))


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch006-frailty-renewal-fit-v1.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = args.config
    config = json.loads(config_path.read_text(encoding="utf-8"))
    challenger_name = config.get("challenger_name", "CH-006")
    if config["period"] != {
        "warmup_start": "2007-01-01",
        "scoring_start": "2014-01-07",
        "end_exclusive": "2019-01-01",
        "warmup_scored": False,
        "development_validation_opened": False,
        "locked_retrospective_opened": False,
    }:
        raise ValueError(f"{challenger_name} fit period violates the pre-registered boundary")
    lock_commit = clean_lock_commit(challenger_name)
    for path_key, hash_key in config["locked_files"]:
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"{challenger_name} locked input changed: {path_key}")

    with np.load(config["event_history"], allow_pickle=False) as source:
        history = {name: source[name].copy() for name in source.files}
    base = build_evaluator(config, history)
    evaluator = FrailtyRenewalFitEvaluator(base)
    parent_model = json.loads(Path(config["parent_model"]).read_text())
    parent_fit = json.loads(Path(config["parent_fit_manifest"]).read_text())
    parent_fit_config = json.loads(Path(config["parent_fit_config"]).read_text())
    parent_values = np.asarray(
        [parent_model["parameters"][name] for name in parent_fit_config["parameter_order"]]
    )
    candidates = transformed_candidates(config)
    scored_etas = history["etas_rates"][
        history["event_issue_days"] >= int(history["scoring_start_day"])
    ]
    low_threshold = float(parent_fit["result"]["low_etas_threshold"])
    low_mask = scored_etas <= low_threshold
    names = config["parameter_order"]
    rows = []
    evaluations = []
    years = range(2014, 2019)
    gate = config["admission_rule"]
    minimum_mean = (
        parent_fit["result"]["mean_igpe"] * gate["minimum_parent_igpe_factor"]
    )
    minimum_robust = parent_fit["result"]["robust_annual_igpe"]
    minimum_low = parent_fit["result"]["low_etas_igpe"]

    for candidate_id, values in enumerate(candidates):
        started = time.monotonic()
        result = evaluator.evaluate(parent_values, values)
        mean_igpe = float(np.mean(result.event_gains))
        robust, annual = annual_robust_score(result.event_gains, result.event_days)
        low_igpe = float(np.mean(result.event_gains[low_mask]))
        admitted = (
            candidate_id > 0
            and mean_igpe >= minimum_mean
            and robust >= minimum_robust
            and low_igpe >= minimum_low
            and min(annual.values()) >= gate["annual_loss_floor"]
        )
        elapsed = time.monotonic() - started
        rows.append(
            {
                "candidate_id": candidate_id,
                **{name: format(float(value), ".12g") for name, value in zip(names, values)},
                "mean_igpe": format(mean_igpe, ".12g"),
                "robust_annual_igpe": format(robust, ".12g"),
                "low_etas_igpe": format(low_igpe, ".12g"),
                **{f"igpe_{year}": format(annual[year], ".12g") for year in years},
                "active_issue_days": result.active_issue_days,
                "admitted": str(admitted).lower(),
                "elapsed_seconds": format(elapsed, ".6f"),
            }
        )
        evaluations.append((robust, mean_igpe, low_igpe, annual, admitted, result))
        print(
            f"candidate={candidate_id:02d} mean={mean_igpe:+.6f} "
            f"robust={robust:+.6f} low={low_igpe:+.6f} admitted={admitted} "
            f"elapsed={elapsed:.2f}s",
            flush=True,
        )

    admitted_ids = [index for index, item in enumerate(evaluations) if item[4]]
    selected_id = (
        max(admitted_ids, key=lambda index: evaluations[index][0])
        if admitted_ids
        else 0
    )
    robust, mean_igpe, low_igpe, annual, admitted, result = evaluations[selected_id]
    selected_values = candidates[selected_id]
    candidate_path = Path(config["candidate_output"])
    write_rows(
        candidate_path,
        rows,
        [
            "candidate_id",
            *names,
            "mean_igpe",
            "robust_annual_igpe",
            "low_etas_igpe",
            *(f"igpe_{year}" for year in years),
            "active_issue_days",
            "admitted",
            "elapsed_seconds",
        ],
    )
    model = {
        "schema_version": 1,
        "model_id": config.get("model_id", "ch006-discounted-frailty-renewal-v1"),
        "status": "fit_locked_validation_unseen",
        "fit_lock_commit": lock_commit,
        "parent_model_id": parent_model["model_id"],
        "selected_candidate_id": selected_id,
        "selected_nonzero_candidate": bool(admitted),
        "parameters": {name: float(value) for name, value in zip(names, selected_values)},
        "fit_scores": {
            "mean_igpe": mean_igpe,
            "relative_factor": math.exp(mean_igpe),
            "parent_mean_igpe": parent_fit["result"]["mean_igpe"],
            "parent_igpe_factor": mean_igpe / parent_fit["result"]["mean_igpe"],
            "robust_annual_igpe": robust,
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
            "name": "scripts/fit_ch006_frailty_renewal.py",
            "script_sha256": sha256_file(Path(__file__)),
            "module_sha256": sha256_file(Path(config["frailty_renewal_module"])),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "protocol": {
            **config["candidate_protocol"],
            "fit_lock_commit": lock_commit,
            "candidate_count": len(candidates),
            "admission_rule": gate,
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
            "selected_candidate_id": selected_id,
            "selected_nonzero_candidate": bool(admitted),
            "events": len(result.event_gains),
            "low_etas_events": int(np.count_nonzero(low_mask)),
            "low_etas_threshold": low_threshold,
            "mean_igpe": mean_igpe,
            "parent_mean_igpe": parent_fit["result"]["mean_igpe"],
            "parent_igpe_factor": mean_igpe / parent_fit["result"]["mean_igpe"],
            "robust_annual_igpe": robust,
            "low_etas_igpe": low_igpe,
            "annual_igpe": {str(year): value for year, value in annual.items()},
            "admit_development_validation": bool(admitted),
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["fit_manifest"]), manifest)
    print(
        f"selected candidate {selected_id}: mean={mean_igpe:+.6f}, "
        f"parent_factor={model['fit_scores']['parent_igpe_factor']:.3f}, "
        f"validation_admitted={admitted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
