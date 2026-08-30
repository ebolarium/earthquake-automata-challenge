"""Deterministic forecast artifacts for the prospective ETAS challenge."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile

import numpy as np

from etas_challenge.prospective_daily import california_background_forecast
from etas_challenge.prospective_daily import regional_background_forecast
from etas_challenge.prospective_etas import california_daily_etas_grid
from etas_challenge.prospective_replay import CH008State
from etas_challenge.training_matrix import write_deterministic_npz


@dataclass(frozen=True, slots=True)
class ForecastArtifactPair:
    baseline_arrays: dict[str, np.ndarray]
    challenger_arrays: dict[str, np.ndarray]
    summary: dict


def canonical_json_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, np.ndarray]) -> bytes:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "forecast.npz"
        write_deterministic_npz(path, arrays)
        return path.read_bytes()


def payload_identity(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def forecast_run_id(protocol_id: str, region_id: str, target_start: datetime) -> str:
    value = f"{protocol_id}\n{region_id}\n{target_start.astimezone(timezone.utc).isoformat()}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def forecast_window(state_as_of: datetime) -> tuple[datetime, datetime]:
    boundary = state_as_of.astimezone(timezone.utc)
    if any((boundary.hour, boundary.minute, boundary.second, boundary.microsecond)):
        raise ValueError("state boundary must be UTC midnight")
    target_start = boundary + timedelta(days=1)
    return target_start, target_start + timedelta(days=1)


def enforce_publication_deadline(
    issue_time: datetime,
    state_as_of: datetime,
    *,
    deadline_minutes: int,
    minimum_lead_time_minutes: int,
) -> tuple[datetime, datetime]:
    issue = issue_time.astimezone(timezone.utc)
    boundary = state_as_of.astimezone(timezone.utc)
    target_start, target_end = forecast_window(boundary)
    deadline = boundary + timedelta(minutes=deadline_minutes)
    if issue < boundary:
        raise ValueError("forecast cannot be issued before its state boundary")
    if issue > deadline:
        raise ValueError("forecast publication deadline has passed")
    lead = (target_start - issue).total_seconds() / 60.0
    if lead < minimum_lead_time_minutes:
        raise ValueError("forecast minimum lead time is not satisfied")
    return target_start, target_end


def state_from_archive(source) -> CH008State:
    return CH008State(
        np.asarray(source["ch008_age"], dtype=float),
        np.asarray(source["ch008_exposure"], dtype=float),
        np.asarray(source["ch008_roots"], dtype=float),
    )


def build_regional_artifacts(
    source,
    *,
    grid,
    etas_model: dict,
    parent_model: dict,
    ch008_model: dict,
) -> ForecastArtifactPair:
    state = state_from_archive(source)
    direct_background = 10.0 ** etas_model["parameters"]["log10_mu"] * grid.areas_km2
    forecast = regional_background_forecast(
        state,
        background_mass=direct_background,
        transition=grid.transition,
        parent_parameters=parent_model["parameters"],
        ch008_parameters=ch008_model["parameters"],
    )
    common = {
        "cell_areas_km2": np.asarray(grid.areas_km2),
    }
    if hasattr(grid, "latent_keys"):
        common["latent_keys"] = np.asarray(grid.latent_keys)
    else:
        common["longitude_edges"] = np.asarray(grid.longitude_edges)
        common["latitude_edges"] = np.asarray(grid.latitude_edges)
    baseline = {**common, "direct_background_mass": forecast.baseline_mass}
    challenger = {
        **common,
        "direct_background_mass": forecast.challenger_mass,
        "ch008_score": forecast.score,
    }
    baseline_total = float(np.sum(forecast.baseline_mass, dtype=np.float64))
    challenger_total = float(np.sum(forecast.challenger_mass, dtype=np.float64))
    if not np.isclose(baseline_total, challenger_total, rtol=1e-12, atol=1e-12):
        raise ValueError("regional CH-008 changed direct background mass")
    return ForecastArtifactPair(
        baseline,
        challenger,
        {
            "artifact_semantics": "pre_target_latent_direct_background_mass",
            "cells": len(forecast.baseline_mass),
            "baseline_direct_background_mass": baseline_total,
            "challenger_direct_background_mass": challenger_total,
            "paired_compensator_gain": 0.0,
        },
    )


def build_california_artifacts(
    source,
    *,
    forecast_start: datetime,
    context,
    etas_model: dict,
    parent_model: dict,
    ch008_model: dict,
    simulation_reference: dict,
    simulations: int,
    random_seed: int,
) -> ForecastArtifactPair:
    state = state_from_archive(source)
    baseline = california_daily_etas_grid(
        issue_time=np.datetime64(forecast_start.replace(tzinfo=None), "ns"),
        history_origin_time_ns=np.asarray(source["origin_time_ns"]),
        history_latitudes=np.asarray(source["latitudes"]),
        history_longitudes=np.asarray(source["longitudes"]),
        history_magnitudes=np.asarray(source["magnitudes"]),
        grid=context.grid,
        background_rates=context.baseline_background_grid,
        polygon_lat_lon=np.asarray(simulation_reference["polygon_lat_lon"]),
        area_km2=simulation_reference["area_km2"],
        beta=etas_model["beta"],
        magnitude_reference=etas_model["magnitude_reference"],
        magnitude_bin_width=simulation_reference["delta_m"],
        parameters=etas_model["parameters"],
        simulations=simulations,
        random_seed=random_seed,
        earth_radius_km=simulation_reference["earth_radius_km"],
        max_events_per_catalog=simulation_reference["max_events_per_catalog"],
    )
    background = california_background_forecast(
        state,
        background_grid=context.baseline_background_grid,
        transitions=list(context.transitions),
        grid_geometries=list(context.grid_geometries),
        parent_parameter_values=np.asarray(
            [
                parent_model["parameters"][name]
                for name in (
                    "full_reset_magnitude",
                    "magnitude_exponent",
                    "bpt_aperiodicity",
                    "graph_neighborhood_mix",
                    "minimum_branch_consensus",
                    "background_mixture_fraction",
                    "renewal_sensitivity",
                )
            ]
        ),
        ch008_parameters=ch008_model["parameters"],
        maximum_log_tilt=context.maximum_log_tilt,
    )
    challenger_rates = baseline.rates + background.challenger_mass - background.baseline_mass
    if np.any(~np.isfinite(challenger_rates)) or np.any(challenger_rates <= 0):
        raise ValueError("California CH-008 grid contains invalid rates")
    baseline_total = float(np.sum(baseline.rates, dtype=np.float64))
    challenger_total = float(np.sum(challenger_rates, dtype=np.float64))
    if not np.isclose(baseline_total, challenger_total, rtol=1e-12, atol=1e-12):
        raise ValueError("California CH-008 changed expected event count")
    common = {
        "origin_units": np.asarray(context.grid.origin_units),
        "coordinate_units_per_degree": np.asarray(context.grid.units_per_degree),
    }
    return ForecastArtifactPair(
        {
            **common,
            "daily_rates": baseline.rates,
            "direct_background_rates": background.baseline_mass,
        },
        {
            **common,
            "daily_rates": challenger_rates,
            "direct_background_rates": background.challenger_mass,
            "ch008_score": background.score,
        },
        {
            "artifact_semantics": "one_day_expected_count_per_relm_cell",
            "cells": len(baseline.rates),
            "baseline_expected_count": baseline_total,
            "challenger_expected_count": challenger_total,
            "paired_compensator_gain": 0.0,
            "simulations": baseline.simulations,
            "sampled_nonbackground_events": baseline.sampled_nonbackground_events,
            "sampled_nonbackground_inside": baseline.sampled_nonbackground_inside,
        },
    )
