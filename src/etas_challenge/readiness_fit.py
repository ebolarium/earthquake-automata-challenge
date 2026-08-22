"""Conditional spatial fit evaluator for the CH-002 readiness challenger."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit

from etas_challenge.readiness_replay import branch_loading_vector
from etas_challenge.readiness_replay import DAYS_PER_YEAR
from etas_challenge.ucerf3_faults import FaultSection, SLIP_RATE_BRANCHES


@dataclass(frozen=True, slots=True)
class SparseGeometry:
    section_indexes: np.ndarray
    probabilities: np.ndarray


@dataclass(frozen=True, slots=True)
class ReplayParameters:
    loading_gain_per_year: float
    assimilation_gain: float
    release_gain: float
    release_magnitude_exponent: float
    background_tilt_sensitivity: float

    @classmethod
    def from_array(cls, values: np.ndarray) -> "ReplayParameters":
        array = np.asarray(values, dtype=float)
        if array.shape != (5,) or not np.all(np.isfinite(array)) or np.any(array < 0):
            raise ValueError("CH-002 fit parameters must be five finite non-negative values")
        return cls(*array.tolist())


@dataclass(frozen=True, slots=True)
class FitEvaluation:
    event_gains: np.ndarray
    event_days: np.ndarray
    challenger_event_rates: np.ndarray

    def igpe(self, start_day: int, end_day_exclusive: int) -> float:
        selected = (self.event_days >= start_day) & (self.event_days < end_day_exclusive)
        if not np.any(selected):
            raise ValueError("requested score period contains no events")
        return float(np.mean(self.event_gains[selected]))


@dataclass(frozen=True, slots=True)
class _BranchReplay:
    particle_indexes: np.ndarray
    active_sections: np.ndarray
    loading: np.ndarray
    grid_geometry: SparseGeometry
    event_geometry: SparseGeometry


def sparse_geometry(
    nearest_section_ids: np.ndarray,
    nearest_distances_km: np.ndarray,
    section_ids: np.ndarray,
    active_sections: np.ndarray,
    *,
    bandwidth_km: float,
    cutoff_km: float,
    fault_prior_odds: float,
) -> SparseGeometry:
    """Convert nearest traces to branch-aware probabilities plus off-fault mass."""

    nearest_ids = np.asarray(nearest_section_ids)
    distances = np.asarray(nearest_distances_km, dtype=float)
    ids = np.asarray(section_ids)
    active = np.asarray(active_sections, dtype=bool)
    if nearest_ids.shape != distances.shape or nearest_ids.ndim != 2:
        raise ValueError("nearest section IDs and distances must be equal matrices")
    if ids.ndim != 1 or active.shape != ids.shape:
        raise ValueError("section IDs and active mask must be equal vectors")
    lookup = {int(section_id): index for index, section_id in enumerate(ids)}
    indexes = np.full(nearest_ids.shape, -1, dtype=np.int32)
    for row in range(len(nearest_ids)):
        for column, section_id in enumerate(nearest_ids[row]):
            index = lookup.get(int(section_id), -1)
            if index >= 0 and active[index]:
                indexes[row, column] = index
    probabilities = fault_prior_odds * np.exp(-0.5 * (distances / bandwidth_km) ** 2)
    probabilities[(distances > cutoff_km) | (indexes < 0)] = 0.0
    probabilities /= 1.0 + np.sum(probabilities, axis=1, keepdims=True)
    return SparseGeometry(section_indexes=indexes, probabilities=probabilities)


def project_sparse_margin(state: np.ndarray, geometry: SparseGeometry) -> np.ndarray:
    """Project particle section states while retaining zero-valued off-fault mass."""

    margins = np.asarray(state, dtype=float)
    indexes = geometry.section_indexes
    if margins.ndim != 2 or indexes.ndim != 2:
        raise ValueError("state and sparse geometry must be matrices")
    safe_indexes = np.maximum(indexes, 0)
    gathered = margins[:, safe_indexes]
    return np.sum(gathered * geometry.probabilities[None, :, :], axis=2)


def adjusted_background_at_events(
    state: np.ndarray,
    grid_geometry: SparseGeometry,
    background_grid: np.ndarray,
    event_cells: np.ndarray,
    sensitivity: float,
) -> np.ndarray:
    """Return each particle's mass-preserving direct background at event cells."""

    margin = project_sparse_margin(state, grid_geometry)
    logits = sensitivity * margin
    logits -= np.max(logits, axis=1, keepdims=True)
    raw = np.asarray(background_grid, dtype=float)[None, :] * np.exp(logits)
    normalization = np.sum(background_grid) / np.sum(raw, axis=1)
    return raw[:, np.asarray(event_cells, dtype=int)] * normalization[:, None]


