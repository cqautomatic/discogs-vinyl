-- Discogs Collection Lab Setup (PostgreSQL Version)
-- Creates database, schema, tables, and functions for storing Discogs collection data and artwork

-- =====================================================================================
-- CLEAN SLATE SETUP: Drop existing objects for fresh start
-- =====================================================================================
-- WARNING: This will permanently delete all existing data!
-- Comment out this section if you want to preserve existing data.

-- Step 0: Clean slate - Drop all existing objects
DO $$ 
DECLARE
    r RECORD;
    schema_name TEXT := 'collection_data';
BEGIN
    -- Set search path to include our schema
    EXECUTE 'SET search_path TO ' || schema_name || ', public';
    
    -- Drop all views first (to avoid dependency issues)
    FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = schema_name) 
    LOOP
        EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(r.viewname) || ' CASCADE';
        RAISE NOTICE 'Dropped view: %', r.viewname;
    END LOOP;
    
    -- Drop all functions and procedures
    FOR r IN (
        SELECT routine_name, routine_type 
        FROM information_schema.routines 
        WHERE routine_schema = schema_name 
        AND routine_type IN ('FUNCTION', 'PROCEDURE')
    ) 
    LOOP
        EXECUTE 'DROP ' || r.routine_type || ' IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(r.routine_name) || ' CASCADE';
        RAISE NOTICE 'Dropped %: %', r.routine_type, r.routine_name;
    END LOOP;
    
    -- Drop all tables (CASCADE will handle foreign key dependencies)
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = schema_name) 
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(r.tablename) || ' CASCADE';
        RAISE NOTICE 'Dropped table: %', r.tablename;
    END LOOP;
    
    -- Drop all sequences
    FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = schema_name) 
    LOOP
        EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(r.sequence_name) || ' CASCADE';
        RAISE NOTICE 'Dropped sequence: %', r.sequence_name;
    END LOOP;
    
    -- Drop all types/enums
    FOR r IN (
        SELECT typname 
        FROM pg_type t 
        JOIN pg_namespace n ON t.typnamespace = n.oid 
        WHERE n.nspname = schema_name 
        AND t.typtype = 'e'
    ) 
    LOOP
        EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(schema_name) || '.' || quote_ident(r.typname) || ' CASCADE';
        RAISE NOTICE 'Dropped type: %', r.typname;
    END LOOP;
    
    RAISE NOTICE 'Clean slate complete - all objects in schema "%" have been dropped', schema_name;
END $$;

-- Optionally drop and recreate the entire schema (uncomment if needed)
-- DROP SCHEMA IF EXISTS collection_data CASCADE;

-- Migration: Handle existing databases with old column names
DO $$ 
BEGIN
    -- Check if old 'position' column exists and rename it to 'track_number'
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'tracks' 
        AND column_name = 'position'
    ) THEN
        ALTER TABLE collection_data.tracks RENAME COLUMN position TO track_number;
        RAISE NOTICE 'Migrated: Renamed column "position" to "track_number" in tracks table';
    END IF;
END $$;

-- =====================================================================================
-- FRESH SETUP: Create database structure from scratch
-- =====================================================================================

-- Step 1: Create database (run this as superuser if creating new database)
-- CREATE DATABASE discogs_collection;
-- \c discogs_collection;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Step 2: Create schema
CREATE SCHEMA IF NOT EXISTS collection_data;
SET search_path TO collection_data, public;

-- Confirm clean setup
DO $$ 
BEGIN 
    RAISE NOTICE 'Starting fresh setup in schema: collection_data';
    RAISE NOTICE 'Search path set to: collection_data, public';
END $$;

