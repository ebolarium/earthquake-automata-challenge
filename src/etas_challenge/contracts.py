"""Validation for committed experiment manifests."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    validate_reference_manifest(payload)
    return payload


def validate_reference_manifest(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported manifest schema_version")
    if payload.get("target_model") != "spatial_temporal_etas":
        raise ValueError("target_model must remain spatial_temporal_etas")

    repositories = payload.get("repositories") or {}
    for name in ("earthquakenpp", "etas_reference"):
        commit = repositories.get(name, {}).get("commit", "")
        if not GIT_SHA_RE.fullmatch(commit):
            raise ValueError(f"{name} must be pinned to a full Git commit")

    artifacts = payload.get("reference_artifacts") or []
    if not artifacts:
        raise ValueError("reference_artifacts must not be empty")
    for artifact in artifacts:
        if not SHA256_RE.fullmatch(artifact.get("sha256", "")):
            raise ValueError(f"invalid SHA-256 for {artifact.get('path')}")

    source = payload.get("local_source_snapshot") or {}
    if not SHA256_RE.fullmatch(source.get("sha256", "")):
        raise ValueError("local source database must have a SHA-256")
    if source.get("committed") is not False:
        raise ValueError("local source database must never be committed")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m etas_challenge.contracts MANIFEST.json")
        return 2
    payload = load_manifest(sys.argv[1])
    print(
        f"valid manifest: {payload['experiment_id']} "
        f"({len(payload['reference_artifacts'])} locked artifacts)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

