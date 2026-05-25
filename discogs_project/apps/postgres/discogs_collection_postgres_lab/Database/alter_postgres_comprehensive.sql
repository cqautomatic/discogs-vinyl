-- =====================================================================================
-- Discogs Collection Lab - Comprehensive Database Migration Script
-- =====================================================================================
-- This script applies all recent enhancements to existing PostgreSQL databases
-- It's designed to be idempotent - safe to run multiple times
-- Date: 2025-08-13
-- =====================================================================================

-- Set search path
SET search_path TO collection_data, public;

-- Start transaction for safety
BEGIN;

DO $$ 
BEGIN 
    RAISE NOTICE 'Starting comprehensive database migration for Discogs Collection Lab';
    RAISE NOTICE 'Timestamp: %', CURRENT_TIMESTAMP;
END $$;

-- =====================================================================================
-- SECTION 1: TABLE STRUCTURE UPDATES
-- =====================================================================================

-- 1.1: Ensure releases table has all required columns
DO $$ 
BEGIN
    -- Add copies_count column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'copies_count'
    ) THEN
        ALTER TABLE releases ADD COLUMN copies_count INTEGER DEFAULT 1;
        RAISE NOTICE 'Added copies_count column to releases table';
    END IF;

    -- Add instance_ids column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'instance_ids'
    ) THEN
        ALTER TABLE releases ADD COLUMN instance_ids JSONB;
        RAISE NOTICE 'Added instance_ids column to releases table';
    END IF;

    -- Add producers column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'producers'
    ) THEN
        ALTER TABLE releases ADD COLUMN producers JSONB;
        RAISE NOTICE 'Added producers column to releases table';
    END IF;

    -- Add marketplace_stats column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'marketplace_stats'
    ) THEN
        ALTER TABLE releases ADD COLUMN marketplace_stats JSONB;
        RAISE NOTICE 'Added marketplace_stats column to releases table';
    END IF;

    -- Add artwork_urls column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'artwork_urls'
    ) THEN
        ALTER TABLE releases ADD COLUMN artwork_urls JSONB;
        RAISE NOTICE 'Added artwork_urls column to releases table';
    END IF;

    -- Add local_artwork_paths column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'local_artwork_paths'
    ) THEN
        ALTER TABLE releases ADD COLUMN local_artwork_paths JSONB;
        RAISE NOTICE 'Added local_artwork_paths column to releases table';
    END IF;

    -- Add community statistics columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'community_have_count'
    ) THEN
        ALTER TABLE releases ADD COLUMN community_have_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Added community_have_count column to releases table';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'community_want_count'
    ) THEN
        ALTER TABLE releases ADD COLUMN community_want_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Added community_want_count column to releases table';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'community_rating_count'
    ) THEN
        ALTER TABLE releases ADD COLUMN community_rating_count INTEGER DEFAULT 0;
        RAISE NOTICE 'Added community_rating_count column to releases table';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'community_average_rating'
    ) THEN
        ALTER TABLE releases ADD COLUMN community_average_rating DECIMAL(3,2) DEFAULT 0.0;
        RAISE NOTICE 'Added community_average_rating column to releases table';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'releases' 
        AND column_name = 'stats_last_updated'
    ) THEN
        ALTER TABLE releases ADD COLUMN stats_last_updated TIMESTAMP;
        RAISE NOTICE 'Added stats_last_updated column to releases table';
    END IF;
END $$;

-- 1.2: Ensure artwork table has thumbnail support
DO $$ 
BEGIN
    -- Add thumbnail_file_path column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'artwork' 
        AND column_name = 'thumbnail_file_path'
    ) THEN
        ALTER TABLE artwork ADD COLUMN thumbnail_file_path TEXT;
        RAISE NOTICE 'Added thumbnail_file_path column to artwork table';
    END IF;
END $$;

-- 1.3: Add marketplace_stats_dim table (SCD1 overwrite semantics)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'collection_data' AND table_name = 'marketplace_stats_dim'
    ) THEN
        CREATE TABLE marketplace_stats_dim (
            discogs_release_id INTEGER PRIMARY KEY,
            last_sold_date DATE,
            low_sold_price DECIMAL(10,2),
            high_sold_price DECIMAL(10,2),
            currency VARCHAR(10),
            as_of TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_marketplace_stats_dim_as_of ON marketplace_stats_dim(as_of);
        RAISE NOTICE 'Created table marketplace_stats_dim';
    END IF;
END $$;

-- 1.3: Ensure tracks table has producers column
DO $$ 
BEGIN
    -- Add producers column to tracks if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'tracks' 
        AND column_name = 'producers'
    ) THEN
        ALTER TABLE tracks ADD COLUMN producers JSONB;
        RAISE NOTICE 'Added producers column to tracks table';
    END IF;
