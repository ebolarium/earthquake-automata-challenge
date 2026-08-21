#!/usr/bin/env python3
"""Generate monthly leakage-free CH-001 catalog feature shards."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sqlite3
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.training_matrix import (  # noqa: E402
    CONTINUOUS_FEATURES,
    COUNT_FEATURES,
    MATRIX_SCHEMA_VERSION,
    FeatureTimeline,
    GridDefinition,
    empirical_background_rate,
    sha256_file,
    validate_matrix_manifest,
    write_deterministic_npz,
)


TOOL_VERSION = "1.0.0"
EPOCH = np.datetime64("1970-01-01", "D")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch001-matrix-v1.json"),
    )
    parser.add_argument("--start")
    parser.add_argument("--end-exclusive")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def day_number(value: str) -> int:
    return int((np.datetime64(value.removesuffix("Z"), "D") - EPOCH).astype(int))


def day_string(value: int) -> str:
    return np.datetime_as_string(EPOCH + np.timedelta64(value, "D"), unit="D")


def load_events(config: dict, grid: GridDefinition):
    catalog_path = Path(config["catalog_path"])
    if sha256_file(catalog_path) != config["catalog_sha256"]:
        raise ValueError("catalog SHA-256 does not match CH-001 config")
    connection = sqlite3.connect(
        f"{catalog_path.resolve().as_uri()}?mode=ro&immutable=1", uri=True
    )
    rows = connection.execute(
        """
        SELECT origin_time_utc, longitude, latitude, magnitude
        FROM catalog_events
        WHERE origin_time_utc >= ? AND origin_time_utc < ?
        ORDER BY origin_time_utc, event_id
        """,
        (config["background_start"], config["issue_end_exclusive"]),
    ).fetchall()
    connection.close()
    times = np.array(
        [np.datetime64(row[0].removesuffix("Z"), "ns") for row in rows]
    )
    magnitudes = np.array([row[3] for row in rows], dtype=float)
    delta_m = config["magnitude_rounding"]
    magnitudes = np.floor(magnitudes / delta_m + 0.5) * delta_m
    selected = magnitudes >= config["history_magnitude_threshold"]
    indexes = grid.cell_indexes(
        np.array([row[1] for row in rows], dtype=float)[selected],
        np.array([row[2] for row in rows], dtype=float)[selected],
    )
    days = ((times[selected].astype("datetime64[D]") - EPOCH)).astype(int)
    return days, indexes, magnitudes[selected]


def build_counts(days, cells, magnitudes, grid, config):
    inside = cells >= 0
    outside_events = int(np.count_nonzero(~inside))
    days = days[inside]
    cells = cells[inside]
    magnitudes = magnitudes[inside]
    background_end = day_number(config["issue_start"])
    background_start = day_number(config["background_start"])
    background_mask = days < background_end
    background_counts = np.bincount(
        cells[background_mask], minlength=grid.num_cells
    ).astype(np.int64)
    background_rate = empirical_background_rate(
        background_counts,
        exposure_days=background_end - background_start,
        prior_days=config["background_prior_days"],
    )

    daily_counts = {}
    targets = {}
    thresholds = config["target_magnitude_thresholds"]
    for day in np.unique(days):
        selected_day = days == day
        day_cells = cells[selected_day]
        day_magnitudes = magnitudes[selected_day]
        daily_counts[int(day)] = np.bincount(
            day_cells, minlength=grid.num_cells
        ).astype(np.int32)
        target_columns = []
        for threshold in thresholds:
            target_columns.append(
                np.bincount(
                    day_cells[day_magnitudes >= threshold],
                    minlength=grid.num_cells,
                )
            )
        target = np.stack(target_columns, axis=1)
        if np.any(target > np.iinfo(np.uint16).max):
            raise OverflowError("target count exceeds uint16 storage")
        targets[int(day)] = target.astype(np.uint16)
    return daily_counts, targets, background_rate, outside_events


def initial_last_event_days(daily_counts, issue_day, num_cells):
    last = np.full(num_cells, -1, dtype=np.int32)
    for day in sorted(value for value in daily_counts if value < issue_day):
        active = daily_counts[day] > 0
        last[active] = day
    return last


def write_shard(output_dir, month, issue_days, count_rows, continuous_rows, targets):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{month}.npz"
    write_deterministic_npz(
        path,
        {
            "issue_days": np.asarray(issue_days, dtype=np.int32),
            "count_features": np.stack(count_rows),
            "continuous_features": np.stack(continuous_rows),
            "target_counts": np.stack(targets),
        },
    )
    return {
        "path": path.as_posix(),
        "sha256": sha256_file(path),
        "issue_days": len(issue_days),
        "first_issue": day_string(issue_days[0]),
        "last_issue": day_string(issue_days[-1]),
        "target_counts": np.sum(np.stack(targets), axis=(0, 1)).astype(int).tolist(),
        "bytes": path.stat().st_size,
    }


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    args = parse_args()
    config_hash = sha256_file(args.config)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if sha256_file(Path(config["challenge_contract"])) != config["challenge_contract_sha256"]:
        raise ValueError("challenge contract SHA-256 does not match CH-001 config")
    grid_path = Path(config["grid_path"])
    if sha256_file(grid_path) != config["grid_sha256"]:
        raise ValueError("grid SHA-256 does not match CH-001 config")
    grid = GridDefinition.load(grid_path)

    configured_start = day_number(config["issue_start"])
    configured_end = day_number(config["issue_end_exclusive"])
    start = day_number(args.start) if args.start else configured_start
    end = day_number(args.end_exclusive) if args.end_exclusive else configured_end
    if start < configured_start or end > configured_end or start >= end:
        raise ValueError("requested period must stay inside fit and validation splits")
    full_run = start == configured_start and end == configured_end
    output_dir = args.output_dir or Path(config["output_dir"])
    manifest_path = args.manifest or Path(config["manifest"])

    days, cells, magnitudes = load_events(config, grid)
    daily_counts, targets, background_rate, outside_events = build_counts(
        days, cells, magnitudes, grid, config
    )
    timeline = FeatureTimeline(
        grid=grid,
        daily_counts=daily_counts,
        issue_day=start,
        windows=tuple(config["activity_windows_days"]),
        background_rate=background_rate,
        last_event_days=initial_last_event_days(
            daily_counts, start, grid.num_cells
        ),
        recency_cap_days=config["recency_cap_days"],
        rate_floor_fraction=config["rate_floor_fraction"],
    )

    shards = []
    issue_days = []
    count_rows = []
    continuous_rows = []
    target_rows = []
    current_month = None
    zero_target = np.zeros(
        (grid.num_cells, len(config["target_magnitude_thresholds"])),
        dtype=np.uint16,
    )
    for issue_day in range(start, end):
        month = day_string(issue_day)[:7]
        if current_month is not None and month != current_month:
            shards.append(
                write_shard(
                    output_dir,
                    current_month,
                    issue_days,
                    count_rows,
                    continuous_rows,
                    target_rows,
                )
            )
            print(f"wrote {current_month}", flush=True)
            issue_days, count_rows, continuous_rows, target_rows = [], [], [], []
        current_month = month
        counts, continuous = timeline.snapshot()
        issue_days.append(issue_day)
        count_rows.append(counts)
        continuous_rows.append(continuous)
        target_rows.append(targets.get(issue_day, zero_target))
        timeline.advance()
    if issue_days:
        shards.append(
            write_shard(
                output_dir,
                current_month,
                issue_days,
                count_rows,
                continuous_rows,
                target_rows,
            )
        )
        print(f"wrote {current_month}", flush=True)

    target_totals = np.sum(
        np.asarray([item["target_counts"] for item in shards], dtype=np.int64),
        axis=0,
    )
    manifest = {
        "schema_version": MATRIX_SCHEMA_VERSION,
        "matrix_id": config["matrix_id"],
        "status": "completed" if full_run else "smoke",
        "tool": {
            "name": "scripts/generate_ch001_matrix.py",
            "version": TOOL_VERSION,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "sqlite": sqlite3.sqlite_version,
        },
        "inputs": {
            "config_sha256": config_hash,
            "challenge_contract_sha256": config["challenge_contract_sha256"],
            "catalog_sha256": config["catalog_sha256"],
            "grid_sha256": config["grid_sha256"],
        },
        "period": {
            "start": day_string(start),
            "end_exclusive": day_string(end),
            "history_boundary": config["history_boundary"],
            "target_window": config["target_window"],
        },
        "features": {
            "count": list(COUNT_FEATURES),
            "count_dtype": "uint16",
            "continuous": list(CONTINUOUS_FEATURES),
            "continuous_dtype": "float32",
            "activity_windows_days": config["activity_windows_days"],
        },
        "outputs": {"shards": shards},
        "results": {
            "grid_cells": grid.num_cells,
            "issue_days": end - start,
            "rows": (end - start) * grid.num_cells,
            "target_magnitude_thresholds": config["target_magnitude_thresholds"],
            "target_counts": target_totals.astype(int).tolist(),
            "catalog_events_outside_relm_grid": outside_events,
        },
        "claim_boundary": (
            "Catalog-only CH-001 features and targets; no ETAS grid offset and "
            "no challenger performance result are included."
        ),
    }
    validate_matrix_manifest(manifest)
    atomic_json(manifest_path, manifest)
    print(json.dumps(manifest["results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
