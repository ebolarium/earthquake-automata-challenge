# CH004-006: Locked Retrospective Test

## Question

Does the unchanged CH-004 candidate retain positive paired information gain
against frozen ETAS on the one-use 2023-01-01 through 2026-08-18 test?

## Lock Boundary

The model remains `ch004-marked-renewal-v1`, SHA-256
`57057b1c1bd9807993f491d16cc1c2c30bfb7ca86071f60b97cee7ef8dd837c8`.
The successful development-validation manifest is frozen at SHA-256
`f1ad4cc837ef15ca645c07209ae9d960ca5fa24e4fcb321a0ae334ae9d7fca5e`.
No model selection, parameter change, feature change, or threshold change is
allowed after this period is opened.

## Required Report

- Overall and annual primary IGPE.
- Fit-locked low-ETAS IGPE.
- `M >= 3.5` and `M >= 4.0` IGPE.
- 10,000-replicate 30-day and 90-day stationary bootstrap intervals.
- Exact ETAS count and magnitude preservation.

## Research-Win Rule

The challenge records a retrospective research win only if the 30-day 95%
bootstrap lower bound is greater than zero, the 90-day lower bound is
nonnegative, and every required diagnostic is reported. A win permits
prospective activation but is not a scientific ETAS-superiority claim.

## Status

Retrospective history completed; scoring protocol pre-registered and unopened.

The first history-construction preflight stopped before producing an artifact
or score because the existing monthly ETAS grid ended at 2023-01-01. The
missing 2023-2026 baseline period is now pre-registered with the unchanged ETAS
parameters, catalog, grid, seed, and 10,000 continuations per issue day. After
those shards are complete, their manifest hash must be added to the history
contract before history construction is retried.

The extension completed all 44 monthly shards and 1,326 issue days with 10,000
continuations per day. The canonical manifest SHA-256 is
`e149a92fd926d16dbb01bfccefcf889a04c3a8018682841bcb95944418c570bf`.
All artifact hashes, shapes, positive rates, expected-count sums, and global day
continuity passed the verifier. The history contract binds both the original
2007-2022 manifest and this contiguous 2023-2026 extension separately.

The resulting replay contains 7,170 issue days and 21,326 in-grid events from
2007-01-01 onward. The locked 1,326-day scoring slice contains 3,995 events.
The ignored NPZ SHA-256 is
`56053ca2f9d853785cd78b62a2df720974c6d894e4c82a0e65090cd9b1d9b28a`.
