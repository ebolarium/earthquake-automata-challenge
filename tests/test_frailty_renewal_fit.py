import unittest

import numpy as np

from etas_challenge.frailty_renewal_fit import FrailtyRenewalFitEvaluator
from etas_challenge.renewal_fit import RenewalFitEvaluator
from etas_challenge.readiness_fit import SparseGeometry


class FrailtyRenewalFitTest(unittest.TestCase):
    @staticmethod
    def evaluator():
        geometry = SparseGeometry(
            section_indexes=np.array([[0], [1], [0]]),
            probabilities=np.ones((3, 1)),
        )
        grid_geometry = SparseGeometry(
            section_indexes=np.array([[0], [1]]), probabilities=np.ones((2, 1))
        )
        parent = RenewalFitEvaluator(
            issue_days=np.array([0, 1, 2]),
            scoring_start_day=0,
            event_days=np.array([0, 1, 2]),
            event_cells=np.array([0, 0, 0]),
            event_magnitudes=np.array([2.5, 2.5, 2.5]),
            event_etas_rates=np.ones(3),
            event_background_probabilities=np.array([1.0, 0.0, 0.0]),
            event_geometries=[geometry],
            expected_section_background=np.array([[0.1, 0.1]]),
            adjacency=np.array([[0.0, 1.0], [1.0, 0.0]]),
            active_sections=np.ones((1, 2), bool),
            grid_geometries=[grid_geometry],
            background_grid=np.array([0.5, 0.5]),
            beta=2.1471442086213064,
            magnitude_reference=2.5,
            graph_neighbors=1,
            maximum_log_tilt=4.0,
        )
        return FrailtyRenewalFitEvaluator(parent)

    def test_zero_weights_are_exact_etas(self):
        result = self.evaluator().evaluate(
            np.array([4.0, 0.5, 0.5, 0.0, 0.0, 0.0, 1.0]),
            np.array([1.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.2]),
        )
        np.testing.assert_array_equal(result.event_gains, 0.0)

    def test_root_excess_affects_only_later_forecasts(self):
        result = self.evaluator().evaluate(
            np.array([4.0, 0.5, 0.5, 0.0, 0.0, 0.0, 1.0]),
            np.array([0.1, 100.0, 0.0, 0.0, 3.0, 0.0, 0.2]),
        )
        self.assertEqual(result.event_gains[0], 0.0)
        self.assertGreater(result.event_gains[1], 0.0)


if __name__ == "__main__":
    unittest.main()
