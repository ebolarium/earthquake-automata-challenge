"""Leakage-free phase-coherent hazard-debt features for CH-009."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True, slots=True)
class FrailtyTrendState:
    short_mean: np.ndarray
    long_mean: np.ndarray


def update_frailty_trend(
    state: FrailtyTrendState,
    log_frailty: np.ndarray,
    short_half_life_days: float,
    long_half_life_days: float,
) -> FrailtyTrendState:
    """Update fast and slow causal EWMAs using only the current issue state."""

    short = np.asarray(state.short_mean, dtype=float)
    long = np.asarray(state.long_mean, dtype=float)
    current = np.asarray(log_frailty, dtype=float)
    if (
        short.shape != long.shape
        or short.shape != current.shape
        or not all(np.all(np.isfinite(value)) for value in (short, long, current))
        or not math.isfinite(short_half_life_days)
        or not math.isfinite(long_half_life_days)
        or short_half_life_days <= 0
        or long_half_life_days <= short_half_life_days
    ):
        raise ValueError("invalid CH-009 frailty-trend inputs")
    short_retention = math.exp(-math.log(2.0) / short_half_life_days)
    long_retention = math.exp(-math.log(2.0) / long_half_life_days)
    return FrailtyTrendState(
        short_mean=short_retention * short + (1.0 - short_retention) * current,
        long_mean=long_retention * long + (1.0 - long_retention) * current,
    )


def positive_frailty_acceleration(
    state: FrailtyTrendState,
    minimum_acceleration: float = 0.0,
) -> np.ndarray:
    """Return positive fast-minus-slow frailty change above a fixed floor."""

    short = np.asarray(state.short_mean, dtype=float)
    long = np.asarray(state.long_mean, dtype=float)
    if (
        short.shape != long.shape
        or not np.all(np.isfinite(short))
        or not np.all(np.isfinite(long))
        or not math.isfinite(minimum_acceleration)
        or minimum_acceleration < 0
    ):
        raise ValueError("invalid CH-009 acceleration inputs")
    return np.maximum(short - long - minimum_acceleration, 0.0)


def phase_coherent_hazard_debt(
    overdue_score: np.ndarray,
    positive_frailty: np.ndarray,
    frailty_acceleration: np.ndarray,
    transition: np.ndarray,
    coherence_mix: float,
) -> np.ndarray:
    """Require joint overdue, frailty, acceleration, and graph support."""

    overdue = np.asarray(overdue_score, dtype=float)
    frailty = np.asarray(positive_frailty, dtype=float)
    acceleration = np.asarray(frailty_acceleration, dtype=float)
    graph = np.asarray(transition, dtype=float)
    if (
        overdue.ndim != 1
        or frailty.shape != overdue.shape
        or acceleration.shape != overdue.shape
        or graph.shape != (len(overdue), len(overdue))
        or not all(
            np.all(np.isfinite(value))
            for value in (overdue, frailty, acceleration, graph)
        )
        or any(np.any(value < 0) for value in (overdue, frailty, acceleration, graph))
        or not np.allclose(np.sum(graph, axis=1), 1.0)
        or not math.isfinite(coherence_mix)
        or not 0 <= coherence_mix <= 1
    ):
        raise ValueError("invalid CH-009 phase-coherence inputs")

    local_debt = np.cbrt(overdue * frailty * acceleration)
    coherent_debt = np.sqrt(local_debt * (graph @ local_debt))
    return (1.0 - coherence_mix) * local_debt + coherence_mix * coherent_debt
