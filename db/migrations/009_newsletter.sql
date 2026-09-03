CREATE TABLE prospective.newsletter_subscribers (
    subscriber_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email text NOT NULL,
    locale text NOT NULL DEFAULT 'tr' CHECK (locale IN ('tr', 'en')),
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'unsubscribed')),
    confirmation_token_sha256 char(64) NOT NULL
        CHECK (confirmation_token_sha256 ~ '^[0-9a-f]{64}$'),
    subscribed_at timestamptz,
    unsubscribed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (email),
    CHECK (email = lower(email)),
    CHECK (status <> 'active' OR subscribed_at IS NOT NULL),
    CHECK (status <> 'unsubscribed' OR unsubscribed_at IS NOT NULL)
);

CREATE INDEX newsletter_subscribers_active_idx
    ON prospective.newsletter_subscribers (subscriber_id)
    WHERE status = 'active';

CREATE TABLE prospective.newsletter_deliveries (
    delivery_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subscriber_id bigint NOT NULL
        REFERENCES prospective.newsletter_subscribers(subscriber_id),
    report_date date NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'failed')),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    provider_message_id text,
    last_error text,
    sent_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (subscriber_id, report_date),
    CHECK (status <> 'sent' OR (provider_message_id IS NOT NULL AND sent_at IS NOT NULL))
);

CREATE INDEX newsletter_deliveries_report_idx
    ON prospective.newsletter_deliveries (report_date DESC, status);
