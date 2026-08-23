# CH008-003: Locked Retrospective

## Question

Does unchanged, validation-admitted CH-008 preserve both its CH-007 advantage
and its distinct frailty contribution on the 2023-2026 as-of-snapshot period?

## Boundary

Full CH-008 and its renewal-only/frailty-only ablations have not been scored on
this period before this lock. The period previously scored CH-004 and CH-007,
so this is supportive retrospective confirmation rather than pristine
independent evidence.

The exact validation gate is reused: every condition, including paired
CH-008-minus-CH-007 and full-minus-renewal frailty bootstrap lower bounds, must
pass. No report-only model can replace CH-008 after outcomes are opened.

## Status

Completed. Every pre-registered admission and mechanism gate passed.

## Result

CH-008 achieved `+0.007865` IGPE over 3,995 retrospective events, compared
with CH-007's `+0.004973`, a 58.1% improvement. The paired
CH-008-minus-CH-007 gain was `+0.002891` per event; its 95% lower bounds were
`+0.001963` for 30-day blocks and `+0.002067` for 90-day blocks.

Low-ETAS IGPE was `+0.028800`, while `M >= 3.5` and `M >= 4.0` IGPE were
`+0.011235` and `+0.013505`. Every annual CH-008 score was positive:

| Year | CH-008 IGPE |
| --- | ---: |
| 2023 | +0.013350 |
| 2024 | +0.007780 |
| 2025 | +0.006777 |
| 2026 | +0.005404 |

## Frailty Mechanism

Renewal-only CH-008 achieved `+0.006049`; full CH-008 achieved `+0.007865`.
The paired full-minus-renewal frailty increment was `+0.001816` per event,
with 30/90-day lower bounds of `+0.001238` and `+0.001270`. Its low-ETAS
increment was `+0.006447`, again with both lower bounds positive.

Frailty contribution was positive in every retrospective year:

| Year | Frailty increment |
| --- | ---: |
| 2023 | +0.002095 |
| 2024 | +0.001573 |
| 2025 | +0.001273 |
| 2026 | +0.002514 |

Frailty-only IGPE was independently positive at `+0.001650`, with positive
30/90-day lower bounds. The full-minus-renewal comparison remains the primary
mechanism evidence.

## Conclusion

CH-008 preserved both its CH-007 advantage and a statistically supported
frailty contribution on the locked retrospective period. It is therefore the
leading challenger and is eligible for immutable prospective shadow testing.
Because CH-004 and CH-007 had previously been scored on this period, this is
supportive retrospective evidence, not pristine prospective evidence or a
scientific ETAS-superiority claim.
