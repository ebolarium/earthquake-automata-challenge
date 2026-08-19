# Reference Alignment Protocol

## Reference Contract

The committed manifest locks EarthquakeNPP, the historical ETAS compatibility
commit, dataset artifacts, configuration, expected parameters, and expected
likelihood scores.

EarthquakeNPP installed its ETAS fork from an unpinned `main` branch. The
compatibility commit in this project is inferred as the final fork commit
before the checked-in ComCat_25 output timestamp. This inference must be
verified by executing the reference experiment; it must not be treated as
confirmed merely because the dates are consistent.

EarthquakeNPP also records Python 3.11.11 even though the inferred ETAS
compatibility commit declares Python 3.12 or newer. The isolated reference
image follows the recorded runtime and bypasses only this metadata check. A
successful numerical reproduction is required before this environment can be
called aligned.

The image platform is fixed to `linux/amd64`, matching EarthquakeNPP's
recorded `linux-64` environment. ARM hosts run the same image through Docker
emulation rather than compiling unavailable ARM variants of pinned packages.

The inferred ETAS commit imports SeismoStats during evaluation without
declaring that dependency in its package metadata. The manifest therefore
locks the SeismoStats commit named by the historical ETAS requirements file.
This is part of the reproducibility contract, not challenge-native model code.

## Gates

1. Input artifact hashes match exactly.
2. Catalog target-event count equals 55,442.
3. Estimated beta and all nine fitted parameters match the expected output
   within recorded numerical tolerances.
4. ETAS and Poisson temporal, spatial, and normalized likelihood components
   match within recorded numerical tolerances.
5. Repeated inversion from the same initialization is stable.
6. Fixed-seed simulation summaries pass distributional tolerances.
7. Native kernel integrals and likelihood terms match independent numerical
   integration tests.

Exact tolerances will be established from deterministic reruns on the pinned
reference environment before native alignment begins.

The first likelihood replay established an absolute tolerance of `1e-10` for
the six ETAS and Poisson likelihood components. Four components matched
exactly; ETAS NLL and TLL differed by approximately `2.4e-11` under AMD64
emulation. Parameter and simulation tolerances remain pending.

The fresh inversion established absolute tolerances of `5e-5` for the nine
transformed ETAS parameters, `1e-12` for beta, `0.01` for `n_hat`, and `2e-6`
for likelihood components evaluated from freshly fitted parameters. The run
matched the reference iteration count and target-event count exactly.

## Failure Policy

Reference mismatches are findings. We diagnose package drift, platform
differences, optimizer tolerances, or undocumented state; we do not edit the
expected values or reference source merely to make the check pass.
