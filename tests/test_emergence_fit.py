import unittest

import numpy as np

from etas_challenge.emergence_fit import EmergenceFitEvaluator
from etas_challenge.emergence_fit import annual_robust_score
from etas_challenge.emergence_fit import candidate_is_admissible
from etas_challenge.emergence_fit import strongest_neighbor_transition
from etas_challenge.readiness_fit import SparseGeometry


class EmergenceFitTest(unittest.TestCase):
    def test_strongest_neighbor_transition_is_sparse_and_normalized(self):
        adjacency = np.array(
            [[0.0, 3.0, 1.0], [3.0, 0.0, 2.0], [1.0, 2.0, 0.0]]
        )
        transition = strongest_neighbor_transition(adjacency, np.ones(3, bool), 1)
        np.testing.assert_allclose(transition.sum(axis=1), 1.0)
        self.assertEqual(transition.nnz, 3)
        self.assertEqual(int(transition[0].indices[0]), 1)

    def test_replay_scores_before_same_day_observation(self):
        geometry = SparseGeometry(
            section_indexes=np.array([[0], [1]]),
            probabilities=np.ones((2, 1)),
        )
        evaluator = EmergenceFitEvaluator(
            issue_days=np.array([0, 1]),
            observed_root_mass=np.array([[[0.0, 2.0]], [[0.0, 0.0]]]),
            expected_daily_root_mass=np.zeros((1, 2)),
            adjacency=np.array([[0.0, 1.0], [1.0, 0.0]]),
            active_sections=np.ones((1, 2), bool),
            grid_geometries=[geometry],
            background_grid=np.array([1.0, 1.0]),
            event_days=np.array([0, 1]),
            event_cells=np.array([0, 1]),
            event_etas_rates=np.array([1.0, 1.0]),
            event_background_rates=np.array([1.0, 1.0]),
            graph_neighbors=1,
            variance_floor=1.0,
            maximum_log_tilt=4.0,
        )
        result = evaluator.evaluate(np.array([30.0, 0.0, 0.0, 0.0, 0.1, 1.0]))
        self.assertAlmostEqual(result.event_gains[0], 0.0)
        self.assertGreater(result.event_gains[1], 0.0)

    def test_robust_admission_requires_low_etas_and_every_year(self):
        days = np.array([0, 365, 366, 731])
        robust, annual = annual_robust_score(np.array([0.1, 0.1, 0.2, 0.2]), days)
        self.assertGreater(robust, 0)
        self.assertTrue(candidate_is_admissible(0.15, robust, annual, 0.01, -0.01))
        self.assertFalse(candidate_is_admissible(0.15, robust, annual, -0.01, -0.01))


if __name__ == "__main__":
    unittest.main()
