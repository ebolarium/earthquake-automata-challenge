"""Masked CSEP geometry aggregated into a coarser latent-state grid."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.sparse import csr_matrix


def spherical_cell_area_km2(
    longitude_min: np.ndarray,
    latitude_min: np.ndarray,
    spacing_degrees: float,
) -> np.ndarray:
    radius = 6378.1
    longitude_width = math.radians(spacing_degrees)
    lat0 = np.radians(np.asarray(latitude_min, dtype=float))
    lat1 = np.radians(np.asarray(latitude_min, dtype=float) + spacing_degrees)
    return radius * radius * longitude_width * (np.sin(lat1) - np.sin(lat0))


@dataclass(frozen=True, slots=True)
class MaskedGrid:
    fine_origins: np.ndarray
    fine_spacing_degrees: float
    latent_keys: np.ndarray
    fine_to_latent: np.ndarray
    areas_km2: np.ndarray
    transition: csr_matrix

    def contains(self, latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
        return self.cells(latitudes, longitudes) >= 0

    def cells(self, latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
        lats = np.asarray(latitudes, dtype=float)
        lons = np.asarray(longitudes, dtype=float)
        if lats.shape != lons.shape:
            raise ValueError("masked-grid coordinates disagree")
        scale = round(1.0 / self.fine_spacing_degrees)
        fine_keys = {
            (round(float(lon) * scale), round(float(lat) * scale)): index
            for index, (lon, lat) in enumerate(self.fine_origins)
        }
        lon_origins = np.floor((lons + 1e-9) * scale) / scale
        lat_origins = np.floor((lats + 1e-9) * scale) / scale
        result = np.full(lats.shape, -1, dtype=np.int32)
        for index, (lon, lat) in enumerate(zip(lon_origins.flat, lat_origins.flat)):
            fine = fine_keys.get((round(float(lon) * scale), round(float(lat) * scale)))
            if fine is not None:
                result.flat[index] = self.fine_to_latent[fine]
        return result


def masked_grid(
    fine_origins: np.ndarray,
    fine_spacing_degrees: float,
    latent_spacing_degrees: float,
) -> MaskedGrid:
    origins = np.asarray(fine_origins, dtype=float)
    ratio = latent_spacing_degrees / fine_spacing_degrees
    if (
        origins.ndim != 2
        or origins.shape[1] != 2
        or not np.all(np.isfinite(origins))
        or fine_spacing_degrees <= 0
        or latent_spacing_degrees < fine_spacing_degrees
        or not math.isclose(ratio, round(ratio))
    ):
        raise ValueError("invalid masked-grid specification")
    latent_lon = np.floor((origins[:, 0] + 1e-9) / latent_spacing_degrees).astype(int)
    latent_lat = np.floor((origins[:, 1] + 1e-9) / latent_spacing_degrees).astype(int)
    keys, inverse = np.unique(
        np.column_stack((latent_lon, latent_lat)), axis=0, return_inverse=True
    )
    fine_areas = spherical_cell_area_km2(
        origins[:, 0], origins[:, 1], fine_spacing_degrees
    )
    areas = np.zeros(len(keys), dtype=float)
    np.add.at(areas, inverse, fine_areas)
    lookup = {tuple(key): index for index, key in enumerate(keys)}
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    for index, (column_key, row_key) in enumerate(keys):
        neighbors = [
            lookup[(other_column, other_row)]
            for other_row in range(row_key - 1, row_key + 2)
            for other_column in range(column_key - 1, column_key + 2)
            if (other_column, other_row) != (column_key, row_key)
            and (other_column, other_row) in lookup
        ]
        if not neighbors:
            neighbors = [index]
        rows.extend([index] * len(neighbors))
        columns.extend(neighbors)
        values.extend([1.0 / len(neighbors)] * len(neighbors))
    transition = csr_matrix(
        (values, (rows, columns)), shape=(len(keys), len(keys))
    )
    return MaskedGrid(
        origins,
        fine_spacing_degrees,
        keys,
        inverse.astype(np.int32),
        areas,
        transition,
    )
