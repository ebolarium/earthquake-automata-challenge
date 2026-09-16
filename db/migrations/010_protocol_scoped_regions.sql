ALTER TABLE prospective.catalog_snapshots
    ADD COLUMN protocol_id text;

UPDATE prospective.catalog_snapshots snapshot
SET protocol_id = region.protocol_id
FROM prospective.regions region
WHERE snapshot.region_id = region.region_id;

ALTER TABLE prospective.catalog_snapshots
    ALTER COLUMN protocol_id SET NOT NULL,
    ADD CONSTRAINT catalog_snapshots_protocol_id_fkey
        FOREIGN KEY (protocol_id) REFERENCES prospective.protocols(protocol_id);

ALTER TABLE prospective.catalog_snapshots DROP CONSTRAINT catalog_snapshots_region_id_fkey;
ALTER TABLE prospective.catalog_snapshots DROP CONSTRAINT catalog_snapshots_region_id_captured_at_key;
ALTER TABLE prospective.forecast_runs DROP CONSTRAINT forecast_runs_region_id_fkey;
ALTER TABLE prospective.daily_scores DROP CONSTRAINT daily_scores_region_id_fkey;
ALTER TABLE prospective.incidents DROP CONSTRAINT incidents_region_id_fkey;
ALTER TABLE prospective.model_states DROP CONSTRAINT model_states_region_id_fkey;
ALTER TABLE prospective.region_day_operations DROP CONSTRAINT region_day_operations_region_id_fkey;
ALTER TABLE prospective.region_operational_status DROP CONSTRAINT region_operational_status_region_id_fkey;

ALTER TABLE prospective.regions DROP CONSTRAINT regions_pkey;
ALTER TABLE prospective.regions
    ADD PRIMARY KEY (protocol_id, region_id);

ALTER TABLE prospective.catalog_snapshots
    ADD CONSTRAINT catalog_snapshots_region_fkey
        FOREIGN KEY (protocol_id, region_id)
        REFERENCES prospective.regions(protocol_id, region_id);
ALTER TABLE prospective.forecast_runs
    ADD CONSTRAINT forecast_runs_region_fkey
        FOREIGN KEY (protocol_id, region_id)
        REFERENCES prospective.regions(protocol_id, region_id);
ALTER TABLE prospective.daily_scores
    ADD CONSTRAINT daily_scores_region_fkey
        FOREIGN KEY (protocol_id, region_id)
        REFERENCES prospective.regions(protocol_id, region_id);
ALTER TABLE prospective.incidents
    ADD CONSTRAINT incidents_region_fkey
        FOREIGN KEY (protocol_id, region_id)
        REFERENCES prospective.regions(protocol_id, region_id);
ALTER TABLE prospective.model_states
    ADD CONSTRAINT model_states_region_fkey
        FOREIGN KEY (protocol_id, region_id)
        REFERENCES prospective.regions(protocol_id, region_id);
ALTER TABLE prospective.region_day_operations
    ADD CONSTRAINT region_day_operations_region_fkey
        FOREIGN KEY (protocol_id, region_id)
        REFERENCES prospective.regions(protocol_id, region_id);
ALTER TABLE prospective.region_operational_status
    ADD CONSTRAINT region_operational_status_region_fkey
        FOREIGN KEY (protocol_id, region_id)
        REFERENCES prospective.regions(protocol_id, region_id);

DROP INDEX prospective.catalog_snapshots_identity_idx;
CREATE UNIQUE INDEX catalog_snapshots_identity_idx
    ON prospective.catalog_snapshots (protocol_id, snapshot_identity)
    WHERE snapshot_identity IS NOT NULL;

DROP INDEX prospective.catalog_snapshots_window_idx;
CREATE INDEX catalog_snapshots_window_idx
    ON prospective.catalog_snapshots
        (protocol_id, region_id, collection_kind, source_start_at, source_cutoff_at);

DROP INDEX prospective.catalog_snapshots_region_cutoff_idx;
CREATE INDEX catalog_snapshots_region_cutoff_idx
    ON prospective.catalog_snapshots
        (protocol_id, region_id, source_cutoff_at DESC);

ALTER TABLE prospective.catalog_snapshots
    ADD CONSTRAINT catalog_snapshots_protocol_region_captured_key
        UNIQUE (protocol_id, region_id, captured_at);
