# CH003-001: Residual-Emergence Component Contract

## Question

Can an ETAS-compensated fault-network signal remain exactly neutral without
evidence, require coherent excess before activation, and bound forecast damage?

## Implemented Components

- One-sided decayed CUSUM of observed posterior root mass minus expected ETAS
  background mass.
- Poisson-compensator variance stabilization.
- Local-plus-neighbor fault-graph coherence gate.
- Loading-branch consensus shrinkage.
- Mass-preserving bounded mixture of ETAS direct background and emergence tilt.

## Invariants

Tests establish that zero evidence reproduces ETAS background exactly, total
background mass is preserved, a 10% mixture leaves at least 90% of every cell's
ETAS background rate, isolated section spikes fail graph coherence, and a
minority particle signal fails consensus.

## Boundary

Only synthetic arrays were used. No catalog objective, development-validation
score, or locked-retrospective result was evaluated.

## Next Step

CH003-002 will build a daily leakage-free section compensator. It must verify
that posterior event-root mass and expected analytical background mass use the
same branch-aware geometry before any CH-003 candidate fit is allowed.
