import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from etas_challenge.fault_readiness import (
    advance_criticality_margin,
    compose_readiness_forecast,
    decompose_etas_rates,
    etas_background_probability,
    redistribute_background,
)


class FaultReadinessTests(unittest.TestCase):
    def setUp(self):
        self.background = np.array([0.1, 0.2, 0.3])
        self.triggered = np.array([0.0, 1.0, 0.4])
        self.etas = self.background + self.triggered

    def test_decomposition_removes_only_direct_background(self):
        components = decompose_etas_rates(self.etas, self.background)
        np.testing.assert_allclose(components.triggered, self.triggered)
        np.testing.assert_allclose(components.background, self.background)

    def test_zero_margin_reproduces_frozen_etas_exactly(self):
        forecast = compose_readiness_forecast(
            self.etas,
            self.background,
            np.zeros(3),
            sensitivity=2.0,
        )
        np.testing.assert_allclose(forecast, self.etas, rtol=1e-15)

    def test_readiness_preserves_background_and_total_mass(self):
        adjusted = redistribute_background(
            self.background,
            np.array([-2.0, 0.0, 3.0]),
            sensitivity=1.5,
        )
        forecast = compose_readiness_forecast(
            self.etas,
            self.background,
            np.array([-2.0, 0.0, 3.0]),
            sensitivity=1.5,
        )
        self.assertAlmostEqual(float(adjusted.sum()), float(self.background.sum()))
        self.assertAlmostEqual(float(forecast.sum()), float(self.etas.sum()))
        np.testing.assert_allclose(forecast - adjusted, self.triggered)
        self.assertGreater(adjusted[2] / self.background[2], 1.0)

    def test_large_margins_are_numerically_stable(self):
        adjusted = redistribute_background(
            self.background,
            np.array([-1000.0, 0.0, 1000.0]),
            sensitivity=10.0,
        )
        self.assertTrue(np.all(np.isfinite(adjusted)))
        self.assertAlmostEqual(float(adjusted.sum()), float(self.background.sum()))

    def test_state_transition_has_loading_release_and_transfer(self):
        state = advance_criticality_margin(
            np.array([1.0, 2.0]),
            np.array([0.1, 0.2]),
            np.array([0.4, 0.0]),
            np.array([0.0, 0.3]),
            elapsed_days=2.0,
        )
        np.testing.assert_allclose(state, [0.8, 2.7])

    def test_background_probability_targets_low_etas_events(self):
        probability = etas_background_probability(self.etas, self.background)
        np.testing.assert_allclose(probability, self.background / self.etas)
        self.assertEqual(probability[0], 1.0)
        self.assertLess(probability[1], probability[2])

    def test_invalid_component_order_is_rejected(self):
        with self.assertRaises(ValueError):
            decompose_etas_rates(np.array([0.1]), np.array([0.2]))


if __name__ == "__main__":
    unittest.main()