def advance_sparse_group(
    state: np.ndarray,
    loading: np.ndarray,
    active: np.ndarray,
    event_geometry: SparseGeometry,
    event_background_probability: np.ndarray,
    event_magnitudes: np.ndarray,
    parameters: ReplayParameters,
) -> np.ndarray:
    """Advance one branch particle group after the issue forecast is scored."""

    result = np.asarray(state, dtype=float).copy()
    result += parameters.loading_gain_per_year * loading / DAYS_PER_YEAR
    for event in range(len(event_magnitudes)):
        indexes = event_geometry.section_indexes[event]
        probabilities = event_geometry.probabilities[event]
        selected = indexes >= 0
        if not np.any(selected):
            continue
        indexes = indexes[selected]
        probabilities = probabilities[selected]
        current = result[:, indexes]
        evidence = (
            parameters.assimilation_gain
            * event_background_probability[event]
            * probabilities[None, :]
            * expit(-current)
        )
        release = parameters.release_gain * 10.0 ** (
            parameters.release_magnitude_exponent * (event_magnitudes[event] - 2.5)
        )
        result[:, indexes] += evidence - release * probabilities[None, :]
    result[:, active] -= np.mean(result[:, active], axis=1, keepdims=True)
    return result


def information_gain_per_event(
    challenger_rates: np.ndarray, etas_rates: np.ndarray
) -> np.ndarray:
    challenger = np.asarray(challenger_rates, dtype=float)
    baseline = np.asarray(etas_rates, dtype=float)
    if (
        challenger.shape != baseline.shape
        or not np.all(np.isfinite(challenger))
        or np.any(challenger < 0)
        or not np.all(np.isfinite(baseline))
        or np.any(baseline <= 0)
    ):
        raise ValueError("challenger and ETAS event rates must be finite valid arrays")
    return np.log(np.maximum(challenger, np.finfo(float).tiny) / baseline)


