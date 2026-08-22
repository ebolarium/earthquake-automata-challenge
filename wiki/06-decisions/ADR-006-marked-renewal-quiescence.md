# ADR-006: Marked Renewal Quiescence

## Status

Accepted as the CH-004 component contract. Development validation and the
one-use locked retrospective passed; prospective activation is admitted.

## Context

CH-003 found that positive ETAS residual clusters occasionally improved mean
fit score but never passed annual robustness and always harmed low-ETAS events.
The complementary hypothesis is negative space: a fault neighborhood may become
more informative when ETAS expected independent roots but none arrived.

Raw elapsed days are not comparable between high- and low-rate faults. CH-004
therefore measures age in expected ETAS direct-background reset hazard. Small
earthquakes cannot be treated as full fault ruptures, while using only large
events would leave too few fit observations. A smooth magnitude mark supplies a
bounded compromise.

## Decision

For section `s`, define the reset mark

```text
w(M) = min(1, 10^(gamma * (M - M_full)))
```

and integrate `E_GR[w(M)]` analytically under the frozen Gutenberg-Richter beta.
The daily clock update after the issue forecast is

```text
H_aged = H_s(t) + lambda_background,s * E_GR[w(M)]
H_s(t+1) = H_aged * exp(-sum_event posterior_root * fault_weight * w(M))
```

`H` is an expected normalized hazard-age proxy, not physical stress or elapsed
time since a known characteristic rupture. A Brownian-passage-time distribution
maps `H` to an overdue hazard score, retaining only positive log hazard above a
unit-rate memoryless baseline.

The score may redistribute at most 10% of ETAS direct background. ETAS
triggering and total expected daily count remain unchanged.

## Warmup and Leakage

The clock starts at zero on 2007-01-01 and is warmed without scoring through
2014-01-06. UCERF3 became available in 2014; at that date, using the published
fault geometry to map already-known historical catalog events is allowed for
forecasts issued afterward. The finite warmup cannot reconstruct a full seismic
cycle and must be reported as a limitation.

Every day is scored before its events reset the clock. The fit-locked CH-004
candidate passed 2019-2022 development validation with positive overall,
annual, low-ETAS, and bootstrap results. The locked retrospective split was
kept closed until its one-use evaluation. The unchanged candidate subsequently
passed that evaluation with positive 30-day and 90-day confidence lower bounds.

## Consequences

CH-004 restores the useful intuition behind stress accumulation without
asserting an unobserved initial stress map. It can still fail because small-event
marks may not proxy characteristic rupture renewal, the warmup is short, and
BPT theory does not directly justify this marked microseismic construction.
Those are tested assumptions, not hidden claims.
