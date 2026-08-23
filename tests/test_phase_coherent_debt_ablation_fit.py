import unittest

import numpy as np

from etas_challenge.phase_coherent_debt_ablation_fit import (
    PhaseCoherentDebtAblationFitEvaluator,
)
from etas_challenge.phase_coherent_debt_fit import PhaseCoherentDebtFitEvaluator
from test_phase_coherent_debt_fit import PhaseCoherentDebtFitTest


class PhaseCoherentDebtAblationFitTest(unittest.TestCase):
    def setUp(self):
        self.parent = PhaseCoherentDebtFitTest.evaluator()
        self.parent_parameters = PhaseCoherentDebtFitTest.parent_parameters()
        self.frailty_parameters = PhaseCoherentDebtFitTest.frailty_parameters()
        self.phase_parameters = np.array([2.0, 10.0, 0.0, 0.5, 3.0])

    def test_full_mode_exactly_matches_locked_daily_evaluator(self):
        locked = PhaseCoherentDebtFitEvaluator(self.parent).evaluate(
            self.parent_parameters, self.frailty_parameters, self.phase_parameters
        )
        versioned = PhaseCoherentDebtAblationFitEvaluator(self.parent).evaluate(
            self.parent_parameters, self.frailty_parameters, self.phase_parameters
        )
        np.testing.assert_array_equal(
            versioned.challenger_event_rates, locked.challenger_event_rates
        )
        np.testing.assert_array_equal(versioned.event_gains, locked.event_gains)

    def test_declared_ablations_are_distinct_counterfactuals(self):
        evaluator = PhaseCoherentDebtAblationFitEvaluator(self.parent)
        full = evaluator.evaluate(
            self.parent_parameters, self.frailty_parameters, self.phase_parameters
        )
        for ablation in (
            "acceleration_removed",
            "network_coherence_removed",
            "frailty_level_removed",
        ):
            result = evaluator.evaluate(
                self.parent_parameters,
                self.frailty_parameters,
                self.phase_parameters,
                ablation=ablation,
            )
            self.assertFalse(
                np.array_equal(result.challenger_event_rates, full.challenger_event_rates),
                ablation,
            )

    def test_unknown_ablation_is_rejected(self):
        with self.assertRaises(ValueError):
            PhaseCoherentDebtAblationFitEvaluator(self.parent).evaluate(
                self.parent_parameters,
                self.frailty_parameters,
                self.phase_parameters,
                ablation="future_outcomes",
            )


if __name__ == "__main__":
    unittest.main()
