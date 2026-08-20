"""Low-memory vectorized replay of event-level ETAS likelihood terms."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.special import exp1, gamma as gamma_function, gammaincc

from etas_challenge.parameters import ETASParameters


@dataclass(frozen=True, slots=True)
class ReplayCatalog:
    times: np.ndarray
    latitudes: np.ndarray
    longitudes: np.ndarray
    magnitudes: np.ndarray

    def __post_init__(self) -> None:
        raw_times = np.asarray(self.times)
        times = (
            raw_times.astype("datetime64[ns]")
            if raw_times.dtype.kind == "M"
            else raw_times.astype(float)
        )
        arrays = (
            times,
            np.asarray(self.latitudes, dtype=float),
            np.asarray(self.longitudes, dtype=float),
            np.asarray(self.magnitudes, dtype=float),
        )
        if not arrays[0].size:
            raise ValueError("catalog must contain at least one event")
        if len({array.shape for array in arrays}) != 1:
            raise ValueError("catalog arrays must have identical shapes")
        if arrays[0].ndim != 1:
            raise ValueError("catalog arrays must be one-dimensional")
        if np.issubdtype(times.dtype, np.datetime64):
            valid_times = not np.any(np.isnat(times))
            increasing = np.all(np.diff(times) > np.timedelta64(0, "ns"))
        else:
            valid_times = np.all(np.isfinite(times))
            increasing = np.all(np.diff(times) > 0)
        if not valid_times or not all(
            np.all(np.isfinite(array)) for array in arrays[1:]
        ):
            raise ValueError("catalog arrays must contain only finite values")
        if not increasing:
            raise ValueError("catalog times must be strictly increasing")
        object.__setattr__(self, "times", arrays[0])
        object.__setattr__(self, "latitudes", arrays[1])
        object.__setattr__(self, "longitudes", arrays[2])
        object.__setattr__(self, "magnitudes", arrays[3])


@dataclass(frozen=True, slots=True)
class ReplayTargetResult:
    point_intensity: float
    temporal_intensity: float
    corrected_compensator: float
    strict_reference_compensator: float


class CatalogReplay:
    def __init__(
        self,
        catalog: ReplayCatalog,
        target_indexes: np.ndarray,
        window_start: float,
        area: float,
        m_ref: float,
        parameters: ETASParameters,
        earth_radius: float = 6_378.1,
    ) -> None:
        self.catalog = catalog
        self.target_indexes = np.asarray(target_indexes, dtype=int)
        if self.target_indexes.ndim != 1 or not self.target_indexes.size:
            raise ValueError("target_indexes must be a non-empty vector")
        if np.any(np.diff(self.target_indexes) <= 0):
            raise ValueError("target_indexes must be strictly increasing")
        if self.target_indexes[0] < 0 or self.target_indexes[-1] >= len(catalog.times):
            raise ValueError("target index lies outside catalog")
        if area <= 0 or earth_radius <= 0:
            raise ValueError("area and earth_radius must be positive")
        if window_start >= catalog.times[self.target_indexes[0]]:
            raise ValueError("window_start must precede the first target")

        self.window_start = window_start
        self.area = float(area)
        self.m_ref = float(m_ref)
        self.parameters = parameters
        self.earth_radius = float(earth_radius)
        self._latitudes_rad = np.radians(catalog.latitudes)
        self._longitudes_rad = np.radians(catalog.longitudes)

        magnitude_delta = catalog.magnitudes - m_ref
        self._productivity = parameters.k0 * np.exp(parameters.a * magnitude_delta)
        self._spatial_scale = parameters.d * np.exp(
            parameters.gamma * magnitude_delta
        )
        whole_plane_integral = (
            math.pi
            / parameters.rho
            * np.power(self._spatial_scale, -parameters.rho)
        )
        self._integrated_productivity = self._productivity * whole_plane_integral

    def evaluate_target(self, target_position: int) -> ReplayTargetResult:
        if target_position < 0 or target_position >= len(self.target_indexes):
            raise IndexError("target_position lies outside target_indexes")
        target_index = int(self.target_indexes[target_position])
        target_time = self.catalog.times[target_index]
        history = slice(0, target_index)
        delta_t = self._days_between(target_time, self.catalog.times[history])
        time_decay = np.exp(-delta_t / self.parameters.tau) / np.power(
            delta_t + self.parameters.c, 1.0 + self.parameters.omega
        )

        distance_squared = self._distance_squared(target_index)
        space_decay = np.power(
            distance_squared + self._spatial_scale[history],
            -(1.0 + self.parameters.rho),
        )
        point = self.parameters.mu + np.sum(
            self._productivity[history] * time_decay * space_decay
        )
        temporal = self.parameters.mu * self.area + np.sum(
            self._integrated_productivity[history] * time_decay
        )

        interval_start = (
            self.window_start
            if target_position == 0
            else self.catalog.times[self.target_indexes[target_position - 1]]
        )
        lower = np.maximum(
            0.0, self._days_between(interval_start, self.catalog.times[history])
        )
        temporal_mass = _temporal_integrals(lower, delta_t, self.parameters)
        background_mass = self.parameters.mu * self.area * (
            self._days_between(target_time, interval_start)
        )
        corrected = background_mass + np.sum(
            self._integrated_productivity[history] * temporal_mass
        )
        strict_reference = background_mass if target_position == 0 else corrected
        return ReplayTargetResult(
            point_intensity=float(point),
            temporal_intensity=float(temporal),
            corrected_compensator=float(corrected),
            strict_reference_compensator=float(strict_reference),
        )

    def _distance_squared(self, target_index: int) -> np.ndarray:
        target_latitude = self._latitudes_rad[target_index]
        target_longitude = self._longitudes_rad[target_index]
        history_latitudes = self._latitudes_rad[:target_index]
        history_longitudes = self._longitudes_rad[:target_index]
        haversine_value = (
            np.sin((target_latitude - history_latitudes) / 2.0) ** 2
            + np.cos(target_latitude)
            * np.cos(history_latitudes)
            * np.sin((target_longitude - history_longitudes) / 2.0) ** 2
        )
        distance = 2.0 * self.earth_radius * np.arcsin(
            np.sqrt(np.clip(haversine_value, 0.0, 1.0))
        )
        return np.square(distance)

    def _days_between(self, later, earlier):
        difference = later - earlier
        if np.issubdtype(self.catalog.times.dtype, np.datetime64):
            return difference / np.timedelta64(1, "D")
        return difference


def _temporal_integrals(
    lower: np.ndarray,
    upper: np.ndarray,
    parameters: ETASParameters,
) -> np.ndarray:
    lower_scaled = (lower + parameters.c) / parameters.tau
    upper_scaled = (upper + parameters.c) / parameters.tau
    scale = math.exp(parameters.c / parameters.tau)
    if parameters.omega == 0:
        return scale * (exp1(lower_scaled) - exp1(upper_scaled))

    shape = -parameters.omega
    scale *= parameters.tau ** (-parameters.omega)
    gamma_value = gamma_function(shape)
    return scale * gamma_value * (
        gammaincc(shape, lower_scaled) - gammaincc(shape, upper_scaled)
    )
