"""Discounted Gamma-Poisson fault frailty for the CH-006 challenger."""

from __future__ import annotations

import math

import numpy as np


def discounted_gamma_poisson_update(
    exposure: np.ndarray,
    root_mass: np.ndarray,
    expected_root_mass: np.ndarray,
    observed_root_mass: np.ndarray,
    half_life_days: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Discount old evidence and assimilate one forecast day's root evidence."""

    current_exposure = np.asarray(exposure, dtype=float)
    current_roots = np.asarray(root_mass, dtype=float)
    expected = np.asarray(expected_root_mass, dtype=float)
    observed = np.asarray(observed_root_mass, dtype=float)
    if (
        current_exposure.shape != current_roots.shape
        or current_exposure.shape != expected.shape
        or current_exposure.shape != observed.shape
        or not all(
            np.all(np.isfinite(value))
            for value in (current_exposure, current_roots, expected, observed)
        )
        or any(
            np.any(value < 0)
            for value in (current_exposure, current_roots, expected, observed)
        )
        or not math.isfinite(half_life_days)
        or half_life_days <= 0
    ):
        raise ValueError("invalid discounted frailty update inputs")
    retention = math.exp(-math.log(2.0) / half_life_days)
    return (
        retention * current_exposure + expected,
        retention * current_roots + observed,
    )


def posterior_log_frailty(
    exposure: np.ndarray,
    root_mass: np.ndarray,
    prior_exposure: float,
) -> np.ndarray:
    """Return the log posterior mean rate multiplier under a unit-mean prior."""

    expected = np.asarray(exposure, dtype=float)
    observed = np.asarray(root_mass, dtype=float)
    if (
        expected.shape != observed.shape
        or not np.all(np.isfinite(expected))
        or not np.all(np.isfinite(observed))
        or np.any(expected < 0)
        or np.any(observed < 0)
        or not math.isfinite(prior_exposure)
        or prior_exposure <= 0
    ):
        raise ValueError("invalid Gamma-Poisson posterior inputs")
    return np.log((prior_exposure + observed) / (prior_exposure + expected))


def positive_frailty_score(
    local_log_frailty: np.ndarray,
    neighbor_log_frailty: np.ndarray,
    neighborhood_mix: float,
    minimum_log_frailty: float,
) -> np.ndarray:
    """Blend local and graph evidence, retaining only reproducible excess strength."""

    local = np.asarray(local_log_frailty, dtype=float)
    neighbor = np.asarray(neighbor_log_frailty, dtype=float)
    if (
        local.shape != neighbor.shape
        or not np.all(np.isfinite(local))
        or not np.all(np.isfinite(neighbor))
        or not math.isfinite(neighborhood_mix)
        or not 0 <= neighborhood_mix <= 1
        or not math.isfinite(minimum_log_frailty)
        or minimum_log_frailty < 0
    ):
        raise ValueError("invalid frailty score inputs")
    context = (1.0 - neighborhood_mix) * local + neighborhood_mix * neighbor
    return np.maximum(context - minimum_log_frailty, 0.0)
