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

## Failure Policy

Reference mismatches are findings. We diagnose package drift, platform
differences, optimizer tolerances, or undocumented state; we do not edit the
expected values or reference source merely to make the check pass.

