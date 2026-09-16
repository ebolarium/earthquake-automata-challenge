# Prospective Database

## Current operational status

The non-claim three-region dry run covered target days 1--14 September 2026 and
is now in its seven-day catalog-settlement phase. Twelve calendar days were
scored; 1 and 2 September remain marked as missed after the early
`utc_timestamp` software failure. They were not backfilled and were not
imputed as zero IGPE. The reconstructed repository record is
`data/manifests/ch008-three-region-dry-run-activation-v1.json`; PostgreSQL
`prospective.forecast_artifacts` and the corresponding S3 objects remain the
authority for each artifact content hash.

This dry run does not activate the 365-day scientific claim. The formal
protocol is frozen in
`configs/prospective/ch008-three-region-prospective-v1.json` and is activated
by the ordinary daily command at the 23 September 2026 UTC issue cycle. A
database activation manifest is created only after all three first formal
forecasts are safely persisted; it is not pre-created or backfilled.

The production schedule runs at `00:05 UTC`:

```bash
python scripts/run_prospective_daily.py
```

No cron change is required for the formal launch. Before 23 September 2026 the
command runs `ch008-three-region-dry-run-v1`. At the 23 September issue time it
atomically activates `ch008-three-region-prospective-v1`, transfers the causal
22 September state byte-for-byte without refitting, advances it through the
ordinary daily path, and publishes the first formal forecast for 24 September
UTC. PostgreSQL rows and S3 objects remain separated by protocol and artifact
lane.

Activation fails closed if it is attempted after `00:15 UTC`, if any source
state is missing, or if the scheduled activation date was missed. It never
creates a retrospective formal forecast. After the formal publication is safe,
the same run collects the final dry-run settlement catalogs and completes any
remaining dry-run scores.

The prospective PostgreSQL database stores operational metadata and scores,
not forecast grids. Large catalog snapshots, forecast grids, and manifests are
stored as object artifacts; PostgreSQL records their keys and SHA-256 hashes.

## Migration

Install the prospective dependency and apply migrations with the private
Coolify connection URL:

```bash
pip install ".[prospective]"
DATABASE_URL='postgresql://...' python scripts/migrate_database.py
```

Applied migration checksums are recorded in
`prospective.schema_migrations`. Editing an applied migration is rejected; a
schema change must be a new numbered migration.

## Core records

- `model_versions`: frozen ETAS and CH-008 identities and hashes.
- `protocols` and `regions`: activation rules, catalog contracts, and regional
  normalization constants.
- `catalog_snapshots` and `catalog_event_versions`: as-observed input history.
- `model_states`: immutable ETAS-history and CH-008 latent-state checkpoints.
- `forecast_runs` and `forecast_artifacts`: issue-time runs and uploaded files.
- `daily_scores`: provisional and final ETAS-versus-CH-008 scores.
- `incidents`: missed runs, source outages, and operational deviations.

## Object storage

Forecast artifacts use a separate S3-compatible store. Configure the worker
with `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`, `S3_ACCESS_KEY_ID`,
`S3_SECRET_ACCESS_KEY`, and `S3_PREFIX`. Set `VERIFY_OBJECT_STORAGE=1` to run a
temporary write/read/delete integrity probe at startup. Set
`REQUIRE_OBJECT_STORAGE=1` to include prefix access in the worker health check.

## Catalog collection

The rolling collector preserves each raw FDSN response in object storage and
records the filtered event versions in PostgreSQL. Its default lookback is 30
days so recent catalog revisions remain observable:

```bash
python scripts/collect_prospective_catalogs.py
```

Use `--cutoff` for a reproducible manual run and `--region` to limit a smoke
test. An identical region/cutoff/content combination is idempotent; changed
provider content at the same cutoff is retained as a new snapshot version.

## Historical bootstrap

Before forecast generation, import each region's history from the
`auxiliary_start` frozen in its ETAS model. The cutoff is mandatory so an
interrupted run can be resumed against the same boundary:

```bash
python scripts/bootstrap_prospective_catalogs.py \
  --cutoff "2026-08-30T18:47:21.112951+00:00" \
  --region new-zealand-csep
```

The importer starts with UTC calendar-year requests. If an FDSN result limit is
reached, it bisects only that interval. Completed windows are skipped on rerun;
`--refresh` explicitly preserves a revised source response as another version.

After all regions finish, verify continuous temporal coverage, unique event
identities, database row counts, and S3 checksum metadata:

```bash
python scripts/verify_prospective_bootstrap.py \
  --cutoff "2026-08-30T18:47:21.112951+00:00"
```

## Initial model states

Migration `005_model_states.sql` records one deterministic checkpoint per
protocol, region, and UTC boundary. The checkpoint artifact is stored in S3;
PostgreSQL stores its object key, byte count, SHA-256, source snapshot IDs, and
manifest identity.

The initial boundary is the end of the locked California retrospective replay:
`2026-08-19T00:00:00Z`. Only events satisfying `origin_time < as_of` enter the
checkpoint. The catalog history hash is computed from that admitted event slice,
not from later events that happen to share the final bootstrap source object.

