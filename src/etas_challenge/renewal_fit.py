"""Daily fit evaluator for the CH-004 marked-renewal challenger."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from etas_challenge.emergence_fit import strongest_neighbor_transition
from etas_challenge.readiness_fit import FitEvaluation, SparseGeometry
from etas_challenge.readiness_fit import information_gain_per_event, project_sparse_margin
from etas_challenge.renewal_quiescence import bpt_overdue_score
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight
from etas_challenge.renewal_quiescence import update_expected_hazard_age
from etas_challenge.residual_emergence import aggregate_sparse_section_mass
from etas_challenge.residual_emergence import bounded_background_mixture
from etas_challenge.residual_emergence import consensus_score


@dataclass(frozen=True, slots=True)
class RenewalParameters:
    full_reset_magnitude: float
    magnitude_exponent: float
    bpt_aperiodicity: float
    graph_neighborhood_mix: float
    minimum_branch_consensus: float
    background_mixture_fraction: float
    renewal_sensitivity: float

    @classmethod
    def from_array(cls, values: np.ndarray) -> "RenewalParameters":
        array = np.asarray(values, dtype=float)
        if array.shape != (7,) or not np.all(np.isfinite(array)):
            raise ValueError("CH-004 parameters must be seven finite values")
        result = cls(*array.tolist())
        if (
            result.magnitude_exponent <= 0
            or result.bpt_aperiodicity <= 0
            or not 0 <= result.graph_neighborhood_mix <= 1
            or not 0 <= result.minimum_branch_consensus < 1
            or not 0 <= result.background_mixture_fraction <= 0.1
            or result.renewal_sensitivity < 0
        ):
            raise ValueError("CH-004 parameters violate the component contract")
        return result


@dataclass(frozen=True, slots=True)
class RenewalFitEvaluation:
    event_gains: np.ndarray
    event_days: np.ndarray
    challenger_event_rates: np.ndarray
    active_issue_days: int
    expected_reset_weight: float


class RenewalFitEvaluator:
    """Warm and score CH-004 with forecast-before-reset ordering."""

    def __init__(
        self,
        *,
        issue_days: np.ndarray,
        scoring_start_day: int,
        event_days: np.ndarray,
        event_cells: np.ndarray,
        event_magnitudes: np.ndarray,
        event_etas_rates: np.ndarray,
        event_background_probabilities: np.ndarray,
        event_geometries: list[SparseGeometry],
        expected_section_background: np.ndarray,
        adjacency: np.ndarray,
        active_sections: np.ndarray,
        grid_geometries: list[SparseGeometry],
        background_grid: np.ndarray,
        beta: float,
        magnitude_reference: float,
        graph_neighbors: int,
        maximum_log_tilt: float,
    ) -> None:
        self.issue_days = np.asarray(issue_days, dtype=np.int32)
        self.scoring_start_day = int(scoring_start_day)
        self.event_days = np.asarray(event_days, dtype=np.int32)
        self.event_cells = np.asarray(event_cells, dtype=np.int32)
        self.event_magnitudes = np.asarray(event_magnitudes, dtype=float)
        self.event_etas = np.asarray(event_etas_rates, dtype=float)
        self.event_probabilities = np.asarray(event_background_probabilities, dtype=float)
        self.expected_background = np.asarray(expected_section_background, dtype=float)
        self.active = np.asarray(active_sections, dtype=bool)
        self.background_grid = np.asarray(background_grid, dtype=float)
        self.event_geometries = event_geometries
        self.grid_geometries = grid_geometries
        self.beta = float(beta)
        self.magnitude_reference = float(magnitude_reference)
        self.maximum_log_tilt = float(maximum_log_tilt)
        branch_count, section_count = self.expected_background.shape
        event_count = len(self.event_days)
        if (
            self.active.shape != (branch_count, section_count)
            or len(self.event_geometries) != branch_count
            or len(self.grid_geometries) != branch_count
            or np.any(np.diff(self.issue_days) != 1)
            or np.any(np.diff(self.event_days) < 0)
            or self.scoring_start_day not in self.issue_days
            or any(
                array.shape != (event_count,)
                for array in (
                    self.event_cells,
                    self.event_magnitudes,
                    self.event_etas,
                    self.event_probabilities,
                )
            )
        ):
            raise ValueError("CH-004 replay arrays disagree")
        self.transitions = [
            strongest_neighbor_transition(adjacency, active, graph_neighbors)
            for active in self.active
        ]
        self.scoring_event_start = int(
            np.searchsorted(self.event_days, self.scoring_start_day, side="left")
        )

    def evaluate(self, parameter_values: np.ndarray) -> RenewalFitEvaluation:
        parameters = RenewalParameters.from_array(parameter_values)
        expected_mark = expected_reset_weight_gr(
            self.beta,
            self.magnitude_reference,
            parameters.full_reset_magnitude,
            parameters.magnitude_exponent,
        )
        expected_hazard = self.expected_background * expected_mark
        marks = magnitude_reset_weight(
            self.event_magnitudes,
            parameters.full_reset_magnitude,
            parameters.magnitude_exponent,
        )
        marked_roots = self.event_probabilities * marks
        age = np.zeros_like(expected_hazard)
        scored_event_count = len(self.event_days) - self.scoring_event_start
        challenger_rates = np.empty(scored_event_count, dtype=float)
        active_issue_days = 0
        for day in self.issue_days:
            start = int(np.searchsorted(self.event_days, day, side="left"))
            end = int(np.searchsorted(self.event_days, day, side="right"))
            if day >= self.scoring_start_day and end > start:
                branch_grid_scores = np.zeros(
                    (len(self.grid_geometries), len(self.background_grid)), dtype=float
                )
                for branch, geometry in enumerate(self.grid_geometries):
                    neighbor_age = self.transitions[branch] @ age[branch]
                    context_age = (
                        (1.0 - parameters.graph_neighborhood_mix) * age[branch]
                        + parameters.graph_neighborhood_mix * neighbor_age
                    )
                    overdue = bpt_overdue_score(
                        context_age, parameters.bpt_aperiodicity
                    )
                    branch_grid_scores[branch] = project_sparse_margin(
                        overdue[None, :], geometry
                    )[0]
                score = consensus_score(
                    branch_grid_scores, parameters.minimum_branch_consensus
                )
                if np.any(score > 0):
                    active_issue_days += 1
                adjusted = bounded_background_mixture(
                    self.background_grid,
                    score,
                    parameters.background_mixture_fraction,
                    parameters.renewal_sensitivity,
                    self.maximum_log_tilt,
                )
                cells = self.event_cells[start:end]
                output_start = start - self.scoring_event_start
                output_end = end - self.scoring_event_start
                background_delta = adjusted[cells] - self.background_grid[cells]
                challenger_rates[output_start:output_end] = (
                    self.event_etas[start:end] + background_delta
                )

            observed = np.zeros_like(age)
            if end > start:
                for branch, geometry in enumerate(self.event_geometries):
                    day_geometry = SparseGeometry(
                        geometry.section_indexes[start:end],
                        geometry.probabilities[start:end],
                    )
                    observed[branch], _ = aggregate_sparse_section_mass(
                        marked_roots[start:end], day_geometry, age.shape[1]
                    )
            age = update_expected_hazard_age(age, expected_hazard, observed)

        baseline = self.event_etas[self.scoring_event_start :]
        gains = information_gain_per_event(challenger_rates, baseline)
        return RenewalFitEvaluation(
            event_gains=gains,
            event_days=self.event_days[self.scoring_event_start :].copy(),
            challenger_event_rates=challenger_rates,
            active_issue_days=active_issue_days,
            expected_reset_weight=expected_mark,
        )
