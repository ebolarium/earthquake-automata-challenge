# CH004-004: Marked Renewal Fit

## Question

Can an ETAS-normalized, magnitude-marked fault renewal clock improve next-day
spatial allocation robustly across years while preserving low-ETAS events?

## Pre-Registered Search

- Seven-year unscored warmup from 2007-01-01 through 2014-01-06.
- 32 scrambled Sobol candidates, seed `20260822`, plus exact ETAS control.
- Full-reset magnitude restricted to 3.5-4.75 by the unscored CH004-003 coverage
  diagnostic; M5/M6-scale inactive regions are excluded.
- Magnitude exponent 0.25-0.75 and BPT aperiodicity 0.3-1.0.
- Eight-neighbor graph context, UCERF3 branch consensus, and at most 10% direct
  background mixture.

The selection metric is mean annual IGPE minus annual population standard
deviation. Admission additionally requires positive mean IGPE, every annual
IGPE at least `-0.01`, and nonnegative low-ETAS IGPE. Otherwise ETAS wins.

## Leakage Boundary

Warmup targets are never scored. Each fit issue is forecast before its same-day
events reset the clock. All code, bounds, seed, vetoes, and input hashes must be
committed before execution. No 2019-2022 CH-004 score or locked-retrospective
outcome may be read.

## Fit Result

The locked run evaluated 3,619 fit-development events, including 906 events in
the fit-defined low-ETAS quartile. Candidate 19 won the risk-sensitive rule.

| Quantity | Value |
| --- | ---: |
| Mean IGPE | +0.00025471 |
| Robust annual IGPE | +0.00011276 |
| Low-ETAS IGPE | +0.00086770 |
| 2014 IGPE | +0.00014164 |
| 2015 IGPE | +0.00021225 |
| 2016 IGPE | +0.00010342 |
| 2017 IGPE | +0.00057579 |
| 2018 IGPE | +0.00053365 |
| Development validation admitted | Yes |

Selected parameters include full-reset magnitude `4.08895`, magnitude exponent
`0.35897`, BPT aperiodicity `0.98928`, graph-neighborhood mix `0.67650`, and a
bounded background mixture fraction of `0.06304`.

The gain is small but consistent across all five fit years, and the low-ETAS
gain is larger than the overall mean. This is the first challenger in the
project to satisfy the pre-registered rare-event and annual-robust admission
rules. It is not yet a validation result or an ETAS-superiority claim.

## Status

Fit completed and locked from commit `e2b551b`; admitted to development
validation. No 2019-2022 CH-004 outcome has been read.
