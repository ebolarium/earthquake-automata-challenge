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

CH-002 UCERF3 raw and clean fault files also remain ignored. Their committed
source and geometry contracts are
`data/manifests/ch002-ucerf3-fault-sections-v1.json` and
`data/manifests/ch002-ucerf3-relm-nearest-v1.json`.
The frozen CH-002 graph and initial-state ensemble are recorded in
`data/manifests/ch002-fault-graph-initial-state-v1.json`.
The CH-002 fit-only event/background-posterior input is recorded in
`data/manifests/ch002-fit-inputs-v1.json`.
