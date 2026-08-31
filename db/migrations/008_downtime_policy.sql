CREATE TABLE prospective.region_day_operations (
    protocol_id text NOT NULL REFERENCES prospective.protocols(protocol_id),
    region_id text NOT NULL REFERENCES prospective.regions(region_id),
    issue_date date NOT NULL,
    target_date date NOT NULL,
    logical_issue_time timestamptz NOT NULL,
    publication_issue_time timestamptz,
    publication_status text NOT NULL DEFAULT 'pending'
        CHECK (publication_status IN ('pending', 'published', 'missed')),
    scoring_status text NOT NULL DEFAULT 'pending'
        CHECK (scoring_status IN ('pending', 'scored', 'deferred')),
    failed_stage text,
    publication_attempt_count integer NOT NULL DEFAULT 0
        CHECK (publication_attempt_count >= 0),
    scoring_attempt_count integer NOT NULL DEFAULT 0
        CHECK (scoring_attempt_count >= 0),
    failure_cause text,
    affected_event_count integer CHECK (affected_event_count >= 0),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (protocol_id, region_id, issue_date)
);

CREATE TABLE prospective.region_operational_status (
    protocol_id text NOT NULL REFERENCES prospective.protocols(protocol_id),
    region_id text NOT NULL REFERENCES prospective.regions(region_id),
    primary_eligible boolean NOT NULL DEFAULT true,
    missed_region_days integer NOT NULL DEFAULT 0 CHECK (missed_region_days >= 0),
    consecutive_missed_days integer NOT NULL DEFAULT 0
        CHECK (consecutive_missed_days >= 0),
    invalidated_at timestamptz,
    invalidation_reason text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (protocol_id, region_id),
    CHECK (primary_eligible OR invalidated_at IS NOT NULL)
);

CREATE INDEX region_day_operations_status_idx
    ON prospective.region_day_operations
        (protocol_id, region_id, publication_status, issue_date);