-- Step 3: Create collections table for basic collection info
CREATE TABLE IF NOT EXISTS collections (
    collection_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    username VARCHAR(100),
    collection_name VARCHAR(200),
    total_items INTEGER,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 4: Create releases table for individual album/release data
CREATE TABLE IF NOT EXISTS releases (
    release_id VARCHAR(50) PRIMARY KEY,
    collection_id VARCHAR(50),
    basic_information JSONB,
    discogs_id INTEGER,
    title TEXT,
    artist TEXT,
    year INTEGER,
    label TEXT,
    catno VARCHAR(100),
    format TEXT,
    genres JSONB,
    styles JSONB,
    copies_count INTEGER DEFAULT 1,
    instance_ids JSONB,
    producers JSONB,
    country VARCHAR(100),
    date_added TIMESTAMP,
    instance_id INTEGER,
    folder_id INTEGER,
    rating INTEGER,
    notes TEXT,
    condition VARCHAR(100),
    sleeve_condition VARCHAR(100),
    marketplace_stats JSONB,
    artwork_urls JSONB,
    local_artwork_paths JSONB,
    -- Community statistics from Discogs API
    community_have_count INTEGER DEFAULT 0,
    community_want_count INTEGER DEFAULT 0,
    community_rating_count INTEGER DEFAULT 0,
    community_average_rating DECIMAL(3,2) DEFAULT 0.0,
    stats_last_updated TIMESTAMP,
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (collection_id) REFERENCES collections(collection_id)
);

-- Step 5: Create artists table for normalized artist data
CREATE TABLE IF NOT EXISTS artists (
    artist_id VARCHAR(50) PRIMARY KEY,
    artist_name TEXT,
    real_name TEXT,
    profile TEXT,
    discogs_artist_id INTEGER UNIQUE,
    images JSONB,
    urls JSONB,
    members JSONB,
    groups JSONB,
    aliases JSONB,
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Producers table (analogous to artists)
CREATE TABLE IF NOT EXISTS producers (
    producer_id VARCHAR(50) PRIMARY KEY,
    producer_name TEXT,
    discogs_producer_id INTEGER,
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 6: Create labels table for record label information
CREATE TABLE IF NOT EXISTS labels (
    label_id VARCHAR(50) PRIMARY KEY,
    label_name TEXT,
    contact_info TEXT,
    profile TEXT,
    discogs_label_id INTEGER UNIQUE,
    images JSONB,
    urls JSONB,
    parent_label TEXT,
    sublabels JSONB,
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 7: Create artwork table for image metadata
CREATE TABLE IF NOT EXISTS artwork (
    artwork_id VARCHAR(50) PRIMARY KEY,
    release_id VARCHAR(50),
    image_type VARCHAR(50), -- 'primary', 'secondary', 'cover', 'back', etc.
    original_url TEXT,
    local_file_path TEXT,
    thumbnail_file_path TEXT, -- Optional separate thumbnail file
    file_size INTEGER,
    image_width INTEGER,
    image_height INTEGER,
    file_format VARCHAR(20),
    download_date TIMESTAMP,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (release_id) REFERENCES releases(release_id)
);

-- Prices & availability for releases (Discogs marketplace refreshes)
CREATE TABLE IF NOT EXISTS release_prices (
    discogs_release_id INTEGER PRIMARY KEY,
    lowest_price DECIMAL(10,2),
    currency VARCHAR(10),
    num_for_sale INTEGER,
    availability BOOLEAN,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT
);

-- Dim table for marketplace aggregates (overwrite/SCD1 style)
CREATE TABLE IF NOT EXISTS marketplace_stats_dim (
    discogs_release_id INTEGER PRIMARY KEY,
    last_sold_date DATE,
    low_sold_price DECIMAL(10,2),
    high_sold_price DECIMAL(10,2),
    currency VARCHAR(10),
    as_of TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_marketplace_stats_dim_as_of ON marketplace_stats_dim(as_of);

-- Wantlist (wishlist) items per user
CREATE TABLE IF NOT EXISTS wantlist (
    want_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    username VARCHAR(100),
    discogs_release_id INTEGER UNIQUE,
    title TEXT,
    artist TEXT,
    year INTEGER,
    label TEXT,
    format TEXT,
    genres JSONB,
    styles JSONB,
    notes TEXT,
    rating INTEGER,
    added TIMESTAMP,
    basic_information JSONB,
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Availability change events for notifications
CREATE TABLE IF NOT EXISTS availability_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discogs_release_id INTEGER,
    from_available BOOLEAN,
    to_available BOOLEAN,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 8: Create tracks table for detailed track information
CREATE TABLE IF NOT EXISTS tracks (
    track_id VARCHAR(50) PRIMARY KEY,
    release_id VARCHAR(50),
    track_number VARCHAR(10), -- Changed from 'position' (PostgreSQL reserved keyword)
    title TEXT,
    duration VARCHAR(20),
    artists JSONB, -- Array of track-level artists for Various Artists albums
    extraartists JSONB, -- Additional artists (featuring, remix, etc.)
    producers JSONB,
    raw_track_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (release_id) REFERENCES releases(release_id)
);

-- Step 9: Create master releases table for release groups
CREATE TABLE IF NOT EXISTS master_releases (
    master_id VARCHAR(50) PRIMARY KEY,
    discogs_master_id INTEGER UNIQUE,
    title TEXT,
    main_release_id VARCHAR(50),
    year INTEGER,
    genres JSONB,
    styles JSONB,
    images JSONB,
    videos JSONB,
    artists JSONB,
    versions_count INTEGER,
    lowest_price DECIMAL(10,2),
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 10: Create artist discography table for comprehensive artist information
CREATE TABLE IF NOT EXISTS artist_discography (
    discography_id VARCHAR(50) PRIMARY KEY,
    artist_id VARCHAR(50),
    discogs_artist_id INTEGER,
    artist_name TEXT,
    release_id VARCHAR(50),
    discogs_release_id INTEGER,
    title TEXT,
    year INTEGER,
    role TEXT, -- 'Main', 'Appearance', 'Remix', 'Producer', etc.
    label TEXT,
    format TEXT,
    country VARCHAR(100),
    in_collection BOOLEAN DEFAULT FALSE,
    collection_release_id VARCHAR(50), -- Links to our releases table if owned
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (artist_id) REFERENCES artists(artist_id),
    FOREIGN KEY (collection_release_id) REFERENCES releases(release_id)
);

-- Producer discography table
CREATE TABLE IF NOT EXISTS producer_discography (
    discography_id VARCHAR(50) PRIMARY KEY,
    producer_id VARCHAR(50),
    discogs_producer_id INTEGER,
    producer_name TEXT,
    release_id VARCHAR(50),
    discogs_release_id INTEGER,
    title TEXT,
    year INTEGER,
    label TEXT,
    format TEXT,
    country VARCHAR(100),
    in_collection BOOLEAN DEFAULT FALSE,
    collection_release_id VARCHAR(50),
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 11: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_releases_collection_id ON releases(collection_id);
CREATE INDEX IF NOT EXISTS idx_releases_discogs_id ON releases(discogs_id);
CREATE INDEX IF NOT EXISTS idx_releases_artist ON releases USING gin(to_tsvector('english', artist));
CREATE INDEX IF NOT EXISTS idx_releases_title ON releases USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_releases_year ON releases(year);
CREATE INDEX IF NOT EXISTS idx_releases_rating ON releases(rating);
CREATE INDEX IF NOT EXISTS idx_releases_genres ON releases USING gin(genres);
CREATE INDEX IF NOT EXISTS idx_releases_styles ON releases USING gin(styles);
CREATE INDEX IF NOT EXISTS idx_releases_producers ON releases USING gin(producers);
-- Community statistics indexes
CREATE INDEX IF NOT EXISTS idx_releases_community_have_count ON releases(community_have_count);
CREATE INDEX IF NOT EXISTS idx_releases_community_want_count ON releases(community_want_count);
CREATE INDEX IF NOT EXISTS idx_releases_community_average_rating ON releases(community_average_rating);
CREATE INDEX IF NOT EXISTS idx_releases_stats_last_updated ON releases(stats_last_updated);

CREATE INDEX IF NOT EXISTS idx_tracks_release_id ON tracks(release_id);
CREATE INDEX IF NOT EXISTS idx_tracks_artists ON tracks USING gin(artists);
CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_tracks_track_number ON tracks(track_number); -- Index for track ordering
CREATE INDEX IF NOT EXISTS idx_tracks_producers ON tracks USING gin(producers);

CREATE INDEX IF NOT EXISTS idx_artist_discography_artist_id ON artist_discography(artist_id);
CREATE INDEX IF NOT EXISTS idx_artist_discography_discogs_artist_id ON artist_discography(discogs_artist_id);
CREATE INDEX IF NOT EXISTS idx_artist_discography_in_collection ON artist_discography(in_collection);
CREATE INDEX IF NOT EXISTS idx_artist_discography_year ON artist_discography(year);

CREATE INDEX IF NOT EXISTS idx_artwork_release_id ON artwork(release_id);
CREATE INDEX IF NOT EXISTS idx_artists_discogs_id ON artists(discogs_artist_id);
CREATE INDEX IF NOT EXISTS idx_labels_discogs_id ON labels(discogs_label_id);
CREATE INDEX IF NOT EXISTS idx_master_releases_discogs_id ON master_releases(discogs_master_id);
CREATE INDEX IF NOT EXISTS idx_wantlist_artist ON wantlist USING gin(to_tsvector('english', artist));
CREATE INDEX IF NOT EXISTS idx_wantlist_label ON wantlist USING gin(to_tsvector('english', label));
CREATE INDEX IF NOT EXISTS idx_wantlist_year ON wantlist(year);

-- Step 10: Create collection statistics view
CREATE OR REPLACE VIEW collection_stats AS
SELECT 
    c.collection_id,
    c.username,
    c.total_items,
    COUNT(r.release_id) as downloaded_items,
    COUNT(DISTINCT r.artist) as unique_artists,
    COUNT(DISTINCT r.label) as unique_labels,
    COUNT(DISTINCT r.year) as years_span,
    MIN(r.year) as earliest_year,
    MAX(r.year) as latest_year,
    COUNT(DISTINCT r.country) as countries,
    ROUND(AVG(r.rating), 2) as avg_rating,
    COUNT(a.artwork_id) as artwork_count,
    SUM(a.file_size) as total_artwork_size_bytes
FROM collections c
LEFT JOIN releases r ON c.collection_id = r.collection_id
LEFT JOIN artwork a ON r.release_id = a.release_id
GROUP BY c.collection_id, c.username, c.total_items;

-- Step 11: Create genre analysis view
CREATE OR REPLACE VIEW genre_analysis AS
SELECT 
    genre_value as genre,
    COUNT(*) as release_count,
    COUNT(DISTINCT r.artist) as artist_count,
    ROUND(AVG(r.year), 0) as avg_year,
    ROUND(AVG(r.rating), 2) as avg_rating
FROM releases r,
LATERAL jsonb_array_elements_text(r.genres) as genre_value
WHERE r.genres IS NOT NULL
GROUP BY genre_value
ORDER BY release_count DESC;

-- Step 12: Create decade analysis view
CREATE OR REPLACE VIEW decade_analysis AS
SELECT 
    (r.year / 10) * 10 as decade,
    COUNT(*) as release_count,
    COUNT(DISTINCT r.artist) as artist_count,
    ROUND(AVG(r.rating), 2) as avg_rating,
    jsonb_agg(DISTINCT genre_value) as genres
FROM releases r,
LATERAL jsonb_array_elements_text(r.genres) as genre_value
WHERE r.year IS NOT NULL AND r.genres IS NOT NULL
GROUP BY (r.year / 10) * 10
ORDER BY decade;

-- Step 13: Create track analysis view for Various Artists albums
CREATE OR REPLACE VIEW various_artists_analysis AS
SELECT 
    r.release_id,
    r.title as album_title,
    r.year,
    COUNT(t.track_id) as track_count,
    jsonb_agg(DISTINCT artist_value) as unique_track_artists,
    COUNT(DISTINCT artist_value) as unique_artist_count
FROM releases r
JOIN tracks t ON r.release_id = t.release_id,
LATERAL jsonb_array_elements_text(t.artists) as artist_value
WHERE UPPER(r.artist) LIKE '%VARIOUS%' OR UPPER(r.artist) LIKE '%COMPILATION%'
GROUP BY r.release_id, r.title, r.year
ORDER BY unique_artist_count DESC;

-- Step 14: Create artist discography summary view
CREATE OR REPLACE VIEW artist_discography_summary AS
SELECT 
    a.artist_id,
    a.artist_name,
    COUNT(ad.discography_id) as total_releases,
    COUNT(CASE WHEN ad.in_collection = true THEN 1 END) as owned_releases,
    COUNT(CASE WHEN ad.in_collection = false THEN 1 END) as missing_releases,
    ROUND(
        (COUNT(CASE WHEN ad.in_collection = true THEN 1 END)::NUMERIC / 
         COUNT(ad.discography_id)::NUMERIC) * 100, 1
    ) as collection_completeness_percent,
    MIN(ad.year) as earliest_release,
    MAX(ad.year) as latest_release,
    jsonb_agg(DISTINCT ad.role) as roles,
    jsonb_agg(DISTINCT ad.format) as formats
FROM artists a
LEFT JOIN artist_discography ad ON a.artist_id = ad.artist_id
GROUP BY a.artist_id, a.artist_name
ORDER BY collection_completeness_percent DESC;

-- Producer discography summary view (analogous to artist)
CREATE OR REPLACE VIEW producer_discography_summary AS
SELECT 
    p.producer_id,
    p.producer_name,
    COUNT(pd.discography_id) as total_releases,
    COUNT(CASE WHEN pd.in_collection = true THEN 1 END) as owned_releases,
    COUNT(CASE WHEN pd.in_collection = false THEN 1 END) as missing_releases,
    ROUND(
        (COUNT(CASE WHEN pd.in_collection = true THEN 1 END)::NUMERIC / 
         NULLIF(COUNT(pd.discography_id),0)::NUMERIC) * 100, 1
    ) as collection_completeness_percent,
    MIN(pd.year) as earliest_release,
    MAX(pd.year) as latest_release,
    jsonb_agg(DISTINCT pd.format) as formats
FROM producers p
LEFT JOIN producer_discography pd ON p.producer_id = pd.producer_id
GROUP BY p.producer_id, p.producer_name
ORDER BY collection_completeness_percent DESC;

-- Step 13: Create search function for collection
CREATE OR REPLACE FUNCTION search_collection(search_term TEXT)
RETURNS TABLE (
    release_id VARCHAR(50),
    title TEXT,
    artist TEXT,
    year INTEGER,
    label TEXT,
    relevance_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.release_id,
        r.title,
        r.artist,
        r.year,
        r.label,
        -- Simple relevance scoring based on text matches
        (
            CASE WHEN UPPER(r.title) LIKE UPPER('%' || search_term || '%') THEN 3.0 ELSE 0.0 END +
            CASE WHEN UPPER(r.artist) LIKE UPPER('%' || search_term || '%') THEN 2.0 ELSE 0.0 END +
            CASE WHEN UPPER(r.label) LIKE UPPER('%' || search_term || '%') THEN 1.0 ELSE 0.0 END +
            CASE WHEN r.genres @> to_jsonb(UPPER(search_term)) THEN 1.5 ELSE 0.0 END +
            CASE WHEN r.styles @> to_jsonb(UPPER(search_term)) THEN 1.0 ELSE 0.0 END
        )::FLOAT as relevance_score
    FROM releases r
    WHERE 
        UPPER(r.title) LIKE UPPER('%' || search_term || '%') OR
        UPPER(r.artist) LIKE UPPER('%' || search_term || '%') OR
        UPPER(r.label) LIKE UPPER('%' || search_term || '%') OR
        r.genres @> to_jsonb(UPPER(search_term)) OR
        r.styles @> to_jsonb(UPPER(search_term))
    ORDER BY relevance_score DESC, r.artist, r.year;
END;
$$ LANGUAGE plpgsql;

-- Step 14: Create full-text search function with better scoring
CREATE OR REPLACE FUNCTION search_collection_fulltext(search_term TEXT)
RETURNS TABLE (
    release_id VARCHAR(50),
    title TEXT,
    artist TEXT,
    year INTEGER,
    label TEXT,
    relevance_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.release_id,
        r.title,
        r.artist,
        r.year,
        r.label,
        (
            ts_rank(to_tsvector('english', COALESCE(r.title, '')), plainto_tsquery('english', search_term)) * 3.0 +
            ts_rank(to_tsvector('english', COALESCE(r.artist, '')), plainto_tsquery('english', search_term)) * 2.0 +
            ts_rank(to_tsvector('english', COALESCE(r.label, '')), plainto_tsquery('english', search_term)) * 1.0
        )::FLOAT as relevance_score
    FROM releases r
    WHERE 
        to_tsvector('english', COALESCE(r.title, '')) @@ plainto_tsquery('english', search_term) OR
        to_tsvector('english', COALESCE(r.artist, '')) @@ plainto_tsquery('english', search_term) OR
        to_tsvector('english', COALESCE(r.label, '')) @@ plainto_tsquery('english', search_term)
    ORDER BY relevance_score DESC, r.artist, r.year;
END;
$$ LANGUAGE plpgsql;

-- Step 15: Create function to update last_updated timestamps
CREATE OR REPLACE FUNCTION update_last_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 16: Create function to search tracks (for Various Artists albums)
CREATE OR REPLACE FUNCTION search_tracks(search_term TEXT)
RETURNS TABLE (
    track_id VARCHAR(50),
    release_title TEXT,
    track_title TEXT,
    track_artists JSONB,
    track_number VARCHAR(10), -- Changed from 'position'
    duration VARCHAR(20)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.track_id,
        r.title as release_title,
        t.title as track_title,
        t.artists as track_artists,
        t.track_number, -- Changed from 'position'
        t.duration
    FROM tracks t
    JOIN releases r ON t.release_id = r.release_id
    WHERE 
        to_tsvector('english', t.title) @@ plainto_tsquery('english', search_term) OR
        t.artists @> to_jsonb(search_term) OR
        UPPER(t.title) LIKE UPPER('%' || search_term || '%')
    ORDER BY ts_rank(to_tsvector('english', t.title), plainto_tsquery('english', search_term)) DESC;
END;
$$ LANGUAGE plpgsql;

-- Step 17: Create function to get missing releases for an artist
CREATE OR REPLACE FUNCTION get_artist_missing_releases(artist_name_param TEXT)
RETURNS TABLE (
    discography_id VARCHAR(50),
    title TEXT,
    year INTEGER,
    role TEXT,
    label TEXT,
    format TEXT,
    country VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ad.discography_id,
        ad.title,
        ad.year,
        ad.role,
        ad.label,
        ad.format,
        ad.country
    FROM artist_discography ad
    JOIN artists a ON ad.artist_id = a.artist_id
    WHERE a.artist_name ILIKE '%' || artist_name_param || '%'
      AND ad.in_collection = false
    ORDER BY ad.year DESC, ad.title;
END;
$$ LANGUAGE plpgsql;

-- Step 18: Create triggers for automatic timestamp updates
CREATE TRIGGER collections_update_trigger
    BEFORE UPDATE ON collections
    FOR EACH ROW
    EXECUTE FUNCTION update_last_modified();

CREATE TRIGGER releases_update_trigger
    BEFORE UPDATE ON releases
    FOR EACH ROW
    EXECUTE FUNCTION update_last_modified();

CREATE TRIGGER artists_update_trigger
    BEFORE UPDATE ON artists
    FOR EACH ROW
    EXECUTE FUNCTION update_last_modified();

CREATE TRIGGER labels_update_trigger
    BEFORE UPDATE ON labels
    FOR EACH ROW
    EXECUTE FUNCTION update_last_modified();

CREATE TRIGGER master_releases_update_trigger
    BEFORE UPDATE ON master_releases
    FOR EACH ROW
    EXECUTE FUNCTION update_last_modified();

-- Step 17: Create utility functions
CREATE OR REPLACE FUNCTION get_collection_summary(collection_id_param VARCHAR(50))
RETURNS TABLE (
    metric_name TEXT,
    metric_value TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'Total Releases'::TEXT,
        COUNT(*)::TEXT
    FROM releases 
    WHERE collection_id = collection_id_param
    UNION ALL
    SELECT 
        'Unique Artists'::TEXT,
        COUNT(DISTINCT artist)::TEXT
    FROM releases 
    WHERE collection_id = collection_id_param
    UNION ALL
    SELECT 
        'Average Rating'::TEXT,
        ROUND(AVG(rating), 2)::TEXT
    FROM releases 
    WHERE collection_id = collection_id_param AND rating IS NOT NULL
    UNION ALL
    SELECT 
        'Year Range'::TEXT,
        CONCAT(MIN(year), ' - ', MAX(year))
    FROM releases 
    WHERE collection_id = collection_id_param AND year IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Step 18: Create backup and maintenance functions
CREATE OR REPLACE FUNCTION cleanup_old_artwork()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete artwork records for releases that no longer exist
    DELETE FROM artwork 
    WHERE release_id NOT IN (SELECT release_id FROM releases);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================================
-- COMPLETION AND UTILITY COMMANDS
-- =====================================================================================

-- Confirmation message
SELECT 'Discogs Collection PostgreSQL database setup completed successfully!' as setup_status;

-- Display basic statistics
SELECT 'Database Statistics:' as info;
SELECT 
    schemaname,
    relname, -- Using relname for consistency with PostgreSQL catalog standards
    n_tup_ins as inserted_rows,
    n_tup_upd as updated_rows,
    n_tup_del as deleted_rows
FROM pg_stat_user_tables 
WHERE schemaname = 'collection_data';

-- =====================================================================================
-- UTILITY: Additional cleanup commands (for manual use)
-- =====================================================================================

/*
-- If you need to reset just the data (keep structure):
TRUNCATE TABLE collection_data.collections, 
               collection_data.releases, 
               collection_data.tracks,
               collection_data.artists, 
               collection_data.labels, 
               collection_data.artwork,
               collection_data.artist_discography 
RESTART IDENTITY CASCADE;

-- If you need to drop just the enhanced tables (keep original structure):
DROP TABLE IF EXISTS collection_data.tracks CASCADE;
DROP TABLE IF EXISTS collection_data.artist_discography CASCADE;
DROP VIEW IF EXISTS collection_data.various_artists_analysis CASCADE;
DROP VIEW IF EXISTS collection_data.artist_discography_summary CASCADE;
DROP FUNCTION IF EXISTS collection_data.search_tracks(TEXT) CASCADE;
DROP FUNCTION IF EXISTS collection_data.get_artist_missing_releases(TEXT) CASCADE;

-- If you need to completely start over with the schema:
DROP SCHEMA IF EXISTS collection_data CASCADE;

-- Quick verification of what exists:
SELECT 'Tables:' as object_type, c.relname as name 
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'collection_data' AND c.relkind = 'r'
UNION ALL
SELECT 'Views:', c.relname as name
FROM pg_class c  
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'collection_data' AND c.relkind = 'v'
UNION ALL
SELECT 'Functions:', routine_name as name FROM information_schema.routines WHERE routine_schema = 'collection_data'
ORDER BY object_type, name;
*/