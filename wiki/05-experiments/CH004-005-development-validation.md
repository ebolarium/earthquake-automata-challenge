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

## Command

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" -w /workspace \
  etas-challenge-reference python scripts/evaluate_ch004_validation.py
```

## Admission Rule

Open the locked retrospective stage only if overall IGPE is positive and the
fit-locked low-ETAS stratum IGPE is nonnegative. Bootstrap intervals and annual
scores are reported as uncertainty and stability diagnostics; they are not
used to alter the locked model or this admission rule.

## Status

Completed. Admitted to locked retrospective evaluation, which remains unopened.

The frozen replay contains 5,844 issue days and 17,331 events. The
2019-2022 scoring slice contains 1,461 days and 5,204 events. The generated
NPZ remains local; its committed manifest records SHA-256
`c818a34fe5c94a8c34e58ff01498b6556e1d46640712cb35f0220f455ff1eddc`.

## Result

The locked candidate achieved overall IGPE `+0.000244` over 5,204 events
(`1.000244x` ETAS event probability). All four annual scores were positive.
The 95% stationary-bootstrap intervals were:

- 30-day blocks: `[+0.000093, +0.000414]`.
- 90-day blocks: `[+0.000087, +0.000433]`.

The fit-locked low-ETAS stratum achieved IGPE `+0.001125` over 956 events.
`M >= 3.5` and `M >= 4.0` achieved `+0.000306` and `+0.000372`, respectively;
their bootstrap lower bounds were also positive. ETAS daily counts and
magnitude forecasts were preserved exactly by construction.

This is positive development-validation evidence, not a final ETAS-superiority
claim. The model remains unchanged and the 2023 onward locked retrospective
has not been read.
