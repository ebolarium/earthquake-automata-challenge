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

## Results

| Quantity | Warmup | Fit development |
| --- | ---: | ---: |
| Issue days | 2,563 | 1,820 |
| RELM events | 8,508 | 3,619 |
| Posterior root mass | 781.7515 | 522.7562 |
| `M >= 3.5` events | 1,439 | 466 |
| `M >= 4.0` events | 318 | 126 |
| `M >= 5.0` events | 30 | 11 |

All 4,383 issue days are contiguous, all events are time ordered, every event
has exactly four fault neighbors, and the scoring boundary reproduces the
existing 3,619-event CH-002 fit subset exactly.

The ignored artifact is `data/local/ch004-event-history-v1.npz`, SHA-256
`303242277044996840daa7f83fe62d12236eb3597870b59925f248279efc1db7`.

## Status

Completed without constructing a renewal state or evaluating a forecast score.

## Next Step

CH004-003 will project event-level marked posterior reset mass and analytical
expected reset hazard through the same four-neighbor branch geometry. It will
test the 2007-2013 warmup state distribution before any candidate search is
registered.
