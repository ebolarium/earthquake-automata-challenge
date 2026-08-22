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

Fit ablation completed; development validation admitted and unopened.

The first execution preflight stopped at module import before loading the
catalog or running a replay. The container script path was made explicit; no
experimental input, initialization rule, admission rule, or score changed.

## Fit Result

The equilibrium mixture improved primary fit IGPE from `+0.000255` to
`+0.000330`, a paired gain of `+0.000075` per event. The low-ETAS paired gain
was `+0.000256`; `M >= 3.5` and `M >= 4.0` paired gains were also positive.
Every annual paired delta from 2014 through 2018 was positive and the annual
risk-adjusted delta was `+0.000034`.

All three frozen admission conditions passed. The initialization definition is
now locked and may be evaluated unchanged on 2019-2022 development validation.

The validation gate requires positive overall paired delta, nonnegative
low-ETAS paired delta, a positive 30-day 95% bootstrap lower bound, and a
nonnegative 90-day lower bound. The 2023 onward period remains excluded.

## Validation Result

The equilibrium mixture retained a small positive mean advantage over zero
initialization: primary paired IGPE `+0.000008`, low-ETAS `+0.000029`,
`M >= 3.5` `+0.000022`, and `M >= 4.0` `+0.000027`. However, annual primary
deltas were negative in 2019, 2021, and 2022. The paired primary intervals were:

- 30-day blocks: `[-0.000019, +0.000036]`.
- 90-day blocks: `[-0.000021, +0.000036]`.

Both confidence-bound conditions failed. CH-005 is therefore completed but not
validated or promoted, and no 2023 onward outcome is opened.

## Conclusion

The equilibrium initialization removes some early zero-age bias, as shown by
the larger and annually consistent fit improvement. After twelve years of
state evolution, its remaining contribution is too small and unstable to
establish durable forecast skill. A future experiment should propagate state
uncertainty dynamically rather than search for another fixed initial state.
