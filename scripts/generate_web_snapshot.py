"""Generate the independent ETAS web forecast snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sqlite3
from pathlib import Path

import numpy as np

from etas_challenge.daily_replay import DailyCatalog
from etas_challenge.kernels import branching_ratio
from etas_challenge.parameters import ETASParameters
from etas_challenge.simulation import ETASContinuationSimulator
from etas_challenge.web_snapshot import (
    WEB_SNAPSHOT_SCHEMA_VERSION,
    ForecastGridAccumulator,
    validate_web_manifest,
    validate_web_snapshot,
)


TOOL_VERSION = "1.0.0"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/web/comcat25-web-v1.json")
    )
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--simulations", type=int)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_time(value: str) -> np.datetime64:
    return np.datetime64(value.removesuffix("Z"), "ns")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_catalog(path: Path, config: dict):
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True
    )
    rows = connection.execute(
        """
        SELECT event_id, origin_time_utc, latitude, longitude, magnitude
        FROM catalog_events
        WHERE origin_time_utc >= ? AND origin_time_utc < ?
        ORDER BY origin_time_utc, event_id
        """,
        (config["auxiliary_start"], config["window_end_exclusive"]),
    ).fetchall()
    connection.close()
    times = np.array([parse_time(row[1]) for row in rows], dtype="datetime64[ns]")
    magnitudes = np.array([row[4] for row in rows], dtype=float)
    delta_m = config["model"]["delta_m"]
    rounded = np.floor(magnitudes / delta_m + 0.5) * delta_m
    selected = rounded >= config["model"]["mc"]
    catalog = DailyCatalog(
        times=times[selected],
        latitudes=np.array([row[2] for row in rows], dtype=float)[selected],
        longitudes=np.array([row[3] for row in rows], dtype=float)[selected],
        magnitudes=rounded[selected],
    )
    selected_rows = [row for row, keep in zip(rows, selected) if keep]
    return catalog, selected_rows


def build_snapshot(config: dict, catalog_path: Path, n_simulations: int) -> dict:
    model_config = json.loads(Path(config["model_config"]).read_text(encoding="utf-8"))
    config = {**config, "model": model_config}
    catalog, rows = load_catalog(catalog_path, config)
    issue_time = parse_time(config["issue_time"])
    history_end = int(np.searchsorted(catalog.times, issue_time, side="left"))
    if history_end != config["expected_counts"]["history_events"]:
        raise ValueError("history event count does not match web config")
    recent_start = issue_time - np.timedelta64(config["recent_history_days"], "D")
    recent_begin = int(np.searchsorted(catalog.times, recent_start, side="left"))
    if history_end - recent_begin != config["expected_counts"]["recent_events"]:
        raise ValueError("recent event count does not match web config")

    parameters = ETASParameters.from_transformed(**model_config["parameters"])
    simulator = ETASContinuationSimulator(
        catalog=catalog,
        polygon_lat_lon=np.asarray(model_config["polygon_lat_lon"]),
        area=model_config["area_km2"],
        m_ref=model_config["m_ref"],
        beta=model_config["beta"],
        parameters=parameters,
        horizon_days=config["horizon_days"],
        earth_radius=model_config["earth_radius_km"],
        max_events_per_catalog=model_config["max_events_per_catalog"],
    )
    accumulator = ForecastGridAccumulator(
        **config["grid"],
        thresholds=config["magnitude_thresholds"],
        n_catalogs=n_simulations,
    )
    for catalog_id in range(n_simulations):
        rng = np.random.default_rng(
            np.random.SeedSequence([config["random_seed"], catalog_id])
        )
        simulated = simulator.simulate(issue_time, rng)
        accumulator.add_catalog(
            simulated.latitudes, simulated.longitudes, simulated.magnitudes
        )
        if (catalog_id + 1) % 1000 == 0:
            print(f"generated {catalog_id + 1}/{n_simulations}", flush=True)
    grid = accumulator.result()

    recent_rows = rows[recent_begin:history_end]
    recent_events = [
        {
            "id": row[0],
            "time": row[1],
            "latitude": row[2],
            "longitude": row[3],
            "magnitude": float(catalog.magnitudes[recent_begin + index]),
        }
        for index, row in enumerate(recent_rows)
    ]
    evaluation_manifest = json.loads(
        Path("data/manifests/pycsep-day7-v1.json").read_text(encoding="utf-8")
    )
    replay_manifest = json.loads(
        Path("data/manifests/daily-replay-v1.json").read_text(encoding="utf-8")
    )
    snapshot = {
        "schema_version": WEB_SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": config["snapshot_id"],
        "forecast": {
            "issue_time": config["issue_time"],
            "window_end_exclusive": config["window_end_exclusive"],
            "horizon_days": config["horizon_days"],
            "n_simulations": n_simulations,
            "seed": config["random_seed"],
        },
        "model": {
            "name": "Native ETAS / ComCat_25",
            "m_ref": model_config["m_ref"],
            "beta": model_config["beta"],
            "branching_ratio": branching_ratio(model_config["beta"], parameters),
            "parameters": model_config["parameters"],
            "polygon_lat_lon": model_config["polygon_lat_lon"],
        },
        "catalog": {
            "history_events": history_end,
            "last_history_event": rows[history_end - 1][1],
            "recent_history_days": config["recent_history_days"],
            "recent_events": recent_events,
        },
        "grid": grid,
        "evaluation": {
            "pycsep": evaluation_manifest["results"]["etas"],
            "replay_days": replay_manifest["results"]["replay_days"],
            "replay_target_events": replay_manifest["results"]["target_events"],
            "information_gain_per_event_vs_poisson": replay_manifest["results"][
                "sequential_information_gain_per_event"
            ],
            "claim_boundary": evaluation_manifest["claim_boundary"],
        },
        "generated_by": {
            "tool": "scripts/generate_web_snapshot.py",
            "version": TOOL_VERSION,
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
    }
    validate_web_snapshot(snapshot)
    return snapshot


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    catalog_path = args.catalog or Path(config["catalog_path"])
    catalog_hash = sha256_file(catalog_path)
    if catalog_hash != config["catalog_sha256"]:
        raise ValueError("catalog SHA-256 does not match web config")
    n_simulations = args.simulations or config["n_simulations"]
    if n_simulations <= 0 or n_simulations > config["n_simulations"]:
        raise ValueError("simulations must be within the frozen configured count")
    output_path = args.output or Path(config["output"])
    snapshot = build_snapshot(config, catalog_path, n_simulations)
    atomic_json(output_path, snapshot)
    if n_simulations == config["n_simulations"]:
        manifest = {
            "schema_version": WEB_SNAPSHOT_SCHEMA_VERSION,
            "snapshot_id": config["snapshot_id"],
            "status": "completed",
            "config_sha256": sha256_file(args.config),
            "catalog_sha256": catalog_hash,
            "snapshot_sha256": sha256_file(output_path),
            "issue_time": config["issue_time"],
            "n_simulations": n_simulations,
            "history_events": snapshot["catalog"]["history_events"],
            "active_grid_cells": len(snapshot["grid"]["cells"]),
        }
        validate_web_manifest(manifest)
        atomic_json(args.manifest or Path(config["manifest"]), manifest)
    print(
        json.dumps(
            {
                "output": output_path.as_posix(),
                "sha256": sha256_file(output_path),
                "simulations": n_simulations,
                "active_grid_cells": len(snapshot["grid"]["cells"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
