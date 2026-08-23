"""CH-009 evaluator correction for inactive fault-transition rows."""

from __future__ import annotations

import numpy as np

from etas_challenge.phase_coherent_debt_ablation_fit import (
    PhaseCoherentDebtAblationFitEvaluator,
)
from etas_challenge.renewal_fit import RenewalFitEvaluator


class PhaseCoherentDebtAblationFitEvaluatorV2(
    PhaseCoherentDebtAblationFitEvaluator
):
    """Complete inactive graph rows with neutral self-loops."""

    def __init__(self, parent: RenewalFitEvaluator) -> None:
        super().__init__(parent)
        completed = []
        for branch, transition in enumerate(self.phase_transitions):
            graph = transition.copy()
            inactive = ~parent.active[branch]
            graph[inactive] = 0.0
            indexes = np.flatnonzero(inactive)
            graph[indexes, indexes] = 1.0
            if not np.allclose(np.sum(graph, axis=1), 1.0):
                raise ValueError("CH-009 active transition rows are not stochastic")
            completed.append(graph)
        self.phase_transitions = completed
