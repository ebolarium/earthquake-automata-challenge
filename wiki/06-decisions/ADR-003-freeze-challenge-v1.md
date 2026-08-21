# ADR-003: Freeze Challenge V1 Before Challenger Development

## Status

Accepted and frozen on 2026-08-21.

## Context

The native ETAS implementation now reproduces the locked EarthquakeNPP
`ComCat_25` baseline, runs a deterministic daily replay, passes the pyCSEP
integration gate, and publishes an inspectable forecast. Challenger development
must not silently change the comparison after its outcomes are observed.

Earlier Earthquake Automata experiments used overlapping global catalog history.
Although their production artifacts are excluded from this repository, they may
have influenced feature ideas. The historical test is therefore confirmatory
as-of-snapshot evidence, not a genuinely blind prospective record.

## Decision

`configs/challenge/challenge-v1.json` is the immutable evaluation contract. It
locks:

- the exact baseline commit, parameters, inputs, and catalog hash;
- the California RELM region, 0.1-degree grid, daily UTC clock, and `M >= 2.5`
  primary target;
- challenger fitting on 2007-2018 and development validation on 2019-2022;
- a one-use-per-artifact retrospective test from 2023-01-01 through
  2026-08-18;
- paired information gain per earthquake as the primary score;
- 10,000-replicate 30-day block-bootstrap uncertainty with a 90-day
  sensitivity analysis;
- mandatory reporting for higher magnitudes and low-ETAS-intensity events;
- a separate prospective gate before any scientific superiority claim.

The retrospective test may promote a challenger to prospective testing. It
cannot establish general ETAS superiority by itself. That claim requires
predictions persisted before observations, at least 365 issue days, at least
500 target events, and a positive prospective confidence-bound result.

## First Admitted Challenger

`CH-001` will be an ETAS residual-emergence model, not an imported RQ artifact.
Its first version will preserve the ETAS daily count and magnitude forecast and
learn only a spatial redistribution on the common CSEP grid:

```text
p_challenger(cell | day) proportional to
    p_ETAS(cell | day) * exp(f(issue-time catalog features))
```

The initial feature family is restricted to leakage-free catalog summaries:
multi-window activity, neighboring-cell activity, acceleration, recency,
quietness, and activity relative to a training-only background. Static strain,
fault, GNSS, legacy RQ scores, and manually selected alarms are excluded from
CH-001.

This conditional spatial design gives the baseline and challenger the same
expected daily event count. Any gain must initially come from locating future
events better, including events in low-ETAS-intensity cells.

## Consequences

- Model selection stops at the end of the validation split.
- Every challenger artifact receives a unique immutable identifier and hash.
- Opening the retrospective test is an auditable experiment, not an iterative
  dashboard action.
- Negative results and ablations remain in the experiment index.
- A future stronger adaptive or nonparametric ETAS comparator may be added as a
  second baseline, but it cannot replace or alter the frozen V1 baseline.
