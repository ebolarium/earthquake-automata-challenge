#!/usr/bin/env python3
"""Fetch official JMA files and export the three FERN experiment regions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.jma_catalog import FERN_REGIONS, parse_hypocenter_lines  # noqa: E402

BASE_URL = "https://www.data.jma.go.jp/eqev/data/bulletin/data/hypo"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/regions/fern-japan-v1.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/jma"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/catalogs/fern-japan-v1"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/fern-japan-catalog-v1.json"))
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_names() -> list[str]:
    return ["h1967.zip", *[f"h{year}.zip" for year in range(1983, 1997)], "h199701.zip", "h199710.zip", *[f"h{year}.zip" for year in range(1998, 2012)]]


def download(url: str, path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", url, "--output", temporary],
        check=True,
    )
    os.replace(temporary, path)


def read_events(paths: list[Path]):
    events = []
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                with archive.open(member) as handle:
                    lines = (line.decode("ascii", errors="replace") for line in handle)
                    events.extend(parse_hypocenter_lines(lines))
    events.sort(key=lambda event: event.time_utc)
    return events


def write_csv(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time_utc", "latitude", "longitude", "depth_km", "magnitude", "magnitude_type", "agency"))
        for event in rows:
            writer.writerow((event.time_utc.isoformat(), f"{event.latitude:.6f}", f"{event.longitude:.6f}", f"{event.depth_km:.3f}", f"{event.magnitude:.2f}", event.magnitude_type, event.agency))
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    paths = []
    for name in source_names():
        path = args.raw_dir / name
        download(f"{BASE_URL}/{name}", path)
        paths.append(path)
    events = read_events(paths)
    periods = {name: tuple(datetime.fromisoformat(value) for value in bounds) for name, bounds in config["periods"].items()}
    outputs = {}
    counts = {}
    for region in FERN_REGIONS:
        target = [event for event in events if region.contains(event)]
        feature = [event for event in events if region.contains(event, feature_catalog=True)]
        target_path = args.output_dir / f"region-{region.name.lower()}-target.csv"
        feature_path = args.output_dir / f"region-{region.name.lower()}-features.csv"
        write_csv(target_path, target)
        write_csv(feature_path, feature)
        outputs[region.name] = {
            "target_path": str(target_path), "target_sha256": sha256_file(target_path), "target_events": len(target),
            "feature_path": str(feature_path), "feature_sha256": sha256_file(feature_path), "feature_events": len(feature),
        }
        counts[region.name] = {
            name: sum(start <= event.time_utc < end for event in target)
            for name, (start, end) in periods.items()
        }
    manifest = {
        "schema_version": 1,
        "catalog_id": "fern-japan-catalog-v1",
        "config": str(args.config),
        "config_sha256": sha256_file(args.config),
        "sources": [{"url": f"{BASE_URL}/{path.name}", "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in paths],
        "parsed_events": len(events),
        "outputs": outputs,
        "period_counts": counts,
        "published_target_counts": config["published_target_counts"],
        "count_deltas": {
            region: {
                split: counts[region][split] - expected
                for split, expected in expected_counts.items()
            }
            for region, expected_counts in config["published_target_counts"].items()
        },
        "claim_boundary": config["claim_boundary"],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.manifest.with_suffix(args.manifest.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.manifest)
    print(json.dumps({"parsed_events": len(events), "period_counts": counts, "count_deltas": manifest["count_deltas"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
