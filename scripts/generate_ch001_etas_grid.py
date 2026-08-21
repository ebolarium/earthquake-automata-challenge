#!/usr/bin/env python3
"""Generate resumable monthly frozen-ETAS rates on the CH-001 RELM grid."""

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

from etas_challenge.daily_replay import DailyCatalog  # noqa: E402
from etas_challenge.grid_forecast import (  # noqa: E402
    GRID_FORECAST_SCHEMA_VERSION,
    RelmGridProjector,
    analytical_background_rates,
    validate_grid_forecast_manifest,
)
from etas_challenge.parameters import ETASParameters  # noqa: E402
from etas_challenge.simulation import ETASContinuationSimulator  # noqa: E402
from etas_challenge.training_matrix import (  # noqa: E402
    GridDefinition,
    sha256_file,
    write_deterministic_npz,
)


TOOL_VERSION = "1.0.0"
EPOCH = np.datetime64("1970-01-01", "D")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/challenge/ch001-etas-grid-v1.json"),
    )
    parser.add_argument("--start")
    parser.add_argument("--end-exclusive")
    parser.add_argument("--simulations", type=int)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def parse_time(value: str) -> np.datetime64:
    return np.datetime64(value.removesuffix("Z"), "ns")


def day_number(value: str) -> int:
    return int((np.datetime64(value.removesuffix("Z"), "D") - EPOCH).astype(int))


def day_string(value: int) -> str:
    return np.datetime_as_string(EPOCH + np.timedelta64(value, "D"), unit="D")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_catalog(config: dict, simulation_config: dict) -> DailyCatalog:
    path = Path(config["catalog_path"])
    if sha256_file(path) != config["catalog_sha256"]:
        raise ValueError("catalog SHA-256 does not match ETAS grid config")
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True
    )
    rows = connection.execute(
        """
        SELECT origin_time_utc, latitude, longitude, magnitude
        FROM catalog_events
        WHERE origin_time_utc >= ? AND origin_time_utc < ?
        ORDER BY origin_time_utc, event_id
        """,
        (config["auxiliary_start"], config["issue_end_exclusive"]),
    ).fetchall()
    connection.close()
    magnitudes = np.asarray([row[3] for row in rows], dtype=float)
    delta_m = simulation_config["delta_m"]
    rounded = np.floor(magnitudes / delta_m + 0.5) * delta_m
    selected = rounded >= simulation_config["mc"]
    return DailyCatalog(
        times=np.asarray([parse_time(row[0]) for row in rows])[selected],
        latitudes=np.asarray([row[1] for row in rows], dtype=float)[selected],
        longitudes=np.asarray([row[2] for row in rows], dtype=float)[selected],
        magnitudes=rounded[selected],
    )


def build_simulator(config: dict, simulation_config: dict, catalog: DailyCatalog):
    parameters = ETASParameters.from_transformed(**simulation_config["parameters"])
    return ETASContinuationSimulator(
        catalog=catalog,
        polygon_lat_lon=np.asarray(simulation_config["polygon_lat_lon"]),
        area=simulation_config["area_km2"],
        m_ref=simulation_config["m_ref"],
        beta=simulation_config["beta"],
        parameters=parameters,
        horizon_days=simulation_config["horizon_days"],
        earth_radius=simulation_config["earth_radius_km"],
        max_events_per_catalog=simulation_config["max_events_per_catalog"],
    )


def month_key(day: int) -> str:
    return day_string(day)[:7]


