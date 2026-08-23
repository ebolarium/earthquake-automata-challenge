#!/usr/bin/env python3
"""Evaluate the locked CH-007 amplitude ablation on development validation."""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(ROOT / "scripts"))

from etas_challenge.challenger import stationary_block_bootstrap_igpe  # noqa: E402
from etas_challenge.frailty_renewal_fit import FrailtyRenewalFitEvaluator  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402
from evaluate_ch004_validation import build_evaluator, daily_vectors  # noqa: E402

EPOCH = np.datetime64("1970-01-01", "D")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch007-amplified-renewal-validation-v1.json"),
    )
    return parser.parse_args()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def summarize(gains: np.ndarray, days: np.ndarray, all_days: np.ndarray, bootstrap: dict, seed_offset: int) -> dict:
    daily_gain, daily_count = daily_vectors(days, gains, np.ones(len(gains), bool), all_days)
    result = {
        "events": int(np.sum(daily_count)),
        "information_gain": float(np.sum(daily_gain)),
        "information_gain_per_event": float(np.sum(daily_gain) / np.sum(daily_count)),
        "bootstrap": {},
    }
    result["relative_factor"] = math.exp(result["information_gain_per_event"])
    for block in bootstrap["mean_block_days"]:
        result["bootstrap"][f"{block}_days"] = stationary_block_bootstrap_igpe(
            daily_gain,
            daily_count,
            replicates=bootstrap["replicates"],
            mean_block_days=block,
            seed=bootstrap["seed"] + seed_offset + block,
            confidence_level=bootstrap["confidence_level"],
        )
    return result


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text())
    validation_period = {
        "start": "2019-01-01",
        "end_exclusive": "2023-01-01",
        "development_validation_opened": True,
        "locked_retrospective_opened": False,
    }
    retrospective_period = {
        "start": "2023-01-01",
        "end_exclusive": "2026-08-19",
        "development_validation_opened": True,
        "locked_retrospective_opened": True,
    }
    evaluation_role = config.get("evaluation_role", "development_validation")
    if not (
        (evaluation_role == "development_validation" and config["period"] == validation_period)
        or (evaluation_role == "locked_retrospective" and config["period"] == retrospective_period)
    ):
        raise ValueError("CH-007 evaluation period violates the frozen boundary")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True):
        raise ValueError("CH-007 validation requires a clean committed worktree")
    evaluation_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    for path_key, hash_key in config["locked_files"]:
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-007 locked input changed: {path_key}")
    if evaluation_role == "locked_retrospective":
        validation = json.loads(Path(config["validation_manifest"]).read_text())
        if validation["admission"]["ch007_validated"] is not True:
            raise ValueError("CH-007 did not pass development validation")

    with np.load(config["event_history"], allow_pickle=False) as source:
        history = {name: source[name].copy() for name in source.files}
    base = build_evaluator(config, history)
    evaluator = FrailtyRenewalFitEvaluator(base)
    parent_model = json.loads(Path(config["parent_model"]).read_text())
    parent_fit_config = json.loads(Path(config["parent_fit_config"]).read_text())
    parent_values = np.asarray(
        [parent_model["parameters"][name] for name in parent_fit_config["parameter_order"]]
    )
    parameter_order = config["parameter_order"]
    model = json.loads(Path(config["model"]).read_text())
    source_model = json.loads(Path(config["source_model"]).read_text())
    candidate_values = np.asarray([model["parameters"][name] for name in parameter_order])
    source_values = np.asarray([source_model["parameters"][name] for name in parameter_order])
    frailty_only_values = source_values.copy()
    frailty_only_values[parameter_order.index("renewal_weight")] = 0.0

    parent = base.evaluate(parent_values)
    candidate = evaluator.evaluate(parent_values, candidate_values)
    source = evaluator.evaluate(parent_values, source_values)
    frailty_only = evaluator.evaluate(parent_values, frailty_only_values)
    scored_start = base.scoring_event_start
    etas_rates = history["etas_rates"][scored_start:]
    magnitudes = history["magnitudes"][scored_start:]
    parent_fit = json.loads(Path(config["parent_fit_manifest"]).read_text())
    low_mask = etas_rates <= parent_fit["result"]["low_etas_threshold"]
    masks = {
        "primary": np.ones(len(candidate.event_gains), bool),
        "low_etas": low_mask,
        "m_gte_3_5": magnitudes >= 3.5,
        "m_gte_4_0": magnitudes >= 4.0,
    }
    all_days = history["all_issue_days"][
        history["all_issue_days"] >= int(history["scoring_start_day"])
    ]
    bootstrap = config["bootstrap"]
    results = {}
    model_index = 0
    for name, result in (
        ("ch007", candidate),
        ("ch006_full_report_only", source),
        ("ch004_parent", parent),
        ("frailty_only_report_only", frailty_only),
    ):
        results[name] = {
            stratum: summarize(
                result.event_gains[mask],
                result.event_days[mask],
                all_days,
                bootstrap,
                model_index * 10000 + stratum_index * 1000,
            )
            for stratum_index, (stratum, mask) in enumerate(masks.items())
        }
        model_index += 1

    paired = candidate.event_gains - parent.event_gains
    results["ch007_minus_ch004"] = {
        stratum: summarize(
            paired[mask], candidate.event_days[mask], all_days, bootstrap, 50000 + index * 1000
        )
        for index, (stratum, mask) in enumerate(masks.items())
    }
    years = (EPOCH + candidate.event_days.astype("timedelta64[D]")).astype("datetime64[Y]").astype(int) + 1970
    annual = {
        str(int(year)): float(np.mean(candidate.event_gains[years == year]))
        for year in np.unique(years)
    }
    primary = results["ch007"]["primary"]
    parent_primary = results["ch004_parent"]["primary"]
    low = results["ch007"]["low_etas"]
    parent_low = results["ch004_parent"]["low_etas"]
    paired_primary = results["ch007_minus_ch004"]["primary"]
    gate = config["validation_rule"]
    admission = {
        "minimum_parent_igpe_factor": (
            primary["information_gain_per_event"]
            >= gate["minimum_parent_igpe_factor"] * parent_primary["information_gain_per_event"]
        ),
        "low_etas_at_least_parent": (
            low["information_gain_per_event"] >= parent_low["information_gain_per_event"]
        ),
        "every_year_positive": min(annual.values()) > 0,
        "paired_30_lower_positive": paired_primary["bootstrap"]["30_days"]["lower"] > 0,
        "paired_90_lower_nonnegative": paired_primary["bootstrap"]["90_days"]["lower"] >= 0,
    }
    admission["ch007_validated"] = all(admission.values())
    manifest = {
        "schema_version": 1,
        "evaluation_id": config["evaluation_id"],
        "status": f"{evaluation_role}_completed",
        "tool": {
            "name": "scripts/evaluate_ch007_validation.py",
            "script_sha256": sha256_file(Path(__file__)),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "repository": {"evaluation_code_commit": evaluation_commit},
        "inputs": {
            "config_sha256": sha256_file(args.config),
            **{key: config[key] for key in config if key.endswith("_sha256")},
        },
        "period": {**config["period"], "events": len(candidate.event_gains)},
        "results": results,
        "annual_ch007_igpe": annual,
        "admission": admission,
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(json.dumps({"annual": annual, "results": results, "admission": admission}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
