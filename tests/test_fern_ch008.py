import unittest

import numpy as np

from etas_challenge.fern_ch008 import evaluate_frozen_ch008, regional_grid


class FernCh008Test(unittest.TestCase):
    @staticmethod
    def parameters():
        parent = {
            "full_reset_magnitude": 4.0, "magnitude_exponent": 0.5,
            "bpt_aperiodicity": 0.9, "graph_neighborhood_mix": 0.2,
        }
        challenger = {
            "prior_exposure": 0.5, "memory_half_life_days": 100.0,
            "frailty_neighborhood_mix": 0.0, "minimum_log_frailty": 0.0,
            "frailty_weight": 1.0, "renewal_weight": 1.0,
            "background_mixture_fraction": 0.2,
        }
        return parent, challenger

    def test_grid_transition_and_area_are_valid(self):
        grid = regional_grid((140.0, 141.0), (40.0, 41.0), 0.5)
        np.testing.assert_allclose(np.asarray(grid.transition.sum(axis=1)).ravel(), 1.0)
        self.assertTrue(np.all(grid.areas_km2 > 0))

    def test_same_day_events_receive_identical_pre_observation_forecast(self):
        grid = regional_grid((140.0, 141.0), (40.0, 41.0), 0.5)
        parent, challenger = self.parameters()
        result = evaluate_frozen_ch008(
            event_days=np.array([0, 0, 1]), event_cells=np.array([0, 0, 0]),
            event_magnitudes=np.array([5.0, 5.0, 5.0]), etas_rates=np.ones(3),
            etas_mu=0.01, beta=2.0, magnitude_reference=5.0, grid=grid,
            issue_day_start=0, issue_day_end_exclusive=2,
            parent_parameters=parent, ch008_parameters=challenger,
        )
        self.assertEqual(result.challenger_rates[0], result.challenger_rates[1])

    def test_zero_mixture_is_exact_etas(self):
        grid = regional_grid((140.0, 141.0), (40.0, 41.0), 0.5)
        parent, challenger = self.parameters()
        challenger["background_mixture_fraction"] = 0.0
        result = evaluate_frozen_ch008(
            event_days=np.array([0, 1]), event_cells=np.array([0, 1]),
            event_magnitudes=np.array([5.0, 5.0]), etas_rates=np.ones(2),
            etas_mu=0.01, beta=2.0, magnitude_reference=5.0, grid=grid,
            issue_day_start=0, issue_day_end_exclusive=2,
            parent_parameters=parent, ch008_parameters=challenger,
        )
        np.testing.assert_array_equal(result.event_gains, 0.0)


if __name__ == "__main__":
    unittest.main()
