"""Frozen downtime policy validation and launch-guard decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Callable, Sequence


@dataclass(frozen=True)
class RetryResult:
    succeeded: bool
    attempts: int
    deadline_blocked: bool
    error: str | None


@dataclass(frozen=True)
class InvalidationResult:
    invalid: bool
    missed_days: int
    consecutive_missed_days: int
    reason: str | None


def _offset_seconds(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 3:
        raise ValueError("downtime deadline offset must be HH:MM:SS")
    hours, minutes, seconds = (int(part) for part in parts)
    if hours < 0 or minutes not in range(60) or seconds not in range(60):
        raise ValueError("downtime deadline offset is invalid")
    return hours * 3600 + minutes * 60 + seconds


def validate_downtime_policy(path: Path) -> dict:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("$schema") != "ch008-downtime-policy-v1":
        raise ValueError("unexpected downtime policy schema")
    implementation = policy.get("implementation_status", {})
    if policy.get("status") != "frozen_before_prospective_launch" or not all(
        implementation.get(key) is True
        for key in ("policy_frozen", "code_wired", "tests_written")
    ):
        raise ValueError("downtime policy is not launch-ready")
    retry = policy["retry"]
    attempts = int(retry["max_attempts"])
    backoffs = retry["backoff_seconds"]
    if attempts < 1 or len(backoffs) != attempts - 1:
        raise ValueError("retry backoff count must equal max_attempts minus one")
    if any(int(value) <= 0 for value in backoffs):
        raise ValueError("retry backoffs must be positive")
    _offset_seconds(retry["hard_deadline_utc_offset"])
    if (
        attempts != 3
        or [int(value) for value in backoffs] != [60, 300]
        or retry["hard_deadline_utc_offset"] != "00:15:00"
    ):
        raise ValueError("downtime retry contract changed")
    failure = policy["region_day_failure"]
    if (
        failure["publication_missed"]["handling"] != "exclude_from_N"
        or failure["scoring_service_outage"]["handling"] != "defer_scoring"
        or failure["missingness_assumption"] != "none_assumed"
    ):
        raise ValueError("downtime failure classification changed")
    invalidation = policy["region_invalidation"]
    if int(invalidation["total_scheduled_region_days"]) != 365:
        raise ValueError("downtime policy must use 365 scheduled days per region")
    if not 0 < float(invalidation["threshold_pct"]) < 1:
        raise ValueError("downtime invalidation percentage is invalid")
    if int(invalidation["consecutive_day_limit"]) < 1:
        raise ValueError("consecutive missed-day limit must be positive")
    if (
        float(invalidation["threshold_pct"]) != 0.05
        or int(invalidation["consecutive_day_limit"]) != 7
        or invalidation["pooled_primary_claim_effect"]
        != "three_region_primary_claim_inconclusive"
    ):
        raise ValueError("downtime invalidation contract changed")
    extension = policy["test_extension"]
    if (
        extension["calendar_allowed"] is not False
        or int(extension["event_count_gate"]["minimum_pooled_target_events"]) != 500
        or extension["event_count_gate"]["if_not_reached_by_day_365"]
        != "result_inconclusive_not_failed"
    ):
        raise ValueError("downtime completion contract changed")
    return policy


def publication_deadline(issue_boundary: datetime, policy: dict) -> datetime:
    boundary = issue_boundary.astimezone(timezone.utc)
    boundary = boundary.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds = _offset_seconds(policy["retry"]["hard_deadline_utc_offset"])
    return boundary + timedelta(seconds=seconds)


def run_with_retries(
    operation: Callable[[], None],
    *,
    max_attempts: int,
    backoff_seconds: Sequence[int],
    deadline: datetime,
    now: Callable[[], datetime],
    sleep: Callable[[float], None],
) -> RetryResult:
    attempts = 0
    last_error = None
    for index in range(max_attempts):
        current = now().astimezone(timezone.utc)
        if current > deadline:
            return RetryResult(False, attempts, True, last_error)
        attempts += 1
        try:
            operation()
            return RetryResult(True, attempts, False, None)
        except Exception as error:  # The caller persists the terminal classification.
            last_error = f"{type(error).__name__}: {error}"[:1000]
        if index >= len(backoff_seconds):
            break
        delay = int(backoff_seconds[index])
        if now().astimezone(timezone.utc) + timedelta(seconds=delay) > deadline:
            return RetryResult(False, attempts, True, last_error)
        sleep(delay)
    return RetryResult(False, attempts, False, last_error)


def invalidation_threshold(policy: dict) -> int:
    config = policy["region_invalidation"]
    return math.floor(
        int(config["total_scheduled_region_days"]) * float(config["threshold_pct"])
    ) + 1


def publication_missed_dates(records: Sequence[dict]) -> list[date]:
    return [
        record["issue_date"]
        for record in records
        if record.get("publication_status") == "missed"
    ]


def evaluate_invalidation(missed_dates: Sequence[date], policy: dict) -> InvalidationResult:
    ordered = sorted(set(missed_dates))
    longest = 0
    current = 0
    previous = None
    for value in ordered:
        current = current + 1 if previous and value == previous + timedelta(days=1) else 1
        longest = max(longest, current)
        previous = value
    threshold = invalidation_threshold(policy)
    consecutive_limit = int(policy["region_invalidation"]["consecutive_day_limit"])
    if len(ordered) >= threshold:
        reason = f"missed_region_days_reached_{threshold}"
    elif longest >= consecutive_limit:
        reason = f"consecutive_missed_days_reached_{consecutive_limit}"
    else:
        reason = None
    return InvalidationResult(reason is not None, len(ordered), longest, reason)
