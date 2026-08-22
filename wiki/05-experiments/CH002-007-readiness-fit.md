# CH002-007: Latent Readiness Fit

## Question

Can a latent fault-readiness state improve ETAS spatial allocation while
preserving the ETAS triggered component and each day's total expected count?

## Frozen Protocol

- Selection period: 2014-01-07 through 2017-12-31.
- Report-only fit holdout: 2018-01-01 through 2018-12-31.
- Sampler: 32-point scrambled Sobol sequence, seed `20260822`, plus the
  all-zero ETAS-equivalent control.
- Selection metric: information gain per earthquake (IGPE) against ETAS.
- Admission rule: the selection winner must also have positive 2018 holdout
  IGPE before development validation may be opened.
- Fit lock: commit `0474f1456f7392bb6614afb86a4754544dbbe717`.

The five fitted quantities were loading gain, background-weighted assimilation
gain, rupture-release gain, release magnitude exponent, and background-tilt
sensitivity. Bounds and all input hashes were frozen in
`configs/challenge/ch002-fit-v1.json` before objective evaluation.

## Execution

```text
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" -w /workspace \
  etas-challenge-reference python scripts/fit_ch002_readiness.py
```

The locked Python 3.11 environment evaluated 33 candidates. The zero candidate
reproduced ETAS at zero IGPE, providing an end-to-end numerical control.

## Result

| Quantity | Value |
| --- | ---: |
| Selection events | 3,225 |
| 2018 holdout events | 394 |
| Selected candidate | 14 |
| Selection IGPE | +0.00033510 |
| Selection relative factor | 1.000335 |
| 2018 holdout IGPE | -0.01157337 |
| 2018 holdout relative factor | 0.988493 |
| Development validation admitted | No |

Selected parameters:

| Parameter | Value |
| --- | ---: |
| Loading gain per year | 0.199766 |
| Assimilation gain | 1.829938 |
| Release gain | 0.261564 |
| Release magnitude exponent | 0.305939 |
| Background-tilt sensitivity | 0.176376 |

Using the informal scalar requested for the challenge, ETAS is `1.000` and the
selected CH-002 candidate is `0.9885` on the untouched 2018 fit holdout.

## Decision

The candidate is not admitted to 2019-2022 development validation. Its tiny
selection gain did not generalize to the pre-registered holdout, while stronger
readiness perturbations were generally much worse. This rejects the current
parameterization and broad gain ranges; it does not reject fault readiness as a
scientific hypothesis.

No validation or locked-retrospective score was read. The selected model and
fit manifest are committed; the ignored candidate table is integrity-bound by
its SHA-256 in the manifest.
