# Catalog Contract

Every event used by the project must have a stable identifier, UTC origin time,
latitude, longitude, magnitude, and source provenance. Depth is retained when
available but is not silently substituted into a two-dimensional ETAS model.

## Required Fields

```text
event_id
source_catalog
source_event_id
origin_time_utc
latitude
longitude
depth_km
magnitude
event_type
source_updated_at
source_retrieved_at
source_payload_hash
is_catalog_earthquake
excluded_reason
```

## Completeness

Magnitude completeness is an experiment parameter, not a property inferred
from the minimum magnitude in a database. Each experiment records its region,
time windows, `Mc`, magnitude bin width, and any space-time variation in
completeness.

## Time Boundary

Forecast issue time is exclusive. An event at or after the issue time cannot
affect that forecast. UTC timestamps, not date-only values, are required for
ETAS.

