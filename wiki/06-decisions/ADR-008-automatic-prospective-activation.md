# ADR-008: Automatic prospective activation

## Status

Accepted and frozen before formal launch.

## Decision

The formal CH-008 test uses the distinct protocol identity
`ch008-three-region-prospective-v1`. It activates during the 23 September 2026
UTC issue cycle and its first scored target is 24 September 2026 UTC. The test
lasts 365 fixed calendar days and requires at least 500 pooled target events.

The dry-run protocol, scores, incidents, states, and artifacts are preserved.
The activation copies the latest causal 22 September state into the formal
protocol byte-for-byte, records its source identity, and performs no fit or
parameter selection. Formal catalog snapshots, states, forecasts, incidents,
and scores use protocol-scoped database identities and the separate
`prospective/v1/prospective` object-storage lane.

The existing daily cron command is the only launcher. Activation is allowed
only on the frozen date and before the frozen publication deadline. Missing the
date, deadline, or a required source state causes a closed failure; formal
forecasts are never backfilled.

## Consequences

The dashboard, maps, AI-readable evaluation, and newsletter resolve the active
protocol from PostgreSQL, so they switch without a service restart. Dry-run
evidence remains inspectable but cannot enter the formal prospective claim.
