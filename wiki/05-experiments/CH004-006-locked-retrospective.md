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

History construction pre-registered; locked retrospective scores unopened.
