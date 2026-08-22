import unittest

import numpy as np

from etas_challenge.residual_emergence import InnovationState
from etas_challenge.residual_emergence import bounded_background_mixture
from etas_challenge.residual_emergence import consensus_score
from etas_challenge.residual_emergence import graph_coherent_score
from etas_challenge.residual_emergence import standardized_excess
from etas_challenge.residual_emergence import update_compensated_cusum


class ResidualEmergenceTest(unittest.TestCase):
    def test_compensated_cusum_accumulates_only_positive_surprise(self):
        state = InnovationState(np.zeros(2), np.zeros(2))
        updated = update_compensated_cusum(
            state, np.array([2.0, 0.0]), np.array([0.5, 0.5]), 0.9
        )
        np.testing.assert_allclose(updated.excess, [1.5, 0.0])
        np.testing.assert_allclose(updated.variance, [0.5, 0.5])
        np.testing.assert_allclose(
            standardized_excess(updated), [1.5 / np.sqrt(1.5), 0.0]
        )

    def test_graph_score_requires_local_and_neighbor_support(self):
        transition = np.array([[0.0, 1.0], [1.0, 0.0]])
        isolated = graph_coherent_score(np.array([3.0, 0.0]), transition, 1.0)
        coherent = graph_coherent_score(np.array([3.0, 2.0]), transition, 1.0)
        np.testing.assert_allclose(isolated, 0.0)
        self.assertTrue(np.all(coherent > 0))

    def test_consensus_rejects_minority_particle_signal(self):
        scores = np.array([[2.0, 2.0], [0.0, 2.0], [0.0, 2.0], [0.0, 0.0]])
        result = consensus_score(scores, minimum_fraction=0.5)
        np.testing.assert_allclose(result, [0.0, 0.75])

    def test_bounded_mixture_preserves_mass_and_limits_downside(self):
        background = np.array([1.0, 2.0, 3.0])
        adjusted = bounded_background_mixture(
            background, np.array([0.0, 0.0, 10.0]), 0.1, 1.0
        )
        self.assertAlmostEqual(float(np.sum(adjusted)), float(np.sum(background)))
        self.assertTrue(np.all(adjusted >= 0.9 * background - 1e-14))

    def test_zero_evidence_is_exactly_etas_background(self):
        background = np.array([1.0, 2.0, 3.0])
        adjusted = bounded_background_mixture(
            background, np.zeros(3), 0.1, 1.0
        )
        np.testing.assert_allclose(adjusted, background)


if __name__ == "__main__":
    unittest.main()
