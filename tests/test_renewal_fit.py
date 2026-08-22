import unittest

import numpy as np

from etas_challenge.readiness_fit import SparseGeometry
from etas_challenge.renewal_fit import RenewalFitEvaluator
from etas_challenge.renewal_quiescence import equilibrium_hazard_age_ensemble


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

    def test_explicit_initial_age_affects_first_issue_forecast(self):
        result = self.evaluator().evaluate(
            np.array([4.0, 0.5, 0.5, 0.0, 0.0, 0.1, 1.0]),
            initial_age=np.array([[3.0, 0.0]]),
        )
        self.assertGreater(result.event_gains[0], 0.0)

    def test_equilibrium_ensemble_is_stratified_and_deterministic(self):
        active = np.array([[True, True, False], [True, False, True]])
        first = equilibrium_hazard_age_ensemble(active, 8, 20260822)
        second = equilibrium_hazard_age_ensemble(active, 8, 20260822)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(first.shape, (8, 2, 3))
        np.testing.assert_array_equal(first[:, ~active], 0.0)
        expected = np.sort(-np.log1p(-(np.arange(8) + 0.5) / 8))
        for branch, section in np.argwhere(active):
            np.testing.assert_allclose(np.sort(first[:, branch, section]), expected)

    def test_ensemble_scores_the_mean_rate_not_mean_member_score(self):
        evaluator = self.evaluator()
        parameters = np.array([4.0, 0.5, 0.5, 0.0, 0.0, 0.1, 1.0])
        ages = np.array([[[0.0, 0.0]], [[3.0, 0.0]]])
        members = [
            evaluator.evaluate(parameters, initial_age=initial_age)
            for initial_age in ages
        ]
        mixture = evaluator.evaluate_initial_age_ensemble(parameters, ages)
        expected_rates = np.mean(
            [member.challenger_event_rates for member in members], axis=0
        )
        np.testing.assert_allclose(mixture.challenger_event_rates, expected_rates)
        np.testing.assert_allclose(mixture.event_gains, np.log(expected_rates))


if __name__ == "__main__":
    unittest.main()