END $$;

-- 1.4: Create producers table if it doesn't exist
CREATE TABLE IF NOT EXISTS producers (
    producer_id VARCHAR(50) PRIMARY KEY,
    producer_name TEXT,
    discogs_producer_id INTEGER,
    raw_data JSONB,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1.5: Create producer_discography table if it doesn't exist
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

-- 1.6: Create release_prices table if it doesn't exist
CREATE TABLE IF NOT EXISTS release_prices (
    discogs_release_id INTEGER PRIMARY KEY,
    lowest_price DECIMAL(10,2),
    currency VARCHAR(10),
    num_for_sale INTEGER,
    availability BOOLEAN,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT
);

-- 1.7: Create availability_events table if it doesn't exist
CREATE TABLE IF NOT EXISTS availability_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    discogs_release_id INTEGER,
    from_available BOOLEAN,
    to_available BOOLEAN,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1.8: Create wantlist table if it doesn't exist
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

-- =====================================================================================
-- SECTION 2: INDEX UPDATES
-- =====================================================================================

-- 2.1: Create missing indexes for new columns
CREATE INDEX IF NOT EXISTS idx_releases_producers ON releases USING gin(producers);
CREATE INDEX IF NOT EXISTS idx_releases_copies_count ON releases(copies_count);
CREATE INDEX IF NOT EXISTS idx_releases_instance_ids ON releases USING gin(instance_ids);

CREATE INDEX IF NOT EXISTS idx_tracks_producers ON tracks USING gin(producers);

CREATE INDEX IF NOT EXISTS idx_producers_name ON producers USING gin(to_tsvector('english', producer_name));
CREATE INDEX IF NOT EXISTS idx_producers_discogs_id ON producers(discogs_producer_id);

CREATE INDEX IF NOT EXISTS idx_producer_discography_producer_id ON producer_discography(producer_id);
CREATE INDEX IF NOT EXISTS idx_producer_discography_discogs_id ON producer_discography(discogs_producer_id);
CREATE INDEX IF NOT EXISTS idx_producer_discography_in_collection ON producer_discography(in_collection);

CREATE INDEX IF NOT EXISTS idx_release_prices_availability ON release_prices(availability);
CREATE INDEX IF NOT EXISTS idx_release_prices_last_seen ON release_prices(last_seen);

CREATE INDEX IF NOT EXISTS idx_availability_events_release_id ON availability_events(discogs_release_id);
CREATE INDEX IF NOT EXISTS idx_availability_events_time ON availability_events(event_time);

CREATE INDEX IF NOT EXISTS idx_wantlist_discogs_id ON wantlist(discogs_release_id);
CREATE INDEX IF NOT EXISTS idx_wantlist_artist ON wantlist USING gin(to_tsvector('english', artist));
CREATE INDEX IF NOT EXISTS idx_wantlist_title ON wantlist USING gin(to_tsvector('english', title));

-- =====================================================================================
-- SECTION 3: VIEW UPDATES
-- =====================================================================================

-- 3.1: Update or create producer_discography_summary view
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

-- 3.2: Update collection_stats view to include new metrics
CREATE OR REPLACE VIEW collection_stats AS
SELECT 
    c.collection_id,
    c.username,
    c.total_items,
    COUNT(r.release_id) as downloaded_items,
    COUNT(DISTINCT r.artist) as unique_artists,
    COUNT(DISTINCT r.label) as unique_labels,
    COUNT(DISTINCT r.year) as years_span,
    MIN(CASE WHEN r.year IS NOT NULL AND r.year >= 1930 THEN r.year END) as earliest_year,
    MAX(CASE WHEN r.year IS NOT NULL AND r.year >= 1930 THEN r.year END) as latest_year,
    COUNT(DISTINCT r.country) as countries,
    ROUND(AVG(r.rating), 2) as avg_rating,
    COUNT(a.artwork_id) as artwork_count,
    SUM(a.file_size) as total_artwork_size_bytes,
    SUM(r.copies_count) as total_copies,
    COUNT(DISTINCT producer_value) as unique_producers
FROM collections c
LEFT JOIN releases r ON c.collection_id = r.collection_id
LEFT JOIN artwork a ON r.release_id = a.release_id
LEFT JOIN LATERAL jsonb_array_elements_text(r.producers) as producer_value ON r.producers IS NOT NULL
GROUP BY c.collection_id, c.username, c.total_items;

-- =====================================================================================
-- SECTION 4: FUNCTION UPDATES
-- =====================================================================================

-- 4.1: Enhanced search function that includes producers and tracks
CREATE OR REPLACE FUNCTION search_collection_enhanced(search_term TEXT)
RETURNS TABLE (
    release_id VARCHAR(50),
    title TEXT,
    artist TEXT,
    year INTEGER,
    label TEXT,
    producers_match BOOLEAN,
    track_match BOOLEAN,
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
        (r.producers @> to_jsonb(search_term)) as producers_match,
        EXISTS(
            SELECT 1 FROM tracks t 
            WHERE t.release_id = r.release_id 
            AND (
                UPPER(t.title) LIKE UPPER('%' || search_term || '%') OR
                t.artists @> to_jsonb(search_term) OR
                t.producers @> to_jsonb(search_term)
            )
        ) as track_match,
        (
            CASE WHEN UPPER(r.title) LIKE UPPER('%' || search_term || '%') THEN 3.0 ELSE 0.0 END +
            CASE WHEN UPPER(r.artist) LIKE UPPER('%' || search_term || '%') THEN 2.0 ELSE 0.0 END +
            CASE WHEN UPPER(r.label) LIKE UPPER('%' || search_term || '%') THEN 1.0 ELSE 0.0 END +
            CASE WHEN r.genres @> to_jsonb(UPPER(search_term)) THEN 1.5 ELSE 0.0 END +
            CASE WHEN r.styles @> to_jsonb(UPPER(search_term)) THEN 1.0 ELSE 0.0 END +
            CASE WHEN r.producers @> to_jsonb(search_term) THEN 2.0 ELSE 0.0 END +
            CASE WHEN EXISTS(
                SELECT 1 FROM tracks t 
                WHERE t.release_id = r.release_id 
                AND UPPER(t.title) LIKE UPPER('%' || search_term || '%')
            ) THEN 1.5 ELSE 0.0 END
        )::FLOAT as relevance_score
    FROM releases r
    WHERE 
        UPPER(r.title) LIKE UPPER('%' || search_term || '%') OR
        UPPER(r.artist) LIKE UPPER('%' || search_term || '%') OR
        UPPER(r.label) LIKE UPPER('%' || search_term || '%') OR
        r.genres @> to_jsonb(UPPER(search_term)) OR
        r.styles @> to_jsonb(UPPER(search_term)) OR
        r.producers @> to_jsonb(search_term) OR
        EXISTS(
            SELECT 1 FROM tracks t 
            WHERE t.release_id = r.release_id 
            AND (
                UPPER(t.title) LIKE UPPER('%' || search_term || '%') OR
                t.artists @> to_jsonb(search_term) OR
                t.producers @> to_jsonb(search_term)
            )
        )
    ORDER BY relevance_score DESC, r.artist, r.year;
END;
$$ LANGUAGE plpgsql;

-- 4.2: Function to get producer missing releases
CREATE OR REPLACE FUNCTION get_producer_missing_releases(producer_name_param TEXT)
RETURNS TABLE (
    discography_id VARCHAR(50),
    title TEXT,
    year INTEGER,
    label TEXT,
    format TEXT,
    country VARCHAR(100)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pd.discography_id,
        pd.title,
        pd.year,
        pd.label,
        pd.format,
        pd.country
    FROM producer_discography pd
    JOIN producers p ON pd.producer_id = p.producer_id
    WHERE p.producer_name ILIKE '%' || producer_name_param || '%'
      AND pd.in_collection = false
    ORDER BY pd.year DESC, pd.title;
END;
$$ LANGUAGE plpgsql;

-- 4.3: Function to get collection valuation summary
CREATE OR REPLACE FUNCTION get_collection_valuation()
RETURNS TABLE (
    currency VARCHAR(10),
    num_priced INTEGER,
    total_low_value DECIMAL(12,2),
    avg_price DECIMAL(10,2),
    max_price DECIMAL(10,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rp.currency,
        COUNT(*)::INTEGER as num_priced,
        SUM(rp.lowest_price) as total_low_value,
        AVG(rp.lowest_price) as avg_price,
        MAX(rp.lowest_price) as max_price
    FROM release_prices rp
    JOIN releases r ON rp.discogs_release_id = r.discogs_id
    WHERE rp.lowest_price IS NOT NULL
    GROUP BY rp.currency
    ORDER BY num_priced DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================================
-- SECTION 5: DATA MIGRATION AND CLEANUP
-- =====================================================================================

-- 5.1: Migrate any existing position column to track_number in tracks table
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = 'tracks' 
        AND column_name = 'position'
    ) THEN
        -- Copy data from position to track_number if track_number is empty
        UPDATE tracks 
        SET track_number = position 
        WHERE track_number IS NULL AND position IS NOT NULL;
        
        -- Drop the old position column
        ALTER TABLE tracks DROP COLUMN position;
        RAISE NOTICE 'Migrated position column to track_number in tracks table';
    END IF;
END $$;

-- 5.2: Update any NULL copies_count to 1
UPDATE releases SET copies_count = 1 WHERE copies_count IS NULL;

-- 5.3: Initialize empty JSONB arrays for new columns where NULL
UPDATE releases SET instance_ids = '[]'::JSONB WHERE instance_ids IS NULL;
UPDATE releases SET producers = '[]'::JSONB WHERE producers IS NULL;
UPDATE releases SET marketplace_stats = '{}'::JSONB WHERE marketplace_stats IS NULL;
UPDATE releases SET artwork_urls = '[]'::JSONB WHERE artwork_urls IS NULL;
UPDATE releases SET local_artwork_paths = '[]'::JSONB WHERE local_artwork_paths IS NULL;

UPDATE tracks SET producers = '[]'::JSONB WHERE producers IS NULL;

-- =====================================================================================
-- SECTION 6: PERMISSIONS AND FINAL SETUP
-- =====================================================================================

-- 6.1: Grant permissions to common database users (adjust as needed)
DO $$ 
DECLARE
    user_name TEXT;
BEGIN
    -- Grant permissions to discogs_user if it exists
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'discogs_user') THEN
        EXECUTE 'GRANT USAGE ON SCHEMA collection_data TO discogs_user';
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA collection_data TO discogs_user';
        EXECUTE 'GRANT USAGE ON ALL SEQUENCES IN SCHEMA collection_data TO discogs_user';
        EXECUTE 'GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA collection_data TO discogs_user';
        RAISE NOTICE 'Granted permissions to discogs_user';
    END IF;
END $$;

-- =====================================================================================
-- SECTION 7: VERIFICATION AND COMPLETION
-- =====================================================================================

-- 7.1: Verify all expected tables exist
DO $$ 
DECLARE
    expected_tables TEXT[] := ARRAY[
        'collections', 'releases', 'artists', 'producers', 'labels', 'artwork', 
        'tracks', 'master_releases', 'artist_discography', 'producer_discography',
        'release_prices', 'availability_events', 'wantlist'
    ];
    table_name TEXT;
    missing_tables TEXT[] := '{}';
BEGIN
    FOREACH table_name IN ARRAY expected_tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'collection_data' 
            AND table_name = table_name
        ) THEN
            missing_tables := array_append(missing_tables, table_name);
        END IF;
    END LOOP;
    
    IF array_length(missing_tables, 1) > 0 THEN
        RAISE WARNING 'Missing tables: %', array_to_string(missing_tables, ', ');
    ELSE
        RAISE NOTICE 'All expected tables are present';
    END IF;
END $$;

-- 7.2: Display migration summary
SELECT 
    'Migration Summary' as info,
    COUNT(*) as total_tables
FROM information_schema.tables 
WHERE table_schema = 'collection_data';

SELECT 
    'Table' as object_type,
    table_name as name,
    (
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_schema = 'collection_data' 
        AND table_name = t.table_name
    ) as column_count
FROM information_schema.tables t
WHERE table_schema = 'collection_data'
UNION ALL
SELECT 
    'View' as object_type,
    table_name as name,
    NULL as column_count
FROM information_schema.views
WHERE table_schema = 'collection_data'
UNION ALL
SELECT 
    'Function' as object_type,
    routine_name as name,
    NULL as column_count
FROM information_schema.routines
WHERE routine_schema = 'collection_data'
ORDER BY object_type, name;

-- Commit the transaction
COMMIT;

-- Final success message
SELECT 'Discogs Collection Lab database migration completed successfully!' as migration_status,
       CURRENT_TIMESTAMP as completed_at;
