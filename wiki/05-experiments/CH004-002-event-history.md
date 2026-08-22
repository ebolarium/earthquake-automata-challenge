# CH004-002: Warmup and Fit Event History

## Question

Can CH-004 receive event-level ETAS root posteriors and magnitudes from 2007
through 2018 without scoring warmup targets or opening validation?

## Pre-Registered Construction

- Warmup issues: 2007-01-01 through 2014-01-06, never scored.
- Future fit-development issues: 2014-01-07 through 2018-12-31.
- Events: rounded `M >= 2.5` inside the frozen California RELM grid.
- Root weight: analytical direct-background rate divided by the issue-day
  frozen ETAS cell rate.
- Geometry: four nearest UCERF3 trace sections from each exact epicenter.
- Magnitudes remain event-level so the reset mark can vary by candidate.

The source catalog, all ETAS shards, fault sections, grid, simulation config,
period boundary, and output schema are hash-locked. This artifact computes no
renewal state, reset mark, forecast, or information-gain score.

## Status

Pre-registered and unbuilt. The generator must be committed before execution.
