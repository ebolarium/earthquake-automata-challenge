# ADR-004: Admit CH-002 Latent Fault Readiness

## Status

Accepted for pre-registration and data construction on 2026-08-22. No model
has been fitted and no validation outcome has been opened.

## Context

CH-001 improved mean development-validation information gain but harmed the
pre-registered low-ETAS subset. A second linear catalog residual would test the
same idea with different knobs. CH-002 instead asks whether slowly evolving
fault readiness contains information that ETAS triggering does not.

Absolute crustal stress, fault strength, and initial stress are not observed
well enough to initialize a deterministic physical ledger. The earlier
Earthquake Automata ledger is useful as a structural hypothesis, but its state
was dimensionless and its stress proxies were not calibrated Coulomb stress.
Its values and production artifacts are therefore not imported.

## Decision

CH-002 is a separate challenger family under the unchanged Challenge V1 split.
It decomposes the frozen daily ETAS grid as

```text
lambda_ETAS(i,t) = lambda_triggered(i,t) + lambda_background(i)
lambda_CH002(i,t) = lambda_triggered(i,t) + B * q(i,t)
q(i,t) proportional to lambda_background(i) * exp(beta * margin(i,t))
B = sum_i lambda_background(i)
```

Only the analytical direct-background component is redistributed. Triggered
events, including descendants of direct background roots, remain exactly as in
the frozen ETAS forecast. This preserves the ETAS daily expected count.

`margin` is a dimensionless latent criticality margin, conceptually stress
minus effective strength. It must not be reported as physical stress or MPa.
Its transition may use tectonic loading, rupture depletion, and directional
transfer, but the initial state and uncertain inputs must be represented by an
ensemble rather than one asserted true map.

Event assimilation is weighted by the frozen ETAS direct-background posterior
`lambda_background / lambda_ETAS`. Events already expected as ETAS aftershocks
therefore have less authority to alter the slow readiness field. Raw surprise
is retained as a diagnostic, not used alone as evidence of tectonic loading.

## Gates

- Freeze source provenance and issue-time availability before constructing any
  feature.
- Fit all parameters and initial-state hyperparameters on 2007-2018 only.
- Use 2019-2022 only for model selection; do not open the locked retrospective
  split during iteration.
- Primary metric remains paired IGPE against frozen ETAS with 30-day block
  bootstrap confidence intervals.
- Mandatory slices are low ETAS intensity, high ETAS intensity, `M >= 3.5`, and
  `M >= 4.0`.
- Report initial-state ensemble dispersion and ablations for loading, release,
  transfer, and event assimilation.
- Promotion requires positive overall evidence without material degradation on
  the low-ETAS subset. A retrospective win still requires a prospective gate.

## Consequences

CH-002 can fail independently without changing ETAS or CH-001. The first
implementation milestone is a provenance-qualified fault-section representation
and grid mapping, not model fitting. Complex graph neural networks are excluded
from the first candidate because the fit period provides too little independent
large-event evidence for their parameter count.
