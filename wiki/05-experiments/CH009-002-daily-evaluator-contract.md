# CH009-002: Daily Evaluator Contract

## Question

Can phase-coherent hazard debt be inserted into CH-008 without changing its
control path or allowing same-day catalog leakage?

## Implementation

The evaluator reproduces CH-008's renewal age, discounted Gamma-Poisson
frailty, loading-branch projection, consensus, and bounded background mixture.
It adds only the CH-009 section interaction before branch projection.

Fast and slow frailty means are updated once per issue day from the frailty
posterior available at that issue. The forecast is then produced. Same-day
events update renewal and frailty state only after issuance and can first affect
a later issue.

Sparse CH-008 graph transitions are materialized once when the evaluator is
constructed. The frozen CH009-001 feature module remains byte-for-byte
unchanged, and no dense graph conversion occurs inside the daily loop.

## Synthetic Verification

- `phase_weight = 0` produces event-rate and event-gain arrays exactly equal to
  `FrailtyRenewalFitEvaluator`, not merely numerically close.
- Events assigned to two connected sections cannot alter their own day's
  forecast.
- After the causal fast trend overtakes the slow trend, coherent nonuniform
  debt changes a later forecast.
- The evaluator reports phase-active issue days separately from ordinary
  CH-008 active days.

## Boundary

Only synthetic arrays were evaluated. No historical catalog replay or CH-009
score has been computed. Existing outcomes through 2026-08-18 remain disclosed
development information, not an unseen test for this family.

## Next Step

Pre-register a limited historical development fit. It must include the exact
CH-008 control and the acceleration-removed, coherence-removed, and
frailty-level-removed ablations before the first CH-009 catalog score is read.
