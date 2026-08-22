import copy
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.challenger import (
    TRANSFORMED_FEATURES,
    FeatureScaler,
    conditional_gain_and_gradient,
    event_log_ratios,
    fit_scaler_from_moments,
    raw_features,
    stationary_block_bootstrap_igpe,
)


class ChallengerTests(unittest.TestCase):
    def test_feature_contract_and_transform(self):
        counts = np.arange(16, dtype=np.uint16).reshape(2, 8)
        continuous = np.array(
            [
                [1.0, 2.0, 3.0, 4.0, 9.0, 24.0, 1e-4],
                [-1.0, -2.0, -3.0, -4.0, 0.0, 3.0, 2e-4],
            ]
        )
        transformed = raw_features(counts, continuous)
        self.assertEqual(transformed.shape, (2, len(TRANSFORMED_FEATURES)))
        np.testing.assert_allclose(transformed[:, :8], np.log1p(counts))
        np.testing.assert_allclose(transformed[:, 12:14], np.log1p(continuous[:, 4:6]))
        np.testing.assert_allclose(transformed[:, 14], np.log(continuous[:, 6]))

    def test_zero_residual_exactly_matches_etas(self):
        design = np.arange(24, dtype=float).reshape(2, 3, 4) / 10.0
        rates = np.array([[1.0, 2.0, 3.0], [3.0, 2.0, 1.0]])
        targets = np.array([[0, 1, 0], [2, 0, 0]])
        gain, gradient, count, daily = conditional_gain_and_gradient(
            np.zeros(4), design, rates, targets
        )
        self.assertAlmostEqual(gain, 0.0, places=14)
        np.testing.assert_allclose(daily, 0.0, atol=1e-14)
        self.assertEqual(count, 3)
        self.assertEqual(gradient.shape, (4,))
        np.testing.assert_allclose(
            event_log_ratios(np.zeros(4), design, rates), 0.0, atol=1e-14
        )

    def test_analytic_gradient_matches_finite_difference(self):
        rng = np.random.default_rng(4)
        design = rng.normal(size=(3, 5, 4))
        rates = rng.uniform(0.1, 2.0, size=(3, 5))
        targets = rng.poisson(0.3, size=(3, 5))
        weights = rng.normal(scale=0.2, size=4)
        gain, gradient, _, _ = conditional_gain_and_gradient(
            weights, design, rates, targets
        )
        numerical = np.empty(4)
        epsilon = 1e-6
        for index in range(4):
            shifted = weights.copy()
            shifted[index] += epsilon
            other, _, _, _ = conditional_gain_and_gradient(
                shifted, design, rates, targets
            )
            numerical[index] = (other - gain) / epsilon
        np.testing.assert_allclose(gradient, numerical, rtol=2e-5, atol=2e-5)

    def test_scaler_clips_and_rejects_wrong_contract(self):
        scaler = fit_scaler_from_moments(
            2,
            np.zeros(len(TRANSFORMED_FEATURES)),
            np.full(len(TRANSFORMED_FEATURES), 2.0),
            3.0,
        )
        values = np.full((1, len(TRANSFORMED_FEATURES)), 100.0)
        self.assertTrue(np.all(scaler.transform(values) == 3.0))
        payload = scaler.to_payload()
        FeatureScaler.from_payload(payload)
        mutated = copy.deepcopy(payload)
        mutated["feature_names"][0] = "changed"
        with self.assertRaisesRegex(ValueError, "contract changed"):
            FeatureScaler.from_payload(mutated)

    def test_stationary_bootstrap_is_deterministic_and_preserves_ratio(self):
        count = np.array([1, 2, 1, 2])
        gain = 2.0 * count
        first = stationary_block_bootstrap_igpe(
            gain,
            count,
            replicates=500,
            mean_block_days=2,
            seed=12,
        )
        second = stationary_block_bootstrap_igpe(
            gain,
            count,
            replicates=500,
            mean_block_days=2,
            seed=12,
        )
        self.assertEqual(first, second)
        self.assertAlmostEqual(first["lower"], 2.0)
        self.assertAlmostEqual(first["upper"], 2.0)


if __name__ == "__main__":
    unittest.main()
