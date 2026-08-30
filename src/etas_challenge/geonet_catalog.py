"""GeoNet FDSN text parsing for the locked New Zealand CSEP experiment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable


@dataclass(frozen=True, slots=True)
class GeoNetEvent:
    event_id: str
    time_utc: datetime
    latitude: float
    longitude: float
    depth_km: float
    magnitude: float
    magnitude_type: str
    event_type: str


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_fdsn_text(lines: Iterable[str]) -> list[GeoNetEvent]:
    """Parse pipe-delimited FDSN text without depending on column order."""

    iterator = iter(lines)
    header = next(iterator, "").lstrip("#").strip().split("|")
    columns = {name.strip().lower(): index for index, name in enumerate(header)}

    def field(parts: list[str], *names: str) -> str:
        for name in names:
            index = columns.get(name.lower())
            if index is not None and index < len(parts):
                return parts[index].strip()
        raise ValueError(f"missing FDSN column: {names[0]}")

    def optional_field(parts: list[str], default: str, *names: str) -> str:
        try:
            return field(parts, *names)
        except ValueError:
            return default

    required = ("eventid", "time", "latitude", "longitude", "depth/km", "magnitude")
    if not all(name in columns for name in required):
        raise ValueError("unrecognized GeoNet FDSN text header")
    events = []
    for line in iterator:
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.rstrip("\r\n").split("|")
        try:
            event = GeoNetEvent(
                event_id=field(parts, "eventid"),
                time_utc=_timestamp(field(parts, "time")),
                latitude=float(field(parts, "latitude")),
                longitude=float(field(parts, "longitude")),
                depth_km=float(field(parts, "depth/km")),
                magnitude=float(field(parts, "magnitude")),
                magnitude_type=field(parts, "magnitudetype", "magtype"),
                event_type=optional_field(parts, "earthquake", "eventtype"),
            )
        except (ValueError, OverflowError):
            continue
        events.append(event)
    events.sort(key=lambda event: (event.time_utc, event.event_id))
    return events
