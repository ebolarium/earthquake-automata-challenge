import unittest

import numpy as np

from etas_challenge.frailty_renewal_fit import FrailtyRenewalFitEvaluator
from etas_challenge.phase_coherent_debt_fit import PhaseCoherentDebtFitEvaluator
from etas_challenge.readiness_fit import SparseGeometry
from etas_challenge.renewal_fit import RenewalFitEvaluator


class PhaseCoherentDebtFitTest(unittest.TestCase):
    @staticmethod
    def evaluator():
        issue_days = np.arange(24)
        event_days = np.array([20, 20, 20, 20, 20, 20, 20, 23])
        event_sections = np.array([[0], [0], [0], [0], [1], [1], [1], [0]])
        event_geometry = SparseGeometry(
            section_indexes=event_sections,
            probabilities=np.ones_like(event_sections, dtype=float),
        )
        grid_geometry = SparseGeometry(
            section_indexes=np.array([[0], [1]]),
            probabilities=np.ones((2, 1)),
        )
        parent = RenewalFitEvaluator(
            issue_days=issue_days,
            scoring_start_day=20,
            event_days=event_days,
            event_cells=np.array([0, 0, 0, 0, 1, 1, 1, 0]),
            event_magnitudes=np.full(len(event_days), 2.5),
            event_etas_rates=np.ones(len(event_days)),
            event_background_probabilities=np.array([1, 1, 1, 1, 1, 1, 1, 0]),
            event_geometries=[event_geometry],
            expected_section_background=np.array([[0.12, 0.12]]),
            adjacency=np.array([[0.0, 1.0], [1.0, 0.0]]),
            active_sections=np.ones((1, 2), bool),
            grid_geometries=[grid_geometry],
            background_grid=np.array([0.5, 0.5]),
            beta=2.1471442086213064,
            magnitude_reference=2.5,
            graph_neighbors=1,
            maximum_log_tilt=4.0,
        )
        return parent

    @staticmethod
    def parent_parameters():
        return np.array([4.0, 0.5, 1.0, 0.0, 0.0, 0.0, 1.0])

    @staticmethod
    def frailty_parameters():
        return np.array([0.1, 100.0, 0.0, 0.0, 0.5, 1.0, 0.2])

    def test_zero_phase_weight_is_exact_ch008(self):
        parent = self.evaluator()
        ch008 = FrailtyRenewalFitEvaluator(parent).evaluate(
            self.parent_parameters(), self.frailty_parameters()
        )
        ch009_control = PhaseCoherentDebtFitEvaluator(parent).evaluate(
            self.parent_parameters(),
            self.frailty_parameters(),
            np.array([2.0, 10.0, 0.0, 0.5, 0.0]),
        )
        np.testing.assert_array_equal(
            ch009_control.challenger_event_rates, ch008.challenger_event_rates
        )
        np.testing.assert_array_equal(ch009_control.event_gains, ch008.event_gains)
        self.assertEqual(ch009_control.active_issue_days, ch008.active_issue_days)

    def test_same_day_roots_affect_only_next_issue_phase_forecast(self):
        parent = self.evaluator()
        evaluator = PhaseCoherentDebtFitEvaluator(parent)
        control = evaluator.evaluate(
            self.parent_parameters(),
            self.frailty_parameters(),
            np.array([2.0, 10.0, 0.0, 0.5, 0.0]),
        )
        phase = evaluator.evaluate(
            self.parent_parameters(),
            self.frailty_parameters(),
            np.array([2.0, 10.0, 0.0, 0.5, 3.0]),
        )
        np.testing.assert_array_equal(
            phase.challenger_event_rates[:7], control.challenger_event_rates[:7]
        )
        self.assertGreater(
            phase.challenger_event_rates[-1], control.challenger_event_rates[-1]
        )
        self.assertEqual(phase.phase_active_issue_days, 1)


if __name__ == "__main__":
    unittest.main()
