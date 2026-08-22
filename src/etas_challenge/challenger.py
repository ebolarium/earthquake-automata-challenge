"""Conditional spatial residual model for the first ETAS challenger."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from etas_challenge.training_matrix import CONTINUOUS_FEATURES, COUNT_FEATURES


CHALLENGER_MODEL_SCHEMA_VERSION = 1
TRANSFORMED_FEATURES = tuple(f"log1p_{name}" for name in COUNT_FEATURES) + (
    "cell_excess_30d",
    "neighbor_excess_30d",
    "cell_acceleration_7v30",
    "neighbor_acceleration_7v30",
    "log1p_cell_recency_days",
    "log1p_neighbor_recency_days",
    "log_background_rate_daily",
)


@dataclass(frozen=True, slots=True)
class FeatureScaler:
    means: np.ndarray
    scales: np.ndarray
    clip: float

    def __post_init__(self) -> None:
        means = np.asarray(self.means, dtype=np.float64)
        scales = np.asarray(self.scales, dtype=np.float64)
        expected = (len(TRANSFORMED_FEATURES),)
        if means.shape != expected or scales.shape != expected:
            raise ValueError("scaler vectors must match transformed features")
        if not np.all(np.isfinite(means)) or not np.all(np.isfinite(scales)):
            raise ValueError("scaler vectors must be finite")
        if np.any(scales <= 0) or self.clip <= 0:
            raise ValueError("scales and clipping threshold must be positive")
        object.__setattr__(self, "means", means)
        object.__setattr__(self, "scales", scales)

    def transform(self, raw: np.ndarray) -> np.ndarray:
        values = (np.asarray(raw, dtype=np.float64) - self.means) / self.scales
        return np.clip(values, -self.clip, self.clip)

    def to_payload(self) -> dict:
        return {
            "feature_names": list(TRANSFORMED_FEATURES),
            "means": self.means.tolist(),
            "scales": self.scales.tolist(),
            "standardized_clip": self.clip,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "FeatureScaler":
        if payload.get("feature_names") != list(TRANSFORMED_FEATURES):
            raise ValueError("transformed feature contract changed")
        return cls(
            means=payload["means"],
            scales=payload["scales"],
            clip=float(payload["standardized_clip"]),
        )


def raw_features(
    count_features: np.ndarray, continuous_features: np.ndarray
) -> np.ndarray:
    counts = np.asarray(count_features)
    continuous = np.asarray(continuous_features)
    if counts.shape[:-1] != continuous.shape[:-1]:
        raise ValueError("count and continuous feature rows must align")
    if counts.shape[-1] != len(COUNT_FEATURES):
        raise ValueError("count feature width changed")
    if continuous.shape[-1] != len(CONTINUOUS_FEATURES):
        raise ValueError("continuous feature width changed")
    if np.any(counts < 0) or not np.all(np.isfinite(continuous)):
        raise ValueError("feature arrays contain invalid values")

    result = np.empty(counts.shape[:-1] + (len(TRANSFORMED_FEATURES),), dtype=np.float64)
    result[..., : len(COUNT_FEATURES)] = np.log1p(counts)
    offset = len(COUNT_FEATURES)
    result[..., offset : offset + 4] = continuous[..., :4]
    result[..., offset + 4 : offset + 6] = np.log1p(continuous[..., 4:6])
    background = continuous[..., 6]
    if np.any(background <= 0):
        raise ValueError("background rates must be positive")
    result[..., offset + 6] = np.log(background)
    return result


def fit_scaler_from_moments(
    row_count: int, sums: np.ndarray, square_sums: np.ndarray, clip: float
) -> FeatureScaler:
    if row_count <= 0:
        raise ValueError("scaler requires feature rows")
    means = np.asarray(sums, dtype=np.float64) / row_count
    variance = np.maximum(
        np.asarray(square_sums, dtype=np.float64) / row_count - means * means,
        0.0,
    )
    scales = np.sqrt(variance)
    scales[scales < 1e-12] = 1.0
    return FeatureScaler(means=means, scales=scales, clip=float(clip))


def conditional_gain_and_gradient(
    weights: np.ndarray,
    design: np.ndarray,
    etas_rates: np.ndarray,
    targets: np.ndarray,
) -> tuple[float, np.ndarray, int, np.ndarray]:
    """Return log gain, its gradient, target count, and daily gains."""

    weights = np.asarray(weights, dtype=np.float64)
    design = np.asarray(design, dtype=np.float64)
    rates = np.asarray(etas_rates, dtype=np.float64)
    targets = np.asarray(targets, dtype=np.float64)
    if design.ndim != 3 or design.shape[-1] != weights.size:
        raise ValueError("design must be day by cell by feature")
    if rates.shape != design.shape[:2] or targets.shape != rates.shape:
        raise ValueError("rates and targets must align with design rows")
    if np.any(rates <= 0) or not np.all(np.isfinite(rates)):
        raise ValueError("ETAS rates must be finite and positive")
    if np.any(targets < 0) or not np.all(np.isfinite(targets)):
        raise ValueError("targets must be finite and non-negative")

    offsets = np.einsum("dcf,f->dc", design, weights, optimize=True)
    maxima = np.max(offsets, axis=1, keepdims=True)
    tilted = rates * np.exp(offsets - maxima)
    tilted_totals = np.sum(tilted, axis=1, keepdims=True)
    probabilities = tilted / tilted_totals
    log_normalizers = (
        maxima[:, 0]
        + np.log(tilted_totals[:, 0])
        - np.log(np.sum(rates, axis=1))
    )
    daily_counts = np.sum(targets, axis=1)
    daily_gain = np.sum(targets * offsets, axis=1) - daily_counts * log_normalizers
    residual = targets - daily_counts[:, None] * probabilities
    gradient = np.einsum("dc,dcf->f", residual, design, optimize=True)
    return (
        float(np.sum(daily_gain)),
        np.asarray(gradient, dtype=np.float64),
        int(np.sum(daily_counts)),
        np.asarray(daily_gain, dtype=np.float64),
    )


def event_log_ratios(
    weights: np.ndarray,
    design: np.ndarray,
    etas_rates: np.ndarray,
) -> np.ndarray:
    weights = np.asarray(weights, dtype=np.float64)
    design = np.asarray(design, dtype=np.float64)
    rates = np.asarray(etas_rates, dtype=np.float64)
    offsets = np.einsum("dcf,f->dc", design, weights, optimize=True)
    maxima = np.max(offsets, axis=1, keepdims=True)
    normalizer = (
        maxima[:, 0]
        + np.log(np.sum(rates * np.exp(offsets - maxima), axis=1))
        - np.log(np.sum(rates, axis=1))
    )
    return offsets - normalizer[:, None]


def stationary_block_bootstrap_igpe(
    daily_gain: np.ndarray,
    daily_count: np.ndarray,
    *,
    replicates: int,
    mean_block_days: float,
    seed: int,
    confidence_level: float = 0.95,
    batch_size: int = 256,
) -> dict:
    gain = np.asarray(daily_gain, dtype=np.float64)
    count = np.asarray(daily_count, dtype=np.int64)
    if gain.ndim != 1 or count.shape != gain.shape or not len(gain):
        raise ValueError("bootstrap daily vectors must be non-empty and aligned")
    if not np.all(np.isfinite(gain)) or np.any(count < 0):
        raise ValueError("bootstrap vectors contain invalid values")
    if replicates <= 0 or mean_block_days <= 1 or batch_size <= 0:
        raise ValueError("bootstrap controls must be positive")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence level must lie between zero and one")

    rng = np.random.default_rng(seed)
    sample_values = np.empty(replicates, dtype=np.float64)
    valid = 0
    n_days = len(gain)
    restart_probability = 1.0 / mean_block_days
    for batch_start in range(0, replicates, batch_size):
        size = min(batch_size, replicates - batch_start)
        indexes = np.empty((size, n_days), dtype=np.int32)
        indexes[:, 0] = rng.integers(0, n_days, size=size)
        for day in range(1, n_days):
            restart = rng.random(size) < restart_probability
            indexes[:, day] = (indexes[:, day - 1] + 1) % n_days
            restart_count = int(np.count_nonzero(restart))
            if restart_count:
                indexes[restart, day] = rng.integers(
                    0, n_days, size=restart_count
                )
        sampled_gain = np.sum(gain[indexes], axis=1)
        sampled_count = np.sum(count[indexes], axis=1)
        usable = sampled_count > 0
        values = sampled_gain[usable] / sampled_count[usable]
        sample_values[valid : valid + len(values)] = values
        valid += len(values)
    if valid < math.ceil(replicates * 0.99):
        raise ValueError("too many bootstrap replicates contain no target events")
    sample_values = sample_values[:valid]
    tail = (1.0 - confidence_level) / 2.0
    return {
        "method": "stationary_daily_block_bootstrap",
        "replicates": replicates,
        "valid_replicates": valid,
        "seed": seed,
        "mean_block_days": mean_block_days,
        "confidence_level": confidence_level,
        "lower": float(np.quantile(sample_values, tail)),
        "median": float(np.quantile(sample_values, 0.5)),
        "upper": float(np.quantile(sample_values, 1.0 - tail)),
    }


def validate_challenger_model(payload: dict) -> None:
    if payload.get("schema_version") != CHALLENGER_MODEL_SCHEMA_VERSION:
        raise ValueError("unsupported challenger model schema_version")
    if payload.get("model_family") != "conditional_linear_etas_residual":
        raise ValueError("unsupported challenger model family")
    if payload.get("status") != "fit_locked_validation_unseen":
        raise ValueError("challenger model must be locked before validation")
    FeatureScaler.from_payload(payload.get("scaler") or {})
    weights = np.asarray(payload.get("weights"), dtype=float)
    if weights.shape != (len(TRANSFORMED_FEATURES),):
        raise ValueError("challenger weights have wrong shape")
    if not np.all(np.isfinite(weights)):
        raise ValueError("challenger weights must be finite")
    sources = payload.get("sources") or {}
    for key in ("config_sha256", "matrix_manifest_sha256", "etas_manifest_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", sources.get(key, "")):
            raise ValueError(f"invalid challenger source hash: {key}")
    threshold = payload.get("low_etas_intensity_threshold")
    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("low-ETAS threshold must be finite and positive")


def load_challenger_model(path: Path) -> tuple[dict, FeatureScaler, np.ndarray]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_challenger_model(payload)
    return payload, FeatureScaler.from_payload(payload["scaler"]), np.asarray(
        payload["weights"], dtype=np.float64
    )


@dataclass(frozen=True, slots=True)
class JoinedShard:
    month: str
    matrix_path: Path
    etas_path: Path
    start: str
    end_inclusive: str


def joined_shards(
    matrix_manifest: dict,
    etas_manifest: dict,
    *,
    start: str,
    end_exclusive: str,
) -> list[JoinedShard]:
    matrix_by_month = {
        Path(item["path"]).stem: item for item in matrix_manifest["outputs"]["shards"]
    }
    etas_by_month = {
        Path(item["path"]).stem.removeprefix("etas-"): item
        for item in etas_manifest["outputs"]["shards"]
    }
    if set(matrix_by_month) != set(etas_by_month):
        raise ValueError("matrix and ETAS manifests contain different months")
    result = []
    for month in sorted(matrix_by_month):
        matrix = matrix_by_month[month]
        etas = etas_by_month[month]
        matrix_start = matrix["first_issue"]
        matrix_end = matrix["last_issue"]
        if (matrix_start, matrix_end) != (etas["start"], etas["end_inclusive"]):
            raise ValueError(f"matrix and ETAS periods differ for {month}")
        if matrix_end < start or matrix_start >= end_exclusive:
            continue
        if matrix_start < start or matrix_end >= end_exclusive:
            raise ValueError("requested split must align to complete monthly shards")
        result.append(
            JoinedShard(
                month=month,
                matrix_path=Path(matrix["path"]),
                etas_path=Path(etas["path"]),
                start=matrix_start,
                end_inclusive=matrix_end,
            )
        )
    if not result:
        raise ValueError("requested split contains no joined shards")
    return result


def load_joined_shard(
    shard: JoinedShard,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with np.load(shard.matrix_path, allow_pickle=False) as matrix:
        issue_days = matrix["issue_days"]
        counts = matrix["count_features"]
        continuous = matrix["continuous_features"]
        targets = matrix["target_counts"]
    with np.load(shard.etas_path, allow_pickle=False) as etas:
        etas_days = etas["issue_days"]
        rates = etas["etas_rates"]
    if not np.array_equal(issue_days, etas_days):
        raise ValueError(f"matrix and ETAS issue days differ for {shard.month}")
    if counts.shape[:2] != rates.shape or targets.shape[:2] != rates.shape:
        raise ValueError(f"matrix and ETAS grid rows differ for {shard.month}")
    return counts, continuous, targets, rates
