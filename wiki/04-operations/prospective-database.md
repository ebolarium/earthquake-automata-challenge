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
