"""Pure event-wise scoring for published prospective ETAS forecasts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from etas_challenge.prospective_daily import incremental_event_rates


DAY_NS = 86_400 * 1_000_000_000


@dataclass(frozen=True, slots=True)
class DailyScore:
    baseline_rates: np.ndarray
    challenger_rates: np.ndarray
    event_gains: np.ndarray

    def summary(self) -> dict:
        count = len(self.event_gains)
        total = float(np.sum(self.event_gains, dtype=np.float64))
        mean = None if not count else total / count
        return {
            "event_count": count,
            "total_log_likelihood_gain": total,
            "mean_igpe": mean,
            "relative_factor": None if mean is None else float(np.exp(mean)),
            "positive_event_fraction": (
                None if not count else float(np.mean(self.event_gains > 0))
            ),
            "paired_compensator_gain": 0.0,
        }


def score_rate_pairs(baseline_rates: np.ndarray, challenger_rates: np.ndarray) -> DailyScore:
    baseline = np.asarray(baseline_rates, dtype=float)
    challenger = np.asarray(challenger_rates, dtype=float)
    if (
        baseline.shape != challenger.shape
        or baseline.ndim != 1
        or np.any(~np.isfinite(baseline))
        or np.any(~np.isfinite(challenger))
        or np.any(baseline <= 0)
        or np.any(challenger <= 0)
    ):
        raise ValueError("prospective event rates are invalid")
    return DailyScore(baseline, challenger, np.log(challenger / baseline))


def score_california_grid(
    event_cells: np.ndarray,
    baseline_grid_rates: np.ndarray,
    challenger_grid_rates: np.ndarray,
) -> DailyScore:
    cells = np.asarray(event_cells, dtype=np.int32)
    baseline = np.asarray(baseline_grid_rates, dtype=float)
    challenger = np.asarray(challenger_grid_rates, dtype=float)
    if (
        baseline.shape != challenger.shape
        or baseline.ndim != 1
        or np.any(cells < 0)
        or np.any(cells >= len(baseline))
        or not np.isclose(
            np.sum(baseline, dtype=np.float64),
            np.sum(challenger, dtype=np.float64),
            rtol=1e-12,
            atol=1e-12,
        )
    ):
        raise ValueError("California forecast grid contract disagrees")
    return score_rate_pairs(baseline[cells], challenger[cells])


def score_regional_events(
    *,
    history_origin_time_ns: np.ndarray,
    history_latitudes: np.ndarray,
    history_longitudes: np.ndarray,
    history_magnitudes: np.ndarray,
    event_origin_time_ns: np.ndarray,
    event_latitudes: np.ndarray,
    event_longitudes: np.ndarray,
    event_magnitudes: np.ndarray,
    event_cells: np.ndarray,
    cell_areas_km2: np.ndarray,
    baseline_background_mass: np.ndarray,
    challenger_background_mass: np.ndarray,
    magnitude_reference: float,
    etas_parameters: dict[str, float],
) -> DailyScore:
    cells = np.asarray(event_cells, dtype=np.int32)
    areas = np.asarray(cell_areas_km2, dtype=float)
    baseline_mass = np.asarray(baseline_background_mass, dtype=float)
    challenger_mass = np.asarray(challenger_background_mass, dtype=float)
    if (
        areas.shape != baseline_mass.shape
        or areas.shape != challenger_mass.shape
        or areas.ndim != 1
        or np.any(areas <= 0)
        or np.any(baseline_mass <= 0)
        or np.any(challenger_mass <= 0)
        or np.any(cells < 0)
        or np.any(cells >= len(areas))
        or not np.isclose(
            np.sum(baseline_mass, dtype=np.float64),
            np.sum(challenger_mass, dtype=np.float64),
            rtol=1e-12,
            atol=1e-12,
        )
    ):
        raise ValueError("regional forecast background contract disagrees")
    baseline_rates = incremental_event_rates(
        np.asarray(history_origin_time_ns, dtype=np.int64) / DAY_NS,
        history_latitudes,
        history_longitudes,
        history_magnitudes,
        np.asarray(event_origin_time_ns, dtype=np.int64) / DAY_NS,
        event_latitudes,
        event_longitudes,
        event_magnitudes,
        magnitude_reference=magnitude_reference,
        parameters=etas_parameters,
    )
    challenger_rates = baseline_rates + (
        challenger_mass[cells] - baseline_mass[cells]
    ) / areas[cells]
    return score_rate_pairs(baseline_rates, challenger_rates)
