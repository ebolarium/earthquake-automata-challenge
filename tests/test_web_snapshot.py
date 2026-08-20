import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.web_snapshot import (
    ForecastGridAccumulator,
    validate_web_manifest,
)


class WebSnapshotTests(unittest.TestCase):
    def test_grid_aggregates_counts_and_catalog_occupancy(self):
        accumulator = ForecastGridAccumulator(
            min_latitude=0.0,
            max_latitude=2.0,
            min_longitude=0.0,
            max_longitude=2.0,
            cell_degrees=1.0,
            thresholds=[2.5, 4.0],
            n_catalogs=2,
        )
        accumulator.add_catalog(
            latitudes=np.array([0.2, 0.3, 1.2]),
            longitudes=np.array([0.2, 0.3, 1.2]),
            magnitudes=np.array([2.5, 4.2, 3.0]),
        )
        accumulator.add_catalog(
            latitudes=np.array([0.4]),
            longitudes=np.array([0.4]),
            magnitudes=np.array([2.8]),
        )
        result = accumulator.result()
        first = next(
            cell for cell in result["cells"]
            if cell["latitude"] == 0.5 and cell["longitude"] == 0.5
        )
        self.assertEqual(first["expected"], [1.5, 0.5])
        self.assertEqual(first["probability"], [1.0, 0.5])
        self.assertEqual(result["summaries"][0]["mean_count"], 2.0)
        self.assertEqual(result["summaries"][1]["probability_at_least_one"], 0.5)

    def test_incomplete_grid_is_rejected(self):
        accumulator = ForecastGridAccumulator(
            min_latitude=0.0,
            max_latitude=1.0,
            min_longitude=0.0,
            max_longitude=1.0,
            cell_degrees=0.5,
            thresholds=[2.5],
            n_catalogs=2,
        )
        accumulator.add_catalog(np.array([]), np.array([]), np.array([]))
        with self.assertRaisesRegex(ValueError, "incomplete"):
            accumulator.result()

    def test_committed_web_manifest_is_valid(self):
        path = ROOT / "data" / "manifests" / "web-snapshot-v1.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        validate_web_manifest(manifest)
        self.assertEqual(manifest["n_simulations"], 10_000)
        self.assertEqual(manifest["history_events"], 56_374)


if __name__ == "__main__":
    unittest.main()
