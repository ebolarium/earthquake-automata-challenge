"""State-only replays for prospective ETAS and CH-008 activation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from etas_challenge.fault_frailty import discounted_gamma_poisson_update
from etas_challenge.readiness_fit import SparseGeometry
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.renewal_fit import RenewalFitEvaluator, RenewalParameters
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight
from etas_challenge.renewal_quiescence import update_expected_hazard_age


@dataclass(frozen=True, slots=True)
class CH008State:
    age: np.ndarray
    exposure: np.ndarray
    roots: np.ndarray


def replay_regional_ch008_state(
    *,
    event_days: np.ndarray,
    event_cells: np.ndarray,
    event_magnitudes: np.ndarray,
    event_background_probabilities: np.ndarray,
    background_mass: np.ndarray,
    beta: float,
    magnitude_reference: float,
    issue_day_start: int,
    issue_day_end_exclusive: int,
    renewal_scale: float,
    parent_parameters: dict[str, float],
    ch008_parameters: dict[str, float],
) -> CH008State:
    """Replay normalized regional CH-008 without reading scored outcomes."""

    days = np.asarray(event_days, dtype=np.int64)
    cells = np.asarray(event_cells, dtype=np.int32)
    magnitudes = np.asarray(event_magnitudes, dtype=float)
    probabilities = np.asarray(event_background_probabilities, dtype=float)
    background = np.asarray(background_mass, dtype=float)
    if (
        any(len(value) != len(days) for value in (cells, magnitudes, probabilities))
        or np.any(np.diff(days) < 0)
        or np.any(cells < 0)
        or np.any(cells >= len(background))
        or np.any(probabilities < 0)
        or np.any(probabilities > 1)
        or not np.isfinite(renewal_scale)
        or renewal_scale <= 0
    ):
        raise ValueError("regional CH-008 state inputs disagree")
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
    expected_hazard = renewal_scale * background * expected_mark
    age = np.zeros_like(background)
    exposure = np.zeros_like(background)
    roots = np.zeros_like(background)
    for day in range(issue_day_start, issue_day_end_exclusive):
        start = int(np.searchsorted(days, day, side="left"))
        end = int(np.searchsorted(days, day, side="right"))
        observed = np.zeros_like(background)
        observed_marked = np.zeros_like(background)
        if end > start:
            np.add.at(observed, cells[start:end], probabilities[start:end])
            np.add.at(
                observed_marked,
                cells[start:end],
                renewal_scale * probabilities[start:end] * marks[start:end],
            )
        age = update_expected_hazard_age(age, expected_hazard, observed_marked)
        exposure, roots = discounted_gamma_poisson_update(
            exposure,
            roots,
            background,
            observed,
            ch008_parameters["memory_half_life_days"],
        )
    return CH008State(age, exposure, roots)


def replay_california_ch008_state(
    evaluator: RenewalFitEvaluator,
    parent_parameter_values: np.ndarray,
    ch008_parameter_values: np.ndarray,
) -> CH008State:
    """Replay the exact California CH-008 update order to its terminal state."""

    from etas_challenge.frailty_renewal_fit import FrailtyRenewalParameters

    parent = RenewalParameters.from_array(parent_parameter_values)
    parameters = FrailtyRenewalParameters.from_array(ch008_parameter_values)
    expected_mark = expected_reset_weight_gr(
        evaluator.beta,
        evaluator.magnitude_reference,
        parent.full_reset_magnitude,
        parent.magnitude_exponent,
    )
    expected_hazard = evaluator.expected_background * expected_mark
    marks = magnitude_reset_weight(
        evaluator.event_magnitudes,
        parent.full_reset_magnitude,
        parent.magnitude_exponent,
    )
    marked_roots = evaluator.event_probabilities * marks
    age = np.zeros_like(expected_hazard)
    exposure = np.zeros_like(expected_hazard)
    roots = np.zeros_like(expected_hazard)
    for day in evaluator.issue_days:
        start = int(np.searchsorted(evaluator.event_days, day, side="left"))
        end = int(np.searchsorted(evaluator.event_days, day, side="right"))
        observed = np.zeros_like(age)
        observed_marked = np.zeros_like(age)
        if end > start:
            for branch, geometry in enumerate(evaluator.event_geometries):
                day_geometry = SparseGeometry(
                    geometry.section_indexes[start:end],
                    geometry.probabilities[start:end],
                )
                observed[branch], _ = aggregate_sparse_section_mass(
                    evaluator.event_probabilities[start:end], day_geometry, age.shape[1]
                )
                observed_marked[branch], _ = aggregate_sparse_section_mass(
                    marked_roots[start:end], day_geometry, age.shape[1]
                )
        age = update_expected_hazard_age(age, expected_hazard, observed_marked)
        exposure, roots = discounted_gamma_poisson_update(
            exposure,
            roots,
            evaluator.expected_background,
            observed,
            parameters.memory_half_life_days,
        )
    return CH008State(age, exposure, roots)
