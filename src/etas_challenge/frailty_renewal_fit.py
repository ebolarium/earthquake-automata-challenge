"""Leakage-free replay for the CH-006 frailty-renewal challenger."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from etas_challenge.fault_frailty import discounted_gamma_poisson_update
from etas_challenge.fault_frailty import positive_frailty_score
from etas_challenge.fault_frailty import posterior_log_frailty
from etas_challenge.readiness_fit import SparseGeometry, information_gain_per_event
from etas_challenge.readiness_fit import project_sparse_margin
from etas_challenge.renewal_fit import RenewalFitEvaluation, RenewalFitEvaluator
from etas_challenge.renewal_fit import RenewalParameters
from etas_challenge.renewal_quiescence import bpt_overdue_score
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight
from etas_challenge.renewal_quiescence import update_expected_hazard_age
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.residual_emergence import bounded_background_mixture, consensus_score


@dataclass(frozen=True, slots=True)
class FrailtyRenewalParameters:
    prior_exposure: float
    memory_half_life_days: float
    frailty_neighborhood_mix: float
    minimum_log_frailty: float
    frailty_weight: float
    renewal_weight: float
    background_mixture_fraction: float

    @classmethod
    def from_array(cls, values: np.ndarray) -> "FrailtyRenewalParameters":
        array = np.asarray(values, dtype=float)
        if array.shape != (7,) or not np.all(np.isfinite(array)):
            raise ValueError("CH-006 parameters must be seven finite values")
        result = cls(*array.tolist())
        if (
            result.prior_exposure <= 0
            or result.memory_half_life_days <= 0
            or not 0 <= result.frailty_neighborhood_mix <= 1
            or result.minimum_log_frailty < 0
            or result.frailty_weight < 0
            or result.renewal_weight < 0
            or not 0 <= result.background_mixture_fraction <= 1
        ):
            raise ValueError("CH-006 parameters violate the component contract")
        return result


class FrailtyRenewalFitEvaluator:
    """Add sequential latent fault strength to an unchanged CH-004 replay."""

    def __init__(self, parent: RenewalFitEvaluator) -> None:
        self.parent = parent

    def evaluate(
        self,
        parent_parameter_values: np.ndarray,
        parameter_values: np.ndarray,
    ) -> RenewalFitEvaluation:
        base = self.parent
        parent = RenewalParameters.from_array(parent_parameter_values)
        parameters = FrailtyRenewalParameters.from_array(parameter_values)
        expected_mark = expected_reset_weight_gr(
            base.beta,
            base.magnitude_reference,
            parent.full_reset_magnitude,
            parent.magnitude_exponent,
        )
        expected_hazard = base.expected_background * expected_mark
        marks = magnitude_reset_weight(
            base.event_magnitudes,
            parent.full_reset_magnitude,
            parent.magnitude_exponent,
        )
        marked_roots = base.event_probabilities * marks
        age = np.zeros_like(expected_hazard)
        exposure = np.zeros_like(expected_hazard)
        roots = np.zeros_like(expected_hazard)
        scored_event_count = len(base.event_days) - base.scoring_event_start
        challenger_rates = np.empty(scored_event_count, dtype=float)
        active_issue_days = 0

        for day in base.issue_days:
            start = int(np.searchsorted(base.event_days, day, side="left"))
            end = int(np.searchsorted(base.event_days, day, side="right"))
            if day >= base.scoring_start_day and end > start:
                branch_grid_scores = np.zeros(
                    (len(base.grid_geometries), len(base.background_grid)), dtype=float
                )
                for branch, geometry in enumerate(base.grid_geometries):
                    neighbor_age = base.transitions[branch] @ age[branch]
                    context_age = (
                        (1.0 - parent.graph_neighborhood_mix) * age[branch]
                        + parent.graph_neighborhood_mix * neighbor_age
                    )
                    overdue = bpt_overdue_score(context_age, parent.bpt_aperiodicity)
                    log_frailty = posterior_log_frailty(
                        exposure[branch], roots[branch], parameters.prior_exposure
                    )
                    frailty = positive_frailty_score(
                        log_frailty,
                        base.transitions[branch] @ log_frailty,
                        parameters.frailty_neighborhood_mix,
                        parameters.minimum_log_frailty,
                    )
                    section_score = (
                        parameters.renewal_weight * overdue
                        + parameters.frailty_weight * frailty
                    )
                    branch_grid_scores[branch] = project_sparse_margin(
                        section_score[None, :], geometry
                    )[0]
                score = consensus_score(
                    branch_grid_scores, parent.minimum_branch_consensus
                )
                if np.any(score > 0):
                    active_issue_days += 1
                adjusted = bounded_background_mixture(
                    base.background_grid,
                    score,
                    parameters.background_mixture_fraction,
                    1.0,
                    base.maximum_log_tilt,
                )
                cells = base.event_cells[start:end]
                output_start = start - base.scoring_event_start
                output_end = end - base.scoring_event_start
                challenger_rates[output_start:output_end] = (
                    base.event_etas[start:end]
                    + adjusted[cells]
                    - base.background_grid[cells]
                )

            observed = np.zeros_like(age)
            observed_marked = np.zeros_like(age)
            if end > start:
                for branch, geometry in enumerate(base.event_geometries):
                    day_geometry = SparseGeometry(
                        geometry.section_indexes[start:end],
                        geometry.probabilities[start:end],
                    )
                    observed[branch], _ = aggregate_sparse_section_mass(
                        base.event_probabilities[start:end], day_geometry, age.shape[1]
                    )
                    observed_marked[branch], _ = aggregate_sparse_section_mass(
                        marked_roots[start:end], day_geometry, age.shape[1]
                    )
            age = update_expected_hazard_age(age, expected_hazard, observed_marked)
            exposure, roots = discounted_gamma_poisson_update(
                exposure,
                roots,
                base.expected_background,
                observed,
                parameters.memory_half_life_days,
            )

        baseline = base.event_etas[base.scoring_event_start :]
        return RenewalFitEvaluation(
            event_gains=information_gain_per_event(challenger_rates, baseline),
            event_days=base.event_days[base.scoring_event_start :].copy(),
            challenger_event_rates=challenger_rates,
            active_issue_days=active_issue_days,
            expected_reset_weight=expected_mark,
        )
