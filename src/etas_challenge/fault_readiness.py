"""Mass-preserving primitives for the CH-002 latent fault-readiness model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class ForecastComponents:
    """ETAS rates split into direct background and all triggered activity."""

    triggered: np.ndarray
    background: np.ndarray


def decompose_etas_rates(
    etas_rates: np.ndarray,
    direct_background_rates: np.ndarray,
    *,
    tolerance: float = 1e-7,
) -> ForecastComponents:
    """Remove only the analytical direct-background component from ETAS."""

    total = np.asarray(etas_rates, dtype=float)
    background = np.asarray(direct_background_rates, dtype=float)
    if total.shape != background.shape or total.ndim == 0:
        raise ValueError("ETAS and background rates must have equal array shapes")
    if not np.all(np.isfinite(total)) or not np.all(np.isfinite(background)):
        raise ValueError("forecast rates must be finite")
    if np.any(total <= 0) or np.any(background <= 0):
        raise ValueError("forecast rates must be positive")
    residual = total - background
    scale = np.maximum(total, background)
    if np.any(residual < -tolerance * scale):
        raise ValueError("direct background cannot exceed the ETAS rate")
    return ForecastComponents(
        triggered=np.maximum(residual, 0.0),
        background=background.copy(),
    )


def redistribute_background(
    direct_background_rates: np.ndarray,
    criticality_margin: np.ndarray,
    *,
    sensitivity: float,
) -> np.ndarray:
    """Tilt direct background by readiness while preserving its exact mass.

    The analytical ETAS background is the spatial prior. A zero margin or zero
    sensitivity therefore returns that prior exactly.
    """

    background = np.asarray(direct_background_rates, dtype=float)
    margin = np.asarray(criticality_margin, dtype=float)
    if background.shape != margin.shape or background.ndim == 0:
        raise ValueError("background rates and margins must have equal shapes")
    if not np.all(np.isfinite(background)) or np.any(background <= 0):
        raise ValueError("background rates must be finite and positive")
    if not np.all(np.isfinite(margin)) or not np.isfinite(sensitivity):
        raise ValueError("margin and sensitivity must be finite")
    if sensitivity < 0:
        raise ValueError("sensitivity must be non-negative")

    logits = sensitivity * margin
    logits -= np.max(logits)
    weights = background * np.exp(logits)
    return weights * (np.sum(background) / np.sum(weights))


def compose_readiness_forecast(
    etas_rates: np.ndarray,
    direct_background_rates: np.ndarray,
    criticality_margin: np.ndarray,
    *,
    sensitivity: float,
) -> np.ndarray:
    """Preserve ETAS triggering and replace only direct-background allocation."""

    components = decompose_etas_rates(etas_rates, direct_background_rates)
    adjusted = redistribute_background(
        components.background,
        criticality_margin,
        sensitivity=sensitivity,
    )
    return components.triggered + adjusted


def advance_criticality_margin(
    margin: np.ndarray,
    loading_rate: np.ndarray,
    rupture_release: np.ndarray,
    directional_transfer: np.ndarray,
    *,
    elapsed_days: float = 1.0,
) -> np.ndarray:
    """Advance a dimensionless stress-minus-strength proxy by one issue step."""

    state = np.asarray(margin, dtype=float)
    loading = np.asarray(loading_rate, dtype=float)
    release = np.asarray(rupture_release, dtype=float)
    transfer = np.asarray(directional_transfer, dtype=float)
    if not (state.shape == loading.shape == release.shape == transfer.shape):
        raise ValueError("all readiness state arrays must have equal shapes")
    if state.ndim == 0 or not all(
        np.all(np.isfinite(value)) for value in (state, loading, release, transfer)
    ):
        raise ValueError("readiness state arrays must be finite and non-scalar")
    if not np.isfinite(elapsed_days) or elapsed_days <= 0:
        raise ValueError("elapsed_days must be finite and positive")
    if np.any(release < 0):
        raise ValueError("rupture release must be non-negative")
    return state + loading * elapsed_days - release + transfer


def etas_background_probability(
    etas_rates: np.ndarray, direct_background_rates: np.ndarray
) -> np.ndarray:
    """Return P(direct background | event cell) under frozen ETAS rates."""

    components = decompose_etas_rates(etas_rates, direct_background_rates)
    return components.background / (components.triggered + components.background)
