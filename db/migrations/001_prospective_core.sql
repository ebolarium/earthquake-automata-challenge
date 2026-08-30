CREATE SCHEMA IF NOT EXISTS prospective;

CREATE TABLE prospective.model_versions (
    model_id text PRIMARY KEY,
    role text NOT NULL CHECK (role IN ('baseline', 'challenger')),
    source_commit char(40) NOT NULL,
    model_sha256 char(64) NOT NULL CHECK (model_sha256 ~ '^[0-9a-f]{64}$'),
    runtime_sha256 char(64) NOT NULL CHECK (runtime_sha256 ~ '^[0-9a-f]{64}$'),
    parameters jsonb NOT NULL,
    frozen_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE prospective.protocols (
    protocol_id text PRIMARY KEY,
    status text NOT NULL CHECK (status IN ('draft', 'dry_run', 'active', 'completed', 'aborted')),
    config jsonb NOT NULL,
    config_sha256 char(64) NOT NULL CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    planned_start timestamptz NOT NULL,
    planned_days integer NOT NULL CHECK (planned_days > 0),
    minimum_events integer NOT NULL CHECK (minimum_events > 0),
    activated_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (status <> 'active' OR activated_at IS NOT NULL)
);

CREATE TABLE prospective.regions (
    region_id text PRIMARY KEY,
    protocol_id text NOT NULL REFERENCES prospective.protocols(protocol_id),
    name text NOT NULL,
    catalog_source text NOT NULL,
    catalog_endpoint text NOT NULL,
    geometry jsonb NOT NULL,
    minimum_magnitude double precision NOT NULL,
    minimum_depth_km double precision NOT NULL DEFAULT 0,
    maximum_depth_km double precision,
    c_region double precision NOT NULL CHECK (c_region > 0),
    config_sha256 char(64) NOT NULL CHECK (config_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (maximum_depth_km IS NULL OR maximum_depth_km > minimum_depth_km)
);

CREATE TABLE prospective.catalog_snapshots (
    snapshot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    region_id text NOT NULL REFERENCES prospective.regions(region_id),
    captured_at timestamptz NOT NULL,
    source_cutoff_at timestamptz NOT NULL,
    source_request jsonb NOT NULL,
    artifact_key text NOT NULL UNIQUE,
    content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    event_count integer NOT NULL CHECK (event_count >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (region_id, captured_at)
);

CREATE TABLE prospective.catalog_event_versions (
    snapshot_id bigint NOT NULL REFERENCES prospective.catalog_snapshots(snapshot_id),
    source_event_id text NOT NULL,
    origin_time timestamptz NOT NULL,
    latitude double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    depth_km double precision NOT NULL,
    magnitude double precision NOT NULL,
    magnitude_type text,
    source_updated_at timestamptz,
    payload jsonb NOT NULL,
    PRIMARY KEY (snapshot_id, source_event_id)
);

CREATE TABLE prospective.forecast_runs (
    run_id text PRIMARY KEY,
    protocol_id text NOT NULL REFERENCES prospective.protocols(protocol_id),
    region_id text NOT NULL REFERENCES prospective.regions(region_id),
    input_snapshot_id bigint NOT NULL REFERENCES prospective.catalog_snapshots(snapshot_id),
    issue_time timestamptz NOT NULL,
    target_start timestamptz NOT NULL,
    target_end timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('running', 'published', 'failed', 'missed')),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    error_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (protocol_id, region_id, target_start),
    CHECK (target_end > target_start),
    CHECK (issue_time <= target_start),
    CHECK (status <> 'published' OR finished_at IS NOT NULL)
);

CREATE TABLE prospective.forecast_artifacts (
    artifact_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id text NOT NULL REFERENCES prospective.forecast_runs(run_id),
    model_id text NOT NULL REFERENCES prospective.model_versions(model_id),
    artifact_kind text NOT NULL CHECK (artifact_kind IN ('grid', 'manifest', 'summary')),
    object_key text NOT NULL UNIQUE,
    content_sha256 char(64) NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    byte_count bigint NOT NULL CHECK (byte_count > 0),
    uploaded_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (run_id, model_id, artifact_kind)
);

CREATE TABLE prospective.daily_scores (
    score_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    protocol_id text NOT NULL REFERENCES prospective.protocols(protocol_id),
    region_id text NOT NULL REFERENCES prospective.regions(region_id),
    target_date date NOT NULL,
    baseline_model_id text NOT NULL REFERENCES prospective.model_versions(model_id),
    challenger_model_id text NOT NULL REFERENCES prospective.model_versions(model_id),
    catalog_snapshot_id bigint NOT NULL REFERENCES prospective.catalog_snapshots(snapshot_id),
    score_revision text NOT NULL CHECK (score_revision IN ('provisional', 'final')),
    event_count integer NOT NULL CHECK (event_count >= 0),
    total_log_likelihood_gain double precision NOT NULL,
    mean_igpe double precision,
    metrics jsonb NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (
        protocol_id,
        region_id,
        target_date,
        baseline_model_id,
        challenger_model_id,
        score_revision
    ),
    CHECK (event_count > 0 OR mean_igpe IS NULL),
    CHECK (event_count = 0 OR mean_igpe IS NOT NULL)
);

CREATE TABLE prospective.incidents (
    incident_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    protocol_id text REFERENCES prospective.protocols(protocol_id),
    region_id text REFERENCES prospective.regions(region_id),
    run_id text REFERENCES prospective.forecast_runs(run_id),
    severity text NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    incident_type text NOT NULL,
    message text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at timestamptz NOT NULL,
    resolved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (resolved_at IS NULL OR resolved_at >= occurred_at)
);

CREATE INDEX catalog_snapshots_region_cutoff_idx
    ON prospective.catalog_snapshots (region_id, source_cutoff_at DESC);
CREATE INDEX catalog_events_origin_idx
    ON prospective.catalog_event_versions (origin_time);
CREATE INDEX forecast_runs_target_idx
    ON prospective.forecast_runs (target_start DESC, region_id);
CREATE INDEX daily_scores_target_idx
    ON prospective.daily_scores (target_date DESC, region_id);
CREATE INDEX incidents_open_idx
    ON prospective.incidents (occurred_at DESC)
    WHERE resolved_at IS NULL;
