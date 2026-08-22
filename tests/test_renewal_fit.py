import unittest

import numpy as np

from etas_challenge.readiness_fit import SparseGeometry
from etas_challenge.renewal_fit import RenewalFitEvaluator


class RenewalFitTest(unittest.TestCase):
    @staticmethod
    def evaluator():
        grid_geometry = SparseGeometry(
            section_indexes=np.array([[0], [1]]),
            probabilities=np.ones((2, 1)),
        )
        event_geometry = SparseGeometry(
            section_indexes=np.array([[0], [0]]),
            probabilities=np.ones((2, 1)),
        )
        return RenewalFitEvaluator(
            issue_days=np.array([0, 1]),
            scoring_start_day=0,
            event_days=np.array([0, 1]),
            event_cells=np.array([0, 0]),
            event_magnitudes=np.array([2.5, 2.5]),
            event_etas_rates=np.array([1.0, 1.0]),
            event_background_probabilities=np.array([0.0, 0.0]),
            event_geometries=[event_geometry],
            expected_section_background=np.array([[10.0, 0.0]]),
            adjacency=np.array([[0.0, 1.0], [1.0, 0.0]]),
            active_sections=np.ones((1, 2), bool),
            grid_geometries=[grid_geometry],
            background_grid=np.array([0.5, 0.5]),
            beta=2.1471442086213064,
            magnitude_reference=2.5,
            graph_neighbors=1,
            maximum_log_tilt=4.0,
        )

    def test_zero_mixture_is_exact_etas_control(self):
        result = self.evaluator().evaluate(
            np.array([4.0, 0.5, 0.5, 0.0, 0.0, 0.0, 1.0])
        )
        np.testing.assert_array_equal(result.challenger_event_rates, [1.0, 1.0])
        np.testing.assert_array_equal(result.event_gains, 0.0)

    def test_day_age_affects_only_next_issue_forecast(self):
        result = self.evaluator().evaluate(
            np.array([4.0, 0.5, 0.5, 0.0, 0.0, 0.1, 1.0])
        )
        self.assertEqual(result.event_gains[0], 0.0)
        self.assertGreater(result.event_gains[1], 0.0)
        self.assertEqual(result.active_issue_days, 1)


if __name__ == "__main__":
    unittest.main()
