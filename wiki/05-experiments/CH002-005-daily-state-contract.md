# CH002-005: Daily Readiness State Contract

## Question

Can loading, event assimilation, and rupture depletion update the CH-002 state
daily without origin-time leakage or deterministic fault assignment?

## Clock Contract

The issue forecast is computed at 00:00 UTC from the state available before
that instant. Events in `[issue, issue + 1 day)` are observations for closing
the day and can first affect the next issue. The transition function therefore
accepts a completed observed-day `M >= 2.5` event list and returns next-day
state.

## Loading

Each particle retains its assigned UCERF3 branch. Section loading is

```text
slip_rate * (1 - aseismicity) * coupling_coefficient
```

and is centered and unit-RMS normalized inside that branch. A common offset is
removed because the mass-preserving forecast softmax cannot identify it.

## Event Assignment

Events receive probabilistic weights over nearby active section traces using a
10 km Gaussian bandwidth, 40 km cutoff, and explicit off-fault state. Fault
prior odds are 4:1 at zero trace distance. No event is assigned to one nearest
fault with certainty.

## State Update

For each observed event, assimilation is proportional to frozen ETAS
`P(direct background | event cell)`. The update is bounded by
`sigmoid(-margin)`, so an already-high readiness state cannot grow without
limit from repeated events. Rupture depletion scales with magnitude. The first
candidate has no directional transfer because source mechanisms and receiver
planes are not yet leakage-qualified.

Four gains remain fit-only parameters inside pre-registered bounds: loading,
assimilation, release, and release magnitude exponent. Assignment geometry is
fixed before fitting.

## Tests

Synthetic tests verify branch-balanced particles, normalized seismic loading,
off-fault probability conservation, stronger assimilation for low-ETAS events,
local rupture depletion, inactive-section preservation, and empty-day identity.

## Result

The state-transition contract is implemented. No catalog target, fit score,
validation result, or locked retrospective result was read.

## Next Step

CH002-006 will join issue-time catalog events to frozen ETAS background
posteriors and build the 2014-2018 fit-only replay inputs. It may calculate
training likelihoods but cannot open 2019-2022 validation during construction.
