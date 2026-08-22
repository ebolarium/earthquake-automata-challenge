import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.readiness_inputs import (
    attach_etas_background_probabilities,
    load_fit_catalog,
)
from etas_challenge.training_matrix import GridDefinition, sha256_file


class ReadinessInputTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.grid = GridDefinition.from_payload(
            {
                "schema_version": 1,
                "grid_id": "test",
                "coordinate_units_per_degree": 10,
                "cell_size_degrees": 0.1,
                "num_cells": 2,
                "origin_units": [[-1180, 340], [-1179, 340]],
            }
        )
        self.database = self.root / "catalog.sqlite"
        connection = sqlite3.connect(self.database)
        connection.execute(
            """CREATE TABLE catalog_events (
                event_id TEXT PRIMARY KEY, origin_time_utc TEXT,
                longitude REAL, latitude REAL, depth_km REAL, magnitude REAL)"""
        )
        connection.executemany(
            "INSERT INTO catalog_events VALUES (?,?,?,?,?,?)",
            [
                ("a", "2014-01-07T01:00:00Z", -117.95, 34.05, 5.0, 2.49),
                ("b", "2014-01-07T02:00:00Z", -117.85, 34.05, None, 3.0),
                ("outside", "2014-01-07T03:00:00Z", -120.0, 34.0, 1.0, 4.0),
            ],
        )
        connection.commit()
        connection.close()

    def tearDown(self):
        self.directory.cleanup()

    def test_catalog_rounds_filters_and_records_outside(self):
        catalog = load_fit_catalog(
            self.database,
            self.grid,
            start="2014-01-07T00:00:00Z",
            end_exclusive="2014-01-08T00:00:00Z",
            magnitude_rounding=0.1,
            magnitude_threshold=2.5,
        )
        np.testing.assert_array_equal(catalog.event_ids, ["a", "b"])
        np.testing.assert_allclose(catalog.magnitudes, [2.5, 3.0])
        np.testing.assert_array_equal(catalog.cell_indexes, [0, 1])
        self.assertEqual(catalog.selected_before_grid, 3)
        self.assertEqual(catalog.outside_grid, 1)
        self.assertTrue(np.isnan(catalog.depths_km[1]))

    def test_event_posterior_uses_same_day_cell_rate(self):
        catalog = load_fit_catalog(
            self.database,
            self.grid,
            start="2014-01-07T00:00:00Z",
            end_exclusive="2014-01-08T00:00:00Z",
            magnitude_rounding=0.1,
            magnitude_threshold=2.5,
        )
        shard = self.root / "etas-2014-01.npz"
        np.savez(
            shard,
            issue_days=np.array([16077], dtype=np.int32),
            etas_rates=np.array([[0.2, 0.4]], dtype=np.float32),
        )
        manifest = {
            "outputs": {
                "shards": [
                    {
                        "path": shard.name,
                        "sha256": sha256_file(shard),
                    }
                ]
            }
        }
        result = attach_etas_background_probabilities(
            catalog,
            grid=self.grid,
            etas_manifest=manifest,
            repository_root=self.root,
            mu_per_km2_day=1e-4,
            earth_radius_km=6371.0,
        )
        np.testing.assert_allclose(result.etas_rates, [0.2, 0.4])
        np.testing.assert_allclose(
            result.etas_background_probabilities,
            result.direct_background_rates / result.etas_rates,
        )


if __name__ == "__main__":
    unittest.main()
