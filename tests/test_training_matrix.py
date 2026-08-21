import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.training_matrix import (
    CONTINUOUS_FEATURES,
    COUNT_FEATURES,
    FeatureTimeline,
    GridDefinition,
    empirical_background_rate,
    validate_matrix_manifest,
    write_deterministic_npz,
)


COMMITTED_MANIFEST = ROOT / "data" / "manifests" / "ch001-matrix-v1.json"


class TrainingMatrixTests(unittest.TestCase):
    def setUp(self):
        self.grid = GridDefinition.from_payload(
            {
                "schema_version": 1,
                "grid_id": "test-grid",
                "coordinate_units_per_degree": 1,
                "cell_size_degrees": 1.0,
                "num_cells": 4,
                "origin_units": [[0, 0], [1, 0], [0, 1], [1, 1]],
            }
        )

    def test_grid_uses_pycsep_right_closed_boundary(self):
        indexes = self.grid.cell_indexes(
            np.array([1.0, 1.000001, 2.0]),
            np.array([1.0, 1.000001, 2.0]),
        )
        np.testing.assert_array_equal(indexes, [0, 3, 3])

    def test_target_day_event_enters_features_only_after_advance(self):
        daily = {
            9: np.array([1, 0, 0, 0], dtype=np.int32),
            10: np.array([0, 1, 0, 0], dtype=np.int32),
        }
        timeline = FeatureTimeline(
            grid=self.grid,
            daily_counts=daily,
            issue_day=10,
            windows=(3, 7, 30, 90),
            background_rate=np.full(4, 0.01),
            last_event_days=np.array([9, -1, -1, -1]),
            recency_cap_days=365,
            rate_floor_fraction=0.1,
        )
        before, continuous_before = timeline.snapshot()
        self.assertEqual(before[0, 0], 1)
        self.assertEqual(before[1, 0], 0)
        self.assertEqual(continuous_before[1, 4], 365)
        self.assertEqual(continuous_before[2, 2], 0.0)

        timeline.advance()
        after, continuous_after = timeline.snapshot()
        self.assertEqual(after[1, 0], 1)
        self.assertEqual(continuous_after[1, 4], 1)

    def test_neighbor_features_exclude_the_center_cell(self):
        values = np.array([2, 3, 5, 7])
        np.testing.assert_array_equal(self.grid.neighbor_sum(values), [15, 14, 12, 10])

    def test_empirical_background_smooths_empty_cells(self):
        rates = empirical_background_rate(
            np.array([10, 0, 0, 0]), exposure_days=100, prior_days=10
        )
        self.assertTrue(np.all(rates > 0))
        self.assertGreater(rates[0], rates[1])

    def test_manifest_rejects_feature_drift(self):
        manifest = self._manifest()
        validate_matrix_manifest(manifest)
        changed = copy.deepcopy(manifest)
        changed["features"]["count"][0] = "future_count"
        with self.assertRaisesRegex(ValueError, "feature contract changed"):
            validate_matrix_manifest(changed)

    def test_deterministic_npz_has_stable_hash(self):
        arrays = {
            "issue_days": np.array([1, 2], dtype=np.int32),
            "values": np.array([[1.5], [2.5]], dtype=np.float32),
        }
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.npz"
            second = Path(directory) / "second.npz"
            write_deterministic_npz(first, arrays)
            write_deterministic_npz(second, arrays)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_committed_matrix_manifest_is_valid(self):
        manifest = json.loads(COMMITTED_MANIFEST.read_text(encoding="utf-8"))
        validate_matrix_manifest(manifest)
        self.assertEqual(manifest["results"]["issue_days"], 5_844)

    @staticmethod
    def _manifest():
        return {
            "schema_version": 1,
            "status": "smoke",
            "inputs": {
                "config_sha256": "0" * 64,
                "challenge_contract_sha256": "1" * 64,
                "catalog_sha256": "2" * 64,
                "grid_sha256": "3" * 64,
            },
            "period": {},
            "features": {
                "count": list(COUNT_FEATURES),
                "continuous": list(CONTINUOUS_FEATURES),
            },
            "outputs": {
                "shards": [{"path": "x.npz", "sha256": "4" * 64}]
            },
            "results": {"issue_days": 1},
        }


if __name__ == "__main__":
    unittest.main()
