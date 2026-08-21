"""Leakage-free catalog features on the pinned California RELM grid."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np


MATRIX_SCHEMA_VERSION = 1
COUNT_FEATURES = (
    "cell_count_3d",
    "neighbor_count_3d",
    "cell_count_7d",
    "neighbor_count_7d",
    "cell_count_30d",
    "neighbor_count_30d",
    "cell_count_90d",
    "neighbor_count_90d",
)
CONTINUOUS_FEATURES = (
    "cell_excess_30d",
    "neighbor_excess_30d",
    "cell_acceleration_7v30",
    "neighbor_acceleration_7v30",
    "cell_recency_days",
    "neighbor_recency_days",
    "background_rate_daily",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_deterministic_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """Write compressed NumPy arrays without wall-clock ZIP metadata."""

    temporary = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(
        temporary, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, value in arrays.items():
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, np.asarray(value), allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, buffer.getvalue(), compresslevel=9)
    os.replace(temporary, path)


@dataclass(frozen=True, slots=True)
class GridDefinition:
    grid_id: str
    units_per_degree: int
    origin_units: np.ndarray
    neighbors: np.ndarray

    @classmethod
    def from_payload(cls, payload: dict) -> "GridDefinition":
        if payload.get("schema_version") != 1:
            raise ValueError("unsupported grid schema_version")
        units = payload.get("coordinate_units_per_degree")
        origins = np.asarray(payload.get("origin_units"), dtype=int)
        if not isinstance(units, int) or units <= 0:
            raise ValueError("grid coordinate scale must be a positive integer")
        if origins.ndim != 2 or origins.shape[1] != 2 or not len(origins):
            raise ValueError("grid origin_units must be an Nx2 array")
        if len(origins) != payload.get("num_cells"):
            raise ValueError("grid cell count does not match origin_units")
        if len({tuple(value) for value in origins.tolist()}) != len(origins):
            raise ValueError("grid cell origins must be unique")
        expected_size = 1.0 / units
        if not np.isclose(payload.get("cell_size_degrees"), expected_size):
            raise ValueError("grid cell size and coordinate scale disagree")

        lookup = {tuple(origin): index for index, origin in enumerate(origins)}
        neighbor_rows = []
        for lon_unit, lat_unit in origins:
            neighbor_rows.append(
                [
                    lookup.get((lon_unit + delta_lon, lat_unit + delta_lat), -1)
                    for delta_lon, delta_lat in (
                        (-1, -1),
                        (-1, 0),
                        (-1, 1),
                        (0, -1),
                        (0, 1),
                        (1, -1),
                        (1, 0),
                        (1, 1),
                    )
                ]
            )
        return cls(
            grid_id=payload["grid_id"],
            units_per_degree=units,
            origin_units=origins,
            neighbors=np.asarray(neighbor_rows, dtype=np.int32),
        )

    @classmethod
    def load(cls, path: Path) -> "GridDefinition":
        return cls.from_payload(json.loads(path.read_text(encoding="utf-8")))

    @property
    def num_cells(self) -> int:
        return int(len(self.origin_units))

    def cell_indexes(
        self, longitudes: np.ndarray, latitudes: np.ndarray
    ) -> np.ndarray:
        longitudes = np.asarray(longitudes, dtype=float)
        latitudes = np.asarray(latitudes, dtype=float)
        if longitudes.shape != latitudes.shape:
            raise ValueError("longitude and latitude arrays must have equal shapes")
        scaled_lon = longitudes * self.units_per_degree
        scaled_lat = latitudes * self.units_per_degree
        lon_units = np.ceil(np.nextafter(scaled_lon, -np.inf)).astype(int) - 1
        lat_units = np.ceil(np.nextafter(scaled_lat, -np.inf)).astype(int) - 1
        lookup = {
            tuple(origin): index for index, origin in enumerate(self.origin_units)
        }
        return np.fromiter(
            (
                lookup.get((int(lon_unit), int(lat_unit)), -1)
                for lon_unit, lat_unit in zip(lon_units, lat_units)
            ),
            dtype=np.int32,
            count=longitudes.size,
        )

    def neighbor_sum(self, values: np.ndarray) -> np.ndarray:
        values = np.asarray(values)
        if values.shape != (self.num_cells,):
            raise ValueError("neighbor input must have one value per cell")
        padded = np.append(values, 0)
        indexes = np.where(self.neighbors >= 0, self.neighbors, self.num_cells)
        return np.sum(padded[indexes], axis=1)

    def neighbor_min(self, values: np.ndarray, missing_value: float) -> np.ndarray:
        values = np.asarray(values)
        if values.shape != (self.num_cells,):
            raise ValueError("neighbor input must have one value per cell")
        padded = np.append(values, missing_value)
        indexes = np.where(self.neighbors >= 0, self.neighbors, self.num_cells)
        return np.min(padded[indexes], axis=1)


class FeatureTimeline:
    """Advance issue dates while keeping target-day events out of features."""

    def __init__(
        self,
        *,
        grid: GridDefinition,
        daily_counts: dict[int, np.ndarray],
        issue_day: int,
        windows: tuple[int, ...],
        background_rate: np.ndarray,
        last_event_days: np.ndarray,
        recency_cap_days: int,
        rate_floor_fraction: float,
    ) -> None:
        if windows != (3, 7, 30, 90):
            raise ValueError("CH-001 V1 windows must remain 3, 7, 30, and 90 days")
        if recency_cap_days <= 0 or rate_floor_fraction <= 0:
            raise ValueError("recency cap and rate floor must be positive")
        self.grid = grid
        self.daily_counts = daily_counts
        self.issue_day = int(issue_day)
        self.windows = windows
        self.background_rate = np.asarray(background_rate, dtype=float)
        self.last_event_days = np.asarray(last_event_days, dtype=np.int32).copy()
        self.recency_cap_days = int(recency_cap_days)
        self.rate_floor_fraction = float(rate_floor_fraction)
        if self.background_rate.shape != (grid.num_cells,):
            raise ValueError("background rate must have one value per cell")
        if self.last_event_days.shape != (grid.num_cells,):
            raise ValueError("last-event state must have one value per cell")
        zero = np.zeros(grid.num_cells, dtype=np.int32)
        self.window_counts = {}
        for window in windows:
            total = zero.copy()
            for day in range(self.issue_day - window, self.issue_day):
                total += daily_counts.get(day, zero)
            self.window_counts[window] = total

    def snapshot(self) -> tuple[np.ndarray, np.ndarray]:
        counts = []
        neighbor_counts = {}
        for window in self.windows:
            cell = self.window_counts[window]
            neighbor = self.grid.neighbor_sum(cell)
            neighbor_counts[window] = neighbor
            counts.extend((cell, neighbor))
        count_matrix = np.stack(counts, axis=1)
        if np.any(count_matrix > np.iinfo(np.uint16).max):
            raise OverflowError("activity count exceeds uint16 storage")

        global_rate = float(np.mean(self.background_rate))
        floor = max(global_rate * self.rate_floor_fraction, np.finfo(float).tiny)
        neighbor_background = self.grid.neighbor_sum(self.background_rate)
        cell_excess = _log_rate_ratio(
            self.window_counts[30], 30, self.background_rate, floor
        )
        neighbor_excess = _log_rate_ratio(
            neighbor_counts[30], 30, neighbor_background, floor
        )
        cell_acceleration = _log_smoothed_rate_ratio(
            self.window_counts[7],
            7,
            self.window_counts[30],
            30,
            np.maximum(self.background_rate, floor),
        )
        neighbor_acceleration = _log_smoothed_rate_ratio(
            neighbor_counts[7],
            7,
            neighbor_counts[30],
            30,
            np.maximum(neighbor_background, floor),
        )
        recency = np.minimum(
            self.issue_day - self.last_event_days, self.recency_cap_days
        ).astype(float)
        recency[self.last_event_days < 0] = self.recency_cap_days
        neighbor_recency = self.grid.neighbor_min(
            recency, float(self.recency_cap_days)
        )
        continuous = np.stack(
            (
                cell_excess,
                neighbor_excess,
                cell_acceleration,
                neighbor_acceleration,
                recency,
                neighbor_recency,
                self.background_rate,
            ),
            axis=1,
        ).astype(np.float32)
        return count_matrix.astype(np.uint16), continuous

    def advance(self) -> None:
        zero = np.zeros(self.grid.num_cells, dtype=np.int32)
        today = self.daily_counts.get(self.issue_day, zero)
        for window in self.windows:
            expired = self.daily_counts.get(self.issue_day - window, zero)
            self.window_counts[window] += today - expired
        active = today > 0
        self.last_event_days[active] = self.issue_day
        self.issue_day += 1


def empirical_background_rate(
    counts: np.ndarray,
    *,
    exposure_days: int,
    prior_days: int,
) -> np.ndarray:
    counts = np.asarray(counts, dtype=float)
    if counts.ndim != 1 or exposure_days <= 0 or prior_days <= 0:
        raise ValueError("background inputs must be a vector and positive days")
    global_rate = float(np.sum(counts) / (exposure_days * len(counts)))
    if global_rate <= 0:
        raise ValueError("background catalog must contain events")
    return (counts + global_rate * prior_days) / (exposure_days + prior_days)


def validate_matrix_manifest(manifest: dict) -> None:
    if manifest.get("schema_version") != MATRIX_SCHEMA_VERSION:
        raise ValueError("unsupported training matrix schema_version")
    if manifest.get("status") not in {"completed", "smoke"}:
        raise ValueError("training matrix status must be completed or smoke")
    for section in ("inputs", "period", "features", "outputs", "results"):
        if not isinstance(manifest.get(section), dict):
            raise ValueError(f"training matrix manifest missing {section}")
    for key in ("config_sha256", "challenge_contract_sha256", "catalog_sha256", "grid_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", manifest["inputs"].get(key, "")):
            raise ValueError(f"invalid SHA-256 at inputs.{key}")
    if manifest["features"].get("count") != list(COUNT_FEATURES):
        raise ValueError("count feature contract changed")
    if manifest["features"].get("continuous") != list(CONTINUOUS_FEATURES):
        raise ValueError("continuous feature contract changed")
    shards = manifest["outputs"].get("shards") or []
    if not shards:
        raise ValueError("training matrix must contain shards")
    if any(not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")) for item in shards):
        raise ValueError("training matrix shard hash is invalid")
    if manifest["results"].get("issue_days", 0) <= 0:
        raise ValueError("training matrix must contain issue days")


def verify_matrix_artifacts(manifest: dict, repository_root: Path) -> None:
    validate_matrix_manifest(manifest)
    root = repository_root.resolve()
    expected_cells = manifest["results"]["grid_cells"]
    expected_thresholds = len(manifest["results"]["target_magnitude_thresholds"])
    total_days = 0
    total_targets = np.zeros(expected_thresholds, dtype=np.int64)
    previous_day = None
    for item in manifest["outputs"]["shards"]:
        path = (root / item["path"]).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError(f"matrix shard is missing or unsafe: {item['path']}")
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"matrix shard hash mismatch: {item['path']}")
        with np.load(path, allow_pickle=False) as shard:
            days = shard["issue_days"]
            counts = shard["count_features"]
            continuous = shard["continuous_features"]
            targets = shard["target_counts"]
        shard_days = len(days)
        if counts.shape != (shard_days, expected_cells, len(COUNT_FEATURES)):
            raise ValueError(f"invalid count feature shape: {item['path']}")
        if continuous.shape != (
            shard_days,
            expected_cells,
            len(CONTINUOUS_FEATURES),
        ):
            raise ValueError(f"invalid continuous feature shape: {item['path']}")
        if targets.shape != (shard_days, expected_cells, expected_thresholds):
            raise ValueError(f"invalid target shape: {item['path']}")
        if counts.dtype != np.uint16 or continuous.dtype != np.float32:
            raise ValueError(f"invalid feature dtype: {item['path']}")
        if targets.dtype != np.uint16 or days.dtype != np.int32:
            raise ValueError(f"invalid target or issue-day dtype: {item['path']}")
        if shard_days != item["issue_days"] or not np.all(np.diff(days) == 1):
            raise ValueError(f"non-contiguous issue days: {item['path']}")
        if previous_day is not None and int(days[0]) != previous_day + 1:
            raise ValueError("matrix shards are not globally contiguous")
        previous_day = int(days[-1])
        if not np.all(np.isfinite(continuous)):
            raise ValueError(f"non-finite continuous feature: {item['path']}")
        total_days += shard_days
        total_targets += np.sum(targets, axis=(0, 1), dtype=np.int64)
    if total_days != manifest["results"]["issue_days"]:
        raise ValueError("matrix issue-day total does not match manifest")
    if total_targets.tolist() != manifest["results"]["target_counts"]:
        raise ValueError("matrix target totals do not match manifest")


def _log_rate_ratio(
    counts: np.ndarray,
    window_days: int,
    background_rate: np.ndarray,
    floor: float,
) -> np.ndarray:
    baseline = np.maximum(background_rate, floor)
    smoothed = (counts + baseline * 7.0) / (window_days + 7.0)
    return np.log(np.maximum(smoothed, floor) / baseline)


def _log_smoothed_rate_ratio(
    recent_counts: np.ndarray,
    recent_days: int,
    long_counts: np.ndarray,
    long_days: int,
    baseline_rate: np.ndarray,
) -> np.ndarray:
    recent_rate = recent_counts / recent_days + baseline_rate
    long_rate = long_counts / long_days + baseline_rate
    return np.log(recent_rate / long_rate)
