"""Deterministic export of a clean, provenance-aware earthquake catalog."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import numpy as np


SCHEMA_VERSION = 1
TOOL_VERSION = "1.0.0"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_PATTERN = re.compile(r"^\d{2}:\d{2}:\d{2}(?:\.\d+)?$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def point_intersects_polygon(
    latitude: float,
    longitude: float,
    polygon: np.ndarray,
    tolerance: float = 1e-12,
) -> bool:
    inside = False
    for index in range(len(polygon) - 1):
        lat_a, lon_a = polygon[index]
        lat_b, lon_b = polygon[index + 1]
        if _point_on_segment(
            latitude,
            longitude,
            lat_a,
            lon_a,
            lat_b,
            lon_b,
            tolerance,
        ):
            return True
        crosses = (lon_a > longitude) != (lon_b > longitude)
        if crosses:
            intersection = lat_a + (longitude - lon_a) * (lat_b - lat_a) / (
                lon_b - lon_a
            )
            if latitude < intersection:
                inside = not inside
    return inside


def load_polygon(path: Path) -> np.ndarray:
    polygon = np.asarray(np.load(path, allow_pickle=False), dtype=float)
    if polygon.ndim != 2 or polygon.shape[1] != 2 or len(polygon) < 4:
        raise ValueError("region polygon must be an Nx2 array with at least 4 rows")
    if not np.all(np.isfinite(polygon)):
        raise ValueError("region polygon must contain only finite coordinates")
    if not np.array_equal(polygon[0], polygon[-1]):
        raise ValueError("region polygon must be closed")
    return polygon


def export_catalog(
    *,
    source_path: Path,
    region_path: Path,
    output_path: Path,
    manifest_path: Path,
    snapshot_id: str,
    expected_source_sha256: str,
    output_label: str,
) -> dict:
    source_path = source_path.resolve()
    region_path = region_path.resolve()
    source_hash_before = sha256_file(source_path)
    if source_hash_before != expected_source_sha256:
        raise ValueError(
            "source SHA-256 does not match the locked snapshot: "
            f"{source_hash_before}"
        )
    polygon = load_polygon(region_path)
    region_hash = sha256_file(region_path)
    bounds = {
        "min_latitude": float(np.min(polygon[:, 0])),
        "max_latitude": float(np.max(polygon[:, 0])),
        "min_longitude": float(np.min(polygon[:, 1])),
        "max_longitude": float(np.max(polygon[:, 1])),
    }

    source = _open_source(source_path)
    temporary_output = output_path.with_suffix(output_path.suffix + ".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _remove_temporary(temporary_output)
    destination = sqlite3.connect(temporary_output)
    try:
        _configure_destination(destination)
        _create_schema(destination)
        source_counts = _source_counts(source)
        export_counts, observed = _copy_events(
            source, destination, polygon, bounds
        )
        _write_metadata(
            destination,
            {
                "schema_version": str(SCHEMA_VERSION),
                "snapshot_id": snapshot_id,
                "source_sha256": source_hash_before,
                "region_sha256": region_hash,
                "region_boundary_policy": "intersects",
                "selection": "is_catalog_earthquake=1; magnitude not null; region intersects",
                "tool_version": TOOL_VERSION,
            },
        )
        destination.commit()
        integrity = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"destination integrity check failed: {integrity}")
        destination.execute("VACUUM")
    except BaseException:
        destination.close()
        source.close()
        _remove_temporary(temporary_output)
        raise
    destination.close()
    source.close()

    source_hash_after = sha256_file(source_path)
    if source_hash_after != source_hash_before:
        _remove_temporary(temporary_output)
        raise ValueError("source database changed during export")
    os.replace(temporary_output, output_path)
    output_path.chmod(0o444)
    output_hash = sha256_file(output_path)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "status": "exported",
        "tool": {
            "name": "etas_challenge.catalog_export",
            "version": TOOL_VERSION,
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
        },
        "source": {
            "name": source_path.name,
            "sha256": source_hash_before,
            "bytes": source_path.stat().st_size,
            "committed": False,
            **source_counts,
        },
        "region": {
            "id": "earthquakenpp-comcat25-california",
            "shape_sha256": region_hash,
            "boundary_policy": "intersects",
            "coordinate_order": "latitude,longitude",
            **bounds,
        },
        "selection": {
            "is_catalog_earthquake": 1,
            "requires_magnitude": True,
            "magnitude_threshold": None,
            **export_counts,
        },
        "normalization": {
            "origin_time": "source date and time interpreted as UTC; Z appended",
            "legacy_source_catalog": "legacy-earthquake-db",
            "legacy_usgs_source_catalog": "usgs-legacy",
            "null_active_event_type": "earthquake",
            "unavailable_provenance": None,
        },
        "output": {
            "label": output_label,
            "path": output_path.as_posix(),
            "sha256": output_hash,
            "bytes": output_path.stat().st_size,
            "rows": export_counts["included_rows"],
            "schema_version": SCHEMA_VERSION,
            **observed,
        },
    }
    validate_export_manifest(manifest)
    _atomic_json(manifest_path, manifest)
    return manifest


def validate_export_manifest(manifest: dict) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported clean catalog schema_version")
    if manifest.get("status") != "exported":
        raise ValueError("clean catalog manifest must have exported status")
    for section in ("source", "region", "selection", "normalization", "output"):
        if not isinstance(manifest.get(section), dict):
            raise ValueError(f"clean catalog manifest missing {section}")
    for section, key in (("source", "sha256"), ("region", "shape_sha256"), ("output", "sha256")):
        value = manifest[section].get(key, "")
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"invalid SHA-256 at {section}.{key}")
    if manifest["source"].get("committed") is not False:
        raise ValueError("source catalog database must never be committed")
    if manifest["output"].get("rows") != manifest["selection"].get(
        "included_rows"
    ):
        raise ValueError("output and selection row counts differ")
    if manifest["output"].get("rows", 0) <= 0:
        raise ValueError("clean catalog export must contain events")


def _open_source(path: Path) -> sqlite3.Connection:
    source = sqlite3.connect(f"{path.as_uri()}?mode=ro&immutable=1", uri=True)
    source.row_factory = sqlite3.Row
    source.execute("PRAGMA query_only = ON")
    required = {
        "event_id",
        "date",
        "time",
        "lat",
        "lon",
        "depth",
        "mag",
        "usgs_event_id",
        "event_type",
        "usgs_status",
        "usgs_updated_at",
        "is_catalog_earthquake",
        "excluded_reason",
        "source_catalog",
        "source_event_id",
        "source_url",
        "source_retrieved_at",
        "source_payload_hash",
    }
    actual = {
        row[1] for row in source.execute("PRAGMA table_info(earthquakes)").fetchall()
    }
    missing = required - actual
    if missing:
        source.close()
        raise ValueError(f"source earthquakes table missing columns: {sorted(missing)}")
    return source


def _configure_destination(destination: sqlite3.Connection) -> None:
    destination.execute("PRAGMA page_size = 4096")
    destination.execute("PRAGMA journal_mode = OFF")
    destination.execute("PRAGMA synchronous = OFF")
    destination.execute("PRAGMA temp_store = MEMORY")
    destination.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    destination.execute("PRAGMA application_id = 1163153747")


def _create_schema(destination: sqlite3.Connection) -> None:
    destination.executescript(
        """
        CREATE TABLE catalog_events (
            event_id TEXT PRIMARY KEY,
            source_catalog TEXT NOT NULL,
            source_event_id TEXT NOT NULL,
            source_row_id INTEGER NOT NULL UNIQUE,
            origin_time_utc TEXT NOT NULL,
            latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90),
            longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
            depth_km REAL,
            magnitude REAL NOT NULL,
            event_type TEXT NOT NULL,
            source_status TEXT,
            source_updated_at TEXT,
            source_retrieved_at TEXT,
            source_url TEXT,
            source_payload_hash TEXT,
            is_catalog_earthquake INTEGER NOT NULL CHECK(is_catalog_earthquake = 1),
            excluded_reason TEXT
        ) WITHOUT ROWID;
        CREATE INDEX catalog_events_origin_time
            ON catalog_events(origin_time_utc, event_id);
        CREATE INDEX catalog_events_magnitude
            ON catalog_events(magnitude);
        CREATE INDEX catalog_events_location
            ON catalog_events(latitude, longitude);
        CREATE UNIQUE INDEX catalog_events_source
            ON catalog_events(source_catalog, source_event_id);
        CREATE TABLE catalog_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        ) WITHOUT ROWID;
        """
    )


def _source_counts(source: sqlite3.Connection) -> dict:
    row = source.execute(
        """
        SELECT
            COUNT(*) AS total_rows,
            SUM(is_catalog_earthquake = 0) AS inactive_rows,
            SUM(is_catalog_earthquake = 1 AND mag IS NULL) AS active_missing_magnitude,
            SUM(is_catalog_earthquake = 1 AND mag IS NOT NULL) AS active_with_magnitude,
            SUM(lat < -90 OR lat > 90 OR lon < -180 OR lon > 180) AS invalid_coordinates
        FROM earthquakes
        """
    ).fetchone()
    return {key: int(row[key] or 0) for key in row.keys()}


def _copy_events(
    source: sqlite3.Connection,
    destination: sqlite3.Connection,
    polygon: np.ndarray,
    bounds: dict,
) -> tuple[dict, dict]:
    query = """
        SELECT event_id, date, time, lat, lon, depth, mag, usgs_event_id,
               event_type, usgs_status, usgs_updated_at, is_catalog_earthquake,
               excluded_reason, source_catalog, source_event_id, source_url,
               source_retrieved_at, source_payload_hash
        FROM earthquakes
        WHERE is_catalog_earthquake = 1
          AND mag IS NOT NULL
          AND lat BETWEEN ? AND ?
          AND lon BETWEEN ? AND ?
        ORDER BY date, time, event_id
    """
    parameters = (
        bounds["min_latitude"],
        bounds["max_latitude"],
        bounds["min_longitude"],
        bounds["max_longitude"],
    )
    insert = """
        INSERT INTO catalog_events VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """
    candidate_rows = 0
    included_rows = 0
    outside_polygon_rows = 0
    missing_payload_hash_rows = 0
    legacy_identity_rows = 0
    observed_times = []
    observed_magnitudes = []
    batch = []
    for row in source.execute(query, parameters):
        candidate_rows += 1
        latitude = float(row["lat"])
        longitude = float(row["lon"])
        magnitude = float(row["mag"])
        if not all(math.isfinite(value) for value in (latitude, longitude, magnitude)):
            raise ValueError(f"source row {row['event_id']} contains non-finite values")
        if not point_intersects_polygon(latitude, longitude, polygon):
            outside_polygon_rows += 1
            continue
        normalized = _normalize_event(row, latitude, longitude, magnitude)
        batch.append(normalized)
        included_rows += 1
        missing_payload_hash_rows += normalized[14] is None
        legacy_identity_rows += normalized[1] != row["source_catalog"]
        observed_times.append(normalized[4])
        observed_magnitudes.append(magnitude)
        if len(batch) == 1000:
            destination.executemany(insert, batch)
            batch.clear()
    if batch:
        destination.executemany(insert, batch)
    return (
        {
            "bounding_box_candidates": candidate_rows,
            "bounding_box_outside_polygon": outside_polygon_rows,
            "included_rows": included_rows,
            "missing_payload_hash_rows": missing_payload_hash_rows,
            "fallback_identity_rows": legacy_identity_rows,
        },
        {
            "first_origin_time_utc": min(observed_times),
            "last_origin_time_utc": max(observed_times),
            "minimum_magnitude": min(observed_magnitudes),
            "maximum_magnitude": max(observed_magnitudes),
        },
    )


def _normalize_event(row, latitude: float, longitude: float, magnitude: float):
    if not DATE_PATTERN.fullmatch(row["date"]) or not TIME_PATTERN.fullmatch(row["time"]):
        raise ValueError(f"source row {row['event_id']} has invalid origin time")
    if row["source_catalog"] and row["source_event_id"]:
        source_catalog = row["source_catalog"]
        source_event_id = row["source_event_id"]
    elif row["usgs_event_id"]:
        source_catalog = "usgs-legacy"
        source_event_id = row["usgs_event_id"]
    else:
        source_catalog = "legacy-earthquake-db"
        source_event_id = str(row["event_id"])
    event_id = f"{source_catalog}:{source_event_id}"
    depth = None if row["depth"] is None else float(row["depth"])
    if depth is not None and not math.isfinite(depth):
        raise ValueError(f"source row {row['event_id']} has non-finite depth")
    return (
        event_id,
        source_catalog,
        source_event_id,
        int(row["event_id"]),
        f"{row['date']}T{row['time']}Z",
        latitude,
        longitude,
        depth,
        magnitude,
        row["event_type"] or "earthquake",
        row["usgs_status"],
        row["usgs_updated_at"],
        row["source_retrieved_at"],
        row["source_url"],
        row["source_payload_hash"],
        1,
        row["excluded_reason"],
    )


def _write_metadata(destination: sqlite3.Connection, metadata: dict) -> None:
    destination.executemany(
        "INSERT INTO catalog_metadata(key, value) VALUES (?, ?)",
        sorted(metadata.items()),
    )


def _point_on_segment(
    point_lat,
    point_lon,
    lat_a,
    lon_a,
    lat_b,
    lon_b,
    tolerance,
) -> bool:
    cross = (point_lon - lon_a) * (lat_b - lat_a) - (
        point_lat - lat_a
    ) * (lon_b - lon_a)
    if abs(cross) > tolerance:
        return False
    return (
        min(lat_a, lat_b) - tolerance
        <= point_lat
        <= max(lat_a, lat_b) + tolerance
        and min(lon_a, lon_b) - tolerance
        <= point_lon
        <= max(lon_a, lon_b) + tolerance
    )


def _remove_temporary(path: Path) -> None:
    if path.exists():
        path.chmod(0o644)
        path.unlink()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
