import unittest

import numpy as np

from etas_challenge.fern_ch008_normalized import prevalidation_exposure_scale
from etas_challenge.renewal_quiescence import expected_reset_weight_gr
from etas_challenge.renewal_quiescence import magnitude_reset_weight


class FernCh008NormalizedTest(unittest.TestCase):
    def test_scale_targets_one_mean_training_exposure(self):
        background = np.array([0.01, 0.02, 0.03])
        scale = prevalidation_exposure_scale(background, 100.0)
        self.assertAlmostEqual(np.mean(scale * background * 100.0), 1.0)

    def test_scale_rejects_invalid_background(self):
        with self.assertRaises(ValueError):
            prevalidation_exposure_scale(np.array([0.0, 1.0]), 100.0)

    def test_state_replay_uses_forecast_then_same_day_observation(self):
        parent = {"full_reset_magnitude": 4.0, "magnitude_exponent": 0.5}
        ch008 = {"memory_half_life_days": 10.0}
        from etas_challenge.prospective_replay import replay_regional_ch008_state

        state = replay_regional_ch008_state(
            event_days=np.array([0]),
            event_cells=np.array([0]),
            event_magnitudes=np.array([3.0]),
            event_background_probabilities=np.array([0.5]),
            background_mass=np.array([0.2]),
            beta=2.0,
            magnitude_reference=2.5,
            issue_day_start=0,
            issue_day_end_exclusive=2,
            renewal_scale=2.0,
            parent_parameters=parent,
            ch008_parameters=ch008,
        )
        expected_mark = expected_reset_weight_gr(2.0, 2.5, 4.0, 0.5)
        observed_mark = 2.0 * 0.5 * magnitude_reset_weight(np.array([3.0]), 4.0, 0.5)[0]
        first_age = (2.0 * 0.2 * expected_mark) * np.exp(-observed_mark)
        np.testing.assert_allclose(state.age, first_age + 2.0 * 0.2 * expected_mark)
        retention = np.exp(-np.log(2.0) / 10.0)
        np.testing.assert_allclose(state.exposure, retention * 0.2 + 0.2)
        np.testing.assert_allclose(state.roots, retention * 0.5)


if __name__ == "__main__":
    unittest.main()
