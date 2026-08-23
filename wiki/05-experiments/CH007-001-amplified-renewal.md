# CH007-001: Amplified Renewal

## Question

Does the stronger renewal amplitude exposed by the CH-006 fit ablation retain a
material advantage over CH-004 on 2019-2022 development validation?

## Origin and Honesty Boundary

CH-006 candidate 23 achieved `+0.003620` fit IGPE, but a fit-only mechanism
ablation found `+0.003622` with frailty disabled and approximately zero with
renewal disabled. The new latent frailty hypothesis therefore failed its first
mechanistic check. The useful candidate is a stronger CH-004 renewal forecast,
not evidence for inferred fault strength.

CH-007 fixes frailty weight to zero and retains candidate 23's renewal weight
and bounded background fraction without refitting. Its 2014-2018 ablation is
`14.22x` the CH-004 fit IGPE and positive in every year. No 2019 onward CH-007
forecast or score has been read.

## Pre-Registered Validation Gate

The locked model passes only if, on 2019-2022:

- overall IGPE is at least `2x` the unchanged CH-004 parent;
- low-ETAS IGPE is no worse than CH-004;
- every annual IGPE is positive;
- paired CH-007-minus-CH-004 30-day bootstrap lower bound is positive;
- paired 90-day lower bound is nonnegative.

The full CH-006 and frailty-only forecasts are fixed report-only ablations and
cannot replace CH-007 after validation is opened.

## Status

Pre-registered and unrun.
