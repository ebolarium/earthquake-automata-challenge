# Prospective Database

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

These are activation inputs, not backfilled forecasts, and do not count toward
the prospective claim. The next runtime stage advances them causally from the
checkpoint boundary to the first dry-run issue time before any target forecast
is persisted.
