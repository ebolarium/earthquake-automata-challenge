"""Parser and FERN-region filters for the JMA hypocenter bulletin."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

JST = timezone(timedelta(hours=9))


@dataclass(frozen=True, slots=True)
class JMAEvent:
    time_utc: datetime
    latitude: float
    longitude: float
    depth_km: float
    magnitude: float
    magnitude_type: str
    agency: str


@dataclass(frozen=True, slots=True)
class FERNRegion:
    name: str
    longitude_min: float
    longitude_max: float
    latitude_min: float
    latitude_max: float
    target_magnitude: float
    feature_magnitude: float = 3.0
    maximum_depth_km: float = 100.0

    def contains(self, event: JMAEvent, *, feature_catalog: bool = False) -> bool:
        threshold = self.feature_magnitude if feature_catalog else self.target_magnitude
        return (
            self.longitude_min <= event.longitude < self.longitude_max
            and self.latitude_min <= event.latitude < self.latitude_max
            and event.depth_km <= self.maximum_depth_km
            and event.magnitude >= threshold
        )


FERN_REGIONS = (
    FERNRegion("A", 141.0, 145.0, 36.0, 42.0, 4.5),
    FERNRegion("B", 145.0, 154.0, 42.0, 47.0, 4.5),
    FERNRegion("C", 141.0, 154.0, 36.0, 47.0, 5.0),
)


def _implied_decimal(value: str, decimal_places: int) -> float:
    stripped = value.strip()
    if not stripped:
        raise ValueError("missing numeric field")
    if "." in stripped:
        return float(stripped)
    return int(stripped) / (10**decimal_places)


def _jma_decimal(value: str, maximum_integer: int) -> float:
    """Parse JMA's left-aligned, decimal-point-omitted F fields."""

    stripped = value.strip()
    if not stripped:
        raise ValueError("missing numeric field")
    if "." in stripped:
        return float(stripped)
    number = int(stripped)
    divisor = 1
    while number / divisor > maximum_integer:
        divisor *= 10
    return number / divisor


def parse_hypocenter_record(line: str) -> JMAEvent | None:
    """Parse one official fixed-width JMA hypocenter record.

    Records without a usable primary magnitude or location are omitted. Times in
    the bulletin are JST and are normalized to UTC.
    """

    record = line.rstrip("\r\n")
    if len(record) < 58 or record[0] not in {"J", "U", "I"}:
        return None
    try:
        year = int(record[1:5])
        month = int(record[5:7])
        day = int(record[7:9])
        hour = int(record[9:11])
        minute = int(record[11:13])
        second = _jma_decimal(record[13:17], 60)
        latitude = int(record[21:24]) + _jma_decimal(record[24:28], 60) / 60
        longitude = int(record[32:36]) + _jma_decimal(record[36:40], 60) / 60
        depth = float(record[44:49].strip())
        magnitude = _implied_decimal(record[52:54], 1)
    except (ValueError, OverflowError):
        return None
    whole_second = int(second)
    microsecond = round((second - whole_second) * 1_000_000)
    if microsecond == 1_000_000:
        whole_second += 1
        microsecond = 0
    try:
        local_time = datetime(
            year,
            month,
            day,
            hour,
            minute,
            whole_second,
            microsecond,
            tzinfo=JST,
        )
    except ValueError:
        return None
    return JMAEvent(
        time_utc=local_time.astimezone(timezone.utc),
        latitude=latitude,
        longitude=longitude,
        depth_km=depth,
        magnitude=magnitude,
        magnitude_type=record[54:55].strip(),
        agency=record[0],
    )


def parse_hypocenter_lines(lines: Iterable[str]) -> list[JMAEvent]:
    events = []
    for line in lines:
        event = parse_hypocenter_record(line)
        if event is not None:
            events.append(event)
    return events
