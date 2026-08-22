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

## Status

Pre-registered and unrun.
