"""Generate deterministic native ETAS and Poisson catalog forecasts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
from pathlib import Path

import numpy as np

from etas_challenge.daily_replay import DailyCatalog
from etas_challenge.kernels import branching_ratio
from etas_challenge.parameters import ETASParameters
from etas_challenge.simulation import ETASContinuationSimulator, SimulatedCatalog


TOOL_VERSION = "1.0.0"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/evaluation/comcat25-pycsep-day7-v1.json"),
    )
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


def load_catalog(config: dict) -> DailyCatalog:
    path = Path(config["catalog_path"])
    if sha256_file(path) != config["catalog_sha256"]:
        raise ValueError("catalog SHA-256 does not match evaluation config")
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
        (config["auxiliary_start"], config["window_end_exclusive"]),
    ).fetchall()
    connection.close()
    magnitudes = np.array([row[3] for row in rows], dtype=float)
    rounded = np.floor(magnitudes / config["delta_m"] + 0.5) * config["delta_m"]
    selected = rounded >= config["mc"]
    return DailyCatalog(
        times=np.array(
            [parse_time(row[0]) for row in rows], dtype="datetime64[ns]"
        )[selected],
        latitudes=np.array([row[1] for row in rows], dtype=float)[selected],
        longitudes=np.array([row[2] for row in rows], dtype=float)[selected],
        magnitudes=rounded[selected],
    )


def poisson_catalog(simulator, issue_time, rate, beta, rng):
    count = int(rng.poisson(rate * simulator.area * simulator.horizon_days))
    offsets = rng.uniform(0.0, simulator.horizon_days, count)
    latitudes, longitudes = simulator._uniform_polygon_points(count, rng)
    magnitudes = simulator.m_ref + rng.exponential(1.0 / beta, count)
    order = np.argsort(offsets, kind="stable")
    return SimulatedCatalog(
        times=simulator._add_days(issue_time, offsets[order]),
        latitudes=latitudes[order],
        longitudes=longitudes[order],
        magnitudes=magnitudes[order],
    )


def write_forecast(path: Path, catalogs, delta_m: float):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    counts = np.empty(len(catalogs), dtype=int)
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            ("lon", "lat", "magnitude", "time_string", "depth", "catalog_id", "event_id")
        )
        for catalog_id, catalog in enumerate(catalogs):
            counts[catalog_id] = catalog.event_count
            if catalog.event_count == 0:
                writer.writerow(("", "", "", "", "", catalog_id, ""))
                continue
            magnitudes = np.floor(catalog.magnitudes / delta_m + 0.5) * delta_m
            for event_index in range(catalog.event_count):
                writer.writerow(
                    (
                        format(float(catalog.longitudes[event_index]), ".12g"),
                        format(float(catalog.latitudes[event_index]), ".12g"),
                        format(float(magnitudes[event_index]), ".1f"),
                        np.datetime_as_string(catalog.times[event_index], unit="ms"),
                        "",
                        catalog_id,
                        f"{catalog_id}-{event_index}",
                    )
                )
    os.replace(temporary, path)
    return counts


def count_summary(counts: np.ndarray) -> dict:
    return {
        "catalogs": int(len(counts)),
        "empty_catalogs": int(np.count_nonzero(counts == 0)),
        "total_events": int(counts.sum()),
        "mean_events": float(counts.mean()),
        "variance_events": float(counts.var()),
        "minimum_events": int(counts.min()),
        "maximum_events": int(counts.max()),
        "quantiles": {
            str(q): float(np.quantile(counts, q))
            for q in (0.025, 0.5, 0.975)
        },
    }


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main():
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    n_simulations = args.simulations or config["n_simulations"]
    if n_simulations <= 0 or n_simulations > config["n_simulations"]:
        raise ValueError("simulations must be within the frozen configured count")
    catalog = load_catalog(config)
    issue_time = parse_time(config["issue_time"])
    target_end = int(
        np.searchsorted(
            catalog.times,
            parse_time(config["window_end_exclusive"]),
            side="left",
        )
    )
    history_end = int(np.searchsorted(catalog.times, issue_time, side="left"))
    observed_count = target_end - history_end
    if history_end != config["expected_observation"]["history_event_count"]:
        raise ValueError("history event count does not match frozen config")
    if observed_count != config["expected_observation"]["event_count"]:
        raise ValueError("observed event count does not match frozen config")

    parameters = ETASParameters.from_transformed(**config["parameters"])
    model_branching_ratio = branching_ratio(config["beta"], parameters)
    if not np.isclose(
        model_branching_ratio, config["expected_branching_ratio"], rtol=1e-15
    ):
        raise ValueError("branching ratio does not match frozen config")
    simulator = ETASContinuationSimulator(
        catalog=catalog,
        polygon_lat_lon=np.asarray(config["polygon_lat_lon"]),
        area=config["area_km2"],
        m_ref=config["m_ref"],
        beta=config["beta"],
        parameters=parameters,
        horizon_days=config["horizon_days"],
        earth_radius=config["earth_radius_km"],
        max_events_per_catalog=config["max_events_per_catalog"],
    )
    etas_catalogs = []
    poisson_catalogs = []
    for catalog_id in range(n_simulations):
        etas_rng = np.random.default_rng(
            np.random.SeedSequence([config["random_seed"], 0, catalog_id])
        )
        poisson_rng = np.random.default_rng(
            np.random.SeedSequence([config["random_seed"], 1, catalog_id])
        )
        etas_catalogs.append(simulator.simulate(issue_time, etas_rng))
        poisson_catalogs.append(
            poisson_catalog(
                simulator,
                issue_time,
                config["poisson"]["mu_per_km2_day"],
                config["beta"],
                poisson_rng,
            )
        )
        if (catalog_id + 1) % 1000 == 0:
            print(f"generated {catalog_id + 1}/{n_simulations}", flush=True)

    outputs = config["outputs"]
    etas_path = Path(outputs["etas_forecast"])
    poisson_path = Path(outputs["poisson_forecast"])
    etas_counts = write_forecast(etas_path, etas_catalogs, config["delta_m"])
    poisson_counts = write_forecast(poisson_path, poisson_catalogs, config["delta_m"])
    summary = {
        "schema_version": 1,
        "evaluation_id": config["evaluation_id"],
        "tool_version": TOOL_VERSION,
        "issue_time": config["issue_time"],
        "observed_events": observed_count,
        "history_events": history_end,
        "branching_ratio": model_branching_ratio,
        "simulations": n_simulations,
        "etas": count_summary(etas_counts),
        "poisson": count_summary(poisson_counts),
        "outputs": {
            "etas_sha256": sha256_file(etas_path),
            "poisson_sha256": sha256_file(poisson_path),
        },
    }
    atomic_json(Path(outputs["generation_summary"]), summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
