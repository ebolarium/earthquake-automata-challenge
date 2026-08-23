#!/usr/bin/env python3
"""Run the pre-registered CH-009 all-history development benchmark."""

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
sys.path.insert(0, str(ROOT / "scripts"))

from etas_challenge.phase_coherent_debt_ablation_fit import (  # noqa: E402
    PhaseCoherentDebtAblationFitEvaluator,
)
from etas_challenge.training_matrix import sha256_file  # noqa: E402
from evaluate_ch004_validation import build_evaluator  # noqa: E402

EPOCH = np.datetime64("1970-01-01", "D")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch009-phase-coherent-fit-v1.json"),
    )
    return parser.parse_args()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def require_clean_commit(config: dict, config_path: Path) -> str:
    status = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    )
    if status:
        raise RuntimeError("CH-009 fit requires a clean committed worktree")
    required = {str(config_path), "scripts/fit_ch009_phase_coherent_debt.py"}
    tracked = set(
        subprocess.check_output(
            ["git", "ls-files", *required], cwd=ROOT, text=True
        ).splitlines()
    )
    if tracked != required:
        raise RuntimeError("CH-009 fit protocol must be committed before scoring")
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


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
            raise ValueError(f"unsupported CH-009 parameter scale: {scale}")
    return np.vstack((np.asarray(config["control_parameters"], dtype=float), values))


def annual_summary(delta: np.ndarray, event_days: np.ndarray) -> tuple[float, dict[int, float]]:
    years = (EPOCH + event_days.astype("timedelta64[D]")).astype("datetime64[Y]")
    years = years.astype(int) + 1970
    annual = {
        int(year): float(np.mean(delta[years == year])) for year in np.unique(years)
    }
    values = np.asarray(list(annual.values()))
    return float(np.mean(values) - np.std(values)), annual


def candidate_summary(
    result,
    control,
    low_mask: np.ndarray,
    magnitude_mask: np.ndarray,
) -> dict:
    delta = result.event_gains - control.event_gains
    robust, annual = annual_summary(delta, result.event_days)
    return {
        "mean_delta_igpe": float(np.mean(delta)),
        "robust_annual_delta_igpe": robust,
        "low_etas_delta_igpe": float(np.mean(delta[low_mask])),
        "magnitude_gte_3_5_delta_igpe": float(np.mean(delta[magnitude_mask])),
        "positive_years": int(sum(value > 0 for value in annual.values())),
        "worst_annual_delta_igpe": float(min(annual.values())),
        "annual_delta_igpe": annual,
        "phase_active_issue_days": result.phase_active_issue_days,
    }


