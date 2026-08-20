"""Leakage-free daily scoring for the native spatial-temporal ETAS model."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

from etas_challenge.parameters import ETASParameters
from etas_challenge.replay import temporal_integrals


DAILY_REPLAY_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class DailyCatalog:
    times: np.ndarray
    latitudes: np.ndarray
    longitudes: np.ndarray
    magnitudes: np.ndarray

    def __post_init__(self) -> None:
        times = np.asarray(self.times)
        if times.dtype.kind == "M":
            times = times.astype("datetime64[ns]")
            valid_times = not np.any(np.isnat(times))
            ordered = np.all(np.diff(times) >= np.timedelta64(0, "ns"))
        else:
            times = times.astype(float)
            valid_times = np.all(np.isfinite(times))
            ordered = np.all(np.diff(times) >= 0)
        arrays = (
            times,
            np.asarray(self.latitudes, dtype=float),
            np.asarray(self.longitudes, dtype=float),
            np.asarray(self.magnitudes, dtype=float),
        )
        if not times.size or times.ndim != 1:
            raise ValueError("daily catalog must be a non-empty vector")
        if len({array.shape for array in arrays}) != 1:
            raise ValueError("daily catalog arrays must have identical shapes")
        if not valid_times or not all(
            np.all(np.isfinite(array)) for array in arrays[1:]
        ):
            raise ValueError("daily catalog must contain only finite values")
        if not ordered:
            raise ValueError("daily catalog times must be non-decreasing")
        object.__setattr__(self, "times", arrays[0])
        object.__setattr__(self, "latitudes", arrays[1])
        object.__setattr__(self, "longitudes", arrays[2])
        object.__setattr__(self, "magnitudes", arrays[3])


@dataclass(frozen=True, slots=True)
class DailyScore:
    history_event_count: int
    target_event_count: int
    frozen_integrated_rate: float
    frozen_log_intensity_sum: float
    frozen_log_likelihood: float
    sequential_integrated_rate: float
    sequential_log_intensity_sum: float
    sequential_log_likelihood: float
    poisson_integrated_rate: float
    poisson_log_likelihood: float

    @property
    def sequential_information_gain(self) -> float:
        return self.sequential_log_likelihood - self.poisson_log_likelihood


class DailyETASReplay:
    def __init__(
        self,
        *,
        catalog: DailyCatalog,
        area: float,
        m_ref: float,
        parameters: ETASParameters,
        poisson_mu: float,
        horizon_days: float = 1.0,
        earth_radius: float = 6_378.1,
    ) -> None:
        if area <= 0 or poisson_mu <= 0 or horizon_days <= 0 or earth_radius <= 0:
            raise ValueError("area, rates, horizon, and earth radius must be positive")
        self.catalog = catalog
        self.area = float(area)
        self.m_ref = float(m_ref)
        self.parameters = parameters
        self.poisson_mu = float(poisson_mu)
        self.horizon_days = float(horizon_days)
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

    def evaluate_day(self, issue_time) -> DailyScore:
        window_end = self._add_days(issue_time, self.horizon_days)
        history_end = int(np.searchsorted(self.catalog.times, issue_time, side="left"))
        target_end = int(np.searchsorted(self.catalog.times, window_end, side="left"))
        target_indexes = np.arange(history_end, target_end, dtype=int)

        history = slice(0, history_end)
        history_lower = self._days_between(issue_time, self.catalog.times[history])
        history_upper = self._days_between(window_end, self.catalog.times[history])
        frozen_integrated = self.parameters.mu * self.area * self.horizon_days
        if history_end:
            frozen_integrated += float(
                np.sum(
                    self._integrated_productivity[history]
                    * temporal_integrals(
                        history_lower, history_upper, self.parameters
                    )
                )
            )

        frozen_logs = 0.0
        sequential_logs = 0.0
        for target_index in target_indexes:
            frozen_intensity = self._point_intensity(target_index, history_end)
            strictly_prior = int(
                np.searchsorted(
                    self.catalog.times,
                    self.catalog.times[target_index],
                    side="left",
                )
            )
            sequential_intensity = self._point_intensity(
                target_index, strictly_prior
            )
            frozen_logs += math.log(frozen_intensity)
            sequential_logs += math.log(sequential_intensity)

        sequential_integrated = frozen_integrated
        if target_indexes.size:
            target_upper = self._days_between(
                window_end, self.catalog.times[target_indexes]
            )
            sequential_integrated += float(
                np.sum(
                    self._integrated_productivity[target_indexes]
                    * temporal_integrals(
                        np.zeros_like(target_upper), target_upper, self.parameters
                    )
                )
            )

        target_count = int(target_indexes.size)
        poisson_integrated = self.poisson_mu * self.area * self.horizon_days
        poisson_logs = target_count * math.log(self.poisson_mu)
        return DailyScore(
            history_event_count=history_end,
            target_event_count=target_count,
            frozen_integrated_rate=frozen_integrated,
            frozen_log_intensity_sum=frozen_logs,
            frozen_log_likelihood=frozen_logs - frozen_integrated,
            sequential_integrated_rate=sequential_integrated,
            sequential_log_intensity_sum=sequential_logs,
            sequential_log_likelihood=sequential_logs - sequential_integrated,
            poisson_integrated_rate=poisson_integrated,
            poisson_log_likelihood=poisson_logs - poisson_integrated,
        )

    def _point_intensity(self, target_index: int, source_end: int) -> float:
        if source_end == 0:
            return self.parameters.mu
        target_time = self.catalog.times[target_index]
        delta_t = self._days_between(target_time, self.catalog.times[:source_end])
        positive = delta_t > 0
        if not np.any(positive):
            return self.parameters.mu
        source_indexes = np.arange(source_end)[positive]
        delta_t = delta_t[positive]
        time_decay = np.exp(-delta_t / self.parameters.tau) / np.power(
            delta_t + self.parameters.c, 1.0 + self.parameters.omega
        )
        distance_squared = self._distance_squared(target_index, source_indexes)
        space_decay = np.power(
            distance_squared + self._spatial_scale[source_indexes],
            -(1.0 + self.parameters.rho),
        )
        return float(
            self.parameters.mu
            + np.sum(
                self._productivity[source_indexes] * time_decay * space_decay
            )
        )

    def _distance_squared(
        self, target_index: int, source_indexes: np.ndarray
    ) -> np.ndarray:
        target_latitude = self._latitudes_rad[target_index]
        target_longitude = self._longitudes_rad[target_index]
        source_latitudes = self._latitudes_rad[source_indexes]
        source_longitudes = self._longitudes_rad[source_indexes]
        haversine_value = (
            np.sin((target_latitude - source_latitudes) / 2.0) ** 2
            + np.cos(target_latitude)
            * np.cos(source_latitudes)
            * np.sin((target_longitude - source_longitudes) / 2.0) ** 2
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

    def _add_days(self, value, days: float):
        if np.issubdtype(self.catalog.times.dtype, np.datetime64):
            nanoseconds = round(days * 86_400 * 1_000_000_000)
            return value + np.timedelta64(nanoseconds, "ns")
        return value + days


def validate_daily_replay_manifest(manifest: dict) -> None:
    if manifest.get("schema_version") != DAILY_REPLAY_SCHEMA_VERSION:
        raise ValueError("unsupported daily replay schema_version")
    if manifest.get("status") != "completed":
        raise ValueError("daily replay manifest must have completed status")
    for section in ("inputs", "protocol", "outputs", "results"):
        if not isinstance(manifest.get(section), dict):
            raise ValueError(f"daily replay manifest missing {section}")
    hash_paths = (
        ("inputs", "catalog_sha256"),
        ("inputs", "config_sha256"),
        ("outputs", "daily_scores_sha256"),
        ("outputs", "summary_sha256"),
    )
    for section, key in hash_paths:
        if not re.fullmatch(r"[0-9a-f]{64}", manifest[section].get(key, "")):
            raise ValueError(f"invalid SHA-256 at {section}.{key}")
    if manifest["results"].get("replay_days", 0) <= 0:
        raise ValueError("daily replay must contain forecast days")
    if manifest["results"].get("target_events", -1) < 0:
        raise ValueError("daily replay target count cannot be negative")
