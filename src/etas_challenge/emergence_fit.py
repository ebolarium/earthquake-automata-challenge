"""Fit-period evaluator for the CH-003 residual-emergence challenger."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix

from etas_challenge.readiness_fit import FitEvaluation, SparseGeometry, project_sparse_margin
from etas_challenge.residual_emergence import InnovationState
from etas_challenge.residual_emergence import bounded_background_mixture
from etas_challenge.residual_emergence import consensus_score
from etas_challenge.residual_emergence import standardized_excess
from etas_challenge.residual_emergence import update_compensated_cusum
from etas_challenge.readiness_fit import information_gain_per_event


@dataclass(frozen=True, slots=True)
class EmergenceParameters:
    memory_half_life_days: float
    standardized_threshold: float
    graph_diffusion: float
    minimum_branch_consensus: float
    background_mixture_fraction: float
    emergence_sensitivity: float

    @classmethod
    def from_array(cls, values: np.ndarray) -> "EmergenceParameters":
        array = np.asarray(values, dtype=float)
        if array.shape != (6,) or not np.all(np.isfinite(array)):
            raise ValueError("CH-003 parameters must be six finite values")
        result = cls(*array.tolist())
        if (
            result.memory_half_life_days <= 0
            or result.standardized_threshold < 0
            or not 0 <= result.graph_diffusion <= 1
            or not 0 <= result.minimum_branch_consensus < 1
            or not 0 <= result.background_mixture_fraction <= 0.1
            or result.emergence_sensitivity < 0
        ):
            raise ValueError("CH-003 parameters violate the component contract")
        return result


def strongest_neighbor_transition(
    adjacency: np.ndarray,
    active_sections: np.ndarray,
    neighbors: int,
) -> csr_matrix:
    """Return a deterministic row-stochastic graph of strongest active neighbors."""

    graph = np.asarray(adjacency, dtype=float)
    active = np.asarray(active_sections, dtype=bool)
    if (
        graph.ndim != 2
        or graph.shape[0] != graph.shape[1]
        or active.shape != (len(graph),)
        or not np.all(np.isfinite(graph))
        or np.any(graph < 0)
        or neighbors <= 0
    ):
        raise ValueError("invalid strongest-neighbor inputs")
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    active_indexes = np.flatnonzero(active)
    for row in active_indexes:
        candidates = active_indexes[(active_indexes != row) & (graph[row, active_indexes] > 0)]
        if not len(candidates):
            rows.append(int(row))
            columns.append(int(row))
            values.append(1.0)
            continue
        ordered = sorted(candidates, key=lambda column: (-graph[row, column], int(column)))
        selected = np.asarray(ordered[:neighbors], dtype=int)
        weights = graph[row, selected]
        weights /= np.sum(weights)
        rows.extend([int(row)] * len(selected))
        columns.extend(selected.tolist())
        values.extend(weights.tolist())
    return csr_matrix((values, (rows, columns)), shape=graph.shape)


def annual_robust_score(event_gains: np.ndarray, event_days: np.ndarray) -> tuple[float, dict[int, float]]:
    gains = np.asarray(event_gains, dtype=float)
    days = np.asarray(event_days, dtype=np.int64)
    if gains.shape != days.shape or gains.ndim != 1 or not len(gains):
        raise ValueError("annual score requires equal non-empty event arrays")
    years = (np.datetime64("1970-01-01") + days.astype("timedelta64[D]")).astype(
        "datetime64[Y]"
    ).astype(int) + 1970
    by_year = {int(year): float(np.mean(gains[years == year])) for year in np.unique(years)}
    values = np.asarray(list(by_year.values()))
    return float(np.mean(values) - np.std(values)), by_year


def candidate_is_admissible(
    mean_igpe: float,
    robust_score: float,
    annual_igpe: dict[int, float],
    low_etas_igpe: float,
    annual_loss_floor: float,
) -> bool:
    return bool(
        mean_igpe > 0
        and robust_score > 0
        and min(annual_igpe.values()) >= annual_loss_floor
        and low_etas_igpe >= 0
    )


class EmergenceFitEvaluator:
    """Replay CH-003 with forecast-before-observation daily ordering."""

    def __init__(
        self,
        *,
        issue_days: np.ndarray,
        observed_root_mass: np.ndarray,
        expected_daily_root_mass: np.ndarray,
        adjacency: np.ndarray,
        active_sections: np.ndarray,
        grid_geometries: list[SparseGeometry],
        background_grid: np.ndarray,
        event_days: np.ndarray,
        event_cells: np.ndarray,
        event_etas_rates: np.ndarray,
        event_background_rates: np.ndarray,
        graph_neighbors: int,
        variance_floor: float,
        maximum_log_tilt: float,
    ) -> None:
        self.issue_days = np.asarray(issue_days, dtype=np.int32)
        self.observed = np.asarray(observed_root_mass, dtype=float)
        self.expected = np.asarray(expected_daily_root_mass, dtype=float)
        self.active = np.asarray(active_sections, dtype=bool)
        self.background = np.asarray(background_grid, dtype=float)
        self.event_days = np.asarray(event_days, dtype=np.int32)
        self.event_cells = np.asarray(event_cells, dtype=np.int32)
        self.event_etas = np.asarray(event_etas_rates, dtype=float)
        self.event_background = np.asarray(event_background_rates, dtype=float)
        self.grid_geometries = grid_geometries
        self.variance_floor = float(variance_floor)
        self.maximum_log_tilt = float(maximum_log_tilt)
        branch_count = self.observed.shape[1] if self.observed.ndim == 3 else 0
        section_count = self.observed.shape[2] if self.observed.ndim == 3 else 0
        if (
            self.observed.shape != (len(self.issue_days), branch_count, section_count)
            or self.expected.shape != (branch_count, section_count)
            or self.active.shape != (branch_count, section_count)
            or len(self.grid_geometries) != branch_count
            or np.any(np.diff(self.issue_days) != 1)
            or np.any(np.diff(self.event_days) < 0)
            or any(
                array.shape != (len(self.event_days),)
                for array in (self.event_cells, self.event_etas, self.event_background)
            )
        ):
            raise ValueError("CH-003 replay arrays disagree")
        self.transitions = [
            strongest_neighbor_transition(adjacency, active, graph_neighbors)
            for active in self.active
        ]

    def evaluate(self, parameter_values: np.ndarray) -> FitEvaluation:
        parameters = EmergenceParameters.from_array(parameter_values)
        decay = 0.5 ** (1.0 / parameters.memory_half_life_days)
        state = InnovationState(
            np.zeros_like(self.expected, dtype=float),
            np.zeros_like(self.expected, dtype=float),
        )
        challenger_rates = np.empty(len(self.event_days), dtype=float)
        for day_index, day in enumerate(self.issue_days):
            start = int(np.searchsorted(self.event_days, day, side="left"))
            end = int(np.searchsorted(self.event_days, day, side="right"))
            if end > start:
                standardized = standardized_excess(state, self.variance_floor)
                branch_grid_scores = np.zeros(
                    (len(self.grid_geometries), len(self.background)), dtype=float
                )
                for branch, geometry in enumerate(self.grid_geometries):
                    neighbor = self.transitions[branch] @ standardized[branch]
                    context = (
                        (1.0 - parameters.graph_diffusion) * standardized[branch]
                        + parameters.graph_diffusion * neighbor
                    )
                    local = np.maximum(
                        standardized[branch] - parameters.standardized_threshold, 0.0
                    )
                    supported = np.maximum(
                        context - parameters.standardized_threshold, 0.0
                    )
                    coherent = np.sqrt(local * supported)
                    branch_grid_scores[branch] = project_sparse_margin(
                        coherent[None, :], geometry
                    )[0]
                score = consensus_score(
                    branch_grid_scores, parameters.minimum_branch_consensus
                )
                adjusted = bounded_background_mixture(
                    self.background,
                    score,
                    parameters.background_mixture_fraction,
                    parameters.emergence_sensitivity,
                    self.maximum_log_tilt,
                )
                cells = self.event_cells[start:end]
                background_delta = adjusted[cells] - self.background[cells]
                challenger_rates[start:end] = self.event_etas[start:end] + background_delta
            state = update_compensated_cusum(
                state,
                self.observed[day_index],
                self.expected,
                decay,
            )
        gains = information_gain_per_event(challenger_rates, self.event_etas)
        return FitEvaluation(gains, self.event_days.copy(), challenger_rates)
