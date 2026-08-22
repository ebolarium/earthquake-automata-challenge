# CH005-001: Equilibrium Initial-Age Ensemble

## Question

Can a stationary ETAS-hazard age ensemble improve the locked CH-004 forecast
without relying on the artificial assumption that every fault had age zero on
2007-01-01?

## Hypothesis

Under the memoryless ETAS direct-background null, integrated reset-hazard age
at an arbitrary observation time follows a unit exponential distribution.
Sixteen deterministic midpoint quantiles approximate that distribution. Each
fault section receives a fixed cyclic permutation of the quantiles so ensemble
members do not synchronize all sections at one age.

Inactive sections remain at zero. Member forecast rates are uniformly averaged
before any logarithm or score is computed.

## Lock Boundary

- Parent parameters are unchanged `ch004-marked-renewal-v1` candidate 19.
- Ensemble size is 16 and seed is `20260822`.
- Fit scoring is 2014-01-07 through 2018-12-31 after the unchanged 2007 warmup.
- No 2019 onward event, forecast rate, or score may be read in this stage.
- CH-004 v1 and its completed retrospective result remain immutable.

## Admission Rule

Development validation opens only if ensemble-minus-zero initialization has:

- positive overall fit IGPE;
- nonnegative annual risk-adjusted IGPE;
- nonnegative fit-locked low-ETAS IGPE.

No parameter, ensemble size, distribution, seed, or phase rule may change after
this fit ablation is scored.

## Status

Component and fit ablation pre-registered; catalog score unopened.
