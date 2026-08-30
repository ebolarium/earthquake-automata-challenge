"""Pure daily forecast and post-observation updates for prospective CH-008."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from etas_challenge.etas_native import haversine_squared_km
from etas_challenge.fault_frailty import discounted_gamma_poisson_update
from etas_challenge.fault_frailty import positive_frailty_score
from etas_challenge.fault_frailty import posterior_log_frailty
from etas_challenge.prospective_replay import CH008State
from etas_challenge.readiness_fit import SparseGeometry, project_sparse_margin
from etas_challenge.renewal_fit import RenewalParameters
from etas_challenge.renewal_quiescence import bpt_overdue_score
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight
from etas_challenge.renewal_quiescence import update_expected_hazard_age
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.residual_emergence import bounded_background_mixture
from etas_challenge.residual_emergence import consensus_score


@dataclass(frozen=True, slots=True)
class DailyBackgroundForecast:
    baseline_mass: np.ndarray
    challenger_mass: np.ndarray
    score: np.ndarray


def regional_background_forecast(
    state: CH008State,
    *,
    background_mass: np.ndarray,
    transition,
    parent_parameters: dict[str, float],
    ch008_parameters: dict[str, float],
) -> DailyBackgroundForecast:
    """Return the pre-observation regional background forecast for one day."""

    background = np.asarray(background_mass, dtype=float)
    age = np.asarray(state.age, dtype=float)
    exposure = np.asarray(state.exposure, dtype=float)
    roots = np.asarray(state.roots, dtype=float)
    if any(value.shape != background.shape for value in (age, exposure, roots)):
        raise ValueError("regional forecast state shape disagrees")
    parent = RenewalParameters.from_array(
        np.asarray(
            [
                parent_parameters[name]
                for name in (
                    "full_reset_magnitude", "magnitude_exponent", "bpt_aperiodicity",
                    "graph_neighborhood_mix", "minimum_branch_consensus",
                    "background_mixture_fraction", "renewal_sensitivity",
                )
            ]
        )
    )
    neighbor_age = transition @ age
    context_age = (
        (1.0 - parent.graph_neighborhood_mix) * age
        + parent.graph_neighborhood_mix * neighbor_age
    )
    overdue = bpt_overdue_score(context_age, parent.bpt_aperiodicity)
    log_frailty = posterior_log_frailty(
        exposure, roots, ch008_parameters["prior_exposure"]
    )
    frailty = positive_frailty_score(
        log_frailty,
        transition @ log_frailty,
        ch008_parameters["frailty_neighborhood_mix"],
        ch008_parameters["minimum_log_frailty"],
    )
    score = (
        ch008_parameters["renewal_weight"] * overdue
        + ch008_parameters["frailty_weight"] * frailty
    )
    challenger = bounded_background_mixture(
        background,
        score,
        ch008_parameters["background_mixture_fraction"],
        1.0,
        4.0,
    )
    return DailyBackgroundForecast(background.copy(), challenger, score)


def advance_regional_day(
    state: CH008State,
    *,
    event_cells: np.ndarray,
    event_magnitudes: np.ndarray,
    event_background_probabilities: np.ndarray,
    background_mass: np.ndarray,
    beta: float,
    magnitude_reference: float,
    renewal_scale: float,
    parent_parameters: dict[str, float],
    ch008_parameters: dict[str, float],
) -> CH008State:
    """Assimilate one completed regional day after its forecast was issued."""

    cells = np.asarray(event_cells, dtype=np.int32)
    magnitudes = np.asarray(event_magnitudes, dtype=float)
    probabilities = np.asarray(event_background_probabilities, dtype=float)
    background = np.asarray(background_mass, dtype=float)
    if (
        cells.shape != magnitudes.shape
        or cells.shape != probabilities.shape
        or np.any(cells < 0)
        or np.any(cells >= len(background))
        or np.any(probabilities < 0)
        or np.any(probabilities > 1)
        or renewal_scale <= 0
    ):
        raise ValueError("regional daily observations disagree")
    marks = magnitude_reset_weight(
        magnitudes,
        parent_parameters["full_reset_magnitude"],
        parent_parameters["magnitude_exponent"],
    )
    expected_mark = expected_reset_weight_gr(
        beta,
        magnitude_reference,
        parent_parameters["full_reset_magnitude"],
        parent_parameters["magnitude_exponent"],
    )
    observed = np.zeros_like(background)
    observed_marked = np.zeros_like(background)
    if len(cells):
        np.add.at(observed, cells, probabilities)
        np.add.at(observed_marked, cells, renewal_scale * probabilities * marks)
    age = update_expected_hazard_age(
        state.age,
        renewal_scale * background * expected_mark,
        observed_marked,
    )
    exposure, roots = discounted_gamma_poisson_update(
        state.exposure,
        state.roots,
        background,
        observed,
        ch008_parameters["memory_half_life_days"],
    )
    return CH008State(age, exposure, roots)


def california_background_forecast(
    state: CH008State,
    *,
    background_grid: np.ndarray,
    transitions: list,
    grid_geometries: list[SparseGeometry],
    parent_parameter_values: np.ndarray,
    ch008_parameters: dict[str, float],
    maximum_log_tilt: float = 4.0,
) -> DailyBackgroundForecast:
    """Return the pre-observation California CH-008 background grid."""

    parent = RenewalParameters.from_array(parent_parameter_values)
    background = np.asarray(background_grid, dtype=float)
    branches = len(transitions)
    if (
        state.age.shape != state.exposure.shape
        or state.age.shape != state.roots.shape
        or state.age.ndim != 2
        or state.age.shape[0] != branches
        or len(grid_geometries) != branches
    ):
        raise ValueError("California forecast state shape disagrees")
    branch_scores = np.zeros((branches, len(background)), dtype=float)
    for branch, geometry in enumerate(grid_geometries):
        neighbor_age = transitions[branch] @ state.age[branch]
        context_age = (
            (1.0 - parent.graph_neighborhood_mix) * state.age[branch]
            + parent.graph_neighborhood_mix * neighbor_age
        )
        overdue = bpt_overdue_score(context_age, parent.bpt_aperiodicity)
        log_frailty = posterior_log_frailty(
            state.exposure[branch],
            state.roots[branch],
            ch008_parameters["prior_exposure"],
        )
        frailty = positive_frailty_score(
            log_frailty,
            transitions[branch] @ log_frailty,
            ch008_parameters["frailty_neighborhood_mix"],
            ch008_parameters["minimum_log_frailty"],
        )
        section_score = (
            ch008_parameters["renewal_weight"] * overdue
            + ch008_parameters["frailty_weight"] * frailty
        )
        branch_scores[branch] = project_sparse_margin(
            section_score[None, :], geometry
        )[0]
    score = consensus_score(branch_scores, parent.minimum_branch_consensus)
    challenger = bounded_background_mixture(
        background,
        score,
        ch008_parameters["background_mixture_fraction"],
        1.0,
        maximum_log_tilt,
    )
    return DailyBackgroundForecast(background.copy(), challenger, score)


def advance_california_day(
    state: CH008State,
    *,
    event_geometries: list[SparseGeometry],
    event_magnitudes: np.ndarray,
    event_background_probabilities: np.ndarray,
    expected_section_background: np.ndarray,
    beta: float,
    magnitude_reference: float,
    parent_parameters: dict[str, float],
    ch008_parameters: dict[str, float],
) -> CH008State:
    """Assimilate one completed California day after its forecast was issued."""

    expected = np.asarray(expected_section_background, dtype=float)
    magnitudes = np.asarray(event_magnitudes, dtype=float)
    probabilities = np.asarray(event_background_probabilities, dtype=float)
    if (
        state.age.shape != expected.shape
        or state.exposure.shape != expected.shape
        or state.roots.shape != expected.shape
        or len(event_geometries) != len(expected)
        or magnitudes.shape != probabilities.shape
        or np.any(probabilities < 0)
        or np.any(probabilities > 1)
    ):
        raise ValueError("California daily observations disagree")
    marks = magnitude_reset_weight(
        magnitudes,
        parent_parameters["full_reset_magnitude"],
        parent_parameters["magnitude_exponent"],
    )
    expected_mark = expected_reset_weight_gr(
        beta,
        magnitude_reference,
        parent_parameters["full_reset_magnitude"],
        parent_parameters["magnitude_exponent"],
    )
    observed = np.zeros_like(expected)
    observed_marked = np.zeros_like(expected)
    for branch, geometry in enumerate(event_geometries):
        observed[branch], _ = aggregate_sparse_section_mass(
            probabilities, geometry, expected.shape[1]
        )
        observed_marked[branch], _ = aggregate_sparse_section_mass(
            probabilities * marks, geometry, expected.shape[1]
        )
    age = update_expected_hazard_age(
        state.age, expected * expected_mark, observed_marked
    )
    exposure, roots = discounted_gamma_poisson_update(
        state.exposure,
        state.roots,
        expected,
        observed,
        ch008_parameters["memory_half_life_days"],
    )
    return CH008State(age, exposure, roots)


def incremental_event_rates(
    history_times_days: np.ndarray,
    history_latitudes: np.ndarray,
    history_longitudes: np.ndarray,
    history_magnitudes: np.ndarray,
    new_times_days: np.ndarray,
    new_latitudes: np.ndarray,
    new_longitudes: np.ndarray,
    new_magnitudes: np.ndarray,
    *,
    magnitude_reference: float,
    parameters: dict[str, float],
) -> np.ndarray:
    """Evaluate only appended ETAS events while retaining strict prior ordering."""

    history = tuple(
        np.asarray(value, dtype=float)
        for value in (
            history_times_days, history_latitudes, history_longitudes, history_magnitudes
        )
    )
    new = tuple(
        np.asarray(value, dtype=float)
        for value in (new_times_days, new_latitudes, new_longitudes, new_magnitudes)
    )
    if (
        len({value.shape for value in history}) != 1
        or len({value.shape for value in new}) != 1
        or history[0].ndim != 1
        or new[0].ndim != 1
        or np.any(np.diff(history[0]) < 0)
        or np.any(np.diff(new[0]) < 0)
        or (len(history[0]) and len(new[0]) and new[0][0] < history[0][-1])
        or not all(np.all(np.isfinite(value)) for value in (*history, *new))
    ):
        raise ValueError("incremental ETAS event arrays disagree")
    mu = 10.0 ** parameters["log10_mu"]
    k0 = 10.0 ** parameters["log10_k0"]
    c = 10.0 ** parameters["log10_c"]
    tau = 10.0 ** parameters["log10_tau"]
    d = 10.0 ** parameters["log10_d"]
    result = np.full(len(new[0]), mu, dtype=float)
    all_times = np.concatenate((history[0], new[0]))
    all_lats = np.concatenate((history[1], new[1]))
    all_lons = np.concatenate((history[2], new[2]))
    all_mags = np.concatenate((history[3], new[3]))
    offset = len(history[0])
    for output, index in enumerate(range(offset, len(all_times))):
        delta = all_times[index] - all_times[:index]
        distance_squared = haversine_squared_km(
            all_lats[index], all_lons[index], all_lats[:index], all_lons[:index]
        )
        productivity = k0 * np.exp(
            parameters["a"] * (all_mags[:index] - magnitude_reference)
        )
        temporal = np.exp(-delta / tau) / (delta + c) ** (1.0 + parameters["omega"])
        spatial = 1.0 / (
            distance_squared
            + d * np.exp(parameters["gamma"] * (all_mags[:index] - magnitude_reference))
        ) ** (1.0 + parameters["rho"])
        result[output] += np.sum(productivity * temporal * spatial)
    if np.any(~np.isfinite(result)) or np.any(result <= 0):
        raise ValueError("incremental ETAS produced invalid rates")
    return result
