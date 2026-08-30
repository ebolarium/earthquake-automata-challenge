#!/usr/bin/env python3
"""Fetch and freeze the ComCat catalog for the locked Chile corridor."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.geonet_catalog import parse_fdsn_text  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402

PROTOCOL = ROOT / "configs/regions/chile-subduction-v1.json"
RAW_DIR = ROOT / "data/raw/usgs/chile-subduction-v1"
OUTPUT = ROOT / "data/catalogs/chile-subduction-v1/catalog.csv"
MANIFEST = ROOT / "data/manifests/chile-subduction-catalog-v1.json"


def download(url: str, parameters: dict[str, str], path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with urlopen(f"{url}?{urlencode(parameters)}", timeout=120) as response:
        temporary.write_bytes(response.read())
    os.replace(temporary, path)


def main() -> int:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    region = protocol["region"]
    start = datetime.fromisoformat(protocol["periods"]["fit"][0])
    end = datetime.fromisoformat(protocol["periods"]["external_evaluation"][1])
    base_parameters = {
        "format": "text",
        "minlatitude": str(region["latitude"][0]),
        "maxlatitude": str(region["latitude"][1]),
        "minlongitude": str(region["longitude"][0]),
        "maxlongitude": str(region["longitude"][1]),
        "minmagnitude": str(region["minimum_magnitude"]),
        "maxdepth": str(region["maximum_depth_km_exclusive"] - 1e-9),
        "eventtype": region["event_type"],
        "orderby": "time-asc",
    }
    paths = []
    parsed = []
    for year in range(start.year, end.year):
        chunk_start = max(start, datetime(year, 1, 1, tzinfo=timezone.utc))
        chunk_end = min(end, datetime(year + 1, 1, 1, tzinfo=timezone.utc))
        parameters = {
            **base_parameters,
            "starttime": chunk_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": chunk_end.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        path = RAW_DIR / f"{year}.txt"
        download(protocol["source"]["catalog_url"], parameters, path)
        paths.append(path)
        with path.open(encoding="utf-8") as handle:
            parsed.extend(parse_fdsn_text(handle))
    parsed.sort(key=lambda event: (event.time_utc, event.event_id))
    accepted = []
    seen = set()
    for event in parsed:
        if (
            event.event_id not in seen
            and start <= event.time_utc < end
            and region["latitude"][0] <= event.latitude < region["latitude"][1]
            and region["longitude"][0] <= event.longitude < region["longitude"][1]
            and event.depth_km < region["maximum_depth_km_exclusive"]
            and event.magnitude >= region["minimum_magnitude"]
            and event.event_type.lower() == region["event_type"].lower()
        ):
            accepted.append(event)
            seen.add(event.event_id)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("event_id", "time_utc", "latitude", "longitude", "depth_km", "magnitude", "magnitude_type", "event_type"))
        for event in accepted:
            writer.writerow((event.event_id, event.time_utc.isoformat(), f"{event.latitude:.6f}", f"{event.longitude:.6f}", f"{event.depth_km:.4f}", f"{event.magnitude:.3f}", event.magnitude_type, event.event_type))
    os.replace(temporary, OUTPUT)
    counts = {
        name: sum(datetime.fromisoformat(bounds[0]) <= event.time_utc < datetime.fromisoformat(bounds[1]) for event in accepted)
        for name, bounds in protocol["periods"].items()
    }
    payload = {
        "schema_version": 1,
        "catalog_id": "chile-subduction-catalog-v1",
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": sha256_file(PROTOCOL),
        "request": {"url": protocol["source"]["catalog_url"], "base_parameters": base_parameters, "chunking": "calendar_year_utc"},
        "raw_files": [{"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in paths],
        "parsed_events": len(parsed),
        "output_path": str(OUTPUT.relative_to(ROOT)),
        "output_sha256": sha256_file(OUTPUT),
        "accepted_events": len(accepted),
        "period_counts": counts,
        "prior_count_disclosure": protocol["prior_count_disclosure"],
        "claim_boundary": protocol["claim_boundary"],
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"accepted_events": len(accepted), "period_counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
