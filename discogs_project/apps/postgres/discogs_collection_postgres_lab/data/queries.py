"""
SQL queries for the Discogs collection application.
Centralized location for all database queries.
"""

# Collection Statistics Queries
COLLECTION_STATS_QUERY = """
SELECT 
    COUNT(*) as total_items,
    COUNT(CASE WHEN discogs_id IS NOT NULL THEN 1 END) as downloaded_items,
    COUNT(DISTINCT artist) as unique_artists,
    COUNT(DISTINCT label) as unique_labels,
    COUNT(DISTINCT country) as countries,
    MIN(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as earliest_year,
    MAX(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as latest_year,
    AVG(CASE WHEN rating > 0 THEN rating END) as avg_rating,
    COUNT(CASE WHEN rating > 0 THEN 1 END) as rated_items,
    (SELECT COUNT(*) FROM artwork) as artwork_count,
    (SELECT COALESCE(SUM(file_size), 0) FROM artwork) as total_artwork_size_bytes,
    -- Collection value information (multiple estimates for condition quality)
    (SELECT MIN(rp.lowest_price) FROM release_prices rp WHERE rp.lowest_price > 0) as min_price,
    (SELECT MAX(rp.lowest_price) FROM release_prices rp WHERE rp.lowest_price > 0) as max_price,
    (SELECT AVG(rp.lowest_price) FROM release_prices rp WHERE rp.lowest_price > 0) as avg_price,
    -- Conservative estimate: sum of lowest marketplace prices (partial collection)
    (SELECT SUM(rp.lowest_price) FROM release_prices rp 
     JOIN releases r2 ON r2.discogs_id = rp.discogs_release_id 
     WHERE rp.lowest_price > 0) as total_value,
    -- High-quality condition estimate: 30% premium over lowest prices
    (SELECT SUM(rp.lowest_price * 1.30) FROM release_prices rp 
     JOIN releases r2 ON r2.discogs_id = rp.discogs_release_id 
     WHERE rp.lowest_price > 0) as high_quality_value,
    -- Excellent condition estimate: 50% premium over lowest prices  
    (SELECT SUM(rp.lowest_price * 1.50) FROM release_prices rp 
     JOIN releases r2 ON r2.discogs_id = rp.discogs_release_id 
     WHERE rp.lowest_price > 0) as excellent_condition_value,
    (SELECT COUNT(*) FROM release_prices rp WHERE rp.lowest_price > 0) as priced_items,
    -- Extrapolated estimates based on average price of priced items
    (SELECT 
        (SUM(rp.lowest_price) / COUNT(rp.lowest_price)) * COUNT(DISTINCT r2.discogs_id)
     FROM release_prices rp 
     JOIN releases r2 ON r2.discogs_id = rp.discogs_release_id 
     WHERE rp.lowest_price > 0) as extrapolated_total_value,
    -- Extrapolated high-quality estimate
    (SELECT 
        (SUM(rp.lowest_price * 1.30) / COUNT(rp.lowest_price)) * COUNT(DISTINCT r2.discogs_id)
     FROM release_prices rp 
     JOIN releases r2 ON r2.discogs_id = rp.discogs_release_id 
     WHERE rp.lowest_price > 0) as extrapolated_high_quality_value
FROM releases
"""

# Genre Analysis Queries
GENRE_ANALYSIS_QUERY = """
SELECT 
    genre,
    COUNT(*) as release_count,
    COUNT(DISTINCT artist) as artist_count,
    AVG(CASE WHEN rating > 0 THEN rating END) as avg_rating
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre
WHERE genre IS NOT NULL AND genre != ''
GROUP BY genre
ORDER BY release_count DESC
LIMIT 20
"""

STYLE_ANALYSIS_QUERY = """
SELECT 
    style,
    COUNT(*) as release_count,
    COUNT(DISTINCT artist) as artist_count,
    AVG(CASE WHEN rating > 0 THEN rating END) as avg_rating
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style
WHERE style IS NOT NULL AND style != ''
GROUP BY style
ORDER BY release_count DESC
LIMIT 20
"""

# Decade Analysis Queries
DECADE_ANALYSIS_QUERY = """
SELECT 
    (year / 10) * 10 AS decade,
    COUNT(*) as release_count
FROM releases 
WHERE year IS NOT NULL 
GROUP BY (year / 10) * 10
HAVING COUNT(*) > 0
ORDER BY decade
"""

YEAR_BREAKDOWN_QUERY = """
SELECT 
    year,
    COUNT(*) as release_count
FROM releases 
WHERE year BETWEEN %s AND %s
    AND year IS NOT NULL
GROUP BY year
HAVING COUNT(*) > 0
ORDER BY year
"""

