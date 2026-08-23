"""Daily evaluator for the CH-009 phase-coherent hazard-debt challenger."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from etas_challenge.fault_frailty import posterior_log_frailty
from etas_challenge.fault_frailty import positive_frailty_score
from etas_challenge.fault_frailty import discounted_gamma_poisson_update
from etas_challenge.frailty_renewal_fit import FrailtyRenewalParameters
from etas_challenge.phase_coherent_debt import FrailtyTrendState
from etas_challenge.phase_coherent_debt import phase_coherent_hazard_debt
from etas_challenge.phase_coherent_debt import positive_frailty_acceleration
from etas_challenge.phase_coherent_debt import update_frailty_trend
from etas_challenge.readiness_fit import SparseGeometry, information_gain_per_event
from etas_challenge.readiness_fit import project_sparse_margin
from etas_challenge.renewal_fit import RenewalFitEvaluator, RenewalParameters
from etas_challenge.renewal_quiescence import bpt_overdue_score
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight
from etas_challenge.renewal_quiescence import update_expected_hazard_age
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.residual_emergence import bounded_background_mixture
from etas_challenge.residual_emergence import consensus_score


@dataclass(frozen=True, slots=True)
class PhaseCoherentDebtParameters:
    short_half_life_days: float
    long_to_short_half_life_ratio: float
    minimum_acceleration: float
    coherence_mix: float
    phase_weight: float

    @classmethod
    def from_array(cls, values: np.ndarray) -> "PhaseCoherentDebtParameters":
        array = np.asarray(values, dtype=float)
        if array.shape != (5,) or not np.all(np.isfinite(array)):
            raise ValueError("CH-009 parameters must be five finite values")
        result = cls(*array.tolist())
        if (
            result.short_half_life_days <= 0
            or result.long_to_short_half_life_ratio <= 1
            or result.minimum_acceleration < 0
            or not 0 <= result.coherence_mix <= 1
            or result.phase_weight < 0
        ):
            raise ValueError("CH-009 parameters violate the component contract")
        return result

    @property
    def long_half_life_days(self) -> float:
        return self.short_half_life_days * self.long_to_short_half_life_ratio


@dataclass(frozen=True, slots=True)
class PhaseCoherentDebtEvaluation:
    event_gains: np.ndarray
    event_days: np.ndarray
    challenger_event_rates: np.ndarray
    active_issue_days: int
    phase_active_issue_days: int
    expected_reset_weight: float


class PhaseCoherentDebtFitEvaluator:
    """Add a causal phase-coherence interaction to unchanged CH-008."""

    def __init__(self, parent: RenewalFitEvaluator) -> None:
        self.parent = parent
        self.phase_transitions = [transition.toarray() for transition in parent.transitions]

    def evaluate(
        self,
        parent_parameter_values: np.ndarray,
        frailty_parameter_values: np.ndarray,
        phase_parameter_values: np.ndarray,
    ) -> PhaseCoherentDebtEvaluation:
        base = self.parent
        parent = RenewalParameters.from_array(parent_parameter_values)
        frailty_parameters = FrailtyRenewalParameters.from_array(
            frailty_parameter_values
        )
        phase_parameters = PhaseCoherentDebtParameters.from_array(
            phase_parameter_values
        )
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
        trend = FrailtyTrendState(
            short_mean=np.zeros_like(expected_hazard),
            long_mean=np.zeros_like(expected_hazard),
        )
        scored_event_count = len(base.event_days) - base.scoring_event_start
        challenger_rates = np.empty(scored_event_count, dtype=float)
        active_issue_days = 0
        phase_active_issue_days = 0

        for day in base.issue_days:
            start = int(np.searchsorted(base.event_days, day, side="left"))
            end = int(np.searchsorted(base.event_days, day, side="right"))
            log_frailty = posterior_log_frailty(
                exposure, roots, frailty_parameters.prior_exposure
            )
            trend = update_frailty_trend(
                trend,
                log_frailty,
                phase_parameters.short_half_life_days,
                phase_parameters.long_half_life_days,
            )
            acceleration = positive_frailty_acceleration(
                trend, phase_parameters.minimum_acceleration
            )

            if day >= base.scoring_start_day and end > start:
                branch_grid_scores = np.zeros(
                    (len(base.grid_geometries), len(base.background_grid)), dtype=float
                )
                branch_phase_active = False
                for branch, geometry in enumerate(base.grid_geometries):
                    neighbor_age = base.transitions[branch] @ age[branch]
                    context_age = (
                        (1.0 - parent.graph_neighborhood_mix) * age[branch]
                        + parent.graph_neighborhood_mix * neighbor_age
                    )
                    overdue = bpt_overdue_score(
                        context_age, parent.bpt_aperiodicity
                    )
                    frailty = positive_frailty_score(
                        log_frailty[branch],
                        base.transitions[branch] @ log_frailty[branch],
                        frailty_parameters.frailty_neighborhood_mix,
                        frailty_parameters.minimum_log_frailty,
                    )
                    phase = phase_coherent_hazard_debt(
                        overdue,
                        frailty,
                        acceleration[branch],
                        self.phase_transitions[branch],
                        phase_parameters.coherence_mix,
                    )
                    branch_phase_active = branch_phase_active or bool(np.any(phase > 0))
                    section_score = (
                        frailty_parameters.renewal_weight * overdue
                        + frailty_parameters.frailty_weight * frailty
                        + phase_parameters.phase_weight * phase
                    )
                    branch_grid_scores[branch] = project_sparse_margin(
                        section_score[None, :], geometry
                    )[0]
                if branch_phase_active:
                    phase_active_issue_days += 1
                score = consensus_score(
                    branch_grid_scores, parent.minimum_branch_consensus
                )
                if np.any(score > 0):
                    active_issue_days += 1
                adjusted = bounded_background_mixture(
                    base.background_grid,
                    score,
                    frailty_parameters.background_mixture_fraction,
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
                        base.event_probabilities[start:end],
                        day_geometry,
                        age.shape[1],
                    )
                    observed_marked[branch], _ = aggregate_sparse_section_mass(
                        marked_roots[start:end],
                        day_geometry,
                        age.shape[1],
                    )
            age = update_expected_hazard_age(age, expected_hazard, observed_marked)
            exposure, roots = discounted_gamma_poisson_update(
                exposure,
                roots,
                base.expected_background,
                observed,
                frailty_parameters.memory_half_life_days,
            )

        baseline = base.event_etas[base.scoring_event_start :]
        return PhaseCoherentDebtEvaluation(
            event_gains=information_gain_per_event(challenger_rates, baseline),
            event_days=base.event_days[base.scoring_event_start :].copy(),
            challenger_event_rates=challenger_rates,
            active_issue_days=active_issue_days,
            phase_active_issue_days=phase_active_issue_days,
            expected_reset_weight=expected_mark,
        )
