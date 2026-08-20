# Local California Catalog V1

## Purpose

Provide the immutable local event input for leakage-free replay without copying
application tables or runtime state from `earthquake.db`.

## Selection

- Source SHA-256:
  `8d7a4faf6082f42490c48979881b7017a7d7d05a778a5062f411e64fc520d3d7`.
- `is_catalog_earthquake = 1`.
- Magnitude is not null.
- Point intersects the locked EarthquakeNPP California polygon.
- Polygon boundary is included.
- No `Mc` filter.

## Result

| Property | Value |
| --- | ---: |
| Source rows | 5,086,795 |
| Active rows with magnitude | 5,078,585 |
| California bounding-box candidates | 82,809 |
| Outside polygon | 2,669 |
| Exported rows | 80,140 |
| Rows at `M >= 2.5` | 56,865 |
| First origin | 1906-04-18T13:12:26.300000Z |
| Last origin | 2026-08-19T07:31:35.970000Z |
| Magnitude range | 0.2 to 7.9 |
| Output size | 32,157,696 bytes |

SQLite `integrity_check` returned `ok`. All project event IDs and normalized
source identity pairs are unique. The exported database contains only
`catalog_events` and `catalog_metadata`.

An independent Shapely `Polygon.intersects` check selected the same 80,140
source row IDs, with zero missing and zero unexpected events.

## Reproduction

```bash
docker run --rm --platform linux/amd64 \
  -v "$PWD:/workspace" \
  -v "$PWD/../earthquake.db:/source/earthquake.db:ro" \
  -w /workspace -e PYTHONPATH=src etas-challenge-reference \
  python scripts/export_clean_catalog.py --source /source/earthquake.db
```

The command writes the ignored database to
`data/local/california-earthquakes-v1.sqlite` and the tracked manifest to
`data/manifests/local-california-catalog-v1.json`. It refuses a source whose
hash differs from the locked snapshot.

## Limitation

Most historical source rows predate payload-level provenance. Stable fallback
IDs preserve lineage to the source row, but they do not reconstruct missing raw
responses. Prospective ingestion must preserve full source payload hashes.
