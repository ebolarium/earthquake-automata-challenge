import unittest

import numpy as np

from etas_challenge.prospective_scoring import score_california_grid
from etas_challenge.prospective_scoring import score_rate_pairs
from etas_challenge.prospective_scoring import score_regional_events


PARAMETERS = {
    "log10_mu": -2.0,
    "log10_k0": -3.0,
    "a": 1.0,
    "log10_c": -2.0,
    "omega": -0.05,
    "log10_tau": 2.0,
    "log10_d": 0.0,
    "gamma": 0.5,
    "rho": 1.0,
}


class ProspectiveScoringTest(unittest.TestCase):
    def test_rate_pair_summary_uses_event_log_ratio(self):
        score = score_rate_pairs(np.array([1.0, 2.0]), np.array([2.0, 1.0]))
        np.testing.assert_allclose(score.event_gains, [np.log(2.0), np.log(0.5)])
        summary = score.summary()
        self.assertEqual(summary["event_count"], 2)
        self.assertAlmostEqual(summary["total_log_likelihood_gain"], 0.0)
        self.assertEqual(summary["paired_compensator_gain"], 0.0)

    def test_empty_day_has_null_event_mean(self):
        summary = score_rate_pairs(np.array([]), np.array([])).summary()
        self.assertEqual(summary["event_count"], 0)
        self.assertEqual(summary["total_log_likelihood_gain"], 0.0)
        self.assertIsNone(summary["mean_igpe"])

    def test_california_uses_published_cell_rates(self):
        score = score_california_grid(
            np.array([1, 0]),
            np.array([0.4, 0.6]),
            np.array([0.5, 0.5]),
        )
        np.testing.assert_allclose(
            score.event_gains, [np.log(0.5 / 0.6), np.log(0.5 / 0.4)]
        )
        with self.assertRaisesRegex(ValueError, "grid contract"):
            score_california_grid(
                np.array([0]), np.array([0.4, 0.6]), np.array([0.7, 0.5])
            )

    def test_regional_score_changes_only_direct_background(self):
        day = 86_400 * 1_000_000_000
        score = score_regional_events(
            history_origin_time_ns=np.array([0], dtype=np.int64),
            history_latitudes=np.array([0.0]),
            history_longitudes=np.array([0.0]),
            history_magnitudes=np.array([3.0]),
            event_origin_time_ns=np.array([2 * day, 2 * day + 1_000_000_000]),
            event_latitudes=np.array([1.0, 1.1]),
            event_longitudes=np.array([1.0, 1.1]),
            event_magnitudes=np.array([3.0, 3.1]),
            event_cells=np.array([0, 1]),
            cell_areas_km2=np.array([10.0, 20.0]),
            baseline_background_mass=np.array([0.1, 0.2]),
            challenger_background_mass=np.array([0.15, 0.15]),
            magnitude_reference=2.5,
            etas_parameters=PARAMETERS,
        )
        self.assertGreater(score.event_gains[0], 0)
        self.assertLess(score.event_gains[1], 0)
        self.assertTrue(np.all(score.baseline_rates > 0))


if __name__ == "__main__":
    unittest.main()
