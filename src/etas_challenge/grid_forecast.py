"""Low-memory gridding helpers for catalog-simulation ETAS forecasts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from etas_challenge.simulation import ForecastSimulation
from etas_challenge.training_matrix import GridDefinition
from etas_challenge.training_matrix import sha256_file


GRID_FORECAST_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class RelmGridProjector:
    """Fast exact assignment to the pinned pyCSEP RELM cell convention."""

    grid: GridDefinition
    minimum_units: np.ndarray
    lookup: np.ndarray

    @classmethod
    def from_grid(cls, grid: GridDefinition) -> "RelmGridProjector":
        minimum = np.min(grid.origin_units, axis=0)
        maximum = np.max(grid.origin_units, axis=0)
        shape = maximum - minimum + 1
        lookup = np.full((int(shape[1]), int(shape[0])), -1, dtype=np.int32)
        offsets = grid.origin_units - minimum
        lookup[offsets[:, 1], offsets[:, 0]] = np.arange(
            grid.num_cells, dtype=np.int32
        )
        return cls(grid=grid, minimum_units=minimum, lookup=lookup)

    def cell_indexes(
        self, longitudes: np.ndarray, latitudes: np.ndarray
    ) -> np.ndarray:
        longitude = np.asarray(longitudes, dtype=float)
        latitude = np.asarray(latitudes, dtype=float)
        if longitude.shape != latitude.shape:
            raise ValueError("longitude and latitude arrays must have equal shapes")
        scale = self.grid.units_per_degree
        lon_units = np.ceil(np.nextafter(longitude * scale, -np.inf)).astype(int) - 1
        lat_units = np.ceil(np.nextafter(latitude * scale, -np.inf)).astype(int) - 1
        x = lon_units - self.minimum_units[0]
        y = lat_units - self.minimum_units[1]
        valid = (
            (x >= 0)
            & (x < self.lookup.shape[1])
            & (y >= 0)
            & (y < self.lookup.shape[0])
        )
        result = np.full(longitude.shape, -1, dtype=np.int32)
        result[valid] = self.lookup[y[valid], x[valid]]
        return result

    def nonbackground_counts(
        self, simulation: ForecastSimulation
    ) -> tuple[np.ndarray, int, int]:
        catalog = simulation.catalog
        selected = ~simulation.background_roots
        selected_count = int(np.count_nonzero(selected))
        indexes = self.cell_indexes(
            catalog.longitudes[selected], catalog.latitudes[selected]
        )
        inside = indexes >= 0
        counts = np.bincount(
            indexes[inside], minlength=self.grid.num_cells
        ).astype(np.uint64)
        return counts, selected_count, int(np.count_nonzero(inside))


def spherical_cell_areas(
    grid: GridDefinition, earth_radius_km: float
) -> np.ndarray:
    if earth_radius_km <= 0:
        raise ValueError("earth radius must be positive")
    scale = grid.units_per_degree
    longitude_width = np.radians(1.0 / scale)
    latitude_lower = np.radians(grid.origin_units[:, 1] / scale)
    latitude_upper = np.radians((grid.origin_units[:, 1] + 1) / scale)
    return (
        earth_radius_km**2
        * longitude_width
        * (np.sin(latitude_upper) - np.sin(latitude_lower))
    )


def analytical_background_rates(
    grid: GridDefinition, mu_per_km2_day: float, earth_radius_km: float
) -> np.ndarray:
    if mu_per_km2_day <= 0:
        raise ValueError("background rate must be positive")
    return spherical_cell_areas(grid, earth_radius_km) * mu_per_km2_day


def validate_grid_forecast_manifest(manifest: dict) -> None:
    if manifest.get("schema_version") != GRID_FORECAST_SCHEMA_VERSION:
        raise ValueError("unsupported grid forecast schema_version")
    if manifest.get("status") not in {"completed", "smoke"}:
        raise ValueError("grid forecast status must be completed or smoke")
    for section in ("inputs", "protocol", "period", "outputs", "results"):
        if not isinstance(manifest.get(section), dict):
            raise ValueError(f"grid forecast manifest missing {section}")
    for key in ("config_sha256", "catalog_sha256", "grid_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", manifest["inputs"].get(key, "")):
            raise ValueError(f"invalid SHA-256 at inputs.{key}")
    shards = manifest["outputs"].get("shards") or []
    if not shards:
        raise ValueError("grid forecast must contain shards")
    if any(
        not re.fullmatch(r"[0-9a-f]{64}", shard.get("sha256", ""))
        for shard in shards
    ):
        raise ValueError("grid forecast shard hash is invalid")
    if manifest["results"].get("issue_days", 0) <= 0:
        raise ValueError("grid forecast must contain issue days")


def verify_grid_forecast_artifacts(manifest: dict, repository_root: Path) -> None:
    validate_grid_forecast_manifest(manifest)
    root = repository_root.resolve()
    expected_cells = manifest["results"]["grid_cells"]
    total_days = 0
    total_sampled = 0
    total_inside = 0
    previous_day = None
    for item in manifest["outputs"]["shards"]:
        path = (root / item["path"]).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError(f"grid forecast shard is missing or unsafe: {item['path']}")
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"grid forecast shard hash mismatch: {item['path']}")
        with np.load(path, allow_pickle=False) as shard:
            days = shard["issue_days"]
            rates = shard["etas_rates"]
            expected_counts = shard["expected_counts"]
            sampled = shard["sampled_nonbackground_events"]
            inside = shard["sampled_nonbackground_inside"]
            simulations = int(shard["simulations_per_issue"])
            config_sha256 = str(shard["config_sha256"])
        shard_days = len(days)
        if rates.shape != (shard_days, expected_cells):
            raise ValueError(f"invalid ETAS rate shape: {item['path']}")
        if expected_counts.shape != (shard_days,):
            raise ValueError(f"invalid expected-count shape: {item['path']}")
        if sampled.shape != (shard_days,) or inside.shape != (shard_days,):
            raise ValueError(f"invalid simulation-count shape: {item['path']}")
        if rates.dtype != np.float32 or days.dtype != np.int32:
            raise ValueError(f"invalid ETAS rate or issue-day dtype: {item['path']}")
        if expected_counts.dtype != np.float64:
            raise ValueError(f"invalid expected-count dtype: {item['path']}")
        if sampled.dtype != np.uint64 or inside.dtype != np.uint64:
            raise ValueError(f"invalid simulation-count dtype: {item['path']}")
        if simulations != manifest["protocol"]["simulations_per_issue"]:
            raise ValueError(f"simulation count changed within shard: {item['path']}")
        if config_sha256 != manifest["inputs"]["config_sha256"]:
            raise ValueError(f"config hash changed within shard: {item['path']}")
        if shard_days != item["issue_days"] or not np.all(np.diff(days) == 1):
            raise ValueError(f"non-contiguous issue days: {item['path']}")
        if previous_day is not None and int(days[0]) != previous_day + 1:
            raise ValueError("grid forecast shards are not globally contiguous")
        previous_day = int(days[-1])
        if not np.all(np.isfinite(rates)) or np.any(rates <= 0):
            raise ValueError(f"ETAS rates must be finite and positive: {item['path']}")
        if not np.all(np.isfinite(expected_counts)) or np.any(expected_counts <= 0):
            raise ValueError(f"expected counts must be finite and positive: {item['path']}")
        np.testing.assert_allclose(
            np.sum(rates, axis=1, dtype=np.float64),
            expected_counts,
            rtol=2e-7,
            atol=1e-9,
        )
        total_days += shard_days
        total_sampled += int(np.sum(sampled, dtype=np.uint64))
        total_inside += int(np.sum(inside, dtype=np.uint64))
    if total_days != manifest["results"]["issue_days"]:
        raise ValueError("grid forecast issue-day total does not match manifest")
    if total_sampled != manifest["results"]["sampled_nonbackground_events"]:
        raise ValueError("sampled event total does not match manifest")
    if total_inside != manifest["results"]["sampled_nonbackground_inside"]:
        raise ValueError("inside event total does not match manifest")
