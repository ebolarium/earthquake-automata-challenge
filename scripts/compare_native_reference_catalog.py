"""Replay ComCat_25 natively and compare it with the frozen reference output."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
from pathlib import Path

import numpy as np
import scipy

from etas_challenge.parameters import ETASParameters
from etas_challenge.replay import CatalogReplay, ReplayCatalog


DEFAULT_ROOT = Path("artifacts/reference-comcat25/workspace/Experiments/ETAS")
DEFAULT_CATALOG = DEFAULT_ROOT / "output_data_ComCat_25/augmented_catalog.csv"
DEFAULT_PARAMETERS = DEFAULT_ROOT / "output_data_ComCat_25/parameters_0.json"
DEFAULT_OUTPUT = Path("artifacts/native-comcat25/alignment-report.json")
ALIGNMENT_LIMITS = {
    "point_intensity_max_absolute": 1e-12,
    "temporal_intensity_max_absolute": 1e-12,
    "strict_compensator_max_absolute": 1e-5,
    "aggregate_score_max_absolute": 1e-9,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--parameters", type=Path, default=DEFAULT_PARAMETERS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checkpoint-every", type=int, default=250)
    parser.add_argument("--max-targets", type=int)
    return parser.parse_args()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_inputs(catalog_path: Path, parameters_path: Path):
    metadata = json.loads(parameters_path.read_text(encoding="utf-8"))
    window_start = np.datetime64(metadata["timewindow_end"], "ns")
    testwindow_end = np.datetime64(metadata["testwindow_end"], "ns")

    times = []
    latitudes = []
    longitudes = []
    magnitudes = []
    target_indexes = []
    reference = {name: [] for name in ("compensator", "point", "temporal")}
    with catalog_path.open(encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            event_time = np.datetime64(row["time"], "ns")
            times.append(event_time)
            latitudes.append(float(row["latitude"]))
            longitudes.append(float(row["longitude"]))
            magnitudes.append(float(row["magnitude"]))
            if window_start <= event_time <= testwindow_end:
                target_indexes.append(index)
                reference["compensator"].append(float(row["int_lambd"]))
                reference["point"].append(float(row["lambd"]))
                reference["temporal"].append(float(row["lambd_star"]))

    transformed = metadata["final_parameters"].copy()
    transformed.pop("log10_iota", None)
    return {
        "catalog": ReplayCatalog(times, latitudes, longitudes, magnitudes),
        "target_indexes": np.asarray(target_indexes, dtype=int),
        "reference": {name: np.asarray(values) for name, values in reference.items()},
        "window_start": window_start,
        "area": float(metadata["area"]),
        "m_ref": float(metadata["m_ref"]),
        "earth_radius": float(metadata["earth_radius"]),
        "parameters": ETASParameters.from_transformed(**transformed),
    }


def save_checkpoint(path: Path, signature: str, completed: int, arrays: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez(handle, signature=signature, completed=completed, **arrays)
    os.replace(temporary, path)


def load_checkpoint(path: Path, signature: str, target_count: int):
    arrays = {
        "point": np.full(target_count, np.nan),
        "temporal": np.full(target_count, np.nan),
        "corrected": np.full(target_count, np.nan),
        "strict": np.full(target_count, np.nan),
    }
    if not path.exists():
        return 0, arrays
    with np.load(path) as checkpoint:
        if str(checkpoint["signature"]) != signature:
            raise ValueError("checkpoint inputs do not match current inputs")
        completed = int(checkpoint["completed"])
        for name in arrays:
            if checkpoint[name].shape != arrays[name].shape:
                raise ValueError("checkpoint target count does not match catalog")
            arrays[name][:] = checkpoint[name]
    return completed, arrays


def score(point: np.ndarray, temporal: np.ndarray, compensator: np.ndarray):
    ll = np.log(point) - compensator
    tll = np.log(temporal) - compensator
    return {
        "nll": float(-np.mean(ll)),
        "tll": float(np.mean(tll)),
        "sll": float(np.mean(ll - tll)),
    }


def deltas(actual: np.ndarray, expected: np.ndarray):
    difference = np.abs(actual - expected)
    return {
        "max_absolute": float(np.max(difference)),
        "mean_absolute": float(np.mean(difference)),
    }


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main():
    args = parse_args()
    if args.checkpoint_every <= 0:
        raise ValueError("checkpoint-every must be positive")
    inputs = read_inputs(args.catalog, args.parameters)
    catalog_hash = file_hash(args.catalog)
    parameters_hash = file_hash(args.parameters)
    signature = f"{catalog_hash}:{parameters_hash}"
    target_count = len(inputs["target_indexes"])
    checkpoint_path = args.output.with_suffix(".checkpoint.npz")
    completed, arrays = load_checkpoint(checkpoint_path, signature, target_count)
    replay = CatalogReplay(
        catalog=inputs["catalog"],
        target_indexes=inputs["target_indexes"],
        window_start=inputs["window_start"],
        area=inputs["area"],
        m_ref=inputs["m_ref"],
        parameters=inputs["parameters"],
        earth_radius=inputs["earth_radius"],
    )
    stop = target_count
    if args.max_targets is not None:
        stop = min(stop, completed + args.max_targets)

    for position in range(completed, stop):
        result = replay.evaluate_target(position)
        arrays["point"][position] = result.point_intensity
        arrays["temporal"][position] = result.temporal_intensity
        arrays["corrected"][position] = result.corrected_compensator
        arrays["strict"][position] = result.strict_reference_compensator
        done = position + 1
        if done % args.checkpoint_every == 0 or done == stop:
            save_checkpoint(checkpoint_path, signature, done, arrays)
            print(f"completed {done}/{target_count}", flush=True)

    if stop < target_count:
        print(f"partial replay saved to {checkpoint_path}")
        return

    reference = inputs["reference"]
    reference_scores = score(
        reference["point"], reference["temporal"], reference["compensator"]
    )
    strict_scores = score(arrays["point"], arrays["temporal"], arrays["strict"])
    corrected_scores = score(
        arrays["point"], arrays["temporal"], arrays["corrected"]
    )
    point_deltas = deltas(arrays["point"], reference["point"])
    temporal_deltas = deltas(arrays["temporal"], reference["temporal"])
    compensator_deltas = deltas(arrays["strict"], reference["compensator"])
    strict_score_deltas = {
        name: strict_scores[name] - reference_scores[name]
        for name in reference_scores
    }
    checks = {
        "point_intensity": point_deltas["max_absolute"]
        <= ALIGNMENT_LIMITS["point_intensity_max_absolute"],
        "temporal_intensity": temporal_deltas["max_absolute"]
        <= ALIGNMENT_LIMITS["temporal_intensity_max_absolute"],
        "strict_compensator": compensator_deltas["max_absolute"]
        <= ALIGNMENT_LIMITS["strict_compensator_max_absolute"],
        "aggregate_scores": max(abs(value) for value in strict_score_deltas.values())
        <= ALIGNMENT_LIMITS["aggregate_score_max_absolute"],
    }
    payload = {
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "catalog_sha256": catalog_hash,
        "parameters_sha256": parameters_hash,
        "event_count": len(inputs["catalog"].times),
        "target_count": target_count,
        "event_level_deltas": {
            "point_intensity": point_deltas,
            "temporal_intensity": temporal_deltas,
            "strict_reference_compensator": compensator_deltas,
        },
        "scores": {
            "stored_reference": reference_scores,
            "native_strict_reference": strict_scores,
            "native_corrected_first_interval": corrected_scores,
            "strict_minus_stored": strict_score_deltas,
            "corrected_minus_strict": {
                name: corrected_scores[name] - strict_scores[name]
                for name in strict_scores
            },
        },
        "first_interval": {
            "stored_reference_compensator": float(reference["compensator"][0]),
            "native_strict_compensator": float(arrays["strict"][0]),
            "native_corrected_compensator": float(arrays["corrected"][0]),
        },
        "acceptance": {
            "limits": ALIGNMENT_LIMITS,
            "checks": checks,
            "aligned": all(checks.values()),
        },
    }
    if not all(math.isfinite(value) for scores in payload["scores"].values() for value in scores.values()):
        raise ValueError("non-finite aggregate score")
    atomic_json(args.output, payload)
    checkpoint_path.unlink(missing_ok=True)
    print(json.dumps(payload, indent=2))
    if not payload["acceptance"]["aligned"]:
        raise SystemExit("native/reference alignment gate failed")


if __name__ == "__main__":
    main()
