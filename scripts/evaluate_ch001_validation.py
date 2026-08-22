#!/usr/bin/env python3
"""Score the committed CH-001 model on development validation only."""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.challenger import (  # noqa: E402
    event_log_ratios,
    joined_shards,
    load_challenger_model,
    load_joined_shard,
    raw_features,
    stationary_block_bootstrap_igpe,
)
from etas_challenge.training_matrix import sha256_file  # noqa: E402


TOOL_VERSION = "1.0.0"
EPOCH = np.datetime64("1970-01-01", "D")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/evaluation/ch001-linear-v1-validation.json"),
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
        raise ValueError("validation requires a clean committed repository")
    required = [
        str(config_path),
        config["model"],
        config["fit_manifest"],
        "scripts/evaluate_ch001_validation.py",
    ]
    tracked = set(git_output("ls-files", *required).splitlines())
    if tracked != set(required):
        raise ValueError("validation config, model, fit manifest, and script must be committed")
    lock_commit = config["model_lock_commit"]
    if not git_output("merge-base", "--is-ancestor", lock_commit, "HEAD") == "":
        raise ValueError("model lock commit is not an ancestor of validation code")
    for path_key, hash_key in (("model", "model_sha256"), ("fit_manifest", "fit_manifest_sha256")):
        committed = subprocess.check_output(
            ["git", "show", f"{lock_commit}:{config[path_key]}"], cwd=ROOT
        )
        import hashlib

        if hashlib.sha256(committed).hexdigest() != config[hash_key]:
            raise ValueError(f"{path_key} did not match the pre-validation lock commit")
    return git_output("rev-parse", "HEAD")