class ReadinessFitEvaluator:
    """Replay CH-002 and score only conditional spatial event-rate gains."""

    def __init__(
        self,
        *,
        sections: list[FaultSection],
        section_ids: np.ndarray,
        initial_state: np.ndarray,
        particle_branches: np.ndarray,
        grid_nearest_ids: np.ndarray,
        grid_nearest_distances_km: np.ndarray,
        event_nearest_ids: np.ndarray,
        event_nearest_distances_km: np.ndarray,
        background_grid: np.ndarray,
        all_issue_days: np.ndarray,
        event_days: np.ndarray,
        event_cells: np.ndarray,
        event_magnitudes: np.ndarray,
        event_etas_rates: np.ndarray,
        event_background_rates: np.ndarray,
        event_background_probabilities: np.ndarray,
        bandwidth_km: float = 10.0,
        cutoff_km: float = 40.0,
        fault_prior_odds: float = 4.0,
    ) -> None:
        self.sections = sorted(sections, key=lambda section: section.section_id)
        self.section_ids = np.asarray(section_ids)
        self.initial_state = np.asarray(initial_state, dtype=float)
        self.particle_branches = np.asarray(particle_branches)
        self.background_grid = np.asarray(background_grid, dtype=float)
        self.all_issue_days = np.asarray(all_issue_days, dtype=np.int32)
        self.event_days = np.asarray(event_days, dtype=np.int32)
        self.event_cells = np.asarray(event_cells, dtype=np.int32)
        self.event_magnitudes = np.asarray(event_magnitudes, dtype=float)
        self.event_etas_rates = np.asarray(event_etas_rates, dtype=float)
        self.event_background_rates = np.asarray(event_background_rates, dtype=float)
        self.event_background_probabilities = np.asarray(
            event_background_probabilities, dtype=float
        )
        if [section.section_id for section in self.sections] != self.section_ids.tolist():
            raise ValueError("fault sections and initial-state section IDs disagree")
        if self.initial_state.shape != (
            len(self.particle_branches),
            len(self.section_ids),
        ):
            raise ValueError("initial state and particle branches disagree")
        event_count = len(self.event_days)
        event_arrays = (
            self.event_cells,
            self.event_magnitudes,
            self.event_etas_rates,
            self.event_background_rates,
            self.event_background_probabilities,
        )
        if any(array.shape != (event_count,) for array in event_arrays):
            raise ValueError("fit event arrays must have equal lengths")
        if np.any(np.diff(self.all_issue_days) != 1) or np.any(np.diff(self.event_days) < 0):
            raise ValueError("issue days must be contiguous and events time ordered")
        self.branches = []
        for branch in SLIP_RATE_BRANCHES:
            particle_indexes = np.flatnonzero(self.particle_branches == branch)
            if not len(particle_indexes):
                continue
            loading, active = branch_loading_vector(self.sections, branch)
            self.branches.append(
                _BranchReplay(
                    particle_indexes=particle_indexes,
                    active_sections=active,
                    loading=loading,
                    grid_geometry=sparse_geometry(
                        grid_nearest_ids,
                        grid_nearest_distances_km,
                        self.section_ids,
                        active,
                        bandwidth_km=bandwidth_km,
                        cutoff_km=cutoff_km,
                        fault_prior_odds=fault_prior_odds,
                    ),
                    event_geometry=sparse_geometry(
                        event_nearest_ids,
                        event_nearest_distances_km,
                        self.section_ids,
                        active,
                        bandwidth_km=bandwidth_km,
                        cutoff_km=cutoff_km,
                        fault_prior_odds=fault_prior_odds,
                    ),
                )
            )
        if sum(len(branch.particle_indexes) for branch in self.branches) != len(
            self.particle_branches
        ):
            raise ValueError("not all particles have an admitted loading branch")

    def evaluate(self, parameter_values: np.ndarray) -> FitEvaluation:
        parameters = ReplayParameters.from_array(parameter_values)
        state = self.initial_state.copy()
        challenger_rates = np.empty(len(self.event_days), dtype=float)
        for day in self.all_issue_days:
            start = int(np.searchsorted(self.event_days, day, side="left"))
            end = int(np.searchsorted(self.event_days, day, side="right"))
            if end > start:
                cells = self.event_cells[start:end]
                adjusted_sum = np.zeros(end - start, dtype=float)
                for branch in self.branches:
                    adjusted = adjusted_background_at_events(
                        state[branch.particle_indexes],
                        branch.grid_geometry,
                        self.background_grid,
                        cells,
                        parameters.background_tilt_sensitivity,
                    )
                    adjusted_sum += np.sum(adjusted, axis=0)
                adjusted_mean = adjusted_sum / len(self.particle_branches)
                triggered = np.maximum(
                    self.event_etas_rates[start:end]
                    - self.event_background_rates[start:end],
                    0.0,
                )
                challenger_rates[start:end] = triggered + adjusted_mean

            for branch in self.branches:
                selected_state = state[branch.particle_indexes]
                if end > start:
                    geometry = SparseGeometry(
                        branch.event_geometry.section_indexes[start:end],
                        branch.event_geometry.probabilities[start:end],
                    )
                    state[branch.particle_indexes] = advance_sparse_group(
                        selected_state,
                        branch.loading,
                        branch.active_sections,
                        geometry,
                        self.event_background_probabilities[start:end],
                        self.event_magnitudes[start:end],
                        parameters,
                    )
                else:
                    state[branch.particle_indexes] = selected_state + (
                        parameters.loading_gain_per_year
                        * branch.loading
                        / DAYS_PER_YEAR
                    )
        gains = information_gain_per_event(challenger_rates, self.event_etas_rates)
        return FitEvaluation(
            event_gains=gains,
            event_days=self.event_days.copy(),
            challenger_event_rates=challenger_rates,
        )
