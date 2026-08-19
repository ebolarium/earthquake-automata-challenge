# ADR-002: Export a Clean Catalog Instead of Copying the Core Database

- Status: Accepted
- Date: 2026-08-19

## Decision

Do not copy the complete `earthquake.db` into the challenge project. Generate a
new immutable SQLite snapshot containing only earthquake observations and
provenance required by the locked experiment.

## Rationale

The source database is approximately 1.5 GB and contains application-specific
state unrelated to ETAS. A filtered export reduces coupling, makes the catalog
contract explicit, and prevents accidental writes to production-derived data.

## Consequences

Database files remain untracked. Reproducibility is provided through the export
script, source and output hashes, schema, and manifest.

