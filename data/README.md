# Local Data

Catalog databases and downloaded reference datasets belong here and must not be
committed. Only manifests under `data/manifests/` are tracked.

Each generated snapshot must have:

- an immutable source checksum;
- an exact extraction query or script;
- source and output row counts;
- minimum and maximum origin times and magnitudes;
- a schema version;
- provenance fields for every event where available;
- an output SHA-256 checksum.

The first local catalog is `data/local/california-earthquakes-v1.sqlite`. It is
a California-only, no-`Mc` snapshot with 80,140 events. The database remains
ignored; its committed contract is
`data/manifests/local-california-catalog-v1.json`.
