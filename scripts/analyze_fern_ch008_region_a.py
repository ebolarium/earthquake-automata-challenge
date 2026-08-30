#!/usr/bin/env python3
"""Post-hoc mechanism diagnostics for the completed FERN-001 experiment."""

from __future__ import annotations

import json
from datetime import timedelta, timezone
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_fern_ch008 import CATALOG_MANIFEST  # noqa: E402
from evaluate_fern_ch008 import CONFIG, ETAS_ROOT, PROTOCOL  # noqa: E402
from evaluate_fern_ch008 import jst_day, read_catalog, timestamp  # noqa: E402
from etas_challenge.etas_native import event_rates  # noqa: E402
from etas_challenge.fern_ch008 import evaluate_frozen_ch008, regional_grid  # noqa: E402
from etas_challenge.training_matrix import sha256_file  # noqa: E402

OUTPUT = ROOT / "data/manifests/fern-ch008-region-a-diagnostic-v1.json"
SOURCE_RESULT = ROOT / "data/manifests/fern-ch008-zero-refit-transfer-v1.json"
JST = timezone(timedelta(hours=9))


def scalar_summary(values: np.ndarray) -> dict:
    array = np.asarray(values, dtype=float)
    return {
        "events": int(len(array)),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "positive_fraction": float(np.mean(array > 0)),
        "total": float(np.sum(array)),
    }


def probability_summary(values: np.ndarray) -> dict:
    array = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "q10": float(np.quantile(array, 0.1)),
        "q90": float(np.quantile(array, 0.9)),
    }


def selected_period(catalog: dict, bounds: list[str]) -> np.ndarray:
    start, end = (timestamp(value) for value in bounds)
    return np.asarray([(value >= start and value < end) for value in catalog["times"]])


