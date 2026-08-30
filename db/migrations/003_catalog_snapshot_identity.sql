ALTER TABLE prospective.protocols
    ALTER COLUMN planned_start DROP NOT NULL;

ALTER TABLE prospective.catalog_snapshots
    ADD COLUMN snapshot_identity char(64)
        CHECK (snapshot_identity ~ '^[0-9a-f]{64}$');

CREATE UNIQUE INDEX catalog_snapshots_identity_idx
    ON prospective.catalog_snapshots (snapshot_identity)
    WHERE snapshot_identity IS NOT NULL;
