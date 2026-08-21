"""Validation for the frozen ETAS challenger evaluation contract."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from etas_challenge.contracts import GIT_SHA_RE, SHA256_RE


REQUIRED_SPLITS = (
    "challenger_fit",
    "development_validation",
    "locked_retrospective_test",
)
REQUIRED_LOCKED_INPUTS = {
    "configs/reference/comcat25.json",
    "configs/replay/comcat25-daily-v1.json",
    "configs/evaluation/comcat25-pycsep-day7-v1.json",
    "data/manifests/reference-comcat25.json",
    "data/manifests/local-california-catalog-v1.json",
    "data/manifests/daily-replay-v1.json",
    "data/manifests/pycsep-day7-v1.json",
}
EXPECTED_SPLIT_BOUNDS = {
    "challenger_fit": (
        "2007-01-01T00:00:00Z",
        "2019-01-01T00:00:00Z",
        True,
    ),
    "development_validation": (
        "2019-01-01T00:00:00Z",
        "2023-01-01T00:00:00Z",
        True,
    ),
    "locked_retrospective_test": (
        "2023-01-01T00:00:00Z",
        "2026-08-19T00:00:00Z",
        False,
    ),
}
REQUIRED_REPORTS = {
    "daily paired log-score difference",
    "ETAS and challenger expected event counts",
    "number, spatial, pseudolikelihood, and magnitude consistency tests",
    "information gain for M>=3.5 and M>=4.0 target events",
    "information gain in the low-ETAS-intensity stratum",
    "30-day and 90-day block-bootstrap intervals",
    "feature ablations and failed experiments",
}


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("split timestamps must be UTC strings ending in Z")
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_challenge_contract(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    validate_challenge_contract(payload)
    return payload


def validate_challenge_contract(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported challenge schema_version")
    if payload.get("status") != "frozen":
        raise ValueError("challenge status must be frozen")

    baseline = payload.get("baseline") or {}
    if not GIT_SHA_RE.fullmatch(baseline.get("repository_commit", "")):
        raise ValueError("baseline repository_commit must be a full Git commit")
    if baseline.get("m_ref") != 2.5:
        raise ValueError("baseline m_ref must remain 2.5")

    inputs = payload.get("locked_inputs") or []
    if not inputs:
        raise ValueError("locked_inputs must not be empty")
    paths = set()
    for item in inputs:
        path = item.get("path", "")
        if not path or path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("locked input paths must be repository-relative")
        if path in paths:
            raise ValueError(f"duplicate locked input: {path}")
        paths.add(path)
        if not SHA256_RE.fullmatch(item.get("sha256", "")):
            raise ValueError(f"invalid locked input SHA-256: {path}")
    if paths != REQUIRED_LOCKED_INPUTS:
        raise ValueError("locked_inputs must contain the complete baseline set")

    catalog = payload.get("catalog") or {}
    if not SHA256_RE.fullmatch(catalog.get("sha256", "")):
        raise ValueError("catalog must have a SHA-256")
    if catalog.get("committed") is not False:
        raise ValueError("catalog database must never be committed")

    forecast = payload.get("forecast_contract") or {}
    if forecast.get("history_boundary") != "strictly_before_issue_time":
        raise ValueError("forecast history boundary must remain strict")
    if forecast.get("horizon_days") != 1:
        raise ValueError("forecast horizon must remain one day")
    if forecast.get("primary_magnitude_threshold") != 2.5:
        raise ValueError("primary magnitude threshold must remain 2.5")
    if forecast.get("region") != "california_relm_region":
        raise ValueError("forecast region must remain california_relm_region")
    if forecast.get("spatial_resolution_degrees") != 0.1:
        raise ValueError("forecast grid must remain 0.1 degrees")
    if forecast.get("secondary_magnitude_thresholds") != [3.5, 4.0]:
        raise ValueError("secondary magnitude thresholds must remain 3.5 and 4.0")

    splits = payload.get("splits") or []
    if tuple(item.get("name") for item in splits) != REQUIRED_SPLITS:
        raise ValueError("challenge splits are missing or out of order")
    previous_end = None
    for item in splits:
        expected_start, expected_end, selection_allowed = EXPECTED_SPLIT_BOUNDS[
            item["name"]
        ]
        if (item.get("start"), item.get("end_exclusive")) != (
            expected_start,
            expected_end,
        ):
            raise ValueError(f"frozen split bounds changed: {item['name']}")
        if item.get("model_selection_allowed") is not selection_allowed:
            raise ValueError(f"model-selection policy changed: {item['name']}")
        start = _parse_utc(item.get("start"))
        end = _parse_utc(item.get("end_exclusive"))
        if start >= end:
            raise ValueError(f"invalid split interval: {item.get('name')}")
        if previous_end is not None and start != previous_end:
            raise ValueError("challenge splits must be contiguous")
        previous_end = end
    locked_test = splits[-1]
    if locked_test.get("immutable") is not True:
        raise ValueError("locked retrospective test must be immutable")
    if locked_test.get("model_selection_allowed") is not False:
        raise ValueError("locked retrospective outcomes must not select models")

    metric = payload.get("primary_metric") or {}
    if metric.get("name") != "paired_point_process_information_gain_per_earthquake":
        raise ValueError("primary metric must remain paired information gain")
    if metric.get("baseline") != "frozen_etas":
        raise ValueError("primary metric baseline must remain frozen ETAS")

    uncertainty = payload.get("uncertainty") or {}
    if uncertainty.get("replicates", 0) < 10_000:
        raise ValueError("bootstrap must use at least 10,000 replicates")
    if uncertainty.get("mean_block_days") != 30:
        raise ValueError("primary bootstrap block must remain 30 days")
    if uncertainty.get("sensitivity_block_days") != 90:
        raise ValueError("sensitivity bootstrap block must remain 90 days")

    reports = set(payload.get("required_reports") or [])
    if not REQUIRED_REPORTS.issubset(reports):
        raise ValueError("required challenge reports are incomplete")

    prospective = payload.get("prospective") or {}
    if prospective.get("minimum_issue_days", 0) < 365:
        raise ValueError("prospective claim requires at least 365 issue days")
    if prospective.get("minimum_target_events", 0) < 500:
        raise ValueError("prospective claim requires at least 500 target events")
    if not payload.get("claim_boundary"):
        raise ValueError("retrospective claim boundary must be explicit")


def verify_locked_inputs(payload: dict[str, Any], repository_root: str | Path) -> None:
    validate_challenge_contract(payload)
    root = Path(repository_root).resolve()
    for item in payload["locked_inputs"]:
        path = (root / item["path"]).resolve()
        if root not in path.parents:
            raise ValueError(f"locked input escapes repository: {item['path']}")
        if not path.is_file():
            raise ValueError(f"locked input is missing: {item['path']}")
        actual = _sha256(path)
        if actual != item["sha256"]:
            raise ValueError(f"locked input hash mismatch: {item['path']}")

    catalog = payload["catalog"]
    catalog_path = (root / catalog["path"]).resolve()
    if catalog_path.is_file() and _sha256(catalog_path) != catalog["sha256"]:
        raise ValueError(f"catalog hash mismatch: {catalog['path']}")
