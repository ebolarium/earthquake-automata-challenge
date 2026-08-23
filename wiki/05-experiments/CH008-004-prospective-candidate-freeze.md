# CH008-004: Prospective Candidate Freeze

## Decision

CH-008 is frozen as the immutable prospective control candidate. Its model,
fit, validation, retrospective evidence, and runtime feature modules are locked
by SHA-256 in `data/manifests/ch008-prospective-candidate-v1.json`.

No CH-009 experiment may alter this artifact or replace it under the CH-008
identifier. A modified implementation is a new model version and has no claim
on CH-008's historical evidence.

## Activation Boundary

This freeze does not claim that prospective collection has started. Activation
requires a separate commit before the first target window that records:

- the first daily issue timestamp;
- the persisted forecast artifact hash;
- the exact collector and catalog-ingestion versions;
- the unchanged model and runtime hashes.

Forecast backfill is prohibited. Only predictions persisted before their target
catalog window count toward the 365-day and 500-event prospective gate.

## Status

Frozen and pending activation infrastructure. Historical fit, validation, and
retrospective scores cannot change after this point.
