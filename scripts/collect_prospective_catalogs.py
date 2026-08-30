#!/usr/bin/env python3
"""Collect one rolling as-observed catalog snapshot for each dry-run region."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.object_storage import ObjectStorageConfig  # noqa: E402
from etas_challenge.object_storage import object_key, put_verified_bytes  # noqa: E402
from etas_challenge.prospective_catalog import fetch_snapshot  # noqa: E402
from etas_challenge.prospective_persistence import persist_snapshot  # noqa: E402
from etas_challenge.prospective_protocol import validate_protocol  # noqa: E402


PROTOCOL_PATH = ROOT / "configs/prospective/three-region-dry-run-v1.json"


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff", type=parse_timestamp)
    parser.add_argument("--lookback-days", type=int, default=int(os.environ.get("CATALOG_LOOKBACK_DAYS", "30")))
    parser.add_argument("--region", action="append", dest="regions")
    return parser.parse_args()


def record_incident(database_url: str, protocol_id: str, region_id: str, error: Exception) -> None:
    import psycopg

    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            INSERT INTO prospective.incidents
                (protocol_id, region_id, severity, incident_type, message, details, occurred_at)
            VALUES (%s, %s, 'critical', 'catalog_collection_failed', %s, %s::jsonb, %s)
            """,
            (protocol_id, region_id, str(error)[:1000], json.dumps({"error_type": type(error).__name__}), datetime.now(timezone.utc)),
        )


def main() -> int:
    args = parse_args()
    if args.lookback_days <= 0:
        raise SystemExit("--lookback-days must be positive")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    import psycopg

    protocol = validate_protocol(PROTOCOL_PATH, ROOT)
    selected = set(args.regions or [region["region_id"] for region in protocol["regions"]])
    known = {region["region_id"] for region in protocol["regions"]}
    if not selected <= known:
        raise SystemExit(f"unknown regions: {', '.join(sorted(selected - known))}")
    cutoff = args.cutoff or datetime.now(timezone.utc)
    start = cutoff - timedelta(days=args.lookback_days)
    storage = ObjectStorageConfig.from_environment()
    expected_prefix = protocol["artifact_contract"]["s3_prefix"]
    if expected_prefix != f"{storage.prefix}/dry-run":
        raise ValueError("configured S3 prefix disagrees with dry-run protocol")
    client = storage.client()
    results = []
    failures = []
    for region in protocol["regions"]:
        if region["region_id"] not in selected:
            continue
        try:
            snapshot = fetch_snapshot(region, ROOT, start, cutoff)
            suffix = (
                f"dry-run/catalogs/{snapshot.region_id}/"
                f"{cutoff.strftime('%Y/%m/%d/%H%M%S%f')}-{snapshot.content_sha256}.txt"
            )
            key = object_key(storage, suffix)
            put_verified_bytes(storage, key, snapshot.raw_payload, "text/plain; charset=utf-8", client)
            with psycopg.connect(database_url) as connection:
                snapshot_id = persist_snapshot(connection, snapshot, key, datetime.now(timezone.utc))
            results.append({"region_id": snapshot.region_id, "snapshot_id": snapshot_id, "events": len(snapshot.events), "sha256": snapshot.content_sha256})
        except Exception as error:
            failures.append(
                {
                    "region_id": region["region_id"],
                    "error": type(error).__name__,
                    "message": str(error)[:500],
                }
            )
            record_incident(database_url, protocol["protocol_id"], region["region_id"], error)
    print(json.dumps({"status": "ok" if not failures else "failed", "cutoff": cutoff.isoformat(), "snapshots": results, "failures": failures}, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
