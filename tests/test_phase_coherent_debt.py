import unittest

import numpy as np

from etas_challenge.phase_coherent_debt import FrailtyTrendState
from etas_challenge.phase_coherent_debt import phase_coherent_hazard_debt
from etas_challenge.phase_coherent_debt import positive_frailty_acceleration
from etas_challenge.phase_coherent_debt import update_frailty_trend


class PhaseCoherentDebtTest(unittest.TestCase):
    def test_fast_frailty_change_precedes_slow_mean(self):
        state = FrailtyTrendState(np.zeros(2), np.zeros(2))
        updated = update_frailty_trend(state, np.array([1.0, 0.0]), 2.0, 20.0)
        acceleration = positive_frailty_acceleration(updated)
        self.assertGreater(acceleration[0], 0.0)
        self.assertEqual(acceleration[1], 0.0)

    def test_constant_frailty_converges_to_zero_acceleration(self):
        state = FrailtyTrendState(np.zeros(1), np.zeros(1))
        for _ in range(500):
            state = update_frailty_trend(state, np.ones(1), 5.0, 40.0)
        self.assertLess(positive_frailty_acceleration(state)[0], 0.0002)

    def test_feature_requires_all_three_local_signals(self):
        transition = np.array([[0.0, 1.0], [1.0, 0.0]])
        for missing in range(3):
            signals = [np.ones(2), np.ones(2), np.ones(2)]
            signals[missing] = np.zeros(2)
            score = phase_coherent_hazard_debt(*signals, transition, 1.0)
            np.testing.assert_array_equal(score, 0.0)

    def test_full_coherence_rejects_isolated_local_debt(self):
        transition = np.array([[0.0, 1.0], [1.0, 0.0]])
        isolated = phase_coherent_hazard_debt(
            np.array([1.0, 0.0]),
            np.array([1.0, 0.0]),
            np.array([1.0, 0.0]),
            transition,
            1.0,
        )
        coherent = phase_coherent_hazard_debt(
            np.ones(2), np.ones(2), np.ones(2), transition, 1.0
        )
        np.testing.assert_array_equal(isolated, 0.0)
        np.testing.assert_allclose(coherent, 1.0)

    def test_feature_is_symmetric_in_its_three_mechanisms(self):
        transition = np.eye(2)
        first = phase_coherent_hazard_debt(
            np.array([1.0, 8.0]),
            np.array([2.0, 4.0]),
            np.array([4.0, 2.0]),
            transition,
            0.5,
        )
        reordered = phase_coherent_hazard_debt(
            np.array([4.0, 2.0]),
            np.array([1.0, 8.0]),
            np.array([2.0, 4.0]),
            transition,
            0.5,
        )
        np.testing.assert_allclose(first, reordered)

    def test_invalid_noncausal_time_scales_are_rejected(self):
        state = FrailtyTrendState(np.zeros(1), np.zeros(1))
        with self.assertRaises(ValueError):
            update_frailty_trend(state, np.zeros(1), 20.0, 10.0)


if __name__ == "__main__":
    unittest.main()
