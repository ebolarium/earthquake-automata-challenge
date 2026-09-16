"""PostgreSQL persistence helpers for prospective catalog snapshots."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json

from etas_challenge.prospective_catalog import CatalogSnapshot, event_payload


COLLECTION_KINDS = {"rolling", "bootstrap"}


def snapshot_identity(snapshot: CatalogSnapshot, collection_kind: str) -> str:
    if collection_kind not in COLLECTION_KINDS:
        raise ValueError("invalid catalog collection kind")
    value = (
        f"{collection_kind}\n{snapshot.region_id}\n{snapshot.start.isoformat()}\n"
        f"{snapshot.cutoff.isoformat()}\n{snapshot.content_sha256}"
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def existing_window(
    connection,
    protocol_id: str,
    region_id: str,
    start: datetime,
    cutoff: datetime,
    collection_kind: str,
) -> tuple[int, int] | None:
    if collection_kind not in COLLECTION_KINDS:
        raise ValueError("invalid catalog collection kind")
    row = connection.execute(
        """
        SELECT snapshot_id, event_count
        FROM prospective.catalog_snapshots
        WHERE protocol_id = %s AND region_id = %s
          AND source_start_at = %s
          AND source_cutoff_at = %s
          AND collection_kind = %s
        ORDER BY captured_at DESC
        LIMIT 1
        """,
        (protocol_id, region_id, start, cutoff, collection_kind),
    ).fetchone()
    return None if row is None else (row[0], row[1])


def persist_snapshot(
    connection,
    protocol_id: str,
    snapshot: CatalogSnapshot,
    artifact_key: str,
    captured_at: datetime,
    collection_kind: str = "rolling",
) -> int:
    identity = snapshot_identity(snapshot, collection_kind)
    source_request = {
        "url": snapshot.request_url,
        "parameters": snapshot.request_parameters,
        "window": [snapshot.start.isoformat(), snapshot.cutoff.isoformat()],
        "collection_kind": collection_kind,
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO prospective.catalog_snapshots
                (protocol_id, region_id, captured_at, source_start_at, source_cutoff_at,
                 collection_kind, source_request, artifact_key, content_sha256,
                 event_count, snapshot_identity)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING snapshot_id
            """,
            (
                protocol_id,
                snapshot.region_id,
                captured_at,
                snapshot.start,
                snapshot.cutoff,
                collection_kind,
                json.dumps(source_request),
                artifact_key,
                snapshot.content_sha256,
                len(snapshot.events),
                identity,
            ),
        )
        returned = cursor.fetchone()
        if returned is None:
            cursor.execute(
                """
                SELECT snapshot_id, region_id, source_start_at, source_cutoff_at,
                       collection_kind, content_sha256
                FROM prospective.catalog_snapshots
                WHERE protocol_id = %s
                  AND (snapshot_identity = %s OR artifact_key = %s)
                ORDER BY (snapshot_identity = %s) DESC
                LIMIT 1
                """,
                (protocol_id, identity, artifact_key, identity),
            )
            existing = cursor.fetchone()
            expected = (
                snapshot.region_id,
                snapshot.start,
                snapshot.cutoff,
                collection_kind,
                snapshot.content_sha256,
            )
            if existing is None or tuple(existing[1:]) != expected:
                raise RuntimeError("conflicting catalog snapshot disagrees")
            snapshot_id = existing[0]
        else:
            snapshot_id = returned[0]
        for event in snapshot.events:
            cursor.execute(
                """
                INSERT INTO prospective.catalog_event_versions
                    (snapshot_id, source_event_id, origin_time, latitude, longitude,
                     depth_km, magnitude, magnitude_type, source_updated_at, payload)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s::jsonb)
                ON CONFLICT (snapshot_id, source_event_id) DO NOTHING
                """,
                (
                    snapshot_id,
                    event.event_id,
                    event.time_utc,
                    event.latitude,
                    event.longitude,
                    event.depth_km,
                    event.magnitude,
                    event.magnitude_type,
                    json.dumps(event_payload(event)),
                ),
            )
    return snapshot_id
