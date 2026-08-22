"""Geometry-only mapping between UCERF3 traces and the RELM forecast grid."""

from __future__ import annotations

import numpy as np

from etas_challenge.training_matrix import GridDefinition
from etas_challenge.ucerf3_faults import FaultSection


EARTH_RADIUS_KM = 6371.0088


def _wrapped_longitude_delta(value: np.ndarray | float) -> np.ndarray:
    return (np.asarray(value, dtype=float) + 180.0) % 360.0 - 180.0


def point_to_trace_distance_km(
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    trace_lat_lon: tuple[tuple[float, float], ...],
) -> np.ndarray:
    """Approximate minimum surface distance to a polyline in local segments."""

    latitude = np.asarray(latitudes, dtype=float)
    longitude = np.asarray(longitudes, dtype=float)
    if latitude.shape != longitude.shape or latitude.ndim != 1:
        raise ValueError("point latitude and longitude must be equal vectors")
    trace = np.asarray(trace_lat_lon, dtype=float)
    if trace.ndim != 2 or trace.shape[1] != 2 or len(trace) < 2:
        raise ValueError("fault trace must be an Nx2 array with at least two points")
    if not np.all(np.isfinite(latitude)) or not np.all(np.isfinite(longitude)):
        raise ValueError("point coordinates must be finite")

    radians_per_degree = np.pi / 180.0
    best_squared = np.full(latitude.shape, np.inf)
    for start, end in zip(trace[:-1], trace[1:]):
        reference_latitude = 0.5 * (start[0] + end[0])
        y = (latitude - start[0]) * radians_per_degree * EARTH_RADIUS_KM
        x = (
            _wrapped_longitude_delta(longitude - start[1])
            * radians_per_degree
            * EARTH_RADIUS_KM
            * np.cos(np.radians(reference_latitude))
        )
        segment_y = (end[0] - start[0]) * radians_per_degree * EARTH_RADIUS_KM
        segment_x = (
            _wrapped_longitude_delta(end[1] - start[1])
            * radians_per_degree
            * EARTH_RADIUS_KM
            * np.cos(np.radians(reference_latitude))
        )
        length_squared = float(segment_x**2 + segment_y**2)
        if length_squared == 0:
            distance_squared = x**2 + y**2
        else:
            fraction = np.clip(
                (x * segment_x + y * segment_y) / length_squared, 0.0, 1.0
            )
            distance_squared = (
                (x - fraction * segment_x) ** 2
                + (y - fraction * segment_y) ** 2
            )
        best_squared = np.minimum(best_squared, distance_squared)
    return np.sqrt(best_squared)


def nearest_fault_sections(
    grid: GridDefinition,
    sections: list[FaultSection],
    *,
    neighbors: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Return stable nearest section IDs and trace distances for each grid cell."""

    if not sections or neighbors <= 0 or neighbors > len(sections):
        raise ValueError("neighbors must be between one and the section count")
    section_ids = np.asarray([section.section_id for section in sections])
    if len(np.unique(section_ids)) != len(section_ids):
        raise ValueError("fault section IDs must be unique")
    order = np.argsort(section_ids, kind="stable")
    ordered = [sections[index] for index in order]
    section_ids = section_ids[order]

    scale = grid.units_per_degree
    center_longitudes = (grid.origin_units[:, 0] + 0.5) / scale
    center_latitudes = (grid.origin_units[:, 1] + 0.5) / scale
    return nearest_fault_sections_for_points(
        center_latitudes,
        center_longitudes,
        ordered,
        neighbors=neighbors,
    )


def nearest_fault_sections_for_points(
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    sections: list[FaultSection],
    *,
    neighbors: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    """Return nearest section IDs and exact trace distances for arbitrary points."""

    latitude = np.asarray(latitudes, dtype=float)
    longitude = np.asarray(longitudes, dtype=float)
    if latitude.shape != longitude.shape or latitude.ndim != 1:
        raise ValueError("point latitude and longitude must be equal vectors")
    if not sections or neighbors <= 0 or neighbors > len(sections):
        raise ValueError("neighbors must be between one and the section count")
    section_ids = np.asarray([section.section_id for section in sections])
    if len(np.unique(section_ids)) != len(section_ids):
        raise ValueError("fault section IDs must be unique")
    order = np.argsort(section_ids, kind="stable")
    ordered = [sections[index] for index in order]
    section_ids = section_ids[order]
    distances = np.empty((len(latitude), len(ordered)), dtype=float)
    for index, section in enumerate(ordered):
        distances[:, index] = point_to_trace_distance_km(
            latitude,
            longitude,
            section.trace_lat_lon,
        )
    nearest = np.argsort(distances, axis=1, kind="stable")[:, :neighbors]
    nearest_ids = section_ids[nearest].astype(np.int32)
    nearest_distances = np.take_along_axis(distances, nearest, axis=1).astype(
        np.float32
    )
    return nearest_ids, nearest_distances


def project_section_margin(
    nearest_section_ids: np.ndarray,
    nearest_distances_km: np.ndarray,
    section_ids: np.ndarray,
    section_margins: np.ndarray,
    *,
    bandwidth_km: float,
    cutoff_km: float,
) -> np.ndarray:
    """Project section margins to cells using a normalized Gaussian kernel."""

    nearest_ids = np.asarray(nearest_section_ids)
    distances = np.asarray(nearest_distances_km, dtype=float)
    ids = np.asarray(section_ids)
    margins = np.asarray(section_margins, dtype=float)
    if nearest_ids.shape != distances.shape or nearest_ids.ndim != 2:
        raise ValueError("nearest IDs and distances must be equal matrices")
    if ids.ndim != 1 or margins.shape != ids.shape or len(np.unique(ids)) != len(ids):
        raise ValueError("section IDs and margins must be unique equal vectors")
    if bandwidth_km <= 0 or cutoff_km <= 0:
        raise ValueError("bandwidth and cutoff must be positive")
    lookup = {int(section_id): index for index, section_id in enumerate(ids)}
    try:
        indexes = np.asarray(
            [[lookup[int(value)] for value in row] for row in nearest_ids],
            dtype=int,
        )
    except KeyError as error:
        raise ValueError(f"unknown nearest fault section ID: {error.args[0]}") from error
    weights = np.exp(-0.5 * (distances / bandwidth_km) ** 2)
    weights[distances > cutoff_km] = 0.0
    totals = np.sum(weights, axis=1)
    projected = np.zeros(len(nearest_ids), dtype=float)
    supported = totals > 0
    projected[supported] = (
        np.sum(weights[supported] * margins[indexes[supported]], axis=1)
        / totals[supported]
    )
    return projected
