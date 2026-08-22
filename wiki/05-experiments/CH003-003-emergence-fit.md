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

## Numerical Preflights

The first execution exposed a `1.19e-9` IGPE offset in the ETAS control because
the stored float ETAS rate was reconstructed from triggered and analytical
background components. Commit `ab5b8d6` changed the evaluator to apply only the
background delta to the exact stored ETAS rate.

A second execution showed inactive candidates changing some event rates at
`1e-16` scale due to cancellation order. Commit `82752d2` made zero mixture and
zero evidence exact no-ops and calculated the background delta first. Both
preflights were discarded, and no validation data were opened.

## Final Result

The final fit ran from clean commit `82752d2` and evaluated 3,619 events,
including 906 events in the fit-defined low-ETAS quartile.

| Quantity | Value |
| --- | ---: |
| Nonzero Sobol candidates | 32 |
| Candidates that changed at least one event rate | 20 |
| Candidates with positive mean IGPE | 7 |
| Candidates with positive robust annual IGPE | 0 |
| Active candidates with nonnegative low-ETAS IGPE | 0 |
| Selected candidate | 0, exact ETAS control |
| Selected mean IGPE | 0 |
| Selected low-ETAS IGPE | 0 |
| Development validation admitted | No |

The highest-mean active candidate was candidate 19: mean IGPE
`+3.49e-7`, robust annual IGPE `-2.90e-7`, and low-ETAS IGPE
`-3.22e-6`. The active candidate closest to a nonnegative robust score was
candidate 20: robust annual IGPE `-2.64e-9`, but low-ETAS IGPE
`-6.75e-7`. Neither passed the frozen rules.

## Decision

CH-003 is not admitted to 2019-2022 development validation. The residual signal
occasionally improved the global mean, but it was not stable across calendar
years and every active candidate harmed the rare low-ETAS target. The bounded
mixture successfully limited losses, yet safety alone did not create useful
information.

The next challenger should not relax these vetoes or merely lower the CUSUM
threshold. The evidence suggests that positive residual clustering is mostly a
remaining clustering/location effect, not a reliable precursor for rare
background events. A successor should model **negative space**: conditional
seismic quiescence or renewal deficit relative to ETAS, with magnitude-scaled
fault release and an explicit time-since-last-independent-event clock.
