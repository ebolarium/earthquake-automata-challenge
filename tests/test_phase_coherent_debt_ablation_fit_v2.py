import unittest

import numpy as np

from etas_challenge.phase_coherent_debt_ablation_fit import (
    PhaseCoherentDebtAblationFitEvaluator,
)
from etas_challenge.phase_coherent_debt_ablation_fit_v2 import (
    PhaseCoherentDebtAblationFitEvaluatorV2,
)
from test_phase_coherent_debt_fit import PhaseCoherentDebtFitTest


class PhaseCoherentDebtAblationFitV2Test(unittest.TestCase):
    def test_all_active_fixture_is_unchanged(self):
        parent = PhaseCoherentDebtFitTest.evaluator()
        original = PhaseCoherentDebtAblationFitEvaluator(parent)
        corrected = PhaseCoherentDebtAblationFitEvaluatorV2(parent)
        parameters = np.array([2.0, 10.0, 0.0, 0.5, 3.0])
        left = original.evaluate(
            PhaseCoherentDebtFitTest.parent_parameters(),
            PhaseCoherentDebtFitTest.frailty_parameters(),
            parameters,
        )
        right = corrected.evaluate(
            PhaseCoherentDebtFitTest.parent_parameters(),
            PhaseCoherentDebtFitTest.frailty_parameters(),
            parameters,
        )
        np.testing.assert_array_equal(
            left.challenger_event_rates, right.challenger_event_rates
        )

    def test_inactive_rows_receive_only_self_loops(self):
        parent = PhaseCoherentDebtFitTest.evaluator()
        parent.active[0, 1] = False
        evaluator = PhaseCoherentDebtAblationFitEvaluatorV2(parent)
        np.testing.assert_array_equal(evaluator.phase_transitions[0][1], [0.0, 1.0])
        np.testing.assert_allclose(np.sum(evaluator.phase_transitions[0], axis=1), 1.0)


if __name__ == "__main__":
    unittest.main()
