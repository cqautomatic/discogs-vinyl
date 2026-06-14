-- =====================================================================================
-- Migration 001: Baseline Schema
-- =====================================================================================
-- Idempotent baseline schema for discogs_collection database.
-- Uses CREATE TABLE IF NOT EXISTS — never drops anything.
-- =====================================================================================

SET search_path TO collection_data, public;

-- Ensure schema and extensions exist
CREATE SCHEMA IF NOT EXISTS collection_data;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set search_path again after schema creation
SET search_path TO collection_data, public;

-- =====================================================================================
-- TABLES
-- =====================================================================================

CREATE TABLE IF NOT EXISTS collections (
    collection_id   TEXT PRIMARY KEY,
    user_id         INTEGER,
    username        TEXT,
    collection_name TEXT,
    total_items     INTEGER,
    last_updated    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS releases (
    release_id               TEXT PRIMARY KEY,
    discogs_id               INTEGER,
    title                    TEXT NOT NULL,
    artist                   TEXT,
    year                     INTEGER,
    label                    TEXT,
    catno                    TEXT,
    format                   TEXT,
    genres                   JSONB,
    styles                   JSONB,
    producers                JSONB,
    country                  TEXT,
    rating                   INTEGER DEFAULT 0,
    condition                TEXT,
    sleeve_condition         TEXT,
    notes                    TEXT,
    date_added               TIMESTAMP,
    copies_count             INTEGER DEFAULT 1,
    instance_ids             JSONB,
    community_have_count     INTEGER DEFAULT 0,
    community_want_count     INTEGER DEFAULT 0,
    community_average_rating DECIMAL(3,2) DEFAULT 0.0,
    community_rating_count   INTEGER DEFAULT 0,
    stats_last_updated       TIMESTAMP,
    marketplace_stats        JSONB,
    artwork_urls             JSONB,
    local_artwork_paths      JSONB,
    collection_id            TEXT,
    basic_information        JSONB,
    instance_id              INTEGER,
    folder_id                INTEGER,
    raw_data                 JSONB,
    last_updated             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS artists (
    artist_id           TEXT PRIMARY KEY,
    artist_name         TEXT,
    real_name           TEXT,
    profile             TEXT,
    discogs_artist_id   INTEGER,
    images              JSONB,
    urls                JSONB,
    members             JSONB,
    groups              JSONB,
    aliases             JSONB,
    raw_data            JSONB,
    discography         JSONB,
    discography_updated TIMESTAMP,
    last_updated        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS artist_discography (
    discography_id        TEXT PRIMARY KEY,
    artist_id             TEXT,
    discogs_artist_id     INTEGER,
    artist_name           TEXT,
    release_id            TEXT,
    discogs_release_id    INTEGER,
    title                 TEXT,
    year                  INTEGER,
    role                  TEXT,
    label                 TEXT,
    format                TEXT,
    country               TEXT,
    in_collection         BOOLEAN DEFAULT false,
    collection_release_id TEXT,
    raw_data              JSONB
);

CREATE TABLE IF NOT EXISTS labels (
    label_id     TEXT PRIMARY KEY,
    name         TEXT,
    discogs_id   INTEGER,
    profile      TEXT,
    parent_label TEXT,
    urls         JSONB,
    raw_data     JSONB
);

CREATE TABLE IF NOT EXISTS tracks (
    track_id       TEXT PRIMARY KEY,
    release_id     TEXT REFERENCES releases(release_id) ON DELETE CASCADE,
    track_number   TEXT,
    title          TEXT,
    duration       TEXT,
    artists        JSONB,
    extraartists   JSONB,
    producers      JSONB,
    raw_track_data JSONB
);

CREATE TABLE IF NOT EXISTS artwork (
    artwork_id          TEXT PRIMARY KEY,
    release_id          TEXT REFERENCES releases(release_id) ON DELETE CASCADE,
    image_type          TEXT,
    local_file_path     TEXT,
    thumbnail_file_path TEXT,
    original_url        TEXT,
    file_size           INTEGER,
    image_width         INTEGER,
    image_height        INTEGER,
    file_format         TEXT,
    download_date       TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wantlist (
    discogs_release_id  INTEGER PRIMARY KEY,
    title               TEXT,
    artist              TEXT,
    year                INTEGER,
    label               TEXT,
    format              TEXT,
    genres              JSONB,
    styles              JSONB,
    notes               TEXT,
    rating              INTEGER,
    added               TIMESTAMP,
    want_id             INTEGER,
    username            TEXT,
    user_id             INTEGER,
    basic_information   JSONB,
    raw_data            JSONB,
    community_want_count INTEGER,
    community_have_count INTEGER
);

CREATE TABLE IF NOT EXISTS release_prices (
    discogs_release_id  INTEGER PRIMARY KEY,
    lowest_price        DECIMAL(10,2),
    currency            VARCHAR(10),
    num_for_sale        INTEGER,
    availability        BOOLEAN DEFAULT false,
    last_seen           TIMESTAMP,
    source              TEXT
);

CREATE TABLE IF NOT EXISTS marketplace_stats_dim (
    discogs_release_id  INTEGER PRIMARY KEY,
    last_sold_date      DATE,
    low_sold_price      DECIMAL(10,2),
    high_sold_price     DECIMAL(10,2),
    currency            VARCHAR(10),
    as_of               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes               TEXT
);

CREATE TABLE IF NOT EXISTS availability_events (
    id                  SERIAL PRIMARY KEY,
    discogs_release_id  INTEGER,
    from_available      BOOLEAN,
    to_available        BOOLEAN,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS discogs_catalog_cache (
    kind       TEXT NOT NULL,
    key        TEXT NOT NULL,
    payload    JSONB,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (kind, key)
);

-- =====================================================================================
-- INDEXES
-- =====================================================================================

CREATE INDEX IF NOT EXISTS idx_releases_artist     ON releases(artist);
CREATE INDEX IF NOT EXISTS idx_releases_year       ON releases(year);
CREATE INDEX IF NOT EXISTS idx_releases_label      ON releases(label);
CREATE INDEX IF NOT EXISTS idx_releases_discogs_id ON releases(discogs_id);
CREATE INDEX IF NOT EXISTS idx_artwork_release_id  ON artwork(release_id);
CREATE INDEX IF NOT EXISTS idx_tracks_release_id   ON tracks(release_id);
