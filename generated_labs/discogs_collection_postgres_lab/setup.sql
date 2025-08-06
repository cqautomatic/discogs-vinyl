-- Discogs Collection Lab Setup (PostgreSQL Version)
-- Creates database, schema, tables, and functions for storing Discogs collection data and artwork

-- Step 1: Create database (run this as superuser)
-- CREATE DATABASE discogs_collection;
-- \c discogs_collection;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Step 2: Create schema
CREATE SCHEMA IF NOT EXISTS collection_data;
SET search_path TO collection_data, public;

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
    file_size INTEGER,
    image_width INTEGER,
    image_height INTEGER,
    file_format VARCHAR(20),
    download_date TIMESTAMP,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (release_id) REFERENCES releases(release_id)
);

-- Step 8: Create master releases table for release groups
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

-- Step 9: Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_releases_collection_id ON releases(collection_id);
CREATE INDEX IF NOT EXISTS idx_releases_discogs_id ON releases(discogs_id);
CREATE INDEX IF NOT EXISTS idx_releases_artist ON releases USING gin(to_tsvector('english', artist));
CREATE INDEX IF NOT EXISTS idx_releases_title ON releases USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_releases_year ON releases(year);
CREATE INDEX IF NOT EXISTS idx_releases_rating ON releases(rating);
CREATE INDEX IF NOT EXISTS idx_releases_genres ON releases USING gin(genres);
CREATE INDEX IF NOT EXISTS idx_releases_styles ON releases USING gin(styles);

CREATE INDEX IF NOT EXISTS idx_artwork_release_id ON artwork(release_id);
CREATE INDEX IF NOT EXISTS idx_artists_discogs_id ON artists(discogs_artist_id);
CREATE INDEX IF NOT EXISTS idx_labels_discogs_id ON labels(discogs_label_id);
CREATE INDEX IF NOT EXISTS idx_master_releases_discogs_id ON master_releases(discogs_master_id);

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

-- Step 16: Create triggers for automatic timestamp updates
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

-- Confirmation message
SELECT 'Discogs Collection PostgreSQL database setup completed successfully!' as setup_status;

-- Display basic statistics
SELECT 'Database Statistics:' as info;
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserted_rows,
    n_tup_upd as updated_rows,
    n_tup_del as deleted_rows
FROM pg_stat_user_tables 
WHERE schemaname = 'collection_data';