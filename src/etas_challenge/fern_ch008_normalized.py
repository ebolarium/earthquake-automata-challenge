"""Exposure-normalized regional renewal clock for one CH-008 development test."""

from __future__ import annotations

import numpy as np

from etas_challenge.fault_frailty import discounted_gamma_poisson_update
from etas_challenge.fault_frailty import positive_frailty_score
from etas_challenge.fault_frailty import posterior_log_frailty
from etas_challenge.fern_ch008 import RegionalEvaluation, RegionalGrid
from etas_challenge.readiness_fit import information_gain_per_event
from etas_challenge.renewal_quiescence import bpt_overdue_score
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight
from etas_challenge.renewal_quiescence import update_expected_hazard_age
from etas_challenge.residual_emergence import bounded_background_mixture


def prevalidation_exposure_scale(
    background_mass: np.ndarray,
    prevalidation_days: float,
    target_mean_cell_exposure: float = 1.0,
) -> float:
    """Calibrate one outcome-free clock scale from pre-validation ETAS exposure."""

    background = np.asarray(background_mass, dtype=float)
    mean_exposure = float(np.mean(background) * prevalidation_days)
    if (
        background.ndim != 1
        or not len(background)
        or np.any(~np.isfinite(background))
        or np.any(background <= 0)
        or not np.isfinite(mean_exposure)
        or mean_exposure <= 0
        or not np.isfinite(target_mean_cell_exposure)
        or target_mean_cell_exposure <= 0
    ):
        raise ValueError("invalid regional renewal exposure calibration")
    return target_mean_cell_exposure / mean_exposure


def evaluate_exposure_normalized_ch008(
    *,
    event_days: np.ndarray,
    event_cells: np.ndarray,
    event_magnitudes: np.ndarray,
    etas_rates: np.ndarray,
    etas_mu: float,
    beta: float,
    magnitude_reference: float,
    grid: RegionalGrid,
    issue_day_start: int,
    issue_day_end_exclusive: int,
    prevalidation_days: float,
    parent_parameters: dict[str, float],
    ch008_parameters: dict[str, float],
    target_mean_cell_exposure: float = 1.0,
) -> tuple[RegionalEvaluation, float]:
    """Replay CH-008 with a pre-validation-calibrated renewal time scale."""

    days = np.asarray(event_days, dtype=np.int64)
    cells = np.asarray(event_cells, dtype=np.int32)
    magnitudes = np.asarray(event_magnitudes, dtype=float)
    baseline = np.asarray(etas_rates, dtype=float)
    if any(len(value) != len(days) for value in (cells, magnitudes, baseline)):
        raise ValueError("normalized CH-008 event arrays disagree")
    background_mass = etas_mu * grid.areas_km2
    renewal_scale = prevalidation_exposure_scale(
        background_mass, prevalidation_days, target_mean_cell_exposure
    )
    event_background = np.divide(
        etas_mu, baseline, out=np.zeros_like(baseline), where=baseline > 0
    )
    expected_mark = expected_reset_weight_gr(
        beta,
        magnitude_reference,
        parent_parameters["full_reset_magnitude"],
        parent_parameters["magnitude_exponent"],
    )
    marks = magnitude_reset_weight(
        magnitudes,
        parent_parameters["full_reset_magnitude"],
        parent_parameters["magnitude_exponent"],
    )
    expected_hazard = renewal_scale * background_mass * expected_mark
    age = np.zeros_like(background_mass)
    exposure = np.zeros_like(background_mass)
    roots = np.zeros_like(background_mass)
    challenger = baseline.copy()

    for day in range(issue_day_start, issue_day_end_exclusive):
        start = int(np.searchsorted(days, day, side="left"))
        end = int(np.searchsorted(days, day, side="right"))
        neighbor_age = grid.transition @ age
        context_age = (
            (1.0 - parent_parameters["graph_neighborhood_mix"]) * age
            + parent_parameters["graph_neighborhood_mix"] * neighbor_age
        )
        overdue = bpt_overdue_score(context_age, parent_parameters["bpt_aperiodicity"])
        log_frailty = posterior_log_frailty(
            exposure, roots, ch008_parameters["prior_exposure"]
        )
        frailty = positive_frailty_score(
            log_frailty,
            grid.transition @ log_frailty,
            ch008_parameters["frailty_neighborhood_mix"],
            ch008_parameters["minimum_log_frailty"],
        )
        score = (
            ch008_parameters["renewal_weight"] * overdue
            + ch008_parameters["frailty_weight"] * frailty
        )
        adjusted_mass = bounded_background_mixture(
            background_mass,
            score,
            ch008_parameters["background_mixture_fraction"],
            1.0,
            4.0,
        )
        if end > start:
            chosen = cells[start:end]
            challenger[start:end] += (
                adjusted_mass[chosen] - background_mass[chosen]
            ) / grid.areas_km2[chosen]
        observed = np.zeros_like(background_mass)
        observed_marked = np.zeros_like(background_mass)
        if end > start:
            np.add.at(observed, cells[start:end], event_background[start:end])
            np.add.at(
                observed_marked,
                cells[start:end],
                renewal_scale * event_background[start:end] * marks[start:end],
            )
        age = update_expected_hazard_age(age, expected_hazard, observed_marked)
        exposure, roots = discounted_gamma_poisson_update(
            exposure,
            roots,
            background_mass,
            observed,
            ch008_parameters["memory_half_life_days"],
        )
    return (
        RegionalEvaluation(
            information_gain_per_event(challenger, baseline),
            challenger,
            event_background,
        ),
        renewal_scale,
    )
