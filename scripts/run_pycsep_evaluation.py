"""Run locked pyCSEP catalog consistency tests for native forecasts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import sqlite3
from pathlib import Path

import csep
import numpy as np
from csep.core import catalog_evaluations, regions
from csep.core.catalogs import CSEPCatalog
from csep.utils.time_utils import datetime_to_utc_epoch

from etas_challenge.evaluation import (
    PYCSEP_EVALUATION_SCHEMA_VERSION,
    validate_pycsep_manifest,
)


TOOL_VERSION = "1.0.0"


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/evaluation/comcat25-pycsep-day7-v1.json"),
    )
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, default=json_default) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def json_default(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def evaluation_region(config: dict):
    specification = config["pycsep"]
    spatial = regions.california_relm_region()
    if spatial.num_nodes != specification["expected_spatial_nodes"]:
        raise ValueError("pyCSEP RELM node count does not match frozen config")
    if not np.isclose(spatial.dh, specification["spatial_cell_degrees"]):
        raise ValueError("pyCSEP RELM cell size does not match frozen config")
    magnitudes = regions.magnitude_bins(
        specification["magnitude_min"],
        specification["magnitude_max"],
        specification["magnitude_bin_width"],
    )
    return regions.create_space_magnitude_region(spatial, magnitudes)


def observed_catalog(config: dict, region):
    path = Path(config["catalog_path"])
    if sha256_file(path) != config["catalog_sha256"]:
        raise ValueError("catalog SHA-256 does not match evaluation config")
    connection = sqlite3.connect(
        f"{path.resolve().as_uri()}?mode=ro&immutable=1", uri=True
    )
    rows = connection.execute(
        """
        SELECT event_id, origin_time_utc, latitude, longitude, depth_km, magnitude
        FROM catalog_events
        WHERE origin_time_utc >= ? AND origin_time_utc < ?
        ORDER BY origin_time_utc, event_id
        """,
        (config["issue_time"], config["window_end_exclusive"]),
    ).fetchall()
    connection.close()
    events = []
    for event_id, origin, latitude, longitude, depth, magnitude in rows:
        rounded = np.floor(magnitude / config["delta_m"] + 0.5) * config["delta_m"]
        if rounded < config["mc"]:
            continue
        origin_datetime = dt.datetime.fromisoformat(origin.replace("Z", "+00:00"))
        epoch = datetime_to_utc_epoch(origin_datetime)
        events.append((event_id, epoch, latitude, longitude, depth, rounded))
    catalog = CSEPCatalog(data=events, name="Observed ComCat_25", region=region)
    catalog = catalog.filter_spatial(region)
    if catalog.event_count != config["expected_observation"]["event_count"]:
        raise ValueError("spatially filtered observation count does not match config")
    return catalog


def load_forecast(path: Path, config: dict, region, model_name: str):
    start = dt.datetime.fromisoformat(config["issue_time"].replace("Z", "+00:00"))
    end = dt.datetime.fromisoformat(
        config["window_end_exclusive"].replace("Z", "+00:00")
    )
    forecast = csep.load_catalog_forecast(
        path,
        start_time=start,
        end_time=end,
        region=region,
        name=model_name,
        n_cat=config["n_simulations"],
        filter_spatial=True,
        apply_filters=True,
    )
    forecast.filters = [
        f"origin_time >= {forecast.start_epoch}",
        f"origin_time < {forecast.end_epoch}",
        f"magnitude >= {forecast.min_magnitude}",
    ]
    return forecast


def run_tests(forecast, observation):
    tests = {
        "number": catalog_evaluations.number_test,
        "spatial": catalog_evaluations.spatial_test,
        "pseudolikelihood": catalog_evaluations.pseudolikelihood_test,
        "magnitude": catalog_evaluations.magnitude_test,
    }
    results = {}
    for name, function in tests.items():
        result = function(forecast, observation, verbose=False)
        if result is None:
            raise RuntimeError(f"pyCSEP returned no {name} result")
        results[name] = result.to_dict()
    return results


def concise_results(results: dict, rejection_quantile: float):
    concise = {}
    for name, result in results.items():
        quantile = result.get("quantile")
        if isinstance(quantile, (list, tuple)):
            rejected = any(
                value is not None and value < rejection_quantile for value in quantile
            )
        else:
            rejected = quantile is not None and (
                quantile < rejection_quantile or quantile > 1.0 - rejection_quantile
            )
        concise[name] = {
            "status": result.get("status"),
            "observed_statistic": result.get("observed_statistic"),
            "quantile": quantile,
            "rejected_at_two_sided_5_percent": bool(rejected),
        }
    return concise


def main():
    args = parse_args()
    config_hash = sha256_file(args.config)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    outputs = config["outputs"]
    generation_path = Path(outputs["generation_summary"])
    generation = json.loads(generation_path.read_text(encoding="utf-8"))
    if generation["simulations"] != config["n_simulations"]:
        raise ValueError("forecast generation is not the frozen 10,000-catalog run")
    region = evaluation_region(config)
    observation = observed_catalog(config, region)
    paths = {
        "etas": Path(outputs["etas_forecast"]),
        "poisson": Path(outputs["poisson_forecast"]),
    }
    full_results = {}
    concise = {}
    rejection = config["pycsep"]["two_sided_rejection_quantile"]
    for model, path in paths.items():
        forecast = load_forecast(path, config, region, model.upper())
        full_results[model] = run_tests(forecast, observation)
        if forecast.n_cat != config["n_simulations"]:
            raise ValueError(f"{model} forecast lost empty catalogs")
        concise[model] = concise_results(full_results[model], rejection)

    summary = {
        "schema_version": PYCSEP_EVALUATION_SCHEMA_VERSION,
        "evaluation_id": config["evaluation_id"],
        "issue_time": config["issue_time"],
        "observed_events": observation.event_count,
        "n_simulations": config["n_simulations"],
        "region": {
            "name": config["pycsep"]["spatial_region"],
            "nodes": region.num_nodes,
            "magnitude_bins": len(region.magnitudes),
        },
        "results": full_results,
    }
    summary_path = Path(outputs["evaluation_summary"])
    atomic_json(summary_path, summary)
    manifest = {
        "schema_version": PYCSEP_EVALUATION_SCHEMA_VERSION,
        "evaluation_id": config["evaluation_id"],
        "status": "completed",
        "tool": {
            "generator": "scripts/generate_pycsep_forecasts.py",
            "evaluator": "scripts/run_pycsep_evaluation.py",
            "version": TOOL_VERSION,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pycsep": csep.__version__,
        },
        "inputs": {
            "config_sha256": config_hash,
            "catalog_sha256": config["catalog_sha256"],
            "parameter_source": config["parameter_source"],
        },
        "protocol": {
            "issue_time": config["issue_time"],
            "window_end_exclusive": config["window_end_exclusive"],
            "history_boundary": config["history_boundary"],
            "n_simulations": config["n_simulations"],
            "seed": config["random_seed"],
            "region": config["pycsep"]["spatial_region"],
            "region_nodes": region.num_nodes,
            "empty_catalogs_preserved": True,
        },
        "outputs": {
            "etas_forecast_sha256": sha256_file(paths["etas"]),
            "poisson_forecast_sha256": sha256_file(paths["poisson"]),
            "generation_summary_sha256": sha256_file(generation_path),
            "evaluation_summary_sha256": sha256_file(summary_path),
        },
        "results": concise,
        "claim_boundary": (
            "One documented active day is an integration and consistency gate, "
            "not a forecast superiority claim."
        ),
    }
    validate_pycsep_manifest(manifest)
    manifest_path = args.manifest or Path(outputs["manifest"])
    atomic_json(manifest_path, manifest)
    print(json.dumps(manifest, indent=2, default=json_default))


if __name__ == "__main__":
    main()
