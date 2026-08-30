#!/usr/bin/env python3
"""Fetch and freeze the GeoNet catalog for the official New Zealand CSEP mask."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.geonet_catalog import parse_fdsn_text  # noqa: E402
from etas_challenge.masked_grid import masked_grid  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=Path("configs/regions/new-zealand-csep-v1.json"))
    parser.add_argument("--region-manifest", type=Path, default=Path("data/manifests/nz-csep-region-v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/geonet/nz-csep-v1"))
    parser.add_argument("--output", type=Path, default=Path("data/catalogs/new-zealand-csep-v1/catalog.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/nz-csep-catalog-v1.json"))
    return parser.parse_args()


def download(url: str, parameters: dict[str, str], path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with urlopen(f"{url}?{urlencode(parameters)}", timeout=120) as response:
        temporary.write_bytes(response.read())
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    region_manifest = json.loads(args.region_manifest.read_text(encoding="utf-8"))
    if sha256_file(args.protocol) != region_manifest["protocol_sha256"]:
        raise ValueError("New Zealand protocol changed after geometry lock")
    region_path = ROOT / region_manifest["output"]
    if sha256_file(region_path) != region_manifest["output_sha256"]:
        raise ValueError("New Zealand region mask changed")
    archive = np.load(region_path, allow_pickle=False)
    origins = archive["origins"]
    region = protocol["region"]
    grid = masked_grid(origins, region["mask_spacing_degrees"], region["latent_spacing_degrees"])
    start = protocol["periods"]["fit"][0]
    end = protocol["periods"]["external_evaluation"][1]
    spacing = region["mask_spacing_degrees"]
    base_parameters = {
        "format": "text",
        "minlatitude": str(float(np.min(origins[:, 1]))),
        "maxlatitude": str(float(np.max(origins[:, 1])) + spacing),
        "minlongitude": str(float(np.min(origins[:, 0]))),
        "maxlongitude": str(float(np.max(origins[:, 0])) + spacing),
        "minmagnitude": str(region["minimum_magnitude"]),
        "maxdepth": str(region["maximum_depth_km_exclusive"] - 1e-9),
        "eventtype": region["event_type"],
        "orderby": "time-asc",
    }
    start_time, end_time = datetime.fromisoformat(start), datetime.fromisoformat(end)
    raw_paths = []
    parsed = []
    for year in range(start_time.year, end_time.year):
        chunk_start = max(start_time, datetime(year, 1, 1, tzinfo=timezone.utc))
        chunk_end = min(end_time, datetime(year + 1, 1, 1, tzinfo=timezone.utc))
        parameters = {
            **base_parameters,
            "starttime": chunk_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": chunk_end.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        raw_path = args.raw_dir / f"{year}.txt"
        download(protocol["source"]["catalog_url"], parameters, raw_path)
        raw_paths.append(raw_path)
        with raw_path.open(encoding="utf-8") as handle:
            parsed.extend(parse_fdsn_text(handle))
    parsed.sort(key=lambda event: (event.time_utc, event.event_id))
    seen = set()
    accepted = []
    for event in parsed:
        inside = bool(grid.contains(np.asarray([event.latitude]), np.asarray([event.longitude]))[0])
        if (
            event.event_id not in seen
            and event.time_utc.isoformat() >= start
            and event.time_utc.isoformat() < end
            and event.magnitude >= region["minimum_magnitude"]
            and event.depth_km < region["maximum_depth_km_exclusive"]
            and event.event_type.lower() == region["event_type"].lower()
            and inside
        ):
            accepted.append(event)
            seen.add(event.event_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("event_id", "time_utc", "latitude", "longitude", "depth_km", "magnitude", "magnitude_type", "event_type"))
        for event in accepted:
            writer.writerow((event.event_id, event.time_utc.isoformat(), f"{event.latitude:.6f}", f"{event.longitude:.6f}", f"{event.depth_km:.4f}", f"{event.magnitude:.3f}", event.magnitude_type, event.event_type))
    os.replace(temporary, args.output)
    periods = {
        name: sum(bounds[0] <= event.time_utc.isoformat() < bounds[1] for event in accepted)
        for name, bounds in protocol["periods"].items()
    }
    manifest = {
        "schema_version": 1,
        "catalog_id": "nz-csep-catalog-v1",
        "protocol": str(args.protocol),
        "protocol_sha256": sha256_file(args.protocol),
        "region_manifest_sha256": sha256_file(args.region_manifest),
        "region_sha256": sha256_file(region_path),
        "request": {"url": protocol["source"]["catalog_url"], "base_parameters": base_parameters, "chunking": "calendar_year_utc"},
        "raw_files": [{"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in raw_paths],
        "parsed_events": len(parsed),
        "output_path": str(args.output),
        "output_sha256": sha256_file(args.output),
        "accepted_events": len(accepted),
        "period_counts": periods,
        "claim_boundary": protocol["claim_boundary"],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"accepted_events": len(accepted), "period_counts": periods}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
