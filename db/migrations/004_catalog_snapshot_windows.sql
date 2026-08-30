ALTER TABLE prospective.catalog_snapshots
    ADD COLUMN source_start_at timestamptz,
    ADD COLUMN collection_kind text NOT NULL DEFAULT 'rolling'
        CHECK (collection_kind IN ('rolling', 'bootstrap'));

UPDATE prospective.catalog_snapshots
SET source_start_at = (source_request -> 'window' ->> 0)::timestamptz
WHERE source_start_at IS NULL;

ALTER TABLE prospective.catalog_snapshots
    ALTER COLUMN source_start_at SET NOT NULL,
    ADD CHECK (source_start_at < source_cutoff_at);

CREATE INDEX catalog_snapshots_window_idx
    ON prospective.catalog_snapshots
        (region_id, collection_kind, source_start_at, source_cutoff_at);
