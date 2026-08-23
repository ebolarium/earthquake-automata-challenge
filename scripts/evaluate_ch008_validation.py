#!/usr/bin/env python3
"""Evaluate locked CH-008 as a distinct frailty-renewal challenger."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from etas_challenge.frailty_renewal_fit import FrailtyRenewalFitEvaluator  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402
from evaluate_ch004_validation import build_evaluator  # noqa: E402
from evaluate_ch007_validation import EPOCH, summarize  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch008-validation-v1.json"),
    )
    return parser.parse_args()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def paired_strata(
    left,
    right,
    masks: dict[str, np.ndarray],
    all_days: np.ndarray,
    bootstrap: dict,
    seed_base: int,
) -> dict:
    differences = left.event_gains - right.event_gains
    return {
        name: summarize(
            differences[mask],
            left.event_days[mask],
            all_days,
            bootstrap,
            seed_base + index * 1000,
        )
        for index, (name, mask) in enumerate(masks.items())
    }


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
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
    role = config.get("evaluation_role", "development_validation")
    if not (
        (role == "development_validation" and config["period"] == validation_period)
        or (role == "locked_retrospective" and config["period"] == retrospective_period)
    ):
        raise ValueError("CH-008 evaluation period violates the locked boundary")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True):
        raise ValueError("CH-008 evaluation requires a clean committed worktree")
    evaluation_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    for path_key, hash_key in config["locked_files"]:
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"CH-008 locked input changed: {path_key}")
    if role == "locked_retrospective":
        validation = json.loads(Path(config["validation_manifest"]).read_text())
        if validation["admission"]["ch008_validated"] is not True:
            raise ValueError("CH-008 did not pass development validation")

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
    ch008_model = json.loads(Path(config["model"]).read_text())
    ch007_model = json.loads(Path(config["incumbent_model"]).read_text())
    ch008_values = np.asarray(
        [ch008_model["parameters"][name] for name in parameter_order]
    )
    ch007_values = np.asarray(
        [ch007_model["parameters"][name] for name in parameter_order]
    )
    renewal_only_values = ch008_values.copy()
    renewal_only_values[parameter_order.index("frailty_weight")] = 0.0
    frailty_only_values = ch008_values.copy()
    frailty_only_values[parameter_order.index("renewal_weight")] = 0.0

    ch008 = evaluator.evaluate(parent_values, ch008_values)
    ch007 = evaluator.evaluate(parent_values, ch007_values)
    renewal_only = evaluator.evaluate(parent_values, renewal_only_values)
    frailty_only = evaluator.evaluate(parent_values, frailty_only_values)
    ch004 = base.evaluate(parent_values)
    scored_start = base.scoring_event_start
    etas_rates = history["etas_rates"][scored_start:]
    magnitudes = history["magnitudes"][scored_start:]
    parent_fit = json.loads(Path(config["parent_fit_manifest"]).read_text())
    masks = {
        "primary": np.ones(len(ch008.event_gains), dtype=bool),
        "low_etas": etas_rates <= parent_fit["result"]["low_etas_threshold"],
        "m_gte_3_5": magnitudes >= 3.5,
        "m_gte_4_0": magnitudes >= 4.0,
    }
    all_days = history["all_issue_days"][
        history["all_issue_days"] >= int(history["scoring_start_day"])
    ]
    bootstrap = config["bootstrap"]
    results = {}
    for model_index, (name, result) in enumerate(
        (
            ("ch008", ch008),
            ("ch007_incumbent", ch007),
            ("ch008_renewal_only", renewal_only),
            ("ch008_frailty_only", frailty_only),
            ("ch004_parent", ch004),
        )
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
    results["ch008_minus_ch007"] = paired_strata(
        ch008, ch007, masks, all_days, bootstrap, 60000
    )
    results["frailty_increment_full_minus_renewal"] = paired_strata(
        ch008, renewal_only, masks, all_days, bootstrap, 70000
    )
    results["ch008_minus_ch004"] = paired_strata(
        ch008, ch004, masks, all_days, bootstrap, 80000
    )

    years = (
        (EPOCH + ch008.event_days.astype("timedelta64[D]"))
        .astype("datetime64[Y]")
        .astype(int)
        + 1970
    )
    annual = {
        str(int(year)): float(np.mean(ch008.event_gains[years == year]))
        for year in np.unique(years)
    }
    annual_frailty_increment = {
        str(int(year)): float(
            np.mean((ch008.event_gains - renewal_only.event_gains)[years == year])
        )
        for year in np.unique(years)
    }
    primary = results["ch008"]["primary"]
    incumbent = results["ch007_incumbent"]["primary"]
    low = results["ch008"]["low_etas"]
    incumbent_low = results["ch007_incumbent"]["low_etas"]
    versus_incumbent = results["ch008_minus_ch007"]["primary"]
    frailty_increment = results["frailty_increment_full_minus_renewal"]["primary"]
    frailty_low = results["frailty_increment_full_minus_renewal"]["low_etas"]
    gate = config["validation_rule"]
    admission = {
        "positive_primary_igpe": primary["information_gain_per_event"] > 0,
        "minimum_incumbent_igpe_factor": (
            primary["information_gain_per_event"]
            >= gate["minimum_incumbent_igpe_factor"]
            * incumbent["information_gain_per_event"]
        ),
        "low_etas_at_least_incumbent": (
            low["information_gain_per_event"]
            >= incumbent_low["information_gain_per_event"]
        ),
        "every_year_positive": min(annual.values()) > 0,
        "magnitude_strata_nonnegative": (
            results["ch008"]["m_gte_3_5"]["information_gain_per_event"] >= 0
            and results["ch008"]["m_gte_4_0"]["information_gain_per_event"] >= 0
        ),
        "incumbent_paired_30_lower_positive": (
            versus_incumbent["bootstrap"]["30_days"]["lower"] > 0
        ),
        "incumbent_paired_90_lower_nonnegative": (
            versus_incumbent["bootstrap"]["90_days"]["lower"] >= 0
        ),
        "frailty_increment_positive": frailty_increment["information_gain_per_event"] > 0,
        "frailty_low_etas_nonnegative": frailty_low["information_gain_per_event"] >= 0,
        "frailty_paired_30_lower_positive": (
            frailty_increment["bootstrap"]["30_days"]["lower"] > 0
        ),
        "frailty_paired_90_lower_nonnegative": (
            frailty_increment["bootstrap"]["90_days"]["lower"] >= 0
        ),
    }
    admission["ch008_validated"] = all(admission.values())
    manifest = {
        "schema_version": 1,
        "evaluation_id": config["evaluation_id"],
        "status": f"{role}_completed",
        "tool": {
            "name": "scripts/evaluate_ch008_validation.py",
            "script_sha256": sha256_file(Path(__file__)),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "repository": {"evaluation_code_commit": evaluation_commit},
        "inputs": {
            "config_sha256": sha256_file(args.config),
            **{key: config[key] for key in config if key.endswith("_sha256")},
        },
        "period": {**config["period"], "events": len(ch008.event_gains)},
        "results": results,
        "annual_ch008_igpe": annual,
        "annual_frailty_increment": annual_frailty_increment,
        "admission": admission,
        "claim_boundary": config["claim_boundary"],
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(
        json.dumps(
            {
                "annual_ch008_igpe": annual,
                "annual_frailty_increment": annual_frailty_increment,
                "results": results,
                "admission": admission,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
