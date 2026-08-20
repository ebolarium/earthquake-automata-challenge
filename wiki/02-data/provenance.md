# Data Provenance

The source `earthquake.db` is an input snapshot, never a committed project
artifact. Its current contract is recorded in the reference manifest.

The database contains 5,086,795 earthquake rows over 1901-11-14 through
2026-08-19 and is approximately 1.5 GB. Copying it wholesale would also copy
application-specific tables and heterogeneous catalog history that are not
part of the ETAS experiment.

The local export therefore creates a new database containing only the region,
time, magnitude, status, and provenance fields required by the experiment. The
export opens the source with SQLite `mode=ro&immutable=1`, verifies its hash
before and after extraction, and is not allowed to alter it.

Every export report must include source and destination checksums, SQL or tool
version, row counts, exclusions, and observed bounds.

## Local California Snapshot V1

The 2026-08-20 export selected active events with non-null magnitude that
intersect the locked EarthquakeNPP California polygon. No magnitude threshold
was applied. The selection reduced 82,809 bounding-box candidates to 80,140
polygon events; 2,669 candidates were outside the polygon.

Only 348 exported events carry complete FDSN payload hashes. The remaining
79,792 legacy rows retain stable fallback identity while unavailable payload
hashes and retrieval timestamps remain null. This limitation is inherited from
the source snapshot and must not be interpreted as full raw-payload provenance.

Two independent exports in the locked Python 3.11 / SQLite 3.40.1 environment
produced the same output SHA-256:
`0f05fcdbf1315a23ace109d1248848ca0cff9dde8cfdd6299bde128116a4d399`.

Full counts and bounds are recorded in
`data/manifests/local-california-catalog-v1.json`.
