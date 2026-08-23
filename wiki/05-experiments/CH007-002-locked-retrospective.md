# CH007-002: Locked Retrospective

## Question

Does the unchanged, validation-admitted CH-007 amplitude survive the
2023-01-01 through 2026-08-18 as-of-snapshot period and remain materially
stronger than CH-004?

## Boundary

The CH-007 forecast for this period has not been computed before this lock. The
period is not pristine, however: it was previously opened to score the CH-004
parent and the decision to continue model development followed that result.
This stage is therefore supportive locked retrospective evidence, not a second
independent prospective test.

The model, event history, comparison models, strata, `2x` parent hurdle, annual
veto, paired bootstrap rules, code, and all input hashes are fixed before the
first CH-007 score is read.

## Status

Completed. Every pre-registered gate passed.

## Result

CH-007 achieved `+0.004973` IGPE over 3,995 events, compared with CH-004's
`+0.000336`, a `14.81x` ratio. Annual CH-007 IGPE remained positive:

| Year | CH-007 IGPE |
| --- | ---: |
| 2023 | +0.009226 |
| 2024 | +0.005114 |
| 2025 | +0.004521 |
| 2026 through August 18 | +0.002387 |

Low-ETAS IGPE was `+0.018455`; `M >= 3.5` and `M >= 4.0` IGPE were
`+0.005640` and `+0.006757`. All absolute bootstrap lower bounds were positive.

The paired CH-007-minus-CH-004 gain was `+0.004637` per event. Its 95% lower
bounds were `+0.002875` for 30-day blocks and `+0.003024` for 90-day blocks.
Every pre-registered condition passed.

The report-only full CH-006 forecast was slightly higher in this period but was
slightly lower in development validation. It cannot replace the locked CH-007
candidate after observing this result. Frailty-only uncertainty intervals still
crossed zero, so the mechanistic conclusion remains unchanged.

CH-007 is eligible for immutable prospective shadow activation. This result is
supportive retrospective confirmation, not prospective ETAS superiority.