def grouped_summary(values: np.ndarray, labels: np.ndarray) -> dict:
    return {
        str(label): scalar_summary(values[labels == label])
        for label in np.unique(labels)
        if np.any(labels == label)
    }


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    catalog_manifest = json.loads(CATALOG_MANIFEST.read_text(encoding="utf-8"))
    parent_path = ROOT / config["parent_model"]
    model_path = ROOT / config["source_model"]
    parent = json.loads(parent_path.read_text(encoding="utf-8"))["parameters"]
    frozen = json.loads(model_path.read_text(encoding="utf-8"))["parameters"]
    variants = {
        "full": frozen,
        "renewal_only": {**frozen, "frailty_weight": 0.0},
        "frailty_only": {**frozen, "renewal_weight": 0.0},
    }
    results = {}
    region_a_context = None
    for region in protocol["regions"]:
        name = region["name"]
        catalog_path = ROOT / catalog_manifest["outputs"][name]["target_path"]
        parameter_path = ETAS_ROOT / f"output_data_FERN_{name}" / "parameters_0.json"
        metadata = json.loads(parameter_path.read_text(encoding="utf-8"))
        catalog = read_catalog(catalog_path)
        rates = event_rates(
            catalog["time_days"], catalog["latitudes"], catalog["longitudes"],
            catalog["magnitudes"], magnitude_reference=metadata["m_ref"],
            parameters=metadata["final_parameters"],
        )
        grid = regional_grid(
            tuple(region["longitude"]), tuple(region["latitude"]),
            config["adaptation"]["spacing_degrees"],
        )
        cells = grid.cells(catalog["latitudes"], catalog["longitudes"])
        evaluations = {
            variant: evaluate_frozen_ch008(
                event_days=catalog["days"], event_cells=cells,
                event_magnitudes=catalog["magnitudes"], etas_rates=rates,
                etas_mu=10.0 ** metadata["final_parameters"]["log10_mu"],
                beta=metadata["beta"], magnitude_reference=metadata["m_ref"],
                grid=grid,
                issue_day_start=jst_day(timestamp(metadata["auxiliary_start"])),
                issue_day_end_exclusive=jst_day(
                    timestamp(config["evaluation"]["locked_test"][1])
                ) + 1,
                parent_parameters=parent, ch008_parameters=parameters,
            )
            for variant, parameters in variants.items()
        }
        periods = {}
        for period_name in ("development_validation", "locked_test"):
            selected = selected_period(catalog, config["evaluation"][period_name])
            full = evaluations["full"].event_gains[selected]
            renewal = evaluations["renewal_only"].event_gains[selected]
            frailty = evaluations["frailty_only"].event_gains[selected]
            background = evaluations["full"].background_probabilities[selected]
            periods[period_name] = {
                "full_igpe": scalar_summary(full),
                "renewal_only_igpe": scalar_summary(renewal),
                "frailty_only_igpe": scalar_summary(frailty),
                "frailty_increment_over_renewal_only": scalar_summary(full - renewal),
                "renewal_increment_over_frailty_only": scalar_summary(full - frailty),
                "etas_background_probability": probability_summary(background),
                "gain_background_probability_correlation": float(
                    np.corrcoef(full, background)[0, 1]
                ),
            }
        results[name] = {
            "etas_mu_per_km2_day": 10.0 ** metadata["final_parameters"]["log10_mu"],
            "etas_background_events_per_day": float(
                (10.0 ** metadata["final_parameters"]["log10_mu"])
                * np.sum(grid.areas_km2)
            ),
            "periods": periods,
        }
        if name == "A":
            region_a_context = (catalog, cells, grid, evaluations["full"])

    if region_a_context is None:
        raise ValueError("region A was not found")
    catalog, cells, grid, full_evaluation = region_a_context
    selected = selected_period(catalog, config["evaluation"]["locked_test"])
    gains = full_evaluation.event_gains[selected]
    selected_magnitudes = catalog["magnitudes"][selected]
    selected_cells = cells[selected]
    selected_times = catalog["times"][selected]
    selected_background = full_evaluation.background_probabilities[selected]
    years = np.asarray([value.astimezone(JST).year for value in catalog["times"][selected]])
    magnitude_labels = np.where(
        selected_magnitudes < 5.0, "4.5-4.9",
        np.where(selected_magnitudes < 6.0, "5.0-5.9", "6.0+"),
    )
    cell_rows = []
    for cell in np.unique(selected_cells):
        chosen = selected_cells == cell
        row, column = divmod(int(cell), grid.shape[1])
        cell_rows.append({
            "cell": int(cell),
            "events": int(np.sum(chosen)),
            "mean_igpe": float(np.mean(gains[chosen])),
            "total_gain": float(np.sum(gains[chosen])),
            "latitude": [36.0 + 0.5 * row, 36.0 + 0.5 * (row + 1)],
            "longitude": [141.0 + 0.5 * column, 141.0 + 0.5 * (column + 1)],
        })
    eligible = [row for row in cell_rows if row["events"] >= 3]
    ordered_positive_cells = sorted(
        eligible, key=lambda row: row["total_gain"], reverse=True
    )
    event_rows = [
        {
            "time_utc": selected_times[index].isoformat(),
            "magnitude": float(selected_magnitudes[index]),
            "cell": int(selected_cells[index]),
            "igpe": float(gains[index]),
            "etas_background_probability": float(selected_background[index]),
        }
        for index in range(len(gains))
    ]
    results["A"]["locked_test_diagnostics"] = {
        "by_year": grouped_summary(gains, years),
        "by_magnitude": grouped_summary(gains, magnitude_labels),
        "highest_total_gain_cells_min_3_events": ordered_positive_cells[:5],
        "lowest_total_gain_cells_min_3_events": sorted(
            eligible, key=lambda row: row["total_gain"]
        )[:5],
        "highest_gain_events": sorted(
            event_rows, key=lambda row: row["igpe"], reverse=True
        )[:10],
        "lowest_gain_events": sorted(event_rows, key=lambda row: row["igpe"])[:10],
        "exclude_highest_gain_cell": scalar_summary(
            gains[selected_cells != ordered_positive_cells[0]["cell"]]
        ),
        "exclude_top_three_gain_cells": scalar_summary(
            gains[
                ~np.isin(
                    selected_cells,
                    [row["cell"] for row in ordered_positive_cells[:3]],
                )
            ]
        ),
    }
    payload = {
        "schema_version": 1,
        "analysis_id": "fern-ch008-region-a-posthoc-diagnostic-v1",
        "status": "completed",
        "analysis_role": "posthoc_explanation_not_model_selection",
        "source_result_sha256": sha256_file(SOURCE_RESULT),
        "source_model_sha256": sha256_file(model_path),
        "parent_model_sha256": sha256_file(parent_path),
        "analysis_script_sha256": sha256_file(Path(__file__)),
        "results": results,
        "claim_boundary": "Outcome-informed diagnostic only. Ablations and strata explain FERN-001 but cannot promote, tune, or independently validate a model.",
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
