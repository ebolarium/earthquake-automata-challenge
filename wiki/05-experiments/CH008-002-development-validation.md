# CH008-002: Distinct-Regime Development Validation

## Question

Does fit-locked CH-008 generalize as a distinct frailty-renewal regime rather
than merely reproducing CH-007 with a larger amplitude?

## Locked Comparisons

- Full CH-008 candidate 43.
- Unchanged validated CH-007 incumbent.
- CH-008 renewal-only ablation with frailty weight fixed to zero.
- CH-008 frailty-only report with renewal weight fixed to zero.
- Unchanged CH-004 and ETAS references.

All models are scored on the same events. No parameter, ablation, threshold, or
comparison model may change after 2019-2022 validation is opened.

## Admission Gate

CH-008 reaches retrospective evaluation only if all conditions pass:

- positive overall IGPE and positive IGPE in every validation year;
- at least `1.10x` CH-007 overall IGPE;
- low-ETAS IGPE no worse than CH-007;
- nonnegative `M >= 3.5` and `M >= 4.0` IGPE;
- CH-008-minus-CH-007 30-day bootstrap lower bound positive and 90-day lower
  bound nonnegative;
- full-minus-renewal-only frailty increment positive overall and in low-ETAS;
- frailty increment 30-day lower bound positive and 90-day lower bound
  nonnegative.

The frailty bootstrap requirements are mechanistic gates, not report-only
diagnostics. Failure blocks CH-008 retrospective promotion even if its total
ETAS gain is large.

## Leakage Boundary

This stage scores only 2019-01-01 through 2022-12-31 after the unchanged
2007 warmup. CH-008 forecasts for 2019 onward have not previously been read.
No 2023 onward CH-008 outcome may be opened unless every gate above passes.

## Status

Completed. Every pre-registered admission and mechanism gate passed. No 2023
onward CH-008 outcome has been read.

## Result

CH-008 achieved `+0.005213` IGPE over 5,204 validation events, compared with
CH-007's `+0.003625`, a 43.8% improvement. Low-ETAS IGPE was `+0.022916`
versus CH-007's `+0.016463`. `M >= 3.5` and `M >= 4.0` IGPE were `+0.006805`
and `+0.008580`.

Every annual CH-008 score was positive:

| Year | CH-008 IGPE |
| --- | ---: |
| 2019 | +0.004947 |
| 2020 | +0.001226 |
| 2021 | +0.009177 |
| 2022 | +0.011346 |

The paired CH-008-minus-CH-007 gain was `+0.001589` per event. Its 95% lower
bounds were `+0.000692` for 30-day blocks and `+0.000663` for 90-day blocks.

## Frailty Mechanism

Renewal-only CH-008 achieved `+0.004411`; full CH-008 achieved `+0.005213`.
The paired full-minus-renewal frailty increment was therefore `+0.000802` per
event. Its lower bounds were `+0.000409` and `+0.000401` for 30- and 90-day
blocks. Low-ETAS frailty increment was `+0.002961` with both lower bounds
positive.

Frailty contribution was positive in every validation year:

| Year | Frailty increment |
| --- | ---: |
| 2019 | +0.000564 |
| 2020 | +0.000382 |
| 2021 | +0.001227 |
| 2022 | +0.001824 |

Frailty-only IGPE was independently positive at `+0.000759`, with positive
30/90-day lower bounds. The full-minus-renewal comparison remains the primary
mechanism evidence because it tests frailty inside the selected combined model.

## Conclusion

CH-008 validates as a distinct frailty-renewal regime under the locked gate,
not merely as a higher-amplitude CH-007. It is admitted to a separately locked
2023-2026 retrospective evaluation. This remains development-validation
evidence and does not yet alter the prospective candidate.
