# CH004-001: Marked Renewal Component Contract

## Question

Can a magnitude-marked, ETAS-normalized renewal clock be implemented without
absolute stress, hard declustering, or same-day target leakage?

## Implemented Components

- Smooth capped rupture-reset mark.
- Closed-form expected mark under the frozen Gutenberg-Richter distribution.
- Expected hazard-age update with probabilistic posterior reset.
- Positive Brownian-passage-time overdue score against a memoryless baseline.

Synthetic tests verify mark monotonicity and saturation, analytic expectation
against numerical quadrature, soft reset arithmetic, and overdue-score behavior.

## Boundary

No earthquake catalog, CH-004 forecast score, development-validation result, or
locked-retrospective outcome was evaluated.

## Next Step

CH004-002 will build 2007-2018 event-level ETAS background posteriors and
branch-aware fault assignments. The 2007-2013 portion will be warmup-only, and
the artifact must retain magnitudes so reset marks remain candidate-dependent.
