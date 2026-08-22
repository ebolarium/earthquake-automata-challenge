"""Marked renewal-age components for the CH-004 quiescence challenger."""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import invgauss


def magnitude_reset_weight(
    magnitudes: np.ndarray,
    full_reset_magnitude: float,
    magnitude_exponent: float,
) -> np.ndarray:
    """Return a smooth rupture-size proxy capped at one full reset."""

    values = np.asarray(magnitudes, dtype=float)
    if (
        not np.all(np.isfinite(values))
        or not math.isfinite(full_reset_magnitude)
        or not math.isfinite(magnitude_exponent)
        or magnitude_exponent <= 0
    ):
        raise ValueError("invalid magnitude-reset inputs")
    return np.minimum(1.0, 10.0 ** (magnitude_exponent * (values - full_reset_magnitude)))


def expected_reset_weight_gr(
    beta: float,
    magnitude_reference: float,
    full_reset_magnitude: float,
    magnitude_exponent: float,
) -> float:
    """Integrate the capped reset mark under an unbounded GR exponential tail."""

    if (
        not all(
            math.isfinite(value)
            for value in (beta, magnitude_reference, full_reset_magnitude, magnitude_exponent)
        )
        or beta <= 0
        or magnitude_exponent <= 0
    ):
        raise ValueError("invalid Gutenberg-Richter reset inputs")
    transition = full_reset_magnitude - magnitude_reference
    if transition <= 0:
        return 1.0
    exponent = magnitude_exponent * math.log(10.0)
    difference = beta - exponent
    if abs(difference) < 1e-12:
        below = beta * math.exp(-exponent * transition) * transition
    else:
        below = (
            beta
            * math.exp(-exponent * transition)
            * (-math.expm1(-difference * transition))
            / difference
        )
    return below + math.exp(-beta * transition)


def update_expected_hazard_age(
    age: np.ndarray,
    expected_daily_reset_hazard: np.ndarray,
    observed_posterior_reset_mass: np.ndarray,
) -> np.ndarray:
    """Advance expected hazard age, then apply a probabilistic marked reset."""

    current = np.asarray(age, dtype=float)
    expected = np.asarray(expected_daily_reset_hazard, dtype=float)
    observed = np.asarray(observed_posterior_reset_mass, dtype=float)
    if (
        current.shape != expected.shape
        or current.shape != observed.shape
        or not np.all(np.isfinite(current))
        or not np.all(np.isfinite(expected))
        or not np.all(np.isfinite(observed))
        or np.any(current < 0)
        or np.any(expected < 0)
        or np.any(observed < 0)
    ):
        raise ValueError("invalid renewal-age inputs")
    return (current + expected) * np.exp(-observed)


def bpt_overdue_score(age: np.ndarray, aperiodicity: float) -> np.ndarray:
    """Return positive log hazard above a unit-rate memoryless baseline."""

    values = np.asarray(age, dtype=float)
    if (
        not np.all(np.isfinite(values))
        or np.any(values < 0)
        or not math.isfinite(aperiodicity)
        or aperiodicity <= 0
    ):
        raise ValueError("invalid BPT hazard inputs")
    score = np.zeros_like(values)
    positive = values > 0
    if np.any(positive):
        alpha_squared = aperiodicity * aperiodicity
        distribution = invgauss(mu=alpha_squared, scale=1.0 / alpha_squared)
        log_hazard = distribution.logpdf(values[positive]) - distribution.logsf(
            values[positive]
        )
        score[positive] = np.maximum(log_hazard, 0.0)
    return score
