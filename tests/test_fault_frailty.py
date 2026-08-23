import unittest

import numpy as np

from etas_challenge.fault_frailty import discounted_gamma_poisson_update
from etas_challenge.fault_frailty import positive_frailty_score
from etas_challenge.fault_frailty import posterior_log_frailty


class FaultFrailtyTest(unittest.TestCase):
    def test_unit_prior_is_neutral_without_evidence(self):
        score = posterior_log_frailty(np.zeros(2), np.zeros(2), 4.0)
        np.testing.assert_array_equal(score, 0.0)

    def test_posterior_compares_roots_with_etas_exposure(self):
        score = posterior_log_frailty(
            np.array([2.0, 2.0]), np.array([4.0, 1.0]), 2.0
        )
        self.assertGreater(score[0], 0.0)
        self.assertLess(score[1], 0.0)

    def test_discounted_update_forgets_old_evidence(self):
        exposure, roots = discounted_gamma_poisson_update(
            np.array([2.0]),
            np.array([4.0]),
            np.array([1.0]),
            np.array([0.0]),
            1.0,
        )
        np.testing.assert_allclose(exposure, [2.0])
        np.testing.assert_allclose(roots, [2.0])

    def test_positive_score_requires_excess_after_graph_blend(self):
        score = positive_frailty_score(
            np.array([0.4, -0.2]), np.array([0.0, 0.4]), 0.5, 0.1
        )
        np.testing.assert_allclose(score, [0.1, 0.0])


if __name__ == "__main__":
    unittest.main()
