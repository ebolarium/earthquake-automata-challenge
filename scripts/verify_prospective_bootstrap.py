#!/usr/bin/env python3
"""Verify database coverage and object metadata for historical bootstrap catalogs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.object_storage import ObjectStorageConfig  # noqa: E402
from etas_challenge.prospective_bootstrap import auxiliary_start  # noqa: E402
from etas_challenge.prospective_bootstrap import utc_timestamp  # noqa: E402
from etas_challenge.prospective_bootstrap import validate_contiguous_windows  # noqa: E402
from etas_challenge.prospective_protocol import validate_protocol  # noqa: E402


PROTOCOL_PATH = ROOT / "configs/prospective/three-region-dry-run-v1.json"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff", type=utc_timestamp, required=True)
    parser.add_argument("--region", action="append", dest="regions")
    parser.add_argument("--skip-object-storage", action="store_true")
    return parser.parse_args()


def selected_snapshots(connection, region_id: str, start, cutoff) -> list[dict]:
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


def event_statistics(connection, snapshot_ids: list[int]) -> dict:
    row = connection.execute(
        """
        SELECT count(*), count(DISTINCT source_event_id),
               min(origin_time), max(origin_time)
        FROM prospective.catalog_event_versions
        WHERE snapshot_id = ANY(%s)
        """,
        (snapshot_ids,),
    ).fetchone()
    return {
        "rows": row[0],
        "unique_event_ids": row[1],
        "first_event": None if row[2] is None else row[2].isoformat(),
        "last_event": None if row[3] is None else row[3].isoformat(),
    }


def verify_region(connection, client, bucket: str, region: dict, root: Path, cutoff) -> dict:
    start = auxiliary_start(region, root)
    snapshots = selected_snapshots(connection, region["region_id"], start, cutoff)
    validate_contiguous_windows(
        [(item["start"], item["cutoff"]) for item in snapshots], start, cutoff
    )
    expected_events = sum(item["event_count"] for item in snapshots)
    statistics = event_statistics(connection, [item["snapshot_id"] for item in snapshots])
    if statistics["rows"] != expected_events:
        raise ValueError("catalog snapshot event counts disagree with stored rows")
    if statistics["unique_event_ids"] != statistics["rows"]:
        raise ValueError("catalog bootstrap contains duplicate source event IDs")
    if client is not None:
        for item in snapshots:
            metadata = client.head_object(Bucket=bucket, Key=item["artifact_key"])
            if metadata.get("Metadata", {}).get("sha256") != item["content_sha256"]:
                raise ValueError(f"object checksum metadata disagrees: {item['artifact_key']}")
    return {
        "region_id": region["region_id"],
        "start": start.isoformat(),
        "cutoff": cutoff.isoformat(),
        "windows": len(snapshots),
        "events": statistics["rows"],
        "first_event": statistics["first_event"],
        "last_event": statistics["last_event"],
        "objects_verified": 0 if client is None else len(snapshots),
    }


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    import psycopg

    protocol = validate_protocol(PROTOCOL_PATH, ROOT)
    selected = set(args.regions or [region["region_id"] for region in protocol["regions"]])
    known = {region["region_id"] for region in protocol["regions"]}
    if not selected <= known:
        raise SystemExit(f"unknown regions: {', '.join(sorted(selected - known))}")
    storage = None if args.skip_object_storage else ObjectStorageConfig.from_environment()
    client = None if storage is None else storage.client()
    bucket = "" if storage is None else storage.bucket
    results = []
    failures = []
    with psycopg.connect(database_url) as connection:
        for region in protocol["regions"]:
            if region["region_id"] not in selected:
                continue
            try:
                results.append(
                    verify_region(connection, client, bucket, region, ROOT, args.cutoff)
                )
            except Exception as error:
                failures.append(
                    {
                        "region_id": region["region_id"],
                        "error": type(error).__name__,
                        "message": str(error)[:500],
                    }
                )
    print(
        json.dumps(
            {
                "status": "ok" if not failures else "failed",
                "cutoff": args.cutoff.isoformat(),
                "regions": results,
                "failures": failures,
            },
            sort_keys=True,
        )
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
