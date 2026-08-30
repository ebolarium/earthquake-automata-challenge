"""Deterministic time windows for prospective catalog bootstrap."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path


def utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def auxiliary_start(region: dict, root: Path) -> datetime:
    model = json.loads((root / region["etas_model_path"]).read_text(encoding="utf-8"))
    if float(model["magnitude_reference"]) != float(region["minimum_magnitude"]):
        raise ValueError("ETAS magnitude reference disagrees with prospective region")
    return utc_timestamp(model["auxiliary_start"])


def calendar_year_windows(start: datetime, cutoff: datetime) -> list[tuple[datetime, datetime]]:
    if start.tzinfo is None or cutoff.tzinfo is None or start >= cutoff:
        raise ValueError("bootstrap window must be timezone-aware and increasing")
    windows = []
    current = start
    while current < cutoff:
        year_boundary = datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
        end = min(year_boundary, cutoff)
        windows.append((current, end))
        current = end
    return windows


def validate_contiguous_windows(
    windows: list[tuple[datetime, datetime]], start: datetime, cutoff: datetime
) -> None:
    if not windows:
        raise ValueError("bootstrap has no stored windows")
    cursor = start
    for window_start, window_end in sorted(windows):
        if window_start != cursor:
            relation = "overlap" if window_start < cursor else "gap"
            raise ValueError(f"bootstrap window {relation} at {cursor.isoformat()}")
        if window_end <= window_start:
            raise ValueError("bootstrap contains a non-increasing window")
        cursor = window_end
    if cursor != cutoff:
        raise ValueError(f"bootstrap ends at {cursor.isoformat()}, expected {cutoff.isoformat()}")
