"""Deterministic event-rate evaluation for the pinned academic ETAS kernel."""

from __future__ import annotations

import math

import numpy as np


EARTH_RADIUS_KM = 6378.1


def haversine_squared_km(
    latitude: float,
    longitude: float,
    source_latitudes: np.ndarray,
    source_longitudes: np.ndarray,
) -> np.ndarray:
    """Match the great-circle distance used by the pinned ETAS package."""

    lat = math.radians(latitude)
    lon = math.radians(longitude)
    source_lat = np.radians(np.asarray(source_latitudes, dtype=float))
    source_lon = np.radians(np.asarray(source_longitudes, dtype=float))
    dlat = source_lat - lat
    dlon = source_lon - lon
    value = np.sin(dlat / 2.0) ** 2 + np.cos(lat) * np.cos(source_lat) * np.sin(
        dlon / 2.0
    ) ** 2
    distance = 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(value, 0.0, 1.0)))
    return distance * distance


def event_rates(
    times_days: np.ndarray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    magnitudes: np.ndarray,
    *,
    magnitude_reference: float,
    parameters: dict[str, float],
) -> np.ndarray:
    """Return conditional space-time rates at each event using prior events only."""

    times = np.asarray(times_days, dtype=float)
    lats = np.asarray(latitudes, dtype=float)
    lons = np.asarray(longitudes, dtype=float)
    mags = np.asarray(magnitudes, dtype=float)
    if (
        times.ndim != 1
        or any(value.shape != times.shape for value in (lats, lons, mags))
        or not all(np.all(np.isfinite(value)) for value in (times, lats, lons, mags))
        or np.any(np.diff(times) < 0)
    ):
        raise ValueError("ETAS event arrays must be finite, equal, and time ordered")
    mu = 10.0 ** parameters["log10_mu"]
    k0 = 10.0 ** parameters["log10_k0"]
    c = 10.0 ** parameters["log10_c"]
    tau = 10.0 ** parameters["log10_tau"]
    d = 10.0 ** parameters["log10_d"]
    a = parameters["a"]
    omega = parameters["omega"]
    gamma = parameters["gamma"]
    rho = parameters["rho"]
    rates = np.full(len(times), mu, dtype=float)
    for index in range(1, len(times)):
        delta_time = times[index] - times[:index]
        distance_squared = haversine_squared_km(
            lats[index], lons[index], lats[:index], lons[:index]
        )
        productivity = k0 * np.exp(a * (mags[:index] - magnitude_reference))
        temporal = np.exp(-delta_time / tau) / (delta_time + c) ** (1.0 + omega)
        spatial = 1.0 / (
            distance_squared + d * np.exp(gamma * (mags[:index] - magnitude_reference))
        ) ** (1.0 + rho)
        rates[index] += np.sum(productivity * temporal * spatial)
    if np.any(~np.isfinite(rates)) or np.any(rates <= 0):
        raise ValueError("ETAS produced invalid event rates")
    return rates
