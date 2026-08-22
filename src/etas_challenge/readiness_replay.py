"""Leakage-free daily state evolution primitives for CH-002."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit

from etas_challenge.fault_grid import point_to_trace_distance_km
from etas_challenge.ucerf3_faults import FaultSection
from etas_challenge.ucerf3_faults import SLIP_RATE_BRANCHES


DAYS_PER_YEAR = 365.2425


@dataclass(frozen=True, slots=True)
class ObservedEvent:
    latitude: float
    longitude: float
    magnitude: float
    etas_background_probability: float


@dataclass(frozen=True, slots=True)
class StateEvolutionParameters:
    loading_gain_per_year: float
    assimilation_gain: float
    release_gain: float
    release_magnitude_exponent: float
    reference_magnitude: float = 2.5
    assignment_bandwidth_km: float = 10.0
    assignment_cutoff_km: float = 40.0
    fault_prior_odds: float = 4.0

    def validate(self) -> None:
        values = (
            self.loading_gain_per_year,
            self.assimilation_gain,
            self.release_gain,
            self.release_magnitude_exponent,
            self.reference_magnitude,
            self.assignment_bandwidth_km,
            self.assignment_cutoff_km,
            self.fault_prior_odds,
        )
        if not all(np.isfinite(value) for value in values):
            raise ValueError("state-evolution parameters must be finite")
        if any(value < 0 for value in values[:4]):
            raise ValueError("state-evolution gains and exponent cannot be negative")
        if (
            self.assignment_bandwidth_km <= 0
            or self.assignment_cutoff_km <= 0
            or self.fault_prior_odds <= 0
        ):
            raise ValueError("assignment scales and prior odds must be positive")


def branch_loading_vector(
    sections: list[FaultSection], branch: str
) -> tuple[np.ndarray, np.ndarray]:
    """Return centered unit-RMS seismic loading and the admitted branch mask."""

    if not sections:
        raise ValueError("fault sections cannot be empty")
    values = np.zeros(len(sections), dtype=float)
    active = np.zeros(len(sections), dtype=bool)
    for index, section in enumerate(sections):
        slip = section.slip_rate_mm_per_year.get(branch)
        aseismicity = section.aseismicity_factor.get(branch)
        coupling = section.coupling_coefficient.get(branch)
        if slip is None:
            continue
        if aseismicity is None or coupling is None:
            raise ValueError(f"incomplete loading terms for section {section.section_id}")
        if slip < 0 or not 0 <= aseismicity <= 1 or not 0 <= coupling <= 1:
            raise ValueError(f"invalid loading terms for section {section.section_id}")
        values[index] = slip * (1.0 - aseismicity) * coupling
        active[index] = True
    if np.count_nonzero(active) < 2:
        raise ValueError(f"loading branch has fewer than two sections: {branch}")
    values[active] -= np.mean(values[active])
    rms = float(np.sqrt(np.mean(values[active] ** 2)))
    if rms <= 0:
        raise ValueError(f"loading branch has no spatial contrast: {branch}")
    values[active] /= rms
    return values, active


def event_section_assignment(
    sections: list[FaultSection],
    active_sections: np.ndarray,
    *,
    latitude: float,
    longitude: float,
    bandwidth_km: float,
    cutoff_km: float,
    fault_prior_odds: float,
) -> tuple[np.ndarray, float]:
    """Assign an event probabilistically to nearby traces plus an off-fault state."""

    active = np.asarray(active_sections, dtype=bool)
    if active.shape != (len(sections),):
        raise ValueError("active-section mask must match the fault sections")
    if (
        not np.isfinite(latitude)
        or not np.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise ValueError("event coordinates must be finite")
    if bandwidth_km <= 0 or cutoff_km <= 0 or fault_prior_odds <= 0:
        raise ValueError("assignment scales and prior odds must be positive")
    distances = np.full(len(sections), np.inf)
    for index in np.flatnonzero(active):
        distances[index] = point_to_trace_distance_km(
            np.asarray([latitude]),
            np.asarray([longitude]),
            sections[index].trace_lat_lon,
        )[0]
    weights = fault_prior_odds * np.exp(-0.5 * (distances / bandwidth_km) ** 2)
    weights[(distances > cutoff_km) | ~active] = 0.0
    total = 1.0 + float(np.sum(weights))
    return weights / total, 1.0 / total


def advance_daily_state(
    criticality_margin: np.ndarray,
    loading_vector: np.ndarray,
    sections: list[FaultSection],
    active_sections: np.ndarray,
    events: list[ObservedEvent],
    parameters: StateEvolutionParameters,
) -> np.ndarray:
    """Close one observed day and return state for the next forecast issue."""

    parameters.validate()
    original = np.asarray(criticality_margin, dtype=float)
    state = original.copy()
    loading = np.asarray(loading_vector, dtype=float)
    active = np.asarray(active_sections, dtype=bool)
    if state.ndim != 2 or state.shape[1] != len(sections):
        raise ValueError("criticality margin must be particles by fault sections")
    if loading.shape != (len(sections),) or active.shape != loading.shape:
        raise ValueError("loading and active mask must match fault sections")
    if not np.all(np.isfinite(state)) or not np.all(np.isfinite(loading)):
        raise ValueError("state and loading must be finite")

    state += parameters.loading_gain_per_year * loading / DAYS_PER_YEAR
    for event in events:
        if (
            not np.isfinite(event.magnitude)
            or not parameters.reference_magnitude <= event.magnitude <= 10.0
            or not 0 <= event.etas_background_probability <= 1
        ):
            raise ValueError("event magnitude and ETAS probability are invalid")
        assignment, _ = event_section_assignment(
            sections,
            active,
            latitude=event.latitude,
            longitude=event.longitude,
            bandwidth_km=parameters.assignment_bandwidth_km,
            cutoff_km=parameters.assignment_cutoff_km,
            fault_prior_odds=parameters.fault_prior_odds,
        )
        evidence = (
            parameters.assimilation_gain
            * event.etas_background_probability
            * assignment[None, :]
            * expit(-state)
        )
        release_amplitude = parameters.release_gain * 10.0 ** (
            parameters.release_magnitude_exponent
            * (event.magnitude - parameters.reference_magnitude)
        )
        state += evidence - release_amplitude * assignment[None, :]

    state[:, ~active] = original[:, ~active]
    active_mean = np.mean(state[:, active], axis=1, keepdims=True)
    state[:, active] -= active_mean
    return state


def balanced_particle_branches(particles: int) -> np.ndarray:
    """Assign equal particle counts to all eight locked UCERF3 branches."""

    if particles <= 0 or particles % len(SLIP_RATE_BRANCHES):
        raise ValueError("particle count must be a positive multiple of eight")
    return np.repeat(
        np.asarray(SLIP_RATE_BRANCHES), particles // len(SLIP_RATE_BRANCHES)
    )


def advance_branch_ensemble(
    criticality_margin: np.ndarray,
    particle_branches: np.ndarray,
    sections: list[FaultSection],
    events: list[ObservedEvent],
    parameters: StateEvolutionParameters,
) -> np.ndarray:
    """Advance all particles without selecting one UCERF3 deformation branch."""

    state = np.asarray(criticality_margin, dtype=float)
    branches = np.asarray(particle_branches)
    if state.ndim != 2 or branches.shape != (state.shape[0],):
        raise ValueError("particle branches must match the state particle axis")
    if not set(branches.tolist()).issubset(SLIP_RATE_BRANCHES):
        raise ValueError("particle ensemble contains an unknown loading branch")
    result = state.copy()
    for branch in SLIP_RATE_BRANCHES:
        selected = branches == branch
        if not np.any(selected):
            continue
        loading, active = branch_loading_vector(sections, branch)
        result[selected] = advance_daily_state(
            state[selected], loading, sections, active, events, parameters
        )
    return result
