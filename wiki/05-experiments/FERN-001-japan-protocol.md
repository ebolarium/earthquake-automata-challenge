# FERN-001: Japan Three-Region Transport Protocol

## Purpose

Test whether the frozen CH-008 frailty-renewal mechanism transports beyond
California using the three Japanese regions reported by Zlydenko et al. (2023).
The catalog-audit stage reproduced geography and catalog counts before any
Japanese score was opened. `fern-ch008-zero-refit-transfer-v1` subsequently
authorized one frozen-parameter transport evaluation.

## Locked Regions

| Region | Longitude | Latitude | Target | Feature | Maximum depth |
| --- | --- | --- | ---: | ---: | ---: |
| A | `[141, 145)` | `[36, 42)` | `M >= 4.5` | `M >= 3.0` | 100 km |
| B | `[145, 154)` | `[42, 47)` | `M >= 4.5` | `M >= 3.0` | 100 km |
| C | `[141, 154)` | `[36, 47)` | `M >= 5.0` | `M >= 3.0` | 100 km |

The catalog source is the official JMA Seismological Bulletin. Bulletin times
are JST and are converted to UTC by the parser.

## Temporal Boundary

- Training: 1979-01-01 through 1995-12-31.
- Validation: 1996-01-01 through 2003-12-31.
- Test: starts 2004-01-01.

The paper states that evaluation ends before the 2011 Tohoku-oki earthquake,
while its supplementary table labels the test period `2004-2011` and reports
rates consistent with an eight-year denominator. The catalog audit therefore
reports both a pre-Tohoku endpoint and a 2012-exclusive calendar endpoint. The
endpoint matching the published counts must be identified before model work.

## Transport Boundary

The California CH-008 artifact remains immutable. Its UCERF3 fault sections
cannot be used in Japan. A separately versioned regional geometry adapter must
preserve the renewal, frailty, bounded-background-mixture, and sequential replay
equations. The first experiment is a zero-refit California-parameter transfer
against a locally fitted ETAS baseline. Any train-only local refit is a separate
future experiment and cannot alter this result.

## Zero-Refit Adapter

- ETAS is independently fitted in each region using only 1979-1995 targets.
- A 0.5-degree equal-angle latent grid replaces unavailable UCERF3 sections.
- Grid cells use a row-normalized eight-neighbor graph.
- The first zero-refit test models each target process at its own ETAS
  completeness threshold. FERN's `M >= 3` neural feature stream is not mixed
  into this ETAS-root state; doing so requires a separately fitted feature-ETAS
  experiment.
- The CH-004 reset mark and BPT age equations and all seven CH-008 parameters
  remain fixed at their California values.
- Direct-root evidence is `mu / lambda_ETAS` at each event.
- Only the spatial allocation of direct background mass changes; triggering
  and total daily background mass remain ETAS.
- Each day's forecast is constructed before any event from that day updates
  renewal age or frailty.
- Primary skill is event-level mean log rate gain over ETAS. Because the
  background integral is conserved, this equals point-process log-likelihood
  gain per event for the challenger difference.

The executable contract is
`configs/challenge/fern-ch008-transfer-v1.json`. Validation and pre-Tohoku test
results are reported separately with stationary 30-day and 90-day block
bootstrap intervals.

## Catalog Audit

The reproducible download on 2026-08-30 parsed 2,132,648 official bulletin
records. The current JMA snapshot does not reproduce the publication's target
counts:

| Region | Train current / paper | Validation current / paper | Test through 2011 current / paper | Pre-Tohoku current |
| --- | ---: | ---: | ---: | ---: |
| A | 988 / 1238 | 128 / 397 | 1078 / 517 | 153 |
| B | 2016 / 1686 | 726 / 1159 | 942 / 1027 | 889 |
| C | 1320 / 1325 | 263 / 524 | 626 / 592 | 354 |

Threshold sweeps and direct record inspection rule out a fixed-column parser
offset. The paper's source release contains model code but no immutable catalog
snapshot. Consequently, exact FERN count reproduction is unresolved. CH-008
transport work uses the hashed current JMA snapshot and must not claim a direct
score comparison with the paper's FERN results.

## Zero-Refit Result

The frozen California parameters do not generalize uniformly across the three
regions:

| Region | Validation IGPE | Pre-Tohoku test IGPE | 30/90-day test interval conclusion |
| --- | ---: | ---: | --- |
| A | +0.016236 | +0.009003 | Both lower bounds positive |
| B | -0.000384 | -0.000026 | Both intervals cross zero on test |
| C | +0.000004 | +0.000019 | Both intervals cross zero |

Region A is a robust positive external result: its test relative factor is
`1.00904`, and the 30-day and 90-day lower bounds are `+0.00450` and
`+0.00472` IGPE. Region B is significantly negative in development validation
and indistinguishable from ETAS in test. Region C is effectively neutral in
both periods.

Therefore FERN-001 rejects a broad three-region transport claim for unchanged
CH-008. Region A is a legitimate follow-up signal, but selecting or tuning a
Japan-specific model after seeing these outcomes must be labeled a new
development experiment. The catalog mismatch and target-only state stream
remain important limitations.

The complete parameters, input hashes, event counts, bootstrap seeds, and
intervals are stored in
`data/manifests/fern-ch008-zero-refit-transfer-v1.json`.

## Post-Hoc Region A Diagnosis

This section was produced after FERN-001 outcomes were known. It explains the
result but cannot be used as independent model-selection evidence.

The A result is primarily renewal skill, with a smaller positive frailty
increment:

| A test component | IGPE |
| --- | ---: |
| Full CH-008 | +0.009003 |
| Renewal only | +0.007906 |
| Frailty only | +0.001097 |
| Full minus renewal only | +0.001097 |

CH-008 can alter only ETAS direct-background mass. That mass is materially more
available in A. The mean event-level ETAS background probability is 20.49% in
A test events, versus 1.95% in B and 1.87% in C. Fitted regional background
rates are 0.0303, 0.00764, and 0.00377 events/day respectively. Thus A gives
the frozen mechanism both a faster renewal clock and about ten times more
event-level background leverage.

The positive result is temporally and magnitude-wise broad: every test year is
positive, as are the `M4.5-4.9`, `M5.0-5.9`, and `M6+` strata. It is spatially
concentrated offshore, especially near `[142.0,142.5) E x [36.5,37.0) N`, but
not wholly dependent on that location. Removing the highest-gain cell leaves
`+0.005372` IGPE; removing the three highest-gain cells leaves `+0.003496`.
The leading events in the strongest cell occur across 2005, 2006, and 2007,
not in one short same-sequence burst.

The diagnosis is therefore: A contains a comparatively substantial ETAS
background process whose long-lived spatial recurrence aligns with CH-008's
renewal clock. B's renewal term is mildly harmful, while C's renewal term is
inactive under the frozen target-only adapter; their small direct-background
fractions also leave little room for CH-008 to improve ETAS.

Full diagnostic ablations and strata are stored in
`data/manifests/fern-ch008-region-a-diagnostic-v1.json`.

## Sources

- Zlydenko et al., *A neural encoder for earthquake rate forecasting* (2023).
- Official supplementary material, especially Tables I and III.
- JMA Seismological Bulletin hypocenter files and record format.
- Official `google-research/earthquakes_fern` source release.
