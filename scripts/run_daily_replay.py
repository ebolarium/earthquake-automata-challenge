"""Run the leakage-free daily ETAS replay from the clean local catalog."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import sqlite3
from pathlib import Path

import numpy as np
import scipy

from etas_challenge.daily_replay import (
    DAILY_REPLAY_SCHEMA_VERSION,
    DailyCatalog,
    DailyETASReplay,
    validate_daily_replay_manifest,
)
from etas_challenge.parameters import ETASParameters


TOOL_VERSION = "1.0.0"
ARRAY_NAMES = (
    "history_count",
    "target_count",
    "frozen_integrated",
    "frozen_log_sum",
    "frozen_ll",
    "sequential_integrated",
    "sequential_log_sum",
    "sequential_ll",
    "poisson_integrated",
    "poisson_ll",
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path, default=Path("configs/replay/comcat25-daily-v1.json")
    )
    parser.add_argument("--daily-scores", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--checkpoint-every", type=int, default=30)
    parser.add_argument("--max-days", type=int)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_time(value: str) -> np.datetime64:
    return np.datetime64(value.removesuffix("Z"), "ns")


def load_catalog(config: dict):
    path = Path(config["catalog_path"])
    catalog_hash = sha256_file(path)
    if catalog_hash != config["catalog_sha256"]:
        raise ValueError("clean catalog SHA-256 does not match replay config")
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True)
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
    times = np.array([parse_time(row[0]) for row in rows], dtype="datetime64[ns]")
    latitudes = np.array([row[1] for row in rows], dtype=float)
    longitudes = np.array([row[2] for row in rows], dtype=float)
    magnitudes = np.array([row[3] for row in rows], dtype=float)
    rounded = (
        np.floor(magnitudes / config["delta_m"] + 0.5) * config["delta_m"]
    )
    selected = rounded >= config["mc"]
    return (
        DailyCatalog(
            times=times[selected],
            latitudes=latitudes[selected],
            longitudes=longitudes[selected],
            magnitudes=rounded[selected],
        ),
        catalog_hash,
    )


def issue_times(config: dict) -> np.ndarray:
    start = parse_time(config["issue_start"])
    end = parse_time(config["issue_end_exclusive"])
    return np.arange(start, end, np.timedelta64(1, "D"), dtype="datetime64[ns]")


def checkpoint_arrays(day_count: int):
    arrays = {
        name: np.full(day_count, np.nan, dtype=float) for name in ARRAY_NAMES
    }
    return arrays


def save_checkpoint(path: Path, signature: str, completed: int, arrays: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez(handle, signature=signature, completed=completed, **arrays)
    os.replace(temporary, path)


def load_checkpoint(path: Path, signature: str, day_count: int):
    arrays = checkpoint_arrays(day_count)
    if not path.exists():
        return 0, arrays
    with np.load(path) as checkpoint:
        if str(checkpoint["signature"]) != signature:
            raise ValueError("checkpoint inputs do not match replay config")
        completed = int(checkpoint["completed"])
        for name in ARRAY_NAMES:
            if checkpoint[name].shape != (day_count,):
                raise ValueError("checkpoint day count does not match config")
            arrays[name][:] = checkpoint[name]
    return completed, arrays


def write_daily_scores(path: Path, issues: np.ndarray, arrays: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    columns = (
        "issue_time_utc",
        "window_end_utc",
        *ARRAY_NAMES,
        "sequential_information_gain",
    )
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for index, issue in enumerate(issues):
            end = issue + np.timedelta64(1, "D")
            values = [arrays[name][index] for name in ARRAY_NAMES]
            writer.writerow(
                [
                    _format_time(issue),
                    _format_time(end),
                    *[_format_number(value) for value in values],
                    _format_number(
                        arrays["sequential_ll"][index]
                        - arrays["poisson_ll"][index]
                    ),
                ]
            )
    os.replace(temporary, path)


def build_summary(config: dict, issues: np.ndarray, arrays: dict) -> dict:
    target_count = int(np.sum(arrays["target_count"]))
    frozen_expected = float(np.sum(arrays["frozen_integrated"]))
    sequential_expected = float(np.sum(arrays["sequential_integrated"]))
    poisson_expected = float(np.sum(arrays["poisson_integrated"]))
    frozen_ll = float(np.sum(arrays["frozen_ll"]))
    sequential_ll = float(np.sum(arrays["sequential_ll"]))
    poisson_ll = float(np.sum(arrays["poisson_ll"]))
    return {
        "schema_version": DAILY_REPLAY_SCHEMA_VERSION,
        "replay_id": config["replay_id"],
        "issue_start": _format_time(issues[0]),
        "issue_end_exclusive": _format_time(issues[-1] + np.timedelta64(1, "D")),
        "replay_days": len(issues),
        "active_days": int(np.count_nonzero(arrays["target_count"])),
        "zero_event_days": int(np.count_nonzero(arrays["target_count"] == 0)),
        "target_events": target_count,
        "frozen": _lane_summary(frozen_expected, frozen_ll, target_count, len(issues)),
        "sequential": _lane_summary(
            sequential_expected, sequential_ll, target_count, len(issues)
        ),
        "poisson": _lane_summary(
            poisson_expected, poisson_ll, target_count, len(issues)
        ),
        "sequential_vs_poisson": {
            "total_information_gain": sequential_ll - poisson_ll,
            "information_gain_per_event": (sequential_ll - poisson_ll)
            / target_count,
        },
    }


def _lane_summary(expected: float, log_likelihood: float, observed: int, days: int):
    return {
        "expected_events": expected,
        "observed_to_expected": observed / expected,
        "total_log_likelihood": log_likelihood,
        "mean_daily_log_likelihood": log_likelihood / days,
        "mean_log_likelihood_per_event": log_likelihood / observed,
    }


def build_manifest(
    config: dict,
    config_hash: str,
    catalog_hash: str,
    daily_path: Path,
    summary_path: Path,
    summary: dict,
) -> dict:
    manifest = {
        "schema_version": DAILY_REPLAY_SCHEMA_VERSION,
        "replay_id": config["replay_id"],
        "status": "completed",
        "tool": {
            "name": "scripts/run_daily_replay.py",
            "version": TOOL_VERSION,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "sqlite": sqlite3.sqlite_version,
        },
        "inputs": {
            "catalog_sha256": catalog_hash,
            "config_sha256": config_hash,
            "parameter_source": config["parameter_source"],
        },
        "protocol": {
            "issue_boundary": config["issue_time_history_boundary"],
            "target_window": config["target_window"],
            "equal_timestamp_policy": config["equal_timestamp_policy"],
            "horizon_days": config["horizon_days"],
            "mc": config["mc"],
        },
        "outputs": {
            "daily_scores_path": daily_path.as_posix(),
            "daily_scores_sha256": sha256_file(daily_path),
            "summary_path": summary_path.as_posix(),
            "summary_sha256": sha256_file(summary_path),
        },
        "results": {
            "replay_days": summary["replay_days"],
            "target_events": summary["target_events"],
            "sequential_information_gain_per_event": summary[
                "sequential_vs_poisson"
            ]["information_gain_per_event"],
        },
    }
    validate_daily_replay_manifest(manifest)
    return manifest


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _format_time(value: np.datetime64) -> str:
    return np.datetime_as_string(value, unit="s") + "Z"


def _format_number(value: float) -> str:
    return format(float(value), ".17g")


def main():
    args = parse_args()
    if args.checkpoint_every <= 0:
        raise ValueError("checkpoint-every must be positive")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    outputs = config["outputs"]
    daily_path = args.daily_scores or Path(outputs["daily_scores"])
    summary_path = args.summary or Path(outputs["summary"])
    manifest_path = args.manifest or Path(outputs["manifest"])
    checkpoint_path = args.checkpoint or daily_path.with_suffix(".checkpoint.npz")
    config_hash = sha256_file(args.config)
    catalog, catalog_hash = load_catalog(config)
    issues = issue_times(config)
    expected = config["expected_counts"]
    if len(issues) != expected["replay_days"]:
        raise ValueError("replay day count does not match frozen config")
    initial_history = int(
        np.searchsorted(catalog.times, parse_time(config["issue_start"]), side="left")
    )
    if initial_history != expected["initial_history_events"]:
        raise ValueError("initial history count does not match frozen config")
    replay_targets = len(catalog.times) - initial_history
    if replay_targets != expected["target_events"]:
        raise ValueError("target event count does not match frozen config")

    poisson = config["poisson"]
    calculated_mu = poisson["training_event_count"] / (
        config["area_km2"] * poisson["training_days"]
    )
    if not math.isclose(calculated_mu, poisson["mu_per_km2_day"], rel_tol=1e-15):
        raise ValueError("Poisson rate does not match frozen training contract")
    transformed = config["parameters"].copy()
    parameters = ETASParameters.from_transformed(**transformed)
    replay = DailyETASReplay(
        catalog=catalog,
        area=config["area_km2"],
        m_ref=config["m_ref"],
        parameters=parameters,
        poisson_mu=poisson["mu_per_km2_day"],
        horizon_days=config["horizon_days"],
        earth_radius=config["earth_radius_km"],
    )

    signature = f"{TOOL_VERSION}:{config_hash}:{catalog_hash}"
    completed, arrays = load_checkpoint(checkpoint_path, signature, len(issues))
    stop = len(issues)
    if args.max_days is not None:
        stop = min(stop, completed + args.max_days)
    for position in range(completed, stop):
        result = replay.evaluate_day(issues[position])
        arrays["history_count"][position] = result.history_event_count
        arrays["target_count"][position] = result.target_event_count
        arrays["frozen_integrated"][position] = result.frozen_integrated_rate
        arrays["frozen_log_sum"][position] = result.frozen_log_intensity_sum
        arrays["frozen_ll"][position] = result.frozen_log_likelihood
        arrays["sequential_integrated"][position] = result.sequential_integrated_rate
        arrays["sequential_log_sum"][position] = result.sequential_log_intensity_sum
        arrays["sequential_ll"][position] = result.sequential_log_likelihood
        arrays["poisson_integrated"][position] = result.poisson_integrated_rate
        arrays["poisson_ll"][position] = result.poisson_log_likelihood
        done = position + 1
        if done % args.checkpoint_every == 0 or done == stop:
            save_checkpoint(checkpoint_path, signature, done, arrays)
            print(f"completed {done}/{len(issues)}", flush=True)
    if stop < len(issues):
        print(f"partial replay saved to {checkpoint_path}")
        return

    if not all(np.all(np.isfinite(arrays[name])) for name in ARRAY_NAMES):
        raise ValueError("daily replay produced non-finite output")
    write_daily_scores(daily_path, issues, arrays)
    summary = build_summary(config, issues, arrays)
    atomic_json(summary_path, summary)
    manifest = build_manifest(
        config,
        config_hash,
        catalog_hash,
        daily_path,
        summary_path,
        summary,
    )
    atomic_json(manifest_path, manifest)
    checkpoint_path.unlink(missing_ok=True)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
