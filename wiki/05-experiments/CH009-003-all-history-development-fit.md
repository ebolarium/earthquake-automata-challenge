# CH009-003: All-History Development Fit

## Question

Can phase-coherent hazard debt add robust, mechanism-specific information to
the frozen CH-008 forecast across the full historical development record?

## Disclosure

CH-009 was designed after aggregate CH-008 results through 2026-08-18 were
opened. The 2014-2026 scoring period is therefore an all-history development
benchmark. It is not validation, a locked retrospective test, or prospective
evidence. No historical split will be relabeled as unseen after this run.

## Search

- Exact CH-008 control plus 64 scrambled five-dimensional Sobol candidates.
- Seed `20260827`.
- CH-008 renewal, frailty, background-mixture, ETAS, geometry, and loading
  parameters remain fixed.
- Only fast/slow frailty scale, acceleration floor, coherence mix, and phase
  weight vary.
- Selection maximizes mean annual paired delta minus its annual standard
  deviation, always relative to the exact CH-008 control on the same events.

## Admission Gate

A nonzero candidate must have positive mean and annual-robust paired IGPE delta
over CH-008; nonnegative low-ETAS and `M >= 3.5` deltas; positive annual delta
in at least 10 of 13 calendar years; no annual delta below `-0.002`; and active
phase evidence on at least 1% of event-bearing issue days.

The selected candidate is then frozen while three counterfactuals are scored:

- acceleration replaced by a neutral factor;
- graph coherence replaced by local debt;
- frailty level replaced by a neutral factor.

Full CH-009 must exceed every ablation in mean paired delta. Otherwise the
proposed four-way synthesis mechanism is rejected even if total performance is
positive.

## Status

Stopped and not promoted. The first execution stopped during control preflight
because inactive fault sections have zero-sum transition rows. It produced no
model, manifest, candidate table, or event score. A committed v2 wrapper now
adds neutral self-loops only to inactive rows; active graph transitions and all
admission rules remain unchanged. Development was then explicitly stopped
before any CH-009 catalog score was read. CH-008 remains the unchanged leading
challenger and no CH-009 output enters the prospective pipeline.

## Outputs

- `models/ch009-phase-coherent-hazard-debt-v1.json`
- `data/manifests/ch009-phase-coherent-hazard-debt-v1-fit.json`
- ignored candidate table under `artifacts/`