def read_shard_summary(
    path: Path, *, simulations_per_issue: int, config_sha256: str
) -> dict:
    with np.load(path, allow_pickle=False) as shard:
        days = shard["issue_days"]
        expected = shard["expected_counts"]
        sampled = shard["sampled_nonbackground_events"]
        inside = shard["sampled_nonbackground_inside"]
        stored_simulations = int(shard["simulations_per_issue"])
        stored_config = str(shard["config_sha256"])
    if stored_simulations != simulations_per_issue:
        raise ValueError(f"existing shard has wrong simulation count: {path}")
    if stored_config != config_sha256:
        raise ValueError(f"existing shard has wrong config hash: {path}")
    return {
        "path": path,
        "issue_days": int(len(days)),
        "start_day": int(days[0]),
        "end_day": int(days[-1]),
        "expected_sum": float(np.sum(expected, dtype=np.float64)),
        "sampled": int(np.sum(sampled, dtype=np.uint64)),
        "inside": int(np.sum(inside, dtype=np.uint64)),
    }


def write_month(
    output_dir: Path,
    month: str,
    days: list[int],
    rates: list[np.ndarray],
    expected: list[float],
    sampled: list[int],
    inside: list[int],
    simulations_per_issue: int,
    config_sha256: str,
) -> Path:
    path = output_dir / f"etas-{month}.npz"
    write_deterministic_npz(
        path,
        {
            "issue_days": np.asarray(days, dtype=np.int32),
            "etas_rates": np.asarray(rates, dtype=np.float32),
            "expected_counts": np.asarray(expected, dtype=np.float64),
            "sampled_nonbackground_events": np.asarray(sampled, dtype=np.uint64),
            "sampled_nonbackground_inside": np.asarray(inside, dtype=np.uint64),
            "simulations_per_issue": np.asarray(
                simulations_per_issue, dtype=np.int32
            ),
            "config_sha256": np.asarray(config_sha256),
        },
    )
    return path


