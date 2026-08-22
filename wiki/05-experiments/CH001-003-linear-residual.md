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

Implementation pending fit-only reproducibility and commit gate.
