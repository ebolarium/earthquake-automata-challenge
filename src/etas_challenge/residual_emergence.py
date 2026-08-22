"""Leakage-free residual-emergence components for the CH-003 challenger."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class InnovationState:
    excess: np.ndarray
    variance: np.ndarray


def update_compensated_cusum(
    state: InnovationState,
    observed_root_mass: np.ndarray,
    expected_root_mass: np.ndarray,
    decay: float,
) -> InnovationState:
    """Update a one-sided CUSUM from ETAS-compensated background innovations."""

    observed = np.asarray(observed_root_mass, dtype=float)
    expected = np.asarray(expected_root_mass, dtype=float)
    excess = np.asarray(state.excess, dtype=float)
    variance = np.asarray(state.variance, dtype=float)
    if (
        observed.shape != expected.shape
        or excess.shape != observed.shape
        or variance.shape != observed.shape
        or not np.all(np.isfinite(observed))
        or not np.all(np.isfinite(expected))
        or not np.all(np.isfinite(excess))
        or not np.all(np.isfinite(variance))
        or np.any(observed < 0)
        or np.any(expected < 0)
        or np.any(variance < 0)
        or not 0 <= decay <= 1
    ):
        raise ValueError("invalid compensated-CUSUM inputs")
    return InnovationState(
        excess=np.maximum(0.0, decay * excess + observed - expected),
        variance=decay * decay * variance + expected,
    )


def standardized_excess(state: InnovationState, variance_floor: float = 1.0) -> np.ndarray:
    """Return a variance-stabilized positive innovation score."""

    if not np.isfinite(variance_floor) or variance_floor <= 0:
        raise ValueError("variance floor must be finite and positive")
    excess = np.asarray(state.excess, dtype=float)
    variance = np.asarray(state.variance, dtype=float)
    if excess.shape != variance.shape or np.any(variance < 0):
        raise ValueError("innovation state arrays must be equal and valid")
    return excess / np.sqrt(variance + variance_floor)


def graph_coherent_score(
    section_scores: np.ndarray,
    transition: np.ndarray,
    threshold: float,
) -> np.ndarray:
    """Retain excess supported both locally and by neighboring fault sections."""

    scores = np.asarray(section_scores, dtype=float)
    graph = np.asarray(transition, dtype=float)
    if (
        scores.ndim != 1
        or graph.shape != (len(scores), len(scores))
        or not np.all(np.isfinite(scores))
        or not np.all(np.isfinite(graph))
        or np.any(scores < 0)
        or np.any(graph < 0)
        or not np.isfinite(threshold)
        or threshold < 0
        or not np.allclose(np.sum(graph, axis=1), 1.0)
    ):
        raise ValueError("invalid graph-coherence inputs")
    local = np.maximum(scores - threshold, 0.0)
    neighbor = np.maximum(graph @ scores - threshold, 0.0)
    return np.sqrt(local * neighbor)


def consensus_score(particle_scores: np.ndarray, minimum_fraction: float) -> np.ndarray:
    """Shrink a particle mean to zero unless enough branches agree on its sign."""

    scores = np.asarray(particle_scores, dtype=float)
    if (
        scores.ndim != 2
        or not np.all(np.isfinite(scores))
        or np.any(scores < 0)
        or not 0 <= minimum_fraction < 1
    ):
        raise ValueError("invalid consensus inputs")
    support = np.mean(scores > 0, axis=0)
    confidence = np.clip(
        (support - minimum_fraction) / (1.0 - minimum_fraction), 0.0, 1.0
    )
    return np.mean(scores, axis=0) * confidence


def bounded_background_mixture(
    background_rates: np.ndarray,
    emergence_score: np.ndarray,
    mixture_fraction: float,
    sensitivity: float,
    max_log_tilt: float = 4.0,
) -> np.ndarray:
    """Tilt only a bounded fraction of direct background mass."""

    background = np.asarray(background_rates, dtype=float)
    score = np.asarray(emergence_score, dtype=float)
    if (
        background.ndim != 1
        or score.shape != background.shape
        or not np.all(np.isfinite(background))
        or not np.all(np.isfinite(score))
        or np.any(background < 0)
        or np.any(score < 0)
        or np.sum(background) <= 0
        or not 0 <= mixture_fraction <= 1
        or not np.isfinite(sensitivity)
        or sensitivity < 0
        or not np.isfinite(max_log_tilt)
        or max_log_tilt <= 0
    ):
        raise ValueError("invalid bounded-mixture inputs")
    baseline = background / np.sum(background)
    logits = np.minimum(sensitivity * score, max_log_tilt)
    tilted = baseline * np.exp(logits - np.max(logits))
    tilted /= np.sum(tilted)
    probabilities = (1.0 - mixture_fraction) * baseline + mixture_fraction * tilted
    return probabilities * np.sum(background)
