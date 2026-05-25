-- Alerts & Subscriptions schema additions

CREATE TABLE IF NOT EXISTS alerts_subscription (
    subscription_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',
    type VARCHAR(50) NOT NULL,
    subject_id VARCHAR(100), -- artist_id, label_id, style/genre name, etc.
    criteria_json JSONB DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_subscription_user_type ON alerts_subscription(user_id, type);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',
    type VARCHAR(50) NOT NULL,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    seen BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_seen ON notifications(user_id, seen);

CREATE TABLE IF NOT EXISTS watchlist (
    discogs_release_id INTEGER NOT NULL,
    user_id VARCHAR(100) NOT NULL DEFAULT 'default',
    target_price DECIMAL(10,2),
    target_grade VARCHAR(20),
    region VARCHAR(50),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (discogs_release_id, user_id)
);

-- Optional: embeddings table for future recs
CREATE TABLE IF NOT EXISTS embeddings (
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    vector BYTEA,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (entity_type, entity_id)
);
