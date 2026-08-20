"""Aggregation and contracts for independent ETAS web snapshots."""

from __future__ import annotations

import re

import numpy as np


WEB_SNAPSHOT_SCHEMA_VERSION = 1


class ForecastGridAccumulator:
    def __init__(
        self,
        *,
        min_latitude: float,
        max_latitude: float,
        min_longitude: float,
        max_longitude: float,
        cell_degrees: float,
        thresholds: list[float],
        n_catalogs: int,
    ) -> None:
        if max_latitude <= min_latitude or max_longitude <= min_longitude:
            raise ValueError("grid maximums must exceed minimums")
        if cell_degrees <= 0 or n_catalogs <= 0:
            raise ValueError("cell size and catalog count must be positive")
        threshold_array = np.asarray(thresholds, dtype=float)
        if not len(threshold_array) or np.any(np.diff(threshold_array) <= 0):
            raise ValueError("thresholds must be non-empty and strictly increasing")
        self.min_latitude = float(min_latitude)
        self.max_latitude = float(max_latitude)
        self.min_longitude = float(min_longitude)
        self.max_longitude = float(max_longitude)
        self.cell_degrees = float(cell_degrees)
        self.thresholds = threshold_array
        self.n_catalogs = int(n_catalogs)
        self.latitude_cells = int(
            np.ceil((max_latitude - min_latitude) / cell_degrees)
        )
        self.longitude_cells = int(
            np.ceil((max_longitude - min_longitude) / cell_degrees)
        )
        shape = (len(threshold_array), self.latitude_cells * self.longitude_cells)
        self.event_totals = np.zeros(shape, dtype=np.int64)
        self.occupied_catalogs = np.zeros(shape, dtype=np.int64)
        self.catalog_counts = np.zeros((len(threshold_array), n_catalogs), dtype=np.int64)
        self.completed = 0

    def add_catalog(
        self, latitudes: np.ndarray, longitudes: np.ndarray, magnitudes: np.ndarray
    ) -> None:
        if self.completed >= self.n_catalogs:
            raise ValueError("more catalogs supplied than configured")
        latitudes = np.asarray(latitudes, dtype=float)
        longitudes = np.asarray(longitudes, dtype=float)
        magnitudes = np.asarray(magnitudes, dtype=float)
        if len({array.shape for array in (latitudes, longitudes, magnitudes)}) != 1:
            raise ValueError("catalog arrays must have identical shapes")
        lat_index = np.floor(
            (latitudes - self.min_latitude) / self.cell_degrees
        ).astype(int)
        lon_index = np.floor(
            (longitudes - self.min_longitude) / self.cell_degrees
        ).astype(int)
        inside = (
            (lat_index >= 0)
            & (lat_index < self.latitude_cells)
            & (lon_index >= 0)
            & (lon_index < self.longitude_cells)
        )
        flat_indexes = lat_index * self.longitude_cells + lon_index
        for threshold_index, threshold in enumerate(self.thresholds):
            selected = inside & (magnitudes >= threshold)
            indexes = flat_indexes[selected]
            self.catalog_counts[threshold_index, self.completed] = len(indexes)
            if len(indexes):
                self.event_totals[threshold_index] += np.bincount(
                    indexes, minlength=self.event_totals.shape[1]
                )
                self.occupied_catalogs[threshold_index, np.unique(indexes)] += 1
        self.completed += 1

    def result(self) -> dict:
        if self.completed != self.n_catalogs:
            raise ValueError("grid aggregation is incomplete")
        active = np.any(self.event_totals > 0, axis=0)
        cells = []
        for flat_index in np.flatnonzero(active):
            lat_index, lon_index = divmod(
                int(flat_index), self.longitude_cells
            )
            cells.append(
                {
                    "latitude": self.min_latitude
                    + (lat_index + 0.5) * self.cell_degrees,
                    "longitude": self.min_longitude
                    + (lon_index + 0.5) * self.cell_degrees,
                    "expected": [
                        float(value / self.n_catalogs)
                        for value in self.event_totals[:, flat_index]
                    ],
                    "probability": [
                        float(value / self.n_catalogs)
                        for value in self.occupied_catalogs[:, flat_index]
                    ],
                }
            )
        summaries = []
        for index, threshold in enumerate(self.thresholds):
            counts = self.catalog_counts[index]
            summaries.append(
                {
                    "threshold": float(threshold),
                    "mean_count": float(counts.mean()),
                    "probability_at_least_one": float(np.mean(counts > 0)),
                    "count_quantiles": {
                        "2.5": float(np.quantile(counts, 0.025)),
                        "50": float(np.quantile(counts, 0.5)),
                        "97.5": float(np.quantile(counts, 0.975)),
                    },
                }
            )
        return {
            "definition": {
                "min_latitude": self.min_latitude,
                "max_latitude": self.max_latitude,
                "min_longitude": self.min_longitude,
                "max_longitude": self.max_longitude,
                "cell_degrees": self.cell_degrees,
                "latitude_cells": self.latitude_cells,
                "longitude_cells": self.longitude_cells,
            },
            "thresholds": self.thresholds.tolist(),
            "cells": cells,
            "summaries": summaries,
        }


def validate_web_snapshot(snapshot: dict) -> None:
    if snapshot.get("schema_version") != WEB_SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("unsupported web snapshot schema_version")
    for section in ("forecast", "model", "catalog", "grid", "evaluation"):
        if not isinstance(snapshot.get(section), dict):
            raise ValueError(f"web snapshot missing {section}")
    if snapshot["forecast"].get("n_simulations", 0) <= 0:
        raise ValueError("web snapshot must contain simulations")
    thresholds = snapshot["grid"].get("thresholds")
    summaries = snapshot["grid"].get("summaries")
    if not thresholds or len(thresholds) != len(summaries or []):
        raise ValueError("web snapshot threshold summaries are incomplete")
    if snapshot["catalog"].get("history_events", 0) <= 0:
        raise ValueError("web snapshot must contain issue-time history")


def validate_web_manifest(manifest: dict) -> None:
    if manifest.get("schema_version") != WEB_SNAPSHOT_SCHEMA_VERSION:
        raise ValueError("unsupported web manifest schema_version")
    if manifest.get("status") != "completed":
        raise ValueError("web manifest must have completed status")
    for key in ("config_sha256", "catalog_sha256", "snapshot_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", manifest.get(key, "")):
            raise ValueError(f"invalid SHA-256 at {key}")
    if manifest.get("n_simulations", 0) <= 0:
        raise ValueError("web manifest must contain simulations")
