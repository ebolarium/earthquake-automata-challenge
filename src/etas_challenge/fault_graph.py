"""Fault-network geometry and seeded initial-state ensemble for CH-002."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from etas_challenge.fault_grid import EARTH_RADIUS_KM, _wrapped_longitude_delta
from etas_challenge.ucerf3_faults import FaultSection


@dataclass(frozen=True, slots=True)
class FaultGraph:
    section_ids: np.ndarray
    trace_distance_km: np.ndarray
    axial_alignment: np.ndarray
    shared_fault_model: np.ndarray
    adjacency: np.ndarray


@dataclass(frozen=True, slots=True)
class InitialStateEnsemble:
    stress_component: np.ndarray
    effective_strength_component: np.ndarray
    criticality_margin: np.ndarray


def condition_ensemble_on_branch_masks(
    ensemble: InitialStateEnsemble, active_masks: np.ndarray
) -> InitialStateEnsemble:
    """Center and scale each particle only on its admitted fault-model branch."""

    stress = np.asarray(ensemble.stress_component, dtype=float).copy()
    strength = np.asarray(ensemble.effective_strength_component, dtype=float).copy()
    masks = np.asarray(active_masks, dtype=bool)
    if stress.shape != strength.shape or masks.shape != stress.shape:
        raise ValueError("ensemble components and branch masks must have equal shapes")
    for particle, active in enumerate(masks):
        if np.count_nonzero(active) < 2:
            raise ValueError("each particle branch must contain at least two sections")
        stress[particle, active] -= np.mean(stress[particle, active])
        strength[particle, active] -= np.mean(strength[particle, active])
        stress[particle, ~active] = 0.0
        strength[particle, ~active] = 0.0
        scale = float(np.std(stress[particle, active] - strength[particle, active]))
        if scale <= 0:
            raise ValueError("branch-conditioned particle has zero dispersion")
        stress[particle, active] /= scale
        strength[particle, active] /= scale
    return InitialStateEnsemble(
        stress_component=stress,
        effective_strength_component=strength,
        criticality_margin=stress - strength,
    )


def _trace_xy(
    trace_lat_lon: tuple[tuple[float, float], ...],
    reference_latitude: float,
    reference_longitude: float,
) -> np.ndarray:
    trace = np.asarray(trace_lat_lon, dtype=float)
    scale = np.pi * EARTH_RADIUS_KM / 180.0
    return np.column_stack(
        (
            _wrapped_longitude_delta(trace[:, 1] - reference_longitude)
            * scale
            * np.cos(np.radians(reference_latitude)),
            (trace[:, 0] - reference_latitude) * scale,
        )
    )


def _cross(left: np.ndarray, right: np.ndarray) -> float:
    return float(left[0] * right[1] - left[1] * right[0])


def _point_segment_distance(
    point: np.ndarray, start: np.ndarray, end: np.ndarray
) -> float:
    segment = end - start
    length_squared = float(segment @ segment)
    if length_squared == 0:
        return float(np.linalg.norm(point - start))
    fraction = float(np.clip(((point - start) @ segment) / length_squared, 0, 1))
    return float(np.linalg.norm(point - (start + fraction * segment)))


def _segment_distance(
    a_start: np.ndarray,
    a_end: np.ndarray,
    b_start: np.ndarray,
    b_end: np.ndarray,
) -> float:
    a_vector = a_end - a_start
    b_vector = b_end - b_start
    denominator = _cross(a_vector, b_vector)
    offset = b_start - a_start
    if abs(denominator) > 1e-12:
        along_a = _cross(offset, b_vector) / denominator
        along_b = _cross(offset, a_vector) / denominator
        if 0 <= along_a <= 1 and 0 <= along_b <= 1:
            return 0.0
    return min(
        _point_segment_distance(a_start, b_start, b_end),
        _point_segment_distance(a_end, b_start, b_end),
        _point_segment_distance(b_start, a_start, a_end),
        _point_segment_distance(b_end, a_start, a_end),
    )


def polyline_distance_km(
    first: tuple[tuple[float, float], ...],
    second: tuple[tuple[float, float], ...],
) -> float:
    """Minimum segment distance after a common local California projection."""

    first_array = np.asarray(first, dtype=float)
    second_array = np.asarray(second, dtype=float)
    if (
        first_array.ndim != 2
        or second_array.ndim != 2
        or first_array.shape[1] != 2
        or second_array.shape[1] != 2
        or len(first_array) < 2
        or len(second_array) < 2
    ):
        raise ValueError("both traces must contain at least two lat/lon vertices")
    reference_latitude = float(
        np.mean(np.concatenate((first_array[:, 0], second_array[:, 0])))
    )
    longitude_values = np.concatenate((first_array[:, 1], second_array[:, 1]))
    reference_longitude = float(longitude_values[0])
    first_xy = _trace_xy(first, reference_latitude, reference_longitude)
    second_xy = _trace_xy(second, reference_latitude, reference_longitude)
    best = np.inf
    for a_start, a_end in zip(first_xy[:-1], first_xy[1:]):
        for b_start, b_end in zip(second_xy[:-1], second_xy[1:]):
            best = min(best, _segment_distance(a_start, a_end, b_start, b_end))
            if best == 0:
                return 0.0
    return float(best)


def axial_strike_degrees(
    trace_lat_lon: tuple[tuple[float, float], ...],
) -> float:
    """Length-weighted axial strike in [0, 180), insensitive to trace direction."""

    trace = np.asarray(trace_lat_lon, dtype=float)
    if trace.ndim != 2 or trace.shape[1] != 2 or len(trace) < 2:
        raise ValueError("trace must contain at least two lat/lon vertices")
    reference_latitude = float(np.mean(trace[:, 0]))
    xy = _trace_xy(trace_lat_lon, reference_latitude, float(trace[0, 1]))
    segments = np.diff(xy, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    valid = lengths > 0
    if not np.any(valid):
        raise ValueError("trace cannot contain only repeated vertices")
    strikes = np.arctan2(segments[valid, 0], segments[valid, 1])
    axial = np.sum(lengths[valid] * np.exp(2j * strikes))
    result = float(np.degrees(0.5 * np.angle(axial)) % 180.0)
    return 0.0 if np.isclose(result, 180.0, atol=1e-12) else result


def build_fault_graph(
    sections: list[FaultSection],
    *,
    correlation_length_km: float = 25.0,
    alignment_floor: float = 0.25,
) -> FaultGraph:
    """Build a symmetric geometry-weighted graph without target observations."""

    if not sections or correlation_length_km <= 0:
        raise ValueError("sections and correlation length must be positive")
    if not 0 <= alignment_floor <= 1:
        raise ValueError("alignment_floor must be between zero and one")
    ordered = sorted(sections, key=lambda section: section.section_id)
    section_ids = np.asarray([section.section_id for section in ordered], dtype=np.int32)
    if len(np.unique(section_ids)) != len(section_ids):
        raise ValueError("fault section IDs must be unique")
    count = len(ordered)
    distances = np.zeros((count, count), dtype=float)
    strikes = np.asarray(
        [axial_strike_degrees(section.trace_lat_lon) for section in ordered]
    )
    for left in range(count):
        for right in range(left + 1, count):
            distance = polyline_distance_km(
                ordered[left].trace_lat_lon, ordered[right].trace_lat_lon
            )
            distances[left, right] = distances[right, left] = distance
    difference = np.radians(strikes[:, None] - strikes[None, :])
    alignment = np.abs(np.cos(difference))
    fm31 = np.asarray([section.in_fault_model_3_1 for section in ordered])
    fm32 = np.asarray([section.in_fault_model_3_2 for section in ordered])
    shared = (fm31[:, None] & fm31[None, :]) | (fm32[:, None] & fm32[None, :])
    orientation_weight = alignment_floor + (1.0 - alignment_floor) * alignment**2
    adjacency = (
        np.exp(-0.5 * (distances / correlation_length_km) ** 2)
        * orientation_weight
        * shared
    )
    np.fill_diagonal(adjacency, 0.0)
    return FaultGraph(
        section_ids=section_ids,
        trace_distance_km=distances.astype(np.float32),
        axial_alignment=alignment.astype(np.float32),
        shared_fault_model=shared,
        adjacency=adjacency.astype(np.float32),
    )


def sample_initial_state_ensemble(
    adjacency: np.ndarray,
    *,
    particles: int = 256,
    seed: int = 20260822,
    graph_smoothness: float = 4.0,
) -> InitialStateEnsemble:
    """Sample stress-minus-strength particles from a graph-Laplacian prior."""

    weights = np.asarray(adjacency, dtype=float)
    if (
        weights.ndim != 2
        or weights.shape[0] != weights.shape[1]
        or not np.all(np.isfinite(weights))
        or np.any(weights < 0)
        or not np.allclose(weights, weights.T, rtol=0, atol=1e-12)
    ):
        raise ValueError("adjacency must be a finite symmetric non-negative matrix")
    if particles <= 1 or graph_smoothness < 0:
        raise ValueError("particles must exceed one and smoothness cannot be negative")
    degree = np.sum(weights, axis=1)
    inverse_root = np.zeros_like(degree)
    connected = degree > 0
    inverse_root[connected] = 1.0 / np.sqrt(degree[connected])
    normalized_adjacency = weights * inverse_root[:, None] * inverse_root[None, :]
    laplacian = np.eye(len(weights)) - normalized_adjacency
    precision = np.eye(len(weights)) + graph_smoothness * laplacian
    cholesky = np.linalg.cholesky(precision)
    rng = np.random.default_rng(seed)

    def draw() -> np.ndarray:
        innovations = rng.standard_normal((len(weights), particles))
        return np.linalg.solve(cholesky.T, innovations).T

    stress = draw()
    strength = draw()
    stress -= np.mean(stress, axis=1, keepdims=True)
    strength -= np.mean(strength, axis=1, keepdims=True)
    margin = stress - strength
    scale = np.std(margin, axis=1, keepdims=True)
    if np.any(scale <= 0):
        raise ValueError("initial-state particle has zero dispersion")
    stress /= scale
    strength /= scale
    margin = stress - strength
    return InitialStateEnsemble(
        stress_component=stress,
        effective_strength_component=strength,
        criticality_margin=margin,
    )
