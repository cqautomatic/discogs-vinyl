-- =====================================================================================
-- Migration 002: New releases feed table
-- =====================================================================================
-- Idempotent — safe to run multiple times.
-- =====================================================================================

SET search_path TO collection_data, public;

CREATE TABLE IF NOT EXISTS new_releases_feed (
    id                 SERIAL PRIMARY KEY,
    discogs_release_id INTEGER NOT NULL UNIQUE,
    master_id          INTEGER,
    title              TEXT,
    artist             TEXT,
    year               INTEGER,
    label              TEXT,
    format             TEXT,
    genres             JSONB,
    styles             JSONB,
    country            TEXT,
    thumb              TEXT,
    source             TEXT DEFAULT 'discogs_api',
    discovered_at      TIMESTAMPTZ DEFAULT NOW(),
    dismissed_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_nrf_artist     ON new_releases_feed(artist);
CREATE INDEX IF NOT EXISTS idx_nrf_discovered ON new_releases_feed(discovered_at DESC);
