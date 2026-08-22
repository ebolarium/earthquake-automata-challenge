#!/usr/bin/env python3
"""Fit CH-001 linear ETAS residual using only the frozen fit split."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.challenger import (  # noqa: E402
    CHALLENGER_MODEL_SCHEMA_VERSION,
    TRANSFORMED_FEATURES,
    conditional_gain_and_gradient,
    fit_scaler_from_moments,
    joined_shards,
    load_joined_shard,
    raw_features,
    validate_challenger_model,
)
from etas_challenge.training_matrix import sha256_file  # noqa: E402


TOOL_VERSION = "1.0.0"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch001-linear-v1.json"),
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


def require_clean_committed_implementation(config_path: Path) -> str:
    if git_output("status", "--porcelain"):
        raise ValueError("fit requires a clean repository with committed implementation")
    tracked = git_output("ls-files", str(config_path), "scripts/fit_ch001_linear.py")
    if len(tracked.splitlines()) != 2:
        raise ValueError("fit config and implementation must be committed")
    return git_output("rev-parse", "HEAD")


class StreamingObjective:
    def __init__(self, shards, scaler, target_index: int, l2: float):
        self.shards = shards
        self.scaler = scaler
        self.target_index = target_index
        self.l2 = float(l2)
        self.evaluations = 0
        self._cached_weights = None
        self._cached_result = None

    def __call__(self, weights):
        weights = np.asarray(weights, dtype=np.float64)
        if self._cached_weights is not None and np.array_equal(
            weights, self._cached_weights
        ):
            return self._cached_result
        gain = 0.0
        gradient = np.zeros_like(weights)
        target_count = 0
        for shard in self.shards:
            counts, continuous, targets, rates = load_joined_shard(shard)
            design = self.scaler.transform(raw_features(counts, continuous))
            shard_gain, shard_gradient, shard_targets, _ = (
                conditional_gain_and_gradient(
                    weights, design, rates, targets[..., self.target_index]
                )
            )
            gain += shard_gain
            gradient += shard_gradient
            target_count += shard_targets
        if target_count <= 0:
            raise ValueError("fit split has no target events")
        loss = -gain / target_count + 0.5 * self.l2 * float(weights @ weights)
        loss_gradient = -gradient / target_count + self.l2 * weights
        self.evaluations += 1
        print(
            f"objective={self.evaluations} loss={loss:.10f} "
            f"fit_igpe={gain / target_count:.10f}",
            flush=True,
        )
        self._cached_weights = weights.copy()
        self._cached_result = (float(loss), loss_gradient)
        return self._cached_result


def scaler_and_threshold(shards, target_index: int, clip: float):
    feature_count = len(TRANSFORMED_FEATURES)
    sums = np.zeros(feature_count, dtype=np.float64)
    square_sums = np.zeros(feature_count, dtype=np.float64)
    rows = 0
    event_rates = []
    target_count = 0
    for shard in shards:
        counts, continuous, targets, rates = load_joined_shard(shard)
        raw = raw_features(counts, continuous)
        flat = raw.reshape(-1, feature_count)
        sums += np.sum(flat, axis=0, dtype=np.float64)
        square_sums += np.einsum("ij,ij->j", flat, flat, optimize=True)
        rows += flat.shape[0]
        primary = targets[..., target_index]
        active = primary > 0
        if np.any(active):
            event_rates.append(np.repeat(rates[active], primary[active].astype(int)))
            target_count += int(np.sum(primary[active], dtype=np.int64))
        print(f"scaler {shard.month}", flush=True)
    scaler = fit_scaler_from_moments(rows, sums, square_sums, clip)
    all_event_rates = np.concatenate(event_rates)
    if len(all_event_rates) != target_count:
        raise ValueError("event intensity extraction lost targets")
    threshold = float(np.quantile(all_event_rates, 0.25, method="linear"))
    return scaler, threshold, rows, target_count


def evaluate_fit(weights, shards, scaler, target_index: int):
    gain = 0.0
    target_count = 0
    daily_gains = []
    for shard in shards:
        counts, continuous, targets, rates = load_joined_shard(shard)
        design = scaler.transform(raw_features(counts, continuous))
        shard_gain, _, shard_targets, shard_daily = conditional_gain_and_gradient(
            weights, design, rates, targets[..., target_index]
        )
        gain += shard_gain
        target_count += shard_targets
        daily_gains.append(shard_daily)
    daily = np.concatenate(daily_gains)
    return {
        "target_events": target_count,
        "information_gain": gain,
        "information_gain_per_event": gain / target_count,
        "positive_gain_days": int(np.count_nonzero(daily > 0)),
        "negative_gain_days": int(np.count_nonzero(daily < 0)),
    }


def main() -> int:
    args = parse_args()
    config_path = args.config.resolve().relative_to(ROOT)
    repository_commit = require_clean_committed_implementation(config_path)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    for path_key, hash_key in (
        ("challenge_contract", "challenge_contract_sha256"),
        ("matrix_manifest", "matrix_manifest_sha256"),
        ("etas_manifest", "etas_manifest_sha256"),
    ):
        if sha256_file(Path(config[path_key])) != config[hash_key]:
            raise ValueError(f"{path_key} SHA-256 does not match fit config")
    matrix_manifest = json.loads(
        Path(config["matrix_manifest"]).read_text(encoding="utf-8")
    )
    etas_manifest = json.loads(
        Path(config["etas_manifest"]).read_text(encoding="utf-8")
    )
    shards = joined_shards(
        matrix_manifest,
        etas_manifest,
        start=config["fit_start"],
        end_exclusive=config["fit_end_exclusive"],
    )
    target_index = config["primary_target_index"]
    scaler, threshold, rows, target_count = scaler_and_threshold(
        shards,
        target_index,
        config["feature_transform"]["standardized_clip"],
    )
    if target_count <= 0:
        raise ValueError("fit split has no primary targets")

    optimizer = config["optimizer"]
    objective = StreamingObjective(
        shards, scaler, target_index, optimizer["l2_per_target"]
    )
    bound = float(optimizer["weight_bound"])
    result = minimize(
        objective,
        np.zeros(len(TRANSFORMED_FEATURES), dtype=np.float64),
        method=optimizer["name"],
        jac=True,
        bounds=[(-bound, bound)] * len(TRANSFORMED_FEATURES),
        options={
            "maxiter": optimizer["max_iterations"],
            "ftol": optimizer["ftol"],
            "gtol": optimizer["gtol"],
            "maxls": 30,
        },
    )
    if not result.success:
        raise RuntimeError(f"optimizer did not converge: {result.message}")
    fit_result = evaluate_fit(result.x, shards, scaler, target_index)
    config_hash = sha256_file(args.config)
    model = {
        "schema_version": CHALLENGER_MODEL_SCHEMA_VERSION,
        "model_id": config["model_id"],
        "model_family": "conditional_linear_etas_residual",
        "status": "fit_locked_validation_unseen",
        "trained_from_repository_commit": repository_commit,
        "fit_period": {
            "start": config["fit_start"],
            "end_exclusive": config["fit_end_exclusive"],
        },
        "sources": {
            "config_sha256": config_hash,
            "matrix_manifest_sha256": config["matrix_manifest_sha256"],
            "etas_manifest_sha256": config["etas_manifest_sha256"],
        },
        "scaler": scaler.to_payload(),
        "weights": result.x.tolist(),
        "low_etas_intensity_threshold": threshold,
        "daily_count_policy": "preserve frozen ETAS expected count exactly",
    }
    validate_challenger_model(model)
    model_path = Path(config["model_output"])
    atomic_json(model_path, model)
    manifest = {
        "schema_version": 1,
        "experiment_id": "CH001-003-fit",
        "status": "fit_locked_validation_unseen",
        "tool": {
            "name": "scripts/fit_ch001_linear.py",
            "version": TOOL_VERSION,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "repository_commit": repository_commit,
        "inputs": model["sources"],
        "protocol": {
            "fit_start": config["fit_start"],
            "fit_end_exclusive": config["fit_end_exclusive"],
            "validation_opened": False,
            "features": list(TRANSFORMED_FEATURES),
            "optimizer": optimizer,
            "daily_count_policy": model["daily_count_policy"],
        },
        "low_etas_intensity": {
            "quantile": 0.25,
            "fit_event_count": target_count,
            "threshold_rate_per_cell_day": threshold,
            "source": "challenger_fit target-event cells only",
        },
        "outputs": {
            "model": str(model_path),
            "model_sha256": sha256_file(model_path),
        },
        "optimizer_result": {
            "success": bool(result.success),
            "message": str(result.message),
            "iterations": int(result.nit),
            "objective_evaluations": objective.evaluations,
            "final_regularized_loss": float(result.fun),
            "gradient_max_absolute": float(np.max(np.abs(result.jac))),
        },
        "fit_result": {
            **fit_result,
            "cell_day_rows": rows,
            "months": len(shards),
        },
        "claim_boundary": (
            "Fit-split optimization only. Development validation and locked "
            "retrospective outcomes were not read by this process."
        ),
    }
    atomic_json(Path(config["fit_manifest"]), manifest)
    print(json.dumps({"model": model, "fit": manifest["fit_result"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