California uses the exact locked CH-008 terminal `age`, `exposure`, and `roots`
arrays. New Zealand and Chile reconstruct those arrays by a native full-history
replay. All three artifacts include the complete pre-boundary ETAS event history,
because ETAS has no smaller sufficient runtime state in this implementation.

After deploying the image that applies migration `005`, build New Zealand first
as a small production smoke test:

```bash
python scripts/build_prospective_initial_states.py \
  --as-of "2026-08-19T00:00:00+00:00" \
  --catalog-cutoff "2026-08-30T18:47:21.112951+00:00" \
  --region new-zealand-csep
```

Repeat with `--region chile-subduction` and `--region california-relm`. A rerun
with identical inputs is idempotent. If a checkpoint already exists with a
different state or artifact hash, the command fails instead of replacing it.

After all three states exist, verify their database records, canonical manifests,
S3 objects, catalog boundaries, model hashes, and latent-array contracts:

```bash
python scripts/verify_prospective_initial_states.py \
  --as-of "2026-08-19T00:00:00+00:00"
```

These are activation inputs, not backfilled forecasts, and do not count toward
the prospective claim. The next runtime stage advances them causally from the
checkpoint boundary to the first dry-run issue time before any target forecast
is persisted.

## Daily runtime contract

The pre-dry-run runtime is locked in
`configs/prospective/daily-runtime-v1.json`. Catalog collection is scheduled for
`00:05 UTC`; forecast publication must finish by `00:15 UTC`; each issue targets
the following UTC day. This leaves a minimum lead time of 1,425 minutes.

California retains the frozen 10,000-catalog native ETAS continuation with
analytical direct background roots. A full local M4 benchmark took 2.66 seconds
for one issue with 52,021 history events, so no simulation-count reduction is
needed. New Zealand and Chile use their locked sequential conditional ETAS
intensity adapters.

CH-008 does not change ETAS triggering, expected counts, or magnitudes. The
pre-target artifact fixes only its bounded, mass-preserving direct-background
redistribution. Consequently the paired compensator difference is exactly zero
and the primary score remains the event-wise conditional log-rate ratio used in
the locked retrospective evaluation.

## Bootstrap state advance

The verified initial states can be advanced only within the same fixed bootstrap
cutoff. The operation creates a new checkpoint and never replaces its parent.
Start with New Zealand:

```bash
python scripts/advance_prospective_bootstrap_states.py \
  --from-as-of "2026-08-19T00:00:00+00:00" \
  --to-as-of "2026-08-30T00:00:00+00:00" \
  --catalog-cutoff "2026-08-30T18:47:21.112951+00:00" \
  --region new-zealand-csep
```

Repeat for Chile and California. California uses exactly 10,000 ETAS continuation
catalogs on every advanced day containing observations; the command rejects a
lower simulation count. After all three complete, run the state verifier at the
new `as_of` boundary.

## Daily checkpoint and forecast publication

Migration `006_forecast_run_state.sql` binds every forecast run to the exact
model checkpoint used to create it. The daily publisher stores one grid, one
summary, and one manifest for ETAS and CH-008 in S3, then records all six object
hashes in PostgreSQL before marking the run `published`.

Run the following chain at `00:05 UTC`. The rolling advance derives yesterday's
and today's UTC boundaries from the clock, admits only events from the completed
day, and preserves the parent checkpoint rather than modifying it:

```bash
python scripts/run_prospective_daily.py
```

This command is the launch guard for
`configs/challenge/ch008-downtime-policy.json`. It runs each region in an
isolated worker, keeps the logical `00:05 UTC` cutoff fixed across retries, and
never retries a pre-publication stage beyond `00:15 UTC`. A publication failure
is permanently recorded as `missed`; a scoring failure for an already published
forecast remains recoverable and is recorded as `deferred`.

Publication is rejected after `00:15 UTC`, before the checkpoint boundary, or
when the 1,425-minute lead-time requirement is not met. A successful rerun for
an already published target returns `already_published`; conflicting checkpoint,
snapshot, or artifact identities fail closed.

California artifacts contain the complete one-day ETAS and CH-008 expected-count
grids for the following UTC day. New Zealand and Chile retain their exact
continuous-space ETAS triggering contract and publish the pre-target latent
direct-background maps changed by CH-008. Both model artifacts preserve total
mass, so their paired compensator difference remains zero.

## Daily scoring

The scorer runs after publication but only considers forecast targets whose UTC
window has already ended. Migration `007_daily_score_run.sql` links every score
to its immutable forecast run. The first rolling snapshot that fully covers the
target produces the `provisional` score. The first snapshot crossing the locked
seven-day settlement threshold produces the separate `final` score; neither row
is subsequently replaced.

California events are scored against the two published daily RELM grids. New
Zealand and Chile reconstruct the sequential ETAS conditional event intensity
from the forecast's frozen pre-lead-day state and events already observed inside
the target window, then add only the CH-008 background delta published before
the target. Event IDs, rates, log-rate gains, snapshot hash, and forecast hashes
are retained in the score metrics. Empty target days are valid and record zero
total gain with a null per-event mean.