def main() -> int:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    config_hash = sha256_file(args.config)
    reference_path = Path(config["simulation_reference"])
    if sha256_file(reference_path) != config["simulation_reference_sha256"]:
        raise ValueError("simulation reference SHA-256 does not match config")
    if sha256_file(Path(config["challenge_contract"])) != config["challenge_contract_sha256"]:
        raise ValueError("challenge contract SHA-256 does not match config")
    if sha256_file(Path(config["grid_path"])) != config["grid_sha256"]:
        raise ValueError("grid SHA-256 does not match config")
    simulation_config = json.loads(reference_path.read_text(encoding="utf-8"))

    configured_start = day_number(config["issue_start"])
    configured_end = day_number(config["issue_end_exclusive"])
    start = day_number(args.start) if args.start else configured_start
    end = day_number(args.end_exclusive) if args.end_exclusive else configured_end
    simulations = args.simulations or config["n_simulations"]
    if start < configured_start or end > configured_end or end <= start:
        raise ValueError("requested period lies outside the frozen ETAS grid period")
    if simulations <= 0 or simulations > config["n_simulations"]:
        raise ValueError("simulations must be within the frozen configured count")
    full_run = (
        start == configured_start
        and end == configured_end
        and simulations == config["n_simulations"]
    )
    if not full_run and (args.output_dir is None or args.manifest is None):
        raise ValueError("smoke runs require explicit --output-dir and --manifest")
    output_dir = args.output_dir or Path(config["output_dir"])
    manifest_path = args.manifest or Path(config["manifest"])
    output_dir.mkdir(parents=True, exist_ok=True)

    grid = GridDefinition.load(Path(config["grid_path"]))
    projector = RelmGridProjector.from_grid(grid)
    background_rates = analytical_background_rates(
        grid,
        10.0 ** simulation_config["parameters"]["log10_mu"],
        simulation_config["earth_radius_km"],
    )
    catalog = load_catalog(config, simulation_config)
    simulator = build_simulator(config, simulation_config, catalog)

    summaries = []
    current = start
    while current < end:
        month = month_key(current)
        month_end = current + 1
        while month_end < end and month_key(month_end) == month:
            month_end += 1
        path = output_dir / f"etas-{month}.npz"
        if path.exists() and full_run and not args.force:
            summary = read_shard_summary(
                path,
                simulations_per_issue=simulations,
                config_sha256=config_hash,
            )
            if summary["start_day"] != current or summary["end_day"] != month_end - 1:
                raise ValueError(f"existing shard has wrong period: {path}")
            summaries.append(summary)
            print(f"reused {month}", flush=True)
            current = month_end
            continue

        issue_days = []
        rate_rows = []
        expected_rows = []
        sampled_rows = []
        inside_rows = []
        for issue_day in range(current, month_end):
            issue_time = (EPOCH + np.timedelta64(issue_day, "D")).astype(
                "datetime64[ns]"
            )
            counts = np.zeros(grid.num_cells, dtype=np.uint64)
            sampled_total = 0
            inside_total = 0
            for catalog_id in range(simulations):
                rng = np.random.default_rng(
                    np.random.SeedSequence(
                        [config["random_seed"], issue_day, catalog_id]
                    )
                )
                forecast = simulator.simulate_with_components(issue_time, rng)
                sample_counts, sampled_count, inside_count = (
                    projector.nonbackground_counts(forecast)
                )
                counts += sample_counts
                sampled_total += sampled_count
                inside_total += inside_count
            rate = background_rates + counts / simulations
            issue_days.append(issue_day)
            rate_rows.append(rate)
            expected_rows.append(float(np.sum(rate, dtype=np.float64)))
            sampled_rows.append(sampled_total)
            inside_rows.append(inside_total)
            print(
                f"{day_string(issue_day)} expected={expected_rows[-1]:.6f} "
                f"sampled={sampled_total}",
                flush=True,
            )
        path = write_month(
            output_dir,
            month,
            issue_days,
            rate_rows,
            expected_rows,
            sampled_rows,
            inside_rows,
            simulations,
            config_hash,
        )
        summaries.append(
            read_shard_summary(
                path,
                simulations_per_issue=simulations,
                config_sha256=config_hash,
            )
        )
        print(f"wrote {path}", flush=True)
        current = month_end

    shards = [
        {
            "path": str(summary["path"]),
            "sha256": sha256_file(summary["path"]),
            "issue_days": summary["issue_days"],
            "start": day_string(summary["start_day"]),
            "end_inclusive": day_string(summary["end_day"]),
        }
        for summary in summaries
    ]
    manifest = {
        "schema_version": GRID_FORECAST_SCHEMA_VERSION,
        "forecast_id": config["forecast_id"],
        "status": "completed" if full_run else "smoke",
        "tool": {
            "name": "scripts/generate_ch001_etas_grid.py",
            "version": TOOL_VERSION,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "sqlite": sqlite3.sqlite_version,
        },
        "inputs": {
            "config_sha256": config_hash,
            "challenge_contract_sha256": config["challenge_contract_sha256"],
            "simulation_reference_sha256": config["simulation_reference_sha256"],
            "catalog_sha256": config["catalog_sha256"],
            "grid_sha256": config["grid_sha256"],
        },
        "protocol": {
            "method": "EarthquakeNPP ETAS catalog continuation",
            "simulations_per_issue": simulations,
            "seed": config["random_seed"],
            "history_boundary": config["history_boundary"],
            "target_window": config["target_window"],
            "background_estimator": config["background_estimator"],
        },
        "period": {
            "start": day_string(start),
            "end_exclusive": day_string(end),
        },
        "outputs": {"shards": shards},
        "results": {
            "grid_cells": grid.num_cells,
            "issue_days": end - start,
            "rows": (end - start) * grid.num_cells,
            "mean_expected_events": float(
                sum(item["expected_sum"] for item in summaries) / (end - start)
            ),
            "sampled_nonbackground_events": sum(
                item["sampled"] for item in summaries
            ),
            "sampled_nonbackground_inside": sum(item["inside"] for item in summaries),
        },
        "claim_boundary": (
            "Frozen ETAS baseline rates only; no challenger fitting or performance "
            "result is included. Monte Carlo descendants use the locked seed and "
            "direct background roots are Rao-Blackwellized analytically."
        ),
    }
    validate_grid_forecast_manifest(manifest)
    atomic_json(manifest_path, manifest)
    print(json.dumps(manifest["results"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
