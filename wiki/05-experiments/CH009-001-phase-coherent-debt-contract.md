# CH009-001: Phase-Coherent Hazard-Debt Contract

## Question

Can a joint fault-network state add information beyond CH-008 when renewal
overdue, positive frailty, fast frailty acceleration, and neighboring-section
support occur together?

## Synthesis Feature

For section `s`, two causal EWMAs track issue-time log frailty. Their positive
fast-minus-slow difference is the acceleration `a_s`. The local debt is

```text
d_s = cuberoot(overdue_s * positive_frailty_s * a_s)
```

and graph-supported debt is

```text
c_s = sqrt(d_s * sum_j(P_sj * d_j)).
```

The final feature blends local and coherent debt. It is added to the unchanged
CH-008 section score before the existing loading-branch consensus and bounded
background redistribution. ETAS triggering, total direct-background mass,
CH-008's mixture fraction, and its maximum log tilt remain unchanged.

The geometric means are deliberate: one extreme input cannot compensate for a
missing mechanism, and full graph coherence rejects isolated spikes.

## Invariants

Synthetic tests establish that:

- a rising frailty state makes the fast mean lead the slow mean;
- constant frailty converges to zero acceleration;
- missing overdue, frailty, or acceleration makes the feature exactly zero;
- full coherence rejects an isolated section but retains a coherent pair;
- invalid fast/slow time ordering is rejected;
- zero phase weight will reproduce CH-008 exactly in the later evaluator.

## Leakage Boundary

No catalog score is computed in this stage. Every forecast must be formed
before same-day event assimilation. Because CH-009 was conceived after CH-008
aggregate results through 2026-08-18 were opened, all existing historical
splits are development benchmarks for this family, not pristine unseen tests.
Only forecasts persisted after a future model freeze can supply new scientific
evidence.

## Next Step

Completed in CH009-002: the daily evaluator gives exact CH-008 equality at zero
phase weight and preserves forecast-before-assimilation ordering. The next step
is a limited, pre-registered fit with the required acceleration, coherence, and
frailty-level ablations before any CH-009 catalog score is read.