# Collection Valuation Query
COLLECTION_VALUATION_QUERY = """
SELECT 
    COUNT(*) as total_releases,
    COUNT(CASE WHEN rp.lowest_price IS NOT NULL THEN 1 END) as priced_releases,
    MIN(rp.lowest_price) as min_price,
    MAX(rp.lowest_price) as max_price,
    AVG(rp.lowest_price) as avg_price,
    SUM(rp.lowest_price) as total_value,
    rp.currency,
    MAX(rp.last_seen) as price_date
FROM releases r
LEFT JOIN release_prices rp ON r.discogs_id = rp.discogs_release_id
WHERE rp.lowest_price IS NOT NULL AND rp.lowest_price > 0
GROUP BY rp.currency
ORDER BY total_value DESC
"""

# Random Covers Query - Simple version for Enhanced Overview (just thumbnails, no navigation)
RANDOM_COVERS_QUERY = """
SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, r.title, r.artist, r.year
FROM artwork a
JOIN releases r ON r.release_id = a.release_id
WHERE a.image_type = 'primary'
    AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
    %s  -- decade filter placeholder
ORDER BY RANDOM()
LIMIT %s
"""

# Available Decades Query
AVAILABLE_DECADES_QUERY = """
SELECT DISTINCT (year / 10) * 10 as decade
FROM releases 
WHERE year IS NOT NULL AND year >= 1950
ORDER BY decade
"""

# Random Releases Query - Complex version with artwork_files for Browse Collection (with navigation)
RANDOM_RELEASES_QUERY = """
SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
       r.genres, r.styles, r.producers, r.country, r.rating, r.condition, r.sleeve_condition, 
       r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids,
       r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count,
       COALESCE(
           JSON_AGG(
               JSON_BUILD_OBJECT(
                   'artwork_id', a.artwork_id,
                   'image_type', a.image_type,
                   'local_file_path', a.local_file_path,
                   'thumbnail_file_path', a.thumbnail_file_path,
                   'original_url', a.original_url,
                   'file_size', a.file_size,
                   'image_width', a.image_width,
                   'image_height', a.image_height
               ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END, a.artwork_id
           ) FILTER (WHERE a.artwork_id IS NOT NULL),
           '[]'::json
       ) as artwork_files
FROM releases r
LEFT JOIN artwork a ON r.release_id = a.release_id
WHERE 1=1
    %s  -- decade filter placeholder
GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
         r.genres, r.styles, r.producers, r.country, r.rating, r.condition, r.sleeve_condition,
         r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids,
         r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
ORDER BY RANDOM()
LIMIT %s
"""

# Collection Search Query
COLLECTION_SEARCH_QUERY = """
SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
       r.genres, r.styles, r.producers, r.country, r.rating, r.condition, r.sleeve_condition, 
       r.date_added, r.artwork_urls, r.local_artwork_paths,
       r.copies_count, r.instance_ids,
       COALESCE(
           JSON_AGG(
               JSON_BUILD_OBJECT(
                   'artwork_id', a.artwork_id,
                   'image_type', a.image_type,
                   'local_file_path', a.local_file_path,
                   'thumbnail_file_path', a.thumbnail_file_path,
                   'original_url', a.original_url,
                   'file_size', a.file_size,
                   'image_width', a.image_width,
                   'image_height', a.image_height
               ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END, a.artwork_id
           ) FILTER (WHERE a.artwork_id IS NOT NULL),
           '[]'::json
       ) as artwork_files
FROM releases r
LEFT JOIN artwork a ON r.release_id = a.release_id
WHERE 
    UPPER(r.title) LIKE UPPER(%s) OR
    UPPER(r.artist) LIKE UPPER(%s)
GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
         r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition, 
         r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids
ORDER BY r.artist, r.year
"""

# Release Statistics Query
RELEASE_STATS_QUERY = """
SELECT 
    r.community_have_count,
    r.community_want_count,
    r.community_average_rating,
    r.community_rating_count,
    r.stats_last_updated,
    ms.last_sold_date,
    ms.low_sold_price,
    ms.high_sold_price,
    ms.currency as currency,
    ms.as_of as marketplace_as_of,
    rp.num_for_sale,
    rp.lowest_price as lowest_price_current,
    rp.currency as currency_current,
    rp.last_seen
FROM releases r
LEFT JOIN marketplace_stats_dim ms ON ms.discogs_release_id = r.discogs_id
LEFT JOIN release_prices rp ON rp.discogs_release_id = r.discogs_id
WHERE r.discogs_id = %s
LIMIT 1
"""

