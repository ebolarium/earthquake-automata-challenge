# CH001-003: Linear ETAS Residual

## Question

Can a small, interpretable catalog-only residual improve the frozen ETAS spatial
distribution while preserving ETAS daily event counts exactly?

## Frozen First Candidate

The first candidate is a regularized conditional linear model:

```text
p_CH001(cell | day) proportional to
    rate_ETAS(cell | day) * exp(standardized_features(cell, day) dot weights)
```

It has no intercept and 15 fixed transformed features. Activity counts use
`log1p`; excess and acceleration retain their signed log-ratio values; recency
uses `log1p`; and the training-only background rate uses a natural logarithm.
All features are standardized from challenger-fit cell-days and clipped at
eight standard deviations. L2 strength, coefficient bounds, optimizer, and
stopping rules are frozen in `configs/challenge/ch001-linear-v1.json`.

## Leakage Gate

The fit command reads only complete monthly shards from 2007-01-01 through
2018-12-31. It also derives the low-ETAS event-intensity 25th percentile from
those fit targets. The generated model and fit manifest must be committed
before the separate validation command is allowed to score 2019-2022.

No static strain, fault, GNSS, legacy RQ score, handcrafted alarm, validation
target, or retrospective-test event is admitted to this candidate.

## Status

The first fit-only preflight reached the frozen 40-iteration optimizer limit
without writing a model. Its final objective was changing at roughly `2e-10`
and fit IGPE had stabilized near `0.0484203`, but the convergence flag remained
false. No validation shard was opened. Because optimizer convergence is a fit
concern, the candidate contract now allows 80 iterations and uses an `ftol` of
`1e-9`; this change must be committed before the fit is rerun.

The committed optimizer contract then converged after 38 iterations and 42
objective evaluations. The fit process read 144 monthly shards and 33,670,206
cell-days, ending before 2019-01-01.

## Fit Lock

| Measure | Value |
|---|---:|
| Fit target events | 12,127 |
| Total fit information gain | 587.192865 nat |
| Fit information gain per event | 0.0484203 nat/event |
| Positive-gain days | 2,139 |
| Negative-gain days | 1,412 |
| Low-ETAS fit-event 25th percentile | 0.0010438695 rate/cell/day |

The model SHA-256 is
`85a76fa4ed612942e7b572eca196bef44fcf7247a0176f64b55c5531d9de7b19`.
Its status is `fit_locked_validation_unseen`, and the fit manifest explicitly
records `validation_opened: false`. These are optimization results, not
out-of-sample evidence.
