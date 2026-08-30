#!/usr/bin/env python3
"""Benchmark one prospective California ETAS issue on local locked data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.prospective_context import load_california_runtime_context  # noqa: E402
from etas_challenge.prospective_etas import california_daily_etas_grid  # noqa: E402


CATALOG_PATH = ROOT / "data/local/california-earthquakes-v1.sqlite"
ETAS_MODEL_PATH = ROOT / "models/etas/california-comcat25-v1.json"
REFERENCE_PATH = ROOT / "configs/evaluation/comcat25-pycsep-day7-v1.json"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-time", default="2026-08-19T00:00:00Z")
    parser.add_argument("--simulations", type=int, default=1000)
    return parser.parse_args()


def load_history(issue_time: str, context):
    connection = sqlite3.connect(
        f"{CATALOG_PATH.resolve().as_uri()}?mode=ro&immutable=1", uri=True
    )
    try:
        rows = connection.execute(
            """
            SELECT origin_time_utc, latitude, longitude, magnitude
            FROM catalog_events
            WHERE origin_time_utc >= '1971-01-01T00:00:00Z'
              AND origin_time_utc < ? AND magnitude >= 2.5
            ORDER BY origin_time_utc, event_id
            """,
            (issue_time,),
        ).fetchall()
    finally:
        connection.close()
    times = np.asarray(
        [np.datetime64(row[0].removesuffix("Z"), "ns").astype(np.int64) for row in rows],
        dtype=np.int64,
    )
    latitudes = np.asarray([row[1] for row in rows], dtype=float)
    longitudes = np.asarray([row[2] for row in rows], dtype=float)
    magnitudes = np.asarray([row[3] for row in rows], dtype=float)
    cells = context.grid.cell_indexes(longitudes, latitudes)
    selected = cells >= 0
    return times[selected], latitudes[selected], longitudes[selected], magnitudes[selected]


def main() -> int:
    args = parse_args()
    if args.simulations <= 0:
        raise SystemExit("--simulations must be positive")
    issue = np.datetime64(args.issue_time.removesuffix("Z"), "ns")
    context = load_california_runtime_context(ROOT)
    model = json.loads(ETAS_MODEL_PATH.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    history = load_history(args.issue_time, context)
    started = time.perf_counter()
    result = california_daily_etas_grid(
        issue_time=issue,
        history_origin_time_ns=history[0],
        history_latitudes=history[1],
        history_longitudes=history[2],
        history_magnitudes=history[3],
        grid=context.grid,
        background_rates=context.baseline_background_grid,
        polygon_lat_lon=np.asarray(reference["polygon_lat_lon"]),
        area_km2=reference["area_km2"],
        beta=model["beta"],
        magnitude_reference=model["magnitude_reference"],
        magnitude_bin_width=reference["delta_m"],
        parameters=model["parameters"],
        simulations=args.simulations,
        random_seed=20260830,
        earth_radius_km=reference["earth_radius_km"],
        max_events_per_catalog=reference["max_events_per_catalog"],
    )
    elapsed = time.perf_counter() - started
    print(
        json.dumps(
            {
                "status": "ok",
                "issue_time": args.issue_time,
                "history_events": len(history[0]),
                "simulations": args.simulations,
                "elapsed_seconds": elapsed,
                "estimated_10000_seconds": elapsed * 10000 / args.simulations,
                "expected_count": result.expected_count,
                "sampled_nonbackground_events": result.sampled_nonbackground_events,
                "sampled_nonbackground_inside": result.sampled_nonbackground_inside,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
