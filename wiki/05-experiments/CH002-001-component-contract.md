# CH002-001: ETAS Component and Readiness Contract

## Question

Can CH-002 alter only the direct tectonic-background allocation while exactly
preserving frozen ETAS triggering and daily expected count?

## Hypothesis

A mass-preserving readiness tilt can provide a clean experimental boundary:
any later score difference comes from where the ETAS background is allocated,
not from changing the expected number of events or its aftershock process.

## Inputs

- Frozen CH001-002 ETAS daily cell rates.
- Exact direct-background rates `mu * spherical_cell_area` from the locked ETAS
  parameters and RELM grid.
- Synthetic dimensionless margins for contract tests only.

No fault, strain, GNSS, production-database, or post-issue observation enters
this milestone.

The resulting experiment family is pre-registered in
`configs/challenge/ch002-readiness-v0.json` before source acquisition.

## Contract

- `sensitivity = 0` or a constant margin reproduces the frozen ETAS grid.
- The triggered component is never reranked.
- The adjusted background remains finite, positive, and equal in total mass to
  the analytical ETAS background.
- The resulting forecast has exactly the same daily expected count as ETAS.
- State evolution is explicitly `margin + loading * dt - release + transfer`.
- The state is dimensionless and cannot support an absolute-stress claim.

## Metrics and Acceptance

This is a numerical contract, not a forecast-skill experiment. Unit tests must
verify component identity, mass conservation, overflow stability, transition
signs, input validation, and ETAS background-posterior weights.

## Next Step

CH002-002 will inventory authoritative California fault geometry, slip/loading,
rupture-history, and mechanism sources. Each candidate source must record
publication/version date, license, spatial coverage, uncertainty, and what was
available at each forecast issue date. No validation scoring is authorized by
this component milestone.
