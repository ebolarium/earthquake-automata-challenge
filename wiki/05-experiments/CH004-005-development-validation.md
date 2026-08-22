# CH004-005: Locked Development Validation

## Question

Does the fit-locked CH-004 candidate generalize to 2019-2022 while retaining
positive low-ETAS performance and acceptable uncertainty?

## Lock Boundary

The selected model was committed as `models/ch004-marked-renewal-v1.json` with
SHA-256 `57057b1c1bd9807993f491d16cc1c2c30bfb7ca86071f60b97cee7ef8dd837c8`
before validation history was opened. No parameter, feature, threshold, or model
selection rule may change in this experiment.

The validation history covers state evolution from 2007-01-01, scores only
2019-01-01 through 2022-12-31, and cannot read the 2023 onward locked
retrospective period.

## Required Report

- Overall and annual IGPE.
- Fit-locked low-ETAS IGPE.
- `M >= 3.5` and `M >= 4.0` IGPE.
- 30-day and 90-day stationary block-bootstrap intervals.
- Exact ETAS count preservation and active issue-day diagnostics.

## Status

Model locked; validation-history construction pre-registered and unbuilt.
