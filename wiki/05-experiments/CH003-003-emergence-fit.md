# CH003-003: Risk-Sensitive Residual-Emergence Fit

## Question

Can persistent, fault-network-coherent ETAS residuals improve next-day spatial
allocation without sacrificing rare low-intensity events or relying on one
favorable calendar year?

## Pre-Registered Search

- 32 scrambled Sobol candidates, seed `20260822`, plus the exact ETAS control.
- Log-uniform residual memory from 30 to 730 days.
- Standardized CUSUM threshold from 0.5 to 4.0.
- Local graph diffusion from 0 to 0.5 over eight strongest fault neighbors.
- Minimum UCERF3 branch consensus from 0.5 to 0.875.
- Bounded direct-background mixture from 0.5% to 10%.
- Emergence tilt sensitivity from 0.1 to 2.0.

All 2014-2018 data are disclosed development data because CH-002 already
exposed 2018 outcomes. The primary fit criterion is mean annual IGPE minus the
population standard deviation of annual IGPE. A nonzero candidate is admissible
only if its mean and robust scores are positive, every annual IGPE is at least
`-0.01`, and fit-defined low-ETAS IGPE is nonnegative. Otherwise ETAS wins.

## Leakage and Claim Boundary

Each issue-day forecast is produced before that day's observed compensator is
applied. The generator, evaluator, candidate bounds, seed, vetoes, and input
hashes must be committed before execution. No 2019-2022 CH-003 score or locked
retrospective outcome may be read during this experiment.

## Status

Pre-registered and unrun.