# Community Statistics Queries
COMMUNITY_STATS_CHECK_QUERY = """
SELECT 
    COUNT(*) as total_releases,
    COUNT(CASE WHEN community_have_count > 0 OR community_want_count > 0 OR community_rating_count > 0 THEN 1 END) as releases_with_stats,
    MAX(stats_last_updated) as last_updated,
    (SELECT MAX(as_of) FROM marketplace_stats_dim) as marketplace_as_of
FROM releases 
WHERE discogs_id IS NOT NULL
"""

MOST_POPULAR_RELEASES_QUERY = """
SELECT 
    title, artist, year, community_have_count, community_want_count,
    community_average_rating, community_rating_count,
    CASE 
        WHEN community_have_count > 0 THEN 
            ROUND((community_want_count::DECIMAL / community_have_count::DECIMAL) * 100, 1)
        ELSE 0 
    END as want_to_have_ratio
FROM releases 
WHERE community_have_count > 0
ORDER BY community_have_count DESC 
LIMIT 20
"""

MOST_WANTED_RELEASES_QUERY = """
SELECT 
    title, artist, year, community_want_count, community_have_count,
    community_average_rating, community_rating_count,
    CASE 
        WHEN community_have_count > 0 THEN 
            ROUND((community_want_count::DECIMAL / community_have_count::DECIMAL) * 100, 1)
        ELSE 0 
    END as want_to_have_ratio
FROM releases 
WHERE community_want_count > 0
ORDER BY community_want_count DESC 
LIMIT 20
"""

HIGHEST_RATED_RELEASES_QUERY = """
SELECT 
    title, artist, year, community_average_rating, community_rating_count,
    community_have_count, community_want_count
FROM releases 
WHERE community_rating_count >= 10  -- Only show releases with meaningful rating counts
ORDER BY community_average_rating DESC, community_rating_count DESC
LIMIT 20
"""

# Genre/Style Drill-down Queries
STYLES_FOR_GENRE_QUERY = """
SELECT 
    style,
    COUNT(*) as release_count
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre,
LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style
WHERE genre = %s AND style IS NOT NULL AND style != ''
GROUP BY style
ORDER BY release_count DESC
LIMIT 20
"""

GENRES_FOR_STYLE_QUERY = """
SELECT 
    genre,
    COUNT(*) as release_count
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre,
LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style
WHERE style = %s AND genre IS NOT NULL AND genre != ''
GROUP BY genre
ORDER BY release_count DESC
LIMIT 20
"""

RELEASES_FOR_GENRE_QUERY = """
SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
       r.genres, r.styles, r.country, r.rating, r.condition,
       r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre
WHERE genre = %s
ORDER BY RANDOM()
OFFSET %s LIMIT %s
"""

RELEASES_FOR_STYLE_QUERY = """
SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
       r.genres, r.styles, r.country, r.rating, r.condition,
       r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style
WHERE style = %s
ORDER BY RANDOM()
OFFSET %s LIMIT %s
"""

RELEASES_FOR_GENRE_AND_STYLE_QUERY = """
SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
       r.genres, r.styles, r.country, r.rating, r.condition,
       r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre,
LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style
WHERE genre = %s AND style = %s
ORDER BY RANDOM()
OFFSET %s LIMIT %s
"""

# Count queries for pagination
TOTAL_RELEASES_FOR_GENRE_QUERY = """
SELECT COUNT(*)
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre
WHERE genre = %s
"""

TOTAL_RELEASES_FOR_STYLE_QUERY = """
SELECT COUNT(*)
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style
WHERE style = %s
"""

TOTAL_RELEASES_FOR_GENRE_AND_STYLE_QUERY = """
SELECT COUNT(*)
FROM releases r,
LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre,
LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style
WHERE genre = %s AND style = %s
"""

# Year-specific releases query
RELEASES_FOR_YEAR_QUERY = """
SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
       r.genres, r.styles, r.country, r.rating, r.condition,
       r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count,
       COALESCE(
           JSON_AGG(
               JSON_BUILD_OBJECT(
                   'artwork_id', a.artwork_id,
                   'image_type', a.image_type,
                   'local_file_path', a.local_file_path,
                   'thumbnail_file_path', a.thumbnail_file_path,
                   'original_url', a.original_url
               ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END, a.artwork_id
           ) FILTER (WHERE a.artwork_id IS NOT NULL),
           '[]'::json
       ) as artwork_files
FROM releases r
LEFT JOIN artwork a ON r.release_id = a.release_id
WHERE r.year = %s
GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
         r.genres, r.styles, r.country, r.rating, r.condition,
         r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
ORDER BY RANDOM()
OFFSET %s LIMIT %s
"""
