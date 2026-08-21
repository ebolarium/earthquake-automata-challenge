"""Deterministic catalog continuation for the native ETAS baseline."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.special import gammaincc, gammainccinv

from etas_challenge.daily_replay import DailyCatalog
from etas_challenge.replay import temporal_integrals
from etas_challenge.parameters import ETASParameters


@dataclass(frozen=True, slots=True)
class SimulatedCatalog:
    times: np.ndarray
    latitudes: np.ndarray
    longitudes: np.ndarray
    magnitudes: np.ndarray

    @property
    def event_count(self) -> int:
        return int(self.times.size)


@dataclass(frozen=True, slots=True)
class ForecastSimulation:
    """A simulated catalog with its directly sampled background roots marked."""

    catalog: SimulatedCatalog
    background_roots: np.ndarray

    def __post_init__(self) -> None:
        roots = np.asarray(self.background_roots, dtype=bool)
        if roots.shape != self.catalog.times.shape:
            raise ValueError("background-root mask must match the simulated catalog")
        object.__setattr__(self, "background_roots", roots)


class ETASContinuationSimulator:
    """Simulate a finite ETAS continuation conditional on pre-issue history.

    Background locations are uniform in the fitted polygon, matching the
    native model's constant ``mu``. Triggered locations use the normalized
    whole-plane spatial kernel and are polygon-filtered only for observation.
    """

    def __init__(
        self,
        *,
        catalog: DailyCatalog,
        polygon_lat_lon: np.ndarray,
        area: float,
        m_ref: float,
        beta: float,
        parameters: ETASParameters,
        horizon_days: float = 1.0,
        earth_radius: float = 6_378.1,
        max_events_per_catalog: int = 1_000_000,
    ) -> None:
        polygon = np.asarray(polygon_lat_lon, dtype=float)
        if polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 4:
            raise ValueError("polygon must contain at least four lat/lon vertices")
        if not np.allclose(polygon[0], polygon[-1]):
            polygon = np.vstack((polygon, polygon[0]))
        if area <= 0 or beta <= 0 or horizon_days <= 0 or earth_radius <= 0:
            raise ValueError("area, beta, horizon, and earth radius must be positive")
        if max_events_per_catalog <= 0:
            raise ValueError("max_events_per_catalog must be positive")
        self.catalog = catalog
        self.polygon = polygon
        self.area = float(area)
        self.m_ref = float(m_ref)
        self.beta = float(beta)
        self.parameters = parameters
        self.horizon_days = float(horizon_days)
        self.earth_radius = float(earth_radius)
        self.max_events_per_catalog = int(max_events_per_catalog)
        self._lat_bounds = (float(polygon[:, 0].min()), float(polygon[:, 0].max()))
        self._lon_bounds = (float(polygon[:, 1].min()), float(polygon[:, 1].max()))
        self._history_issue = None
        self._history_sources = None

    def simulate(self, issue_time, rng: np.random.Generator) -> SimulatedCatalog:
        return self.simulate_with_components(issue_time, rng).catalog

    def simulate_with_components(
        self, issue_time, rng: np.random.Generator
    ) -> ForecastSimulation:
        """Simulate a forecast and identify direct background events.

        Descendants of background events are deliberately not marked. This lets
        grid forecasts replace only the noisy Monte Carlo background roots with
        their exact analytical cell rates while retaining all ETAS branching.
        """

        history_end = int(np.searchsorted(self.catalog.times, issue_time, side="left"))
        history_times = self._days_between(
            self.catalog.times[:history_end], issue_time
        )
        history_lats = self.catalog.latitudes[:history_end]
        history_lons = self.catalog.longitudes[:history_end]
        history_mags = self.catalog.magnitudes[:history_end]

        background_count = int(
            rng.poisson(self.parameters.mu * self.area * self.horizon_days)
        )
        background_times = rng.uniform(0.0, self.horizon_days, background_count)
        background_lats, background_lons = self._uniform_polygon_points(
            background_count, rng
        )
        background_mags = self._magnitudes(background_count, rng)

        if self._history_issue != issue_time:
            self._history_sources = self._prepare_sources(
                history_times,
                history_lats,
                history_lons,
                history_mags,
                lower=np.maximum(0.0, -history_times),
                upper=self.horizon_days - history_times,
            )
            self._history_issue = issue_time
        first = self._sample_offspring(self._history_sources, rng)
        generations = [
            (background_times, background_lats, background_lons, background_mags),
            first,
        ]
        background_masks = [
            np.ones(background_count, dtype=bool),
            np.zeros(len(first[0]), dtype=bool),
        ]
        total = background_count + len(first[0])
        if total > self.max_events_per_catalog:
            raise RuntimeError("simulated catalog exceeded the configured event limit")
        current = self._merge_generations(generations)

        while len(current[0]):
            children = self._offspring(
                *current,
                lower=np.zeros(len(current[0]), dtype=float),
                upper=self.horizon_days - current[0],
                rng=rng,
            )
            if not len(children[0]):
                break
            total += len(children[0])
            if total > self.max_events_per_catalog:
                raise RuntimeError("simulated catalog exceeded the configured event limit")
            generations.append(children)
            background_masks.append(np.zeros(len(children[0]), dtype=bool))
            current = children

        all_events = self._merge_generations(generations)
        if not len(all_events[0]):
            return ForecastSimulation(
                catalog=self._empty_catalog(issue_time),
                background_roots=np.empty(0, dtype=bool),
            )
        all_background_roots = np.concatenate(background_masks)
        inside = points_in_polygon(all_events[1], all_events[2], self.polygon)
        order = np.argsort(all_events[0][inside], kind="stable")
        offsets = all_events[0][inside][order]
        return ForecastSimulation(
            catalog=SimulatedCatalog(
                times=self._add_days(issue_time, offsets),
                latitudes=all_events[1][inside][order],
                longitudes=all_events[2][inside][order],
                magnitudes=all_events[3][inside][order],
            ),
            background_roots=all_background_roots[inside][order],
        )

    def _offspring(
        self,
        source_times: np.ndarray,
        source_lats: np.ndarray,
        source_lons: np.ndarray,
        source_mags: np.ndarray,
        *,
        lower: np.ndarray,
        upper: np.ndarray,
        rng: np.random.Generator,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        prepared = self._prepare_sources(
            source_times,
            source_lats,
            source_lons,
            source_mags,
            lower=lower,
            upper=upper,
        )
        return self._sample_offspring(prepared, rng)

    def _prepare_sources(
        self,
        source_times: np.ndarray,
        source_lats: np.ndarray,
        source_lons: np.ndarray,
        source_mags: np.ndarray,
        *,
        lower: np.ndarray,
        upper: np.ndarray,
    ):
        if not len(source_times):
            return None
        valid = upper > lower
        if not np.any(valid):
            return None
        source_times = source_times[valid]
        source_lats = source_lats[valid]
        source_lons = source_lons[valid]
        source_mags = source_mags[valid]
        lower_valid = lower[valid]
        upper_valid = upper[valid]
        magnitude_delta = source_mags - self.m_ref
        spatial_mass = (
            math.pi
            / self.parameters.rho
            * np.power(
                self.parameters.d * np.exp(self.parameters.gamma * magnitude_delta),
                -self.parameters.rho,
            )
        )
        temporal_mass = temporal_integrals(
            lower_valid, upper_valid, self.parameters
        )
        means = (
            self.parameters.k0
            * np.exp(self.parameters.a * magnitude_delta)
            * spatial_mass
            * temporal_mass
        )
        return (
            source_times,
            source_lats,
            source_lons,
            source_mags,
            lower_valid,
            upper_valid,
            np.cumsum(means),
        )

    def _sample_offspring(self, prepared, rng: np.random.Generator):
        if prepared is None:
            return self._empty_arrays()
        (
            source_times,
            source_lats,
            source_lons,
            source_mags,
            lower,
            upper,
            cumulative,
        ) = prepared
        count = int(rng.poisson(float(cumulative[-1])))
        if count == 0:
            return self._empty_arrays()
        parents = np.searchsorted(
            cumulative, rng.uniform(0.0, cumulative[-1], count), side="right"
        )
        delays = self._sample_temporal(lower[parents], upper[parents], rng)
        child_times = source_times[parents] + delays

        scale = self.parameters.d * np.exp(
            self.parameters.gamma * (source_mags[parents] - self.m_ref)
        )
        uniforms = rng.random(count)
        radii = np.sqrt(
            scale * (np.power(1.0 - uniforms, -1.0 / self.parameters.rho) - 1.0)
        )
        bearings = rng.uniform(0.0, 2.0 * math.pi, count)
        child_lats, child_lons = destination_points(
            source_lats[parents],
            source_lons[parents],
            radii,
            bearings,
            self.earth_radius,
        )
        return child_times, child_lats, child_lons, self._magnitudes(count, rng)

    def _sample_temporal(
        self, lower: np.ndarray, upper: np.ndarray, rng: np.random.Generator
    ) -> np.ndarray:
        shape = -self.parameters.omega
        if shape <= 0:
            raise ValueError("simulation requires the fitted negative omega")
        lower_scaled = (lower + self.parameters.c) / self.parameters.tau
        upper_scaled = (upper + self.parameters.c) / self.parameters.tau
        q_lower = gammaincc(shape, lower_scaled)
        q_upper = gammaincc(shape, upper_scaled)
        q_sample = q_lower - rng.random(len(lower)) * (q_lower - q_upper)
        return self.parameters.tau * gammainccinv(shape, q_sample) - self.parameters.c

    def _uniform_polygon_points(
        self, count: int, rng: np.random.Generator
    ) -> tuple[np.ndarray, np.ndarray]:
        if count == 0:
            return np.empty(0), np.empty(0)
        latitudes = []
        longitudes = []
        remaining = count
        while remaining:
            batch = max(remaining * 3, 32)
            sin_bounds = np.sin(np.radians(self._lat_bounds))
            lat = np.degrees(np.arcsin(rng.uniform(*sin_bounds, batch)))
            lon = rng.uniform(*self._lon_bounds, batch)
            keep = points_in_polygon(lat, lon, self.polygon)
            latitudes.append(lat[keep][:remaining])
            longitudes.append(lon[keep][:remaining])
            remaining -= min(int(np.count_nonzero(keep)), remaining)
        return np.concatenate(latitudes), np.concatenate(longitudes)

    def _magnitudes(self, count: int, rng: np.random.Generator) -> np.ndarray:
        return self.m_ref + rng.exponential(1.0 / self.beta, count)

    @staticmethod
    def _merge_generations(generations):
        nonempty = [generation for generation in generations if len(generation[0])]
        if not nonempty:
            return ETASContinuationSimulator._empty_arrays()
        return tuple(np.concatenate(parts) for parts in zip(*nonempty))

    @staticmethod
    def _empty_arrays():
        return (np.empty(0), np.empty(0), np.empty(0), np.empty(0))

    @staticmethod
    def _empty_catalog(issue_time):
        dtype = "datetime64[ns]" if isinstance(issue_time, np.datetime64) else float
        return SimulatedCatalog(
            times=np.empty(0, dtype=dtype),
            latitudes=np.empty(0),
            longitudes=np.empty(0),
            magnitudes=np.empty(0),
        )

    def _days_between(self, later, earlier):
        difference = later - earlier
        if np.issubdtype(self.catalog.times.dtype, np.datetime64):
            return np.asarray(difference / np.timedelta64(1, "D"), dtype=float)
        return np.asarray(difference, dtype=float)

    def _add_days(self, value, days: np.ndarray):
        if np.issubdtype(self.catalog.times.dtype, np.datetime64):
            nanoseconds = np.rint(days * 86_400 * 1_000_000_000).astype(
                "timedelta64[ns]"
            )
            return value + nanoseconds
        return value + days


def points_in_polygon(
    latitudes: np.ndarray, longitudes: np.ndarray, polygon_lat_lon: np.ndarray
) -> np.ndarray:
    """Vectorized even-odd point-in-polygon test; boundary has measure zero."""
    lat = np.asarray(latitudes, dtype=float)
    lon = np.asarray(longitudes, dtype=float)
    polygon = np.asarray(polygon_lat_lon, dtype=float)
    inside = np.zeros(lat.shape, dtype=bool)
    for index in range(len(polygon) - 1):
        lat_a, lon_a = polygon[index]
        lat_b, lon_b = polygon[index + 1]
        crosses = (lat_a > lat) != (lat_b > lat)
        intersection = (
            (lon_b - lon_a) * (lat - lat_a) / (lat_b - lat_a + 1e-300)
            + lon_a
        )
        inside ^= crosses & (lon < intersection)
    return inside


def destination_points(latitudes, longitudes, distances, bearings, radius):
    """Destination coordinates on a sphere for distances in radius units."""
    lat1 = np.radians(latitudes)
    lon1 = np.radians(longitudes)
    angular = np.asarray(distances) / radius
    lat2 = np.arcsin(
        np.sin(lat1) * np.cos(angular)
        + np.cos(lat1) * np.sin(angular) * np.cos(bearings)
    )
    lon2 = lon1 + np.arctan2(
        np.sin(bearings) * np.sin(angular) * np.cos(lat1),
        np.cos(angular) - np.sin(lat1) * np.sin(lat2),
    )
    longitude = (np.degrees(lon2) + 180.0) % 360.0 - 180.0
    return np.degrees(lat2), longitude