def write_daily(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    fields = list(rows[0])
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def summarize_stratum(gain, count, bootstrap, seed_offset: int):
    total_count = int(np.sum(count, dtype=np.int64))
    total_gain = float(np.sum(gain, dtype=np.float64))
    result = {
        "target_events": total_count,
        "information_gain": total_gain,
        "information_gain_per_event": total_gain / total_count,
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


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    config_path = args.config.resolve().relative_to(ROOT)
    evaluation_commit = require_committed_gate(config, config_path)
    for path_key, hash_key in (
        ("challenge_contract", "challenge_contract_sha256"),
        ("matrix_manifest", "matrix_manifest_sha256"),
        ("etas_manifest", "etas_manifest_sha256"),
        ("model", "model_sha256"),
        ("fit_manifest", "fit_manifest_sha256"),
    ):
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"{path_key} SHA-256 does not match validation config")

    model_payload, scaler, weights = load_challenger_model(Path(config["model"]))
    fit_manifest = json.loads(Path(config["fit_manifest"]).read_text(encoding="utf-8"))
    if fit_manifest["protocol"]["validation_opened"] is not False:
        raise ValueError("fit manifest does not preserve the validation-unseen gate")
    threshold = model_payload["low_etas_intensity_threshold"]
    if threshold != fit_manifest["low_etas_intensity"]["threshold_rate_per_cell_day"]:
        raise ValueError("low-ETAS threshold differs between model and fit manifest")

    matrix_manifest = json.loads(Path(config["matrix_manifest"]).read_text(encoding="utf-8"))
    etas_manifest = json.loads(Path(config["etas_manifest"]).read_text(encoding="utf-8"))
    shards = joined_shards(
        matrix_manifest,
        etas_manifest,
        start=config["validation_start"],
        end_exclusive=config["validation_end_exclusive"],
    )
    thresholds = config["target_magnitude_thresholds"]
    all_days = []
    all_expected = []
    gains = [[] for _ in thresholds]
    counts = [[] for _ in thresholds]
    low_gains = []
    low_counts = []
    for shard in shards:
        count_features, continuous, targets, rates = load_joined_shard(shard)
        design = scaler.transform(raw_features(count_features, continuous))
        log_ratios = event_log_ratios(weights, design, rates)
        with np.load(shard.matrix_path, allow_pickle=False) as matrix:
            issue_days = matrix["issue_days"]
        all_days.append(issue_days)
        all_expected.append(np.sum(rates, axis=1, dtype=np.float64))
        for index in range(len(thresholds)):
            target = targets[..., index]
            gains[index].append(np.sum(target * log_ratios, axis=1))
            counts[index].append(np.sum(target, axis=1, dtype=np.int64))
        low_mask = rates <= threshold
        primary = targets[..., 0]
        low_gains.append(np.sum(primary * low_mask * log_ratios, axis=1))
        low_counts.append(np.sum(primary * low_mask, axis=1, dtype=np.int64))
        print(f"scored {shard.month}", flush=True)

    days = np.concatenate(all_days)
    expected = np.concatenate(all_expected)
    gain_vectors = [np.concatenate(values) for values in gains]
    count_vectors = [np.concatenate(values) for values in counts]
    low_gain = np.concatenate(low_gains)
    low_count = np.concatenate(low_counts)
    rows = []
    for index, day in enumerate(days):
        row = {
            "issue_date": np.datetime_as_string(EPOCH + np.timedelta64(int(day), "D")),
            "etas_expected_count": format(float(expected[index]), ".12g"),
            "challenger_expected_count": format(float(expected[index]), ".12g"),
        }
        for threshold_index, threshold_value in enumerate(thresholds):
            label = str(threshold_value).replace(".", "_")
            row[f"target_count_m{label}"] = int(count_vectors[threshold_index][index])
            row[f"paired_gain_m{label}"] = format(
                float(gain_vectors[threshold_index][index]), ".12g"
            )
        row["low_etas_target_count"] = int(low_count[index])
        row["low_etas_paired_gain"] = format(float(low_gain[index]), ".12g")
        rows.append(row)
    daily_path = Path(config["daily_output"])
    write_daily(daily_path, rows)

    summaries = {
        f"m_gte_{threshold}": summarize_stratum(
            gain_vectors[index], count_vectors[index], config["bootstrap"], index * 1000
        )
        for index, threshold in enumerate(thresholds)
    }
    summaries["low_etas_intensity"] = summarize_stratum(
        low_gain, low_count, config["bootstrap"], 9000
    )
    manifest = {
        "schema_version": 1,
        "evaluation_id": config["evaluation_id"],
        "status": "development_validation_completed",
        "tool": {
            "name": "scripts/evaluate_ch001_validation.py",
            "version": TOOL_VERSION,
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "repository": {
            "model_lock_commit": config["model_lock_commit"],
            "evaluation_code_commit": evaluation_commit,
        },
        "inputs": {
            "config_sha256": sha256_file(args.config),
            "model_sha256": config["model_sha256"],
            "fit_manifest_sha256": config["fit_manifest_sha256"],
            "matrix_manifest_sha256": config["matrix_manifest_sha256"],
            "etas_manifest_sha256": config["etas_manifest_sha256"],
        },
        "period": {
            "start": config["validation_start"],
            "end_exclusive": config["validation_end_exclusive"],
            "issue_days": len(days),
            "months": len(shards),
        },
        "protocol": {
            "baseline": "frozen_etas",
            "daily_count_policy": model_payload["daily_count_policy"],
            "low_etas_threshold_rate_per_cell_day": threshold,
            "bootstrap": config["bootstrap"],
            "locked_retrospective_opened": False,
        },
        "count_and_magnitude_invariants": {
            "etas_expected_count_sum": float(np.sum(expected)),
            "challenger_expected_count_sum": float(np.sum(expected)),
            "maximum_daily_expected_count_difference": 0.0,
            "number_test": "identical to frozen ETAS by construction",
            "magnitude_test": "identical to frozen ETAS by construction",
            "pseudolikelihood_gain": "equal to conditional spatial log gain because count and magnitude forecasts are unchanged",
        },
        "results": summaries,
        "outputs": {
            "daily_paired_scores": str(daily_path),
            "daily_paired_scores_sha256": sha256_file(daily_path),
        },
        "claim_boundary": (
            "Development-validation evidence only. The locked retrospective "
            "test was not read and no ETAS-superiority claim is made."
        ),
    }
    atomic_json(Path(config["manifest"]), manifest)
    print(json.dumps(manifest["results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
