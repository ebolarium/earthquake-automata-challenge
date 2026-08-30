"""Canonical bootstrap catalog reads and prospective model-state identities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib

import numpy as np


@dataclass(frozen=True, slots=True)
class BootstrapCatalog:
    snapshot_ids: tuple[int, ...]
    event_ids: np.ndarray
    origin_time_ns: np.ndarray
    latitudes: np.ndarray
    longitudes: np.ndarray
    depths_km: np.ndarray
    magnitudes: np.ndarray


def selected_bootstrap_snapshots(connection, region_id: str, start, cutoff) -> list[dict]:
    rows = connection.execute(
        """
        SELECT DISTINCT ON (source_start_at, source_cutoff_at)
               snapshot_id, source_start_at, source_cutoff_at, event_count,
               artifact_key, content_sha256
        FROM prospective.catalog_snapshots
        WHERE region_id = %s
          AND collection_kind = 'bootstrap'
          AND source_start_at >= %s
          AND source_cutoff_at <= %s
        ORDER BY source_start_at, source_cutoff_at, captured_at DESC, snapshot_id DESC
        """,
        (region_id, start, cutoff),
    ).fetchall()
    return [
        {
            "snapshot_id": row[0],
            "start": row[1],
            "cutoff": row[2],
            "event_count": row[3],
            "artifact_key": row[4],
            "content_sha256": row[5],
        }
        for row in rows
    ]


def load_bootstrap_catalog(connection, snapshot_ids: list[int], as_of: datetime) -> BootstrapCatalog:
    if not snapshot_ids:
        raise ValueError("bootstrap catalog requires snapshot IDs")
    rows = connection.execute(
        """
        SELECT source_event_id, origin_time, latitude, longitude, depth_km, magnitude
        FROM prospective.catalog_event_versions
        WHERE snapshot_id = ANY(%s) AND origin_time < %s
        ORDER BY origin_time, source_event_id
        """,
        (snapshot_ids, as_of),
    ).fetchall()
    if not rows:
        raise ValueError("bootstrap catalog contains no events before state boundary")
    event_ids = np.asarray([row[0] for row in rows])
    if len(np.unique(event_ids)) != len(event_ids):
        raise ValueError("bootstrap state catalog contains duplicate event IDs")
    origin_time_ns = np.asarray(
        [int(row[1].timestamp() * 1_000_000_000) for row in rows], dtype=np.int64
    )
    return BootstrapCatalog(
        tuple(snapshot_ids),
        event_ids,
        origin_time_ns,
        np.asarray([row[2] for row in rows], dtype=np.float64),
        np.asarray([row[3] for row in rows], dtype=np.float64),
        np.asarray([row[4] for row in rows], dtype=np.float64),
        np.asarray([row[5] for row in rows], dtype=np.float64),
    )


def model_state_id(
    protocol_id: str,
    region_id: str,
    as_of: datetime,
    catalog_cutoff: datetime,
    catalog_sha256: str,
    baseline_model_sha256: str,
    challenger_model_sha256: str,
) -> str:
    value = "\n".join(
        (
            protocol_id,
            region_id,
            as_of.isoformat(),
            catalog_cutoff.isoformat(),
            catalog_sha256,
            baseline_model_sha256,
            challenger_model_sha256,
        )
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def catalog_history_sha256(catalog: BootstrapCatalog) -> str:
    """Hash only the canonical event history admitted before the state boundary."""

    digest = hashlib.sha256(b"prospective-catalog-history-v1\0")
    for event_id in catalog.event_ids:
        encoded = str(event_id).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    for name, values, dtype in (
        ("origin_time_ns", catalog.origin_time_ns, "<i8"),
        ("latitudes", catalog.latitudes, "<f8"),
        ("longitudes", catalog.longitudes, "<f8"),
        ("depths_km", catalog.depths_km, "<f8"),
        ("magnitudes", catalog.magnitudes, "<f8"),
    ):
        array = np.ascontiguousarray(values, dtype=np.dtype(dtype))
        digest.update(name.encode("ascii") + b"\0")
        digest.update(len(array).to_bytes(8, "big"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()
