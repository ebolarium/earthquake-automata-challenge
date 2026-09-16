#!/usr/bin/env python3
"""Atomically activate the frozen formal protocol from causal dry-run state."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from advance_prospective_bootstrap_states import persist_state  # noqa: E402
from etas_challenge.object_storage import ObjectStorageConfig  # noqa: E402
from etas_challenge.object_storage import object_key, put_verified_bytes  # noqa: E402
from etas_challenge.prospective_bootstrap import utc_timestamp  # noqa: E402
from etas_challenge.prospective_protocol import validate_protocol  # noqa: E402
from etas_challenge.prospective_runtime import DRY_RUN_PROTOCOL_ID  # noqa: E402
from etas_challenge.prospective_runtime import PROSPECTIVE_PROTOCOL_ID  # noqa: E402
from etas_challenge.prospective_runtime import PROSPECTIVE_PROTOCOL_PATH  # noqa: E402
from etas_challenge.prospective_state import model_state_id  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-time", required=True, type=utc_timestamp)
    return parser.parse_args()


def read_verified(client, storage, key: str, expected_sha: str, expected_bytes=None):
    response = client.get_object(Bucket=storage.bucket, Key=key)
    payload = response["Body"].read()
    if expected_bytes is not None and len(payload) != int(expected_bytes):
        raise RuntimeError("source state byte count disagrees")
    if hashlib.sha256(payload).hexdigest() != expected_sha:
        raise RuntimeError("source state checksum disagrees")
    return payload


def transfer_state(connection, client, storage, protocol, region, issue_midnight):
    expected_as_of = issue_midnight - timedelta(days=1)
    row = connection.execute(
        """
        SELECT state_id, as_of, source_catalog_cutoff, source_snapshot_ids,
               baseline_model_id, challenger_model_id, artifact_key,
               artifact_sha256, artifact_bytes, manifest_key, manifest_sha256
        FROM prospective.model_states
        WHERE protocol_id = %s AND region_id = %s AND as_of < %s
        ORDER BY as_of DESC LIMIT 1
        """,
        (DRY_RUN_PROTOCOL_ID, region["region_id"], issue_midnight),
    ).fetchone()
    if row is None or row[1] != expected_as_of:
        raise RuntimeError(
            f"causal source state missing for {region['region_id']} at {expected_as_of.isoformat()}"
        )
    artifact = read_verified(client, storage, row[6], row[7], row[8])
    source_manifest_bytes = read_verified(client, storage, row[9], row[10])
    source_manifest = json.loads(source_manifest_bytes)
    state_id = model_state_id(
        protocol["protocol_id"], region["region_id"], row[1], row[2],
        source_manifest["catalog_history_sha256"],
        source_manifest["baseline_model_sha256"],
        source_manifest["challenger_model_sha256"],
    )
    stem = row[1].strftime("%Y%m%dT%H%M%SZ")
    artifact_key = object_key(
        storage, f"prospective/states/{region['region_id']}/{stem}-{row[7]}.npz"
    )
    put_verified_bytes(
        storage, artifact_key, artifact, "application/octet-stream", client
    )
    manifest = {
        **source_manifest,
        "schema_version": 2,
        "state_id": state_id,
        "protocol_id": protocol["protocol_id"],
        "artifact_key": artifact_key,
        "transferred_from": {
            "protocol_id": DRY_RUN_PROTOCOL_ID,
            "state_id": row[0],
            "manifest_key": row[9],
            "manifest_sha256": row[10],
            "transfer_rule": "no_refit_byte_identical_state",
        },
    }
    encoded = json.dumps(
        manifest, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    manifest_sha = hashlib.sha256(encoded).hexdigest()
    manifest_key = object_key(
        storage, f"prospective/states/{region['region_id']}/{stem}-{state_id}.json"
    )
    put_verified_bytes(storage, manifest_key, encoded, "application/json", client)
    record = {
        "state_id": state_id,
        "protocol_id": protocol["protocol_id"],
        "region_id": region["region_id"],
        "as_of": row[1],
        "catalog_cutoff": row[2],
        "snapshot_ids": list(row[3]),
        "baseline_model_id": row[4],
        "challenger_model_id": row[5],
        "artifact_key": artifact_key,
        "artifact_sha256": row[7],
        "artifact_bytes": int(row[8]),
        "manifest_key": manifest_key,
        "manifest_sha256": manifest_sha,
    }
    persist_state(connection, record)
    return {
        "region_id": region["region_id"],
        "source_state_id": row[0],
        "state_id": state_id,
        "as_of": row[1].isoformat(),
        "artifact_sha256": row[7],
    }


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    issue_time = args.issue_time.astimezone(timezone.utc)
    issue_midnight = issue_time.replace(hour=0, minute=0, second=0, microsecond=0)
    protocol = validate_protocol(ROOT / PROSPECTIVE_PROTOCOL_PATH, ROOT)
    activation_date = datetime.fromisoformat(
        protocol["automatic_activation"]["activation_issue_date_utc"]
    ).date()
    if issue_time.date() != activation_date:
        raise SystemExit("formal protocol may only be activated on its frozen issue date")
    if issue_time > issue_midnight + timedelta(minutes=15):
        raise SystemExit("formal protocol activation deadline has passed")

    import psycopg

    storage = ObjectStorageConfig.from_environment()
    client = storage.client()
    transferred = []
    with psycopg.connect(database_url) as connection:
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            ("ch008-formal-protocol-activation",),
        )
        row = connection.execute(
            "SELECT status FROM prospective.protocols WHERE protocol_id = %s",
            (PROSPECTIVE_PROTOCOL_ID,),
        ).fetchone()
        if row is None:
            raise RuntimeError("formal protocol was not seeded")
        if row[0] == "active":
            print(json.dumps({
                "status": "already_active", "protocol_id": PROSPECTIVE_PROTOCOL_ID
            }, sort_keys=True))
            return 0
        if row[0] != "draft":
            raise RuntimeError(f"formal protocol cannot activate from status {row[0]}")
        for region in protocol["regions"]:
            transferred.append(
                transfer_state(
                    connection, client, storage, protocol, region, issue_midnight
                )
            )
        first_target = datetime.fromisoformat(
            protocol["automatic_activation"]["first_target_start"]
        )
        connection.execute(
            """
            UPDATE prospective.protocols
            SET status = 'completed', completed_at = %s
            WHERE protocol_id = %s AND status <> 'completed'
            """,
            (issue_time, DRY_RUN_PROTOCOL_ID),
        )
        connection.execute(
            """
            UPDATE prospective.protocols
            SET status = 'active', planned_start = %s, activated_at = %s
            WHERE protocol_id = %s AND status = 'draft'
            """,
            (first_target, issue_time, PROSPECTIVE_PROTOCOL_ID),
        )
    print(json.dumps({
        "status": "activated",
        "protocol_id": PROSPECTIVE_PROTOCOL_ID,
        "issue_time": issue_time.isoformat(),
        "first_target_start": protocol["automatic_activation"]["first_target_start"],
        "states": transferred,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
