"""Deterministic daily ETAS grid generation for prospective California."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from etas_challenge.daily_replay import DailyCatalog
from etas_challenge.grid_forecast import RelmGridProjector
from etas_challenge.parameters import ETASParameters
from etas_challenge.simulation import ETASContinuationSimulator
from etas_challenge.training_matrix import GridDefinition


@dataclass(frozen=True, slots=True)
class ETASGridForecast:
    rates: np.ndarray
    expected_count: float
    simulations: int
    sampled_nonbackground_events: int
    sampled_nonbackground_inside: int


def california_daily_etas_grid(
    *,
    issue_time: np.datetime64,
    history_origin_time_ns: np.ndarray,
    history_latitudes: np.ndarray,
    history_longitudes: np.ndarray,
    history_magnitudes: np.ndarray,
    grid: GridDefinition,
    background_rates: np.ndarray,
    polygon_lat_lon: np.ndarray,
    area_km2: float,
    beta: float,
    magnitude_reference: float,
    magnitude_bin_width: float,
    parameters: dict[str, float],
    simulations: int,
    random_seed: int,
    earth_radius_km: float = 6378.1,
    max_events_per_catalog: int = 1_000_000,
) -> ETASGridForecast:
    """Simulate one frozen-history ETAS grid with analytical background roots."""

    if simulations <= 0 or magnitude_bin_width <= 0:
        raise ValueError("ETAS grid simulations and magnitude bin must be positive")
    times = np.asarray(history_origin_time_ns, dtype=np.int64).astype("datetime64[ns]")
    latitudes = np.asarray(history_latitudes, dtype=float)
    longitudes = np.asarray(history_longitudes, dtype=float)
    magnitudes = np.asarray(history_magnitudes, dtype=float)
    background = np.asarray(background_rates, dtype=float)
    if (
        any(value.shape != times.shape for value in (latitudes, longitudes, magnitudes))
        or np.any(np.diff(times) < np.timedelta64(0, "ns"))
        or background.shape != (grid.num_cells,)
        or np.any(background <= 0)
    ):
        raise ValueError("California ETAS grid inputs disagree")
    rounded = (
        np.floor(magnitudes / magnitude_bin_width + 0.5) * magnitude_bin_width
    )
    selected = (times < issue_time) & (rounded >= magnitude_reference)
    catalog = DailyCatalog(
        times=times[selected],
        latitudes=latitudes[selected],
        longitudes=longitudes[selected],
        magnitudes=rounded[selected],
    )
    simulator = ETASContinuationSimulator(
        catalog=catalog,
        polygon_lat_lon=np.asarray(polygon_lat_lon, dtype=float),
        area=area_km2,
        m_ref=magnitude_reference,
        beta=beta,
        parameters=ETASParameters.from_transformed(**parameters),
        horizon_days=1.0,
        earth_radius=earth_radius_km,
        max_events_per_catalog=max_events_per_catalog,
    )
    projector = RelmGridProjector.from_grid(grid)
    counts = np.zeros(grid.num_cells, dtype=np.uint64)
    sampled = 0
    inside = 0
    issue_day = int(
        (issue_time.astype("datetime64[D]") - np.datetime64("1970-01-01", "D")).astype(int)
    )
    for catalog_id in range(simulations):
        rng = np.random.default_rng(
            np.random.SeedSequence([random_seed, issue_day, catalog_id])
        )
        forecast = simulator.simulate_with_components(issue_time, rng)
        sample_counts, sample_total, sample_inside = projector.nonbackground_counts(
            forecast
        )
        counts += sample_counts
        sampled += sample_total
        inside += sample_inside
    rates = background + counts.astype(np.float64) / simulations
    if np.any(~np.isfinite(rates)) or np.any(rates <= 0):
        raise ValueError("California ETAS grid contains invalid rates")
    return ETASGridForecast(
        rates=rates,
        expected_count=float(np.sum(rates, dtype=np.float64)),
        simulations=simulations,
        sampled_nonbackground_events=sampled,
        sampled_nonbackground_inside=inside,
    )
