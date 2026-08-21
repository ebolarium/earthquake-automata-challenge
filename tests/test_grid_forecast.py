import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.grid_forecast import (
    RelmGridProjector,
    analytical_background_rates,
    spherical_cell_areas,
)
from etas_challenge.simulation import ForecastSimulation, SimulatedCatalog
from etas_challenge.training_matrix import GridDefinition


class GridForecastTests(unittest.TestCase):
    def setUp(self):
        self.grid = GridDefinition.from_payload(
            {
                "schema_version": 1,
                "grid_id": "test-grid",
                "coordinate_units_per_degree": 10,
                "cell_size_degrees": 0.1,
                "num_cells": 2,
                "origin_units": [[-1180, 340], [-1179, 340]],
            }
        )
        self.projector = RelmGridProjector.from_grid(self.grid)

    def test_fast_projector_matches_csep_boundary_convention(self):
        longitude = np.array([-118.0, -117.95, -117.9, -117.85, 0.0])
        latitude = np.full(5, 34.05)
        expected = self.grid.cell_indexes(longitude, latitude)
        actual = self.projector.cell_indexes(longitude, latitude)
        np.testing.assert_array_equal(actual, expected)
        np.testing.assert_array_equal(actual, [-1, 0, 0, 1, -1])

    def test_nonbackground_count_excludes_only_marked_roots(self):
        catalog = SimulatedCatalog(
            times=np.arange(4, dtype=float),
            latitudes=np.full(4, 34.05),
            longitudes=np.array([-117.95, -117.95, -117.85, -100.0]),
            magnitudes=np.full(4, 2.5),
        )
        simulation = ForecastSimulation(
            catalog=catalog,
            background_roots=np.array([True, False, False, False]),
        )
        counts, selected, inside = self.projector.nonbackground_counts(simulation)
        np.testing.assert_array_equal(counts, [1, 1])
        self.assertEqual(selected, 3)
        self.assertEqual(inside, 2)

    def test_spherical_areas_and_background_rates_are_positive(self):
        areas = spherical_cell_areas(self.grid, 6378.1)
        rates = analytical_background_rates(self.grid, 2e-6, 6378.1)
        self.assertTrue(np.all(areas > 0))
        np.testing.assert_allclose(rates, areas * 2e-6, rtol=1e-15)
        self.assertGreater(areas[0], 90.0)
        self.assertLess(areas[0], 110.0)


if __name__ == "__main__":
    unittest.main()
