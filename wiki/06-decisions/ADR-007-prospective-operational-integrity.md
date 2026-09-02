# ADR-007: Prospective Operational Integrity

## Status

Accepted and frozen before the 365-day prospective launch.

## Context

The New Zealand and Chile adapter definitions and retrospective result artifacts
first appeared in the same commits. Their positive scores remain reproducible,
but Git history cannot prove that each adapter was frozen before its result was
read. Operational outages can also create informative missingness, particularly
when a large earthquake increases catalog-service load.

## Decision

New Zealand and Chile are permanently labeled exploratory external-geography
evidence, not confirmatory or pre-registered evidence. Future adapter freezes
must precede result generation in a separate commit, contain no declared result
paths, and have a server or third-party timestamp proof. The verifier is
`scripts/verify_adapter_freeze.py`.

The frozen downtime contract is
`configs/challenge/ch008-downtime-policy.json`. Each region and pipeline stage
gets at most three attempts, separated by 60 and 300 seconds, while retaining a
single logical catalog cutoff. A separate publication issue time is persisted
once after catalog/state completion and reused by publication retries. Forecast
publication after `00:15 UTC` is forbidden and cannot be backfilled.
Scoring of earlier, timely forecasts remains independent of the current day's
publication outcome and may recover after that publication deadline.

A forecast not published by the deadline is a missed region-day and is excluded
from both the primary-score numerator and event denominator. It is never imputed
as zero IGPE. A timely forecast whose scoring is temporarily unavailable is
deferred and later scored against its immutable artifacts; it is not a missed
day. No missing-at-random assumption is made.

A region becomes ineligible for primary promotion after 19 missed days out of
365 or seven consecutive missed days. The full three-region primary claim then
becomes inconclusive, while unaffected regional results continue as secondary
evidence. The calendar is not extended. Fewer than 500 pooled target events at
day 365 also yields an inconclusive, not failed, result.

## Consequences

The launch guard `scripts/run_prospective_daily.py` replaces the manual shell
chain. Migration `008_downtime_policy.sql` persists region-day outcomes and
irreversible invalidation. The dashboard exposes regional eligibility and the
pooled claim status. Operational exclusions remain visible and cannot silently
improve or dilute IGPE.
