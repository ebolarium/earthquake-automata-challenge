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

The first local catalog will be a California-only export created after the
published EarthquakeNPP dataset has been reproduced.

