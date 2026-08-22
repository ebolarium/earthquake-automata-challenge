# ADR-005: ETAS-Compensated Residual Emergence

## Status

Accepted as the CH-003 component contract. No catalog score has been read.

## Context

CH-002 applied an uncertain absolute latent margin to all direct-background
mass. Its best selection candidate gained only `0.000335` IGPE and lost
`0.011573` IGPE on the report-only 2018 holdout. Stronger tilts failed more
severely. Tuning the same gains again would not test a meaningfully different
hypothesis.

Under a correctly specified conditional-intensity model, observed increments
minus the predictable compensator form a martingale innovation. For an event,
the frozen ETAS direct-background posterior supplies fractional root mass. Its
expected counterpart is the analytical ETAS background mass projected to the
same fault sections.

## Decision

CH-003 will accumulate only positive, persistent ETAS-compensated innovations:

```text
innovation_s(t) = observed_background_root_mass_s(t)
                  - expected_background_mass_s(t)
C_s(t) = max(0, rho * C_s(t-1) + innovation_s(t))
V_s(t) = rho^2 * V_s(t-1) + expected_background_mass_s(t)
Z_s(t) = C_s(t) / sqrt(V_s(t) + variance_floor)
```

A section can influence a forecast only when both its local standardized excess
and its graph-neighbor excess clear the threshold. Loading-branch particles
must agree on the sign. Absolute initial stress and strength maps are excluded.

The resulting direct-background distribution is a bounded mixture:

```text
q = (1 - epsilon) * q_ETAS_background
    + epsilon * q_emergence
lambda_CH003 = lambda_ETAS_triggered + B * q
```

`epsilon <= 0.10`, so no cell retains less than 90% of its ETAS direct
background solely because of CH-003. With zero evidence, CH-003 is exactly ETAS.

## Leakage Boundary

The CH-002 experiment exposed its 2018 fit holdout before this design. CH-003
therefore treats all 2014-2018 observations as development data and makes no
blind-holdout claim for them. Its mechanism and fitted artifact must be locked
before any 2019-2022 score is read for CH-003. The 2023 onward retrospective
period remains locked.

## Consequences

This model challenges ETAS only where ETAS produces a sustained, spatially
coherent residual. It cannot manufacture a static forecast from an arbitrary
initial stress realization, and its per-cell downside from background
redistribution is explicitly bounded. A failure would reject this residual
emergence mechanism without weakening the ETAS baseline or reopening CH-002.