def main() -> int:
    args = parse_args()
    config_path = args.config
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["status"] != "pre_registered_unrun":
        raise ValueError("CH-009 fit config is not an unrun preregistration")
    if config["period"] != {
        "warmup_start": "2007-01-01",
        "scoring_start": "2014-01-07",
        "end_exclusive": "2026-08-19",
        "historical_outcomes_known": True,
        "prospective_evidence": False,
    }:
        raise ValueError("CH-009 development period differs from preregistration")
    lock_commit = require_clean_commit(config, config_path)
    for path_key, hash_key in config["locked_files"]:
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-009 locked input changed: {path_key}")

    with np.load(config["event_history"], allow_pickle=False) as source:
        history = {name: source[name].copy() for name in source.files}
    scoring_start_day = int(
        (np.datetime64(config["period"]["scoring_start"], "D") - EPOCH)
        / np.timedelta64(1, "D")
    )
    history["scoring_start_day"] = np.asarray(scoring_start_day, dtype=np.int32)
    base = build_evaluator(config, history)
    evaluator = PhaseCoherentDebtAblationFitEvaluator(base)

    parent_model = json.loads(Path(config["parent_model"]).read_text())
    parent_config = json.loads(Path(config["parent_fit_config"]).read_text())
    parent_values = np.asarray(
        [parent_model["parameters"][name] for name in parent_config["parameter_order"]]
    )
    control_model = json.loads(Path(config["control_model"]).read_text())
    control_config = json.loads(Path(config["control_fit_config"]).read_text())
    frailty_values = np.asarray(
        [control_model["parameters"][name] for name in control_config["parameter_order"]]
    )
    candidates = transformed_candidates(config)
    control = evaluator.evaluate(
        parent_values, frailty_values, np.asarray(config["control_parameters"])
    )
    scored_start = base.scoring_event_start
    etas_rates = history["etas_rates"][scored_start:]
    magnitudes = history["magnitudes"][scored_start:]
    control_fit = json.loads(Path(config["control_fit_manifest"]).read_text())
    low_mask = etas_rates <= float(control_fit["result"]["low_etas_threshold"])
    magnitude_mask = magnitudes >= 3.5
    event_issue_day_count = len(np.unique(control.event_days))
    gate = config["admission_rule"]
    names = config["parameter_order"]
    years = list(range(2014, 2027))
    evaluations = []
    rows = []

    for candidate_id, values in enumerate(candidates):
        started = time.monotonic()
        result = control if candidate_id == 0 else evaluator.evaluate(
            parent_values, frailty_values, values
        )
        summary = candidate_summary(result, control, low_mask, magnitude_mask)
        active_fraction = summary["phase_active_issue_days"] / event_issue_day_count
        admitted = (
            candidate_id > 0
            and summary["mean_delta_igpe"] > gate["minimum_mean_delta_igpe"]
            and summary["robust_annual_delta_igpe"] > gate["minimum_robust_annual_delta_igpe"]
            and summary["low_etas_delta_igpe"] >= gate["minimum_low_etas_delta_igpe"]
            and summary["magnitude_gte_3_5_delta_igpe"]
            >= gate["minimum_magnitude_gte_3_5_delta_igpe"]
            and summary["positive_years"] >= gate["minimum_positive_years"]
            and summary["worst_annual_delta_igpe"] >= gate["worst_annual_delta_floor"]
            and active_fraction >= gate["minimum_phase_active_issue_fraction"]
        )
        elapsed = time.monotonic() - started
        rows.append(
            {
                "candidate_id": candidate_id,
                **{name: format(float(value), ".12g") for name, value in zip(names, values)},
                **{
                    key: format(value, ".12g") if isinstance(value, float) else value
                    for key, value in summary.items()
                    if key != "annual_delta_igpe"
                },
                "phase_active_issue_fraction": format(active_fraction, ".12g"),
                **{
                    f"delta_{year}": format(summary["annual_delta_igpe"][year], ".12g")
                    for year in years
                },
                "admitted": str(admitted).lower(),
                "elapsed_seconds": format(elapsed, ".6f"),
            }
        )
        evaluations.append((summary, admitted, result))
        print(
            f"candidate={candidate_id:02d} delta={summary['mean_delta_igpe']:+.6f} "
            f"robust={summary['robust_annual_delta_igpe']:+.6f} "
            f"low={summary['low_etas_delta_igpe']:+.6f} admitted={admitted} "
            f"elapsed={elapsed:.2f}s",
            flush=True,
        )

    admitted_ids = [index for index, item in enumerate(evaluations) if item[1]]
    selected_id = (
        max(admitted_ids, key=lambda index: evaluations[index][0]["robust_annual_delta_igpe"])
        if admitted_ids
        else 0
    )
    selected_summary, selected_admitted, selected_result = evaluations[selected_id]
    selected_values = candidates[selected_id]
    ablation_results = {}
    mechanism_supported = False
    if selected_id > 0:
        for ablation in config["required_ablations"]:
            result = evaluator.evaluate(
                parent_values,
                frailty_values,
                selected_values,
                ablation=ablation,
            )
            ablation_results[ablation] = candidate_summary(
                result, control, low_mask, magnitude_mask
            )
        mechanism_supported = all(
            selected_summary["mean_delta_igpe"]
            > result["mean_delta_igpe"] + gate["minimum_full_minus_ablation_delta"]
            for result in ablation_results.values()
        )

    candidate_path = Path(config["candidate_output"])
    fields = [
        "candidate_id",
        *names,
        "mean_delta_igpe",
        "robust_annual_delta_igpe",
        "low_etas_delta_igpe",
        "magnitude_gte_3_5_delta_igpe",
        "positive_years",
        "worst_annual_delta_igpe",
        "phase_active_issue_days",
        "phase_active_issue_fraction",
        *(f"delta_{year}" for year in years),
        "admitted",
        "elapsed_seconds",
    ]
    write_rows(candidate_path, rows, fields)
    final_admission = bool(selected_admitted and mechanism_supported)
    model = {
        "schema_version": 1,
        "model_id": config["model_id"],
        "status": "development_fit_completed",
        "fit_lock_commit": lock_commit,
        "control_model_id": control_model["model_id"],
        "selected_candidate_id": selected_id,
        "parameters": {name: float(value) for name, value in zip(names, selected_values)},
        "development_scores": selected_summary,
        "ablation_scores": ablation_results,
        "mechanism_supported": mechanism_supported,
        "prospective_freeze_admitted": final_admission,
        "claim_boundary": config["claim_boundary"],
    }
    model_path = Path(config["model_output"])
    atomic_json(model_path, model)
    manifest = {
        "schema_version": 1,
        "fit_id": config["fit_id"],
        "status": "development_fit_completed",
        "tool": {
            "name": "scripts/fit_ch009_phase_coherent_debt.py",
            "script_sha256": sha256_file(Path(__file__)),
            "evaluator_sha256": sha256_file(Path(config["ablation_evaluator_module"])),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "repository": {"fit_lock_commit": lock_commit},
        "inputs": {
            "config_sha256": sha256_file(config_path),
            **{key: config[key] for key in config if key.endswith("_sha256")},
        },
        "protocol": {
            **config["candidate_protocol"],
            "candidate_count_including_control": len(candidates),
            "admission_rule": gate,
            "required_ablations": config["required_ablations"],
        },
        "period": {
            **config["period"],
            "events": len(control.event_gains),
            "event_issue_days": event_issue_day_count,
        },
        "result": {
            "selected_candidate_id": selected_id,
            "selected_candidate_admitted": bool(selected_admitted),
            "selected_summary": selected_summary,
            "ablation_results": ablation_results,
            "mechanism_supported": mechanism_supported,
            "admit_prospective_freeze": final_admission,
        },
        "outputs": {
            "model": str(model_path),
            "model_sha256": sha256_file(model_path),
            "candidates": str(candidate_path),
            "candidates_sha256": sha256_file(candidate_path),
        },
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["fit_manifest"]), manifest)
    print(
        f"selected candidate {selected_id}: "
        f"delta={selected_summary['mean_delta_igpe']:+.6f}, "
        f"mechanism_supported={mechanism_supported}, "
        f"prospective_freeze_admitted={final_admission}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
