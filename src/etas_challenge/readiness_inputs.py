"""Build fit-only CH-002 event inputs from the frozen catalog and ETAS grids."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from etas_challenge.grid_forecast import analytical_background_rates
from etas_challenge.training_matrix import GridDefinition, sha256_file


EPOCH = np.datetime64("1970-01-01", "D")


@dataclass(frozen=True, slots=True)
class FitCatalog:
    event_ids: np.ndarray
    origin_time_ns: np.ndarray
    issue_days: np.ndarray
    longitudes: np.ndarray
    latitudes: np.ndarray
    depths_km: np.ndarray
    magnitudes: np.ndarray
    cell_indexes: np.ndarray
    selected_before_grid: int
    outside_grid: int


@dataclass(frozen=True, slots=True)
class FitInputs:
    catalog: FitCatalog
    etas_rates: np.ndarray
    direct_background_rates: np.ndarray
    etas_background_probabilities: np.ndarray


def day_number(value: str) -> int:
    return int((np.datetime64(value.removesuffix("Z"), "D") - EPOCH).astype(int))


def load_fit_catalog(
    path: Path,
    grid: GridDefinition,
    *,
    start: str,
    end_exclusive: str,
    magnitude_rounding: float,
    magnitude_threshold: float,
) -> FitCatalog:
    """Load, round, threshold, and RELM-filter events in deterministic order."""

    if magnitude_rounding <= 0 or magnitude_threshold <= 0:
        raise ValueError("magnitude rounding and threshold must be positive")
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True
    )
    try:
        rows = connection.execute(
            """
            SELECT event_id, origin_time_utc, longitude, latitude, depth_km, magnitude
            FROM catalog_events
            WHERE origin_time_utc >= ? AND origin_time_utc < ?
            ORDER BY origin_time_utc, event_id
            """,
            (start, end_exclusive),
        ).fetchall()
    finally:
        connection.close()
    times = np.asarray(
        [np.datetime64(row[1].removesuffix("Z"), "ns") for row in rows]
    )
    magnitudes = np.asarray([row[5] for row in rows], dtype=float)
    rounded = np.floor(magnitudes / magnitude_rounding + 0.5) * magnitude_rounding
    selected = rounded >= magnitude_threshold
    event_ids = np.asarray([row[0] for row in rows])[selected]
    times = times[selected]
    longitudes = np.asarray([row[2] for row in rows], dtype=float)[selected]
    latitudes = np.asarray([row[3] for row in rows], dtype=float)[selected]
    depths = np.asarray(
        [np.nan if row[4] is None else row[4] for row in rows], dtype=float
    )[selected]
    rounded = rounded[selected]
    cells = grid.cell_indexes(longitudes, latitudes)
    inside = cells >= 0
    issue_days = (times.astype("datetime64[D]") - EPOCH).astype(np.int32)
    return FitCatalog(
        event_ids=event_ids[inside],
        origin_time_ns=times.astype(np.int64)[inside],
        issue_days=issue_days[inside],
        longitudes=longitudes[inside],
        latitudes=latitudes[inside],
        depths_km=depths[inside],
        magnitudes=rounded[inside],
        cell_indexes=cells[inside].astype(np.int32),
        selected_before_grid=int(np.count_nonzero(selected)),
        outside_grid=int(np.count_nonzero(~inside)),
    )


def attach_etas_background_probabilities(
    catalog: FitCatalog,
    *,
    grid: GridDefinition,
    etas_manifest: dict,
    repository_root: Path,
    mu_per_km2_day: float,
    earth_radius_km: float,
) -> FitInputs:
    """Join each event to its issue-day ETAS cell rate and exact background."""

    background_grid = analytical_background_rates(
        grid, mu_per_km2_day, earth_radius_km
    )
    shard_by_month = {
        Path(item["path"]).stem.removeprefix("etas-"): item
        for item in etas_manifest["outputs"]["shards"]
    }
    event_etas = np.empty(len(catalog.event_ids), dtype=np.float64)
    months = np.asarray(
        [
            np.datetime_as_string(EPOCH + np.timedelta64(int(day), "D"), unit="M")
            for day in catalog.issue_days
        ]
    )
    for month in np.unique(months):
        if month not in shard_by_month:
            raise ValueError(f"ETAS manifest has no shard for event month: {month}")
        item = shard_by_month[month]
        path = repository_root / item["path"]
        if sha256_file(path) != item["sha256"]:
            raise ValueError(f"ETAS shard SHA-256 changed: {item['path']}")
        with np.load(path, allow_pickle=False) as shard:
            days = shard["issue_days"]
            rates = shard["etas_rates"]
        day_lookup = {int(day): index for index, day in enumerate(days)}
        selected = np.flatnonzero(months == month)
        for event_index in selected:
            day = int(catalog.issue_days[event_index])
            if day not in day_lookup:
                raise ValueError(f"ETAS shard has no issue day: {day}")
            event_etas[event_index] = rates[
                day_lookup[day], catalog.cell_indexes[event_index]
            ]
    event_background = background_grid[catalog.cell_indexes]
    if (
        not np.all(np.isfinite(event_etas))
        or np.any(event_etas <= 0)
        or np.any(event_background > event_etas * (1 + 1e-6))
    ):
        raise ValueError("invalid ETAS/background event-rate decomposition")
    probability = np.clip(event_background / event_etas, 0.0, 1.0)
    return FitInputs(
        catalog=catalog,
        etas_rates=event_etas,
        direct_background_rates=event_background,
        etas_background_probabilities=probability,
    )
