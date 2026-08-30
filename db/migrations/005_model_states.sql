CREATE TABLE prospective.model_states (
    state_id char(64) PRIMARY KEY CHECK (state_id ~ '^[0-9a-f]{64}$'),
    protocol_id text NOT NULL REFERENCES prospective.protocols(protocol_id),
    region_id text NOT NULL REFERENCES prospective.regions(region_id),
    as_of timestamptz NOT NULL,
    source_catalog_cutoff timestamptz NOT NULL,
    source_snapshot_ids bigint[] NOT NULL,
    baseline_model_id text NOT NULL REFERENCES prospective.model_versions(model_id),
    challenger_model_id text NOT NULL REFERENCES prospective.model_versions(model_id),
    artifact_key text NOT NULL UNIQUE,
    artifact_sha256 char(64) NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    artifact_bytes bigint NOT NULL CHECK (artifact_bytes > 0),
    manifest_key text NOT NULL UNIQUE,
    manifest_sha256 char(64) NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (protocol_id, region_id, as_of),
    CHECK (cardinality(source_snapshot_ids) > 0),
    CHECK (as_of <= source_catalog_cutoff)
);

CREATE INDEX model_states_region_as_of_idx
    ON prospective.model_states (region_id, as_of DESC);
