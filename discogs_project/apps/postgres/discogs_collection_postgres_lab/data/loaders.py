"""
Data loading functions for the Discogs collection application.
Handles all database queries and data transformations.
"""

import pandas as pd
import streamlit as st
from typing import List, Dict, Optional, Tuple
from core.database import PostgreSQLConnection
from data.queries import *

@st.cache_data(ttl=300)  # Cache for 5 minutes (pricing data can change)
def load_collection_stats(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load collection statistics with current pricing data."""
    # Always use the direct query to ensure we get pricing data
    # Note: Materialized views are outdated and don't contain pricing columns
    result = _db_conn.execute_query(COLLECTION_STATS_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_genre_analysis(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load genre analysis data using optimized materialized view if available."""
    # Try materialized view first
    try:
        result = _db_conn.execute_query("SELECT * FROM genre_analysis_mv LIMIT 20")
        if result:
            return pd.DataFrame(result)
    except Exception:
        pass
    
    # Fallback to original query
    result = _db_conn.execute_query(GENRE_ANALYSIS_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_style_analysis(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load style analysis data using optimized materialized view if available."""
    # Try materialized view first
    try:
        result = _db_conn.execute_query("SELECT * FROM style_analysis_mv LIMIT 20")
        if result:
            return pd.DataFrame(result)
    except Exception:
        pass
    
    # Fallback to original query
    result = _db_conn.execute_query(STYLE_ANALYSIS_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_styles_for_genre(_db_conn: PostgreSQLConnection, genre: str) -> pd.DataFrame:
    """Load styles for a specific genre."""
    result = _db_conn.execute_query(STYLES_FOR_GENRE_QUERY, (genre,))
    return pd.DataFrame(result) if result else pd.DataFrame()

@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_genres_for_style(_db_conn: PostgreSQLConnection, style: str) -> pd.DataFrame:
    """Load genres for a specific style."""
    result = _db_conn.execute_query(GENRES_FOR_STYLE_QUERY, (style,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_releases_for_genre(_db_conn: PostgreSQLConnection, genre: str, offset: int = 0, limit: int = 25, random_seed: int = 0) -> pd.DataFrame:
    """Load releases for a specific genre with pagination."""
    # Set random seed for consistent results
    if random_seed:
        _db_conn.execute_query(f"SELECT setseed({random_seed / 1000.0})")
    
    result = _db_conn.execute_query(RELEASES_FOR_GENRE_QUERY, (genre, offset, limit))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_releases_for_style(_db_conn: PostgreSQLConnection, style: str, offset: int = 0, limit: int = 25, random_seed: int = 0) -> pd.DataFrame:
    """Load releases for a specific style with pagination."""
    # Set random seed for consistent results
    if random_seed:
        _db_conn.execute_query(f"SELECT setseed({random_seed / 1000.0})")
    
    result = _db_conn.execute_query(RELEASES_FOR_STYLE_QUERY, (style, offset, limit))
    return pd.DataFrame(result) if result else pd.DataFrame()

def get_total_releases_for_genre(_db_conn: PostgreSQLConnection, genre: str) -> int:
    """Get total count of releases for a genre."""
    result = _db_conn.execute_query(TOTAL_RELEASES_FOR_GENRE_QUERY, (genre,))
    return result[0]['count'] if result else 0

def get_total_releases_for_style(_db_conn: PostgreSQLConnection, style: str) -> int:
    """Get total count of releases for a style."""
    result = _db_conn.execute_query(TOTAL_RELEASES_FOR_STYLE_QUERY, (style,))
    return result[0]['count'] if result else 0

def load_releases_for_genre_and_style(_db_conn: PostgreSQLConnection, genre: str, style: str, offset: int = 0, limit: int = 25, random_seed: int = 0) -> pd.DataFrame:
    """Load releases for a specific genre AND style combination with pagination."""
    # Set random seed for consistent results
    if random_seed:
        _db_conn.execute_query(f"SELECT setseed({random_seed / 1000.0})")
    
    result = _db_conn.execute_query(RELEASES_FOR_GENRE_AND_STYLE_QUERY, (genre, style, offset, limit))
    return pd.DataFrame(result) if result else pd.DataFrame()

def get_total_releases_for_genre_and_style(_db_conn: PostgreSQLConnection, genre: str, style: str) -> int:
    """Get total count of releases for a genre AND style combination."""
    result = _db_conn.execute_query(TOTAL_RELEASES_FOR_GENRE_AND_STYLE_QUERY, (genre, style))
    return result[0]['count'] if result else 0

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_decade_analysis(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load decade analysis data using optimized materialized view if available."""
    # Try materialized view first
    try:
        result = _db_conn.execute_query("SELECT * FROM decade_analysis_mv")
        if result:
            return pd.DataFrame(result)
    except Exception:
        pass
    
    # Fallback to original query
    result = _db_conn.execute_query(DECADE_ANALYSIS_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_year_breakdown(_db_conn: PostgreSQLConnection, decade_start: int) -> pd.DataFrame:
    """Load year breakdown for a specific decade with only years that have data."""
    decade_end = decade_start + 9
    result = _db_conn.execute_query(YEAR_BREAKDOWN_QUERY, (decade_start, decade_end))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_releases_for_year(_db_conn: PostgreSQLConnection, year: int, limit: int, offset: int, random_seed: int = 0) -> pd.DataFrame:
    """Load releases for a specific year with pagination and randomization."""
    # Set random seed for consistent results
    if random_seed:
        _db_conn.execute_query(f"SELECT setseed({random_seed / 1000.0})")
    
    result = _db_conn.execute_query(RELEASES_FOR_YEAR_QUERY, (year, offset, limit))
    return pd.DataFrame(result) if result else pd.DataFrame()

@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_collection_valuation(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load collection valuation data."""
    result = _db_conn.execute_query(COLLECTION_VALUATION_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_random_covers(_db_conn: PostgreSQLConnection, count: int = 10, seed: int = 0, sort_clause: str = "ORDER BY RANDOM()") -> pd.DataFrame:
    """Load random album covers (simple version for Enhanced Overview)."""
    # Set random seed for consistent results
    if seed:
        _db_conn.execute_query(f"SELECT setseed({seed / 1000.0})")
    
    # Build query without decade filter for now
    query = """
    SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, r.title, r.artist, r.year, r.release_id
    FROM artwork a
    JOIN releases r ON r.release_id = a.release_id
    WHERE a.image_type = 'primary'
        AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
    {sort_clause}
    LIMIT %s
    """
    result = _db_conn.execute_query(query.format(sort_clause=sort_clause), (count,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_random_releases_with_artwork(_db_conn: PostgreSQLConnection, count: int = 20, seed: int = 0) -> pd.DataFrame:
    """Load random releases with full artwork data for navigation (Browse Collection)."""
    # Set random seed for consistent results
    if seed:
        _db_conn.execute_query(f"SELECT setseed({seed / 1000.0})")
    
    decade_filter = ""  # No decade filter for now
    query = RANDOM_RELEASES_QUERY % (decade_filter, "%s")
    result = _db_conn.execute_query(query, (count,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_tracks_for_release(_db_conn: PostgreSQLConnection, release_id: str) -> pd.DataFrame:
    """Load track listing for a specific release with rich details."""
    query = """
    SELECT 
        track_number,
        title,
        duration,
        artists,
        extraartists,
        producers,
        raw_track_data
    FROM tracks
    WHERE release_id = %s
    ORDER BY 
        CASE 
            WHEN track_number ~ '^[0-9]+$' THEN CAST(track_number AS INTEGER)
            ELSE 999
        END,
        track_number
    """
    result = _db_conn.execute_query(query, (release_id,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_release_details(_db_conn: PostgreSQLConnection, release_id: str) -> dict:
    """Load complete release details for accordion view."""
    query = """
    SELECT 
        r.*,
        rp.lowest_price,
        rp.currency,
        rp.num_for_sale,
        rp.last_seen as price_last_seen
    FROM releases r
    LEFT JOIN release_prices rp ON r.discogs_id = rp.discogs_release_id
    WHERE r.release_id = %s
    """
    result = _db_conn.execute_query(query, (release_id,))
    return result[0] if result else {}

def load_wantlist_items(_db_conn: PostgreSQLConnection, limit: int = 50) -> pd.DataFrame:
    """Load wantlist items with pricing data."""
    query = """
    SELECT 
        w.discogs_release_id,
        w.title,
        w.artist,
        w.year,
        w.label,
        w.format,
        w.genres,
        w.styles,
        w.notes,
        w.rating,
        w.added,
        rp.lowest_price,
        rp.currency,
        rp.num_for_sale,
        rp.availability,
        rp.last_seen as price_last_seen
    FROM wantlist w
    LEFT JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
    ORDER BY 
        CASE WHEN rp.availability = true THEN 0 ELSE 1 END,
        rp.lowest_price ASC NULLS LAST,
        w.added DESC
    LIMIT %s
    """
    result = _db_conn.execute_query(query, (limit,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_artist_gaps(_db_conn: PostgreSQLConnection, limit: int = 20) -> pd.DataFrame:
    """Find artists you collect but are missing albums from."""
    query = """
    WITH artist_collection AS (
        SELECT 
            artist,
            COUNT(*) as owned_releases,
            array_agg(DISTINCT year ORDER BY year) as owned_years
        FROM releases 
        WHERE artist IS NOT NULL
        GROUP BY artist
        HAVING COUNT(*) >= 2  -- Artists with 2+ releases
    ),
    artist_discog AS (
        SELECT 
            ad.artist_name,
            COUNT(*) as total_releases,
            COUNT(CASE WHEN ad.in_collection THEN 1 END) as owned_count,
            COUNT(CASE WHEN NOT ad.in_collection THEN 1 END) as missing_count,
            array_agg(DISTINCT ad.year ORDER BY ad.year) FILTER (WHERE NOT ad.in_collection) as missing_years
        FROM artist_discography ad
        WHERE ad.in_collection = false
        GROUP BY ad.artist_name
        HAVING COUNT(CASE WHEN NOT ad.in_collection THEN 1 END) > 0
    )
    SELECT 
        ac.artist,
        ac.owned_releases,
        ad.missing_count,
        ad.total_releases,
        ROUND((ac.owned_releases::decimal / ad.total_releases) * 100, 1) as completion_percentage,
        ad.missing_years[1:5] as next_missing_years
    FROM artist_collection ac
    JOIN artist_discog ad ON ac.artist = ad.artist_name
    WHERE ad.missing_count > 0
    ORDER BY completion_percentage DESC, ac.owned_releases DESC
    LIMIT %s
    """
    result = _db_conn.execute_query(query, (limit,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_label_gaps(_db_conn: PostgreSQLConnection, limit: int = 15) -> pd.DataFrame:
    """Find labels you collect but are missing releases from."""
    query = """
    WITH label_stats AS (
        SELECT 
            label,
            COUNT(*) as owned_releases,
            COUNT(DISTINCT artist) as unique_artists,
            AVG(rating) as avg_rating
        FROM releases 
        WHERE label IS NOT NULL AND label != ''
        GROUP BY label
        HAVING COUNT(*) >= 2  -- Labels with 2+ releases
    )
    SELECT 
        ls.label,
        ls.owned_releases,
        ls.unique_artists,
        ROUND(ls.avg_rating, 1) as avg_rating,
        CASE 
            WHEN ls.avg_rating >= 4 THEN '🔥 Hot Label'
            WHEN ls.owned_releases >= 5 THEN '📀 Major Focus'
            ELSE '🎯 Growing Interest'
        END as collection_status
    FROM label_stats ls
    ORDER BY ls.avg_rating DESC NULLS LAST, ls.owned_releases DESC
    LIMIT %s
    """
    result = _db_conn.execute_query(query, (limit,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_decade_gaps(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Find decades with gaps in collection."""
    query = """
    WITH decade_coverage AS (
        SELECT 
            (year / 10) * 10 as decade_start,
            COUNT(*) as releases_owned,
            MIN(year) as earliest_year,
            MAX(year) as latest_year,
            array_agg(DISTINCT year ORDER BY year) as years_owned
        FROM releases 
        WHERE year IS NOT NULL
        GROUP BY (year / 10) * 10
    ),
    decade_analysis AS (
        SELECT 
            decade_start,
            decade_start || 's' as decade_label,
            releases_owned,
            latest_year - earliest_year + 1 as year_span,
            array_length(years_owned, 1) as unique_years,
            ROUND((array_length(years_owned, 1)::decimal / (latest_year - earliest_year + 1)) * 100, 1) as coverage_percentage
        FROM decade_coverage
    )
    SELECT 
        decade_label,
        releases_owned,
        unique_years,
        year_span,
        coverage_percentage,
        CASE 
            WHEN coverage_percentage >= 80 THEN '✅ Complete'
            WHEN coverage_percentage >= 50 THEN '📈 Growing'
            ELSE '🎯 Opportunity'
        END as status
    FROM decade_analysis
    WHERE releases_owned > 0
    ORDER BY decade_start DESC
    """
    result = _db_conn.execute_query(query)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_format_gaps(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Analyze format distribution and gaps."""
    query = """
    SELECT 
        format,
        COUNT(*) as count,
        COUNT(DISTINCT artist) as unique_artists,
        AVG(rating) as avg_rating,
        MIN(year) as earliest,
        MAX(year) as latest
    FROM releases 
    WHERE format IS NOT NULL AND format != ''
    GROUP BY format
    ORDER BY count DESC
    """
    result = _db_conn.execute_query(query)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_budget_recommendations(_db_conn: PostgreSQLConnection, max_price: float = 50.0, limit: int = 20) -> pd.DataFrame:
    """Find affordable releases from your wantlist and similar items."""
    query = """
    WITH wantlist_recommendations AS (
        SELECT 
            w.discogs_release_id,
            w.title,
            w.artist,
            w.year,
            w.label,
            w.format,
            w.genres,
            w.styles,
            rp.lowest_price,
            rp.currency,
            rp.num_for_sale,
            'wantlist' as source,
            0 as priority_order
        FROM wantlist w
        INNER JOIN release_prices rp ON w.discogs_release_id = rp.discogs_release_id
        WHERE rp.lowest_price <= %s 
            AND rp.availability = true
            AND rp.lowest_price IS NOT NULL
    ),
    affordable_available AS (
        SELECT 
            rp.discogs_release_id,
            'Available Item'::text as title,
            'Various Artists'::text as artist,
            NULL::integer as year,
            'Various Labels'::text as label,
            'Unknown'::text as format,
            NULL::jsonb as genres,
            NULL::jsonb as styles,
            rp.lowest_price,
            rp.currency,
            rp.num_for_sale,
            'marketplace'::text as source,
            1 as priority_order
        FROM release_prices rp
        WHERE rp.lowest_price <= %s 
            AND rp.availability = true
            AND rp.lowest_price IS NOT NULL
            AND rp.discogs_release_id NOT IN (SELECT discogs_release_id FROM wantlist)
        ORDER BY rp.lowest_price ASC
        LIMIT 10
    )
    SELECT 
        discogs_release_id,
        title,
        artist,
        year,
        label,
        format,
        genres,
        styles,
        lowest_price,
        currency,
        num_for_sale,
        source
    FROM (
        SELECT * FROM wantlist_recommendations
        UNION ALL 
        SELECT * FROM affordable_available
    ) combined_results
    ORDER BY priority_order ASC, lowest_price ASC
    LIMIT %s
    """
    result = _db_conn.execute_query(query, (max_price, max_price, limit))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_top_remixers(_db_conn: PostgreSQLConnection, limit: int = 20) -> pd.DataFrame:
    """Load top remixers/producers from track extraartists data."""
    query = """
    WITH remix_artists AS (
        SELECT 
            r.release_id,
            r.title as release_title,
            r.artist as release_artist,
            r.year,
            r.genres,
            t.track_id,
            t.title as track_title,
            jsonb_array_elements(COALESCE(t.extraartists, '[]'::jsonb)) as extra_artist
        FROM releases r
        JOIN tracks t ON r.release_id = t.release_id
        WHERE t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb
    ),
    expanded_remix_artists AS (
        SELECT 
            extra_artist->>'name' as remixer_name,
            extra_artist->>'role' as role,
            release_id,
            year,
            jsonb_array_elements_text(COALESCE(genres, '[]'::jsonb)) as genre
        FROM remix_artists
        WHERE extra_artist->>'name' IS NOT NULL 
            AND extra_artist->>'name' != ''
            AND extra_artist->>'role' IS NOT NULL
            AND (
                lower(extra_artist->>'role') LIKE '%remix%' 
                OR lower(extra_artist->>'role') LIKE '%mix%' 
                OR lower(extra_artist->>'role') LIKE '%producer%'
                OR lower(extra_artist->>'role') LIKE '%produce%'
            )
    ),
    remixer_stats AS (
        SELECT 
            remixer_name,
            role,
            COUNT(*) as track_count,
            COUNT(DISTINCT release_id) as release_count,
            array_agg(DISTINCT genre) as genres_worked,
            MIN(year) as earliest_year,
            MAX(year) as latest_year,
            array_agg(DISTINCT year ORDER BY year) as active_years
        FROM expanded_remix_artists
        GROUP BY remixer_name, role
    )
    SELECT 
        remixer_name,
        role,
        track_count,
        release_count,
        genres_worked,
        earliest_year,
        latest_year,
        active_years
    FROM remixer_stats
    WHERE track_count >= 2  -- Filter for significant remixers
    ORDER BY track_count DESC, release_count DESC
    LIMIT %s
    """
    result = _db_conn.execute_query(query, (limit,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_remix_by_genre(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Analyze remix density by genre."""
    query = """
    WITH track_genres AS (
        SELECT 
            t.track_id,
            t.release_id,
            jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) as genre,
            CASE WHEN t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb 
                 THEN true ELSE false END as has_remix_credits
        FROM tracks t
        JOIN releases r ON t.release_id = r.release_id
        WHERE r.genres IS NOT NULL AND r.genres != '[]'::jsonb
    ),
    genre_remix_stats AS (
        SELECT 
            genre,
            COUNT(*) as total_tracks,
            COUNT(CASE WHEN has_remix_credits THEN 1 END) as tracks_with_remixes,
            ROUND(
                (COUNT(CASE WHEN has_remix_credits THEN 1 END)::decimal / COUNT(*)) * 100, 1
            ) as remix_percentage
        FROM track_genres
        WHERE genre IS NOT NULL AND genre != ''
        GROUP BY genre
        HAVING COUNT(*) >= 5  -- Only genres with substantial track count
    )
    SELECT * FROM genre_remix_stats
    ORDER BY remix_percentage DESC, total_tracks DESC
    """
    result = _db_conn.execute_query(query)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_remix_timeline(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Analyze remix activity by year/decade."""
    query = """
    WITH yearly_remix_stats AS (
        SELECT 
            r.year,
            (r.year / 10) * 10 as decade_start,
            COUNT(t.track_id) as total_tracks,
            COUNT(CASE WHEN t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb 
                  THEN 1 END) as remix_tracks,
            ROUND(
                (COUNT(CASE WHEN t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb 
                      THEN 1 END)::decimal / COUNT(t.track_id)) * 100, 1
            ) as remix_percentage
        FROM releases r
        JOIN tracks t ON r.release_id = t.release_id
        WHERE r.year IS NOT NULL AND r.year >= 1960 AND r.year <= 2030
        GROUP BY r.year
        HAVING COUNT(t.track_id) >= 3  -- Years with substantial track count
    )
    SELECT 
        year,
        decade_start,
        decade_start || 's' as decade_label,
        total_tracks,
        remix_tracks,
        remix_percentage
    FROM yearly_remix_stats
    ORDER BY year DESC
    """
    result = _db_conn.execute_query(query)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_most_remixed_tracks(_db_conn: PostgreSQLConnection, limit: int = 15) -> pd.DataFrame:
    """Find tracks with the most remix versions in collection."""
    query = """
    WITH track_remix_counts AS (
        SELECT 
            r.title as release_title,
            r.artist as release_artist,
            r.year,
            t.title as track_title,
            COUNT(remix_elem) as remix_count
        FROM releases r
        JOIN tracks t ON r.release_id = t.release_id
        LEFT JOIN LATERAL jsonb_array_elements(COALESCE(t.extraartists, '[]'::jsonb)) AS remix_elem ON true
        WHERE t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb
        GROUP BY r.release_id, r.title, r.artist, r.year, t.track_id, t.title
    ),
    aggregated_tracks AS (
        SELECT 
            COALESCE(track_title, release_title) as track_name,
            release_artist as artist,
            year,
            SUM(remix_count) as total_remixes,
            COUNT(*) as versions_in_collection
        FROM track_remix_counts
        GROUP BY COALESCE(track_title, release_title), release_artist, year
    )
    SELECT 
        track_name,
        artist,
        year,
        total_remixes,
        versions_in_collection
    FROM aggregated_tracks
    WHERE total_remixes >= 2  -- Only tracks with multiple remix credits
    ORDER BY total_remixes DESC, versions_in_collection DESC
    LIMIT %s
    """
    result = _db_conn.execute_query(query, (limit,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_producer_collaborations(_db_conn: PostgreSQLConnection, limit: int = 10) -> pd.DataFrame:
    """Find producers who frequently collaborate."""
    query = """
    WITH track_producers AS (
        SELECT 
            t.track_id,
            r.release_id,
            r.title as release_title,
            r.artist as release_artist,
            jsonb_array_elements(COALESCE(t.extraartists, '[]'::jsonb)) as producer
        FROM releases r
        JOIN tracks t ON r.release_id = t.release_id
        WHERE t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb
    ),
    producer_pairs AS (
        SELECT 
            p1.producer->>'name' as producer1,
            p2.producer->>'name' as producer2,
            COUNT(DISTINCT p1.release_id) as collaborations
        FROM track_producers p1
        JOIN track_producers p2 ON p1.track_id = p2.track_id
        WHERE p1.producer->>'name' < p2.producer->>'name'  -- Avoid duplicates
            AND p1.producer->>'name' IS NOT NULL AND p1.producer->>'name' != ''
            AND p2.producer->>'name' IS NOT NULL AND p2.producer->>'name' != ''
            AND (
                lower(p1.producer->>'role') LIKE '%remix%' OR lower(p1.producer->>'role') LIKE '%producer%' OR
                lower(p2.producer->>'role') LIKE '%remix%' OR lower(p2.producer->>'role') LIKE '%producer%'
            )
        GROUP BY p1.producer->>'name', p2.producer->>'name'
    )
    SELECT 
        producer1,
        producer2,
        collaborations,
        producer1 || ' & ' || producer2 as collaboration_name
    FROM producer_pairs
    WHERE collaborations >= 2  -- Only frequent collaborators
    ORDER BY collaborations DESC
    LIMIT %s
    """
    result = _db_conn.execute_query(query, (limit,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def search_by_remixer(_db_conn: PostgreSQLConnection, search_term: str, limit: int = 50, sort_clause: str = "ORDER BY r.year DESC, r.artist") -> pd.DataFrame:
    """Search for releases by remixer/producer name (unique releases only)."""
    
    # Handle RANDOM() sort for DISTINCT queries
    if "RANDOM()" in sort_clause:
        query = """
        WITH remixer_releases AS (
            SELECT DISTINCT
                r.release_id,
                r.title,
                r.artist,
                r.year,
                r.label,
                r.format,
                r.country,
                r.rating,
                a.local_file_path,
                a.thumbnail_file_path,
                a.original_url,
                RANDOM() as random_col
            FROM releases r
            JOIN tracks t ON r.release_id = t.release_id
            LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(t.extraartists, '[]'::jsonb)) as remixer_info
            WHERE t.extraartists IS NOT NULL 
                AND t.extraartists != '[]'::jsonb
                AND lower(remixer_info->>'name') LIKE lower(%s)
                AND remixer_info->>'name' IS NOT NULL
                AND remixer_info->>'name' != ''
                AND (
                    lower(remixer_info->>'role') LIKE '%%remix%%' 
                    OR lower(remixer_info->>'role') LIKE '%%mix%%' 
                    OR lower(remixer_info->>'role') LIKE '%%producer%%'
                    OR lower(remixer_info->>'role') LIKE '%%produce%%'
                )
        )
        SELECT * FROM remixer_releases
        ORDER BY random_col
        LIMIT %s
        """
    else:
        query = """
        WITH remixer_releases AS (
            SELECT DISTINCT
                r.release_id,
                r.title,
                r.artist,
                r.year,
                r.label,
                r.format,
                r.country,
                r.rating,
                a.local_file_path,
                a.thumbnail_file_path,
                a.original_url
            FROM releases r
            JOIN tracks t ON r.release_id = t.release_id
            LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(t.extraartists, '[]'::jsonb)) as remixer_info
            WHERE t.extraartists IS NOT NULL 
                AND t.extraartists != '[]'::jsonb
                AND lower(remixer_info->>'name') LIKE lower(%s)
                AND remixer_info->>'name' IS NOT NULL
                AND remixer_info->>'name' != ''
                AND (
                    lower(remixer_info->>'role') LIKE '%%remix%%' 
                    OR lower(remixer_info->>'role') LIKE '%%mix%%' 
                    OR lower(remixer_info->>'role') LIKE '%%producer%%'
                    OR lower(remixer_info->>'role') LIKE '%%produce%%'
                )
        )
        SELECT * FROM remixer_releases
        {sort_clause}
        LIMIT %s
        """
    
    result = _db_conn.execute_query(query.format(sort_clause=sort_clause), (f'%{search_term}%', limit))
    return pd.DataFrame(result) if result else pd.DataFrame()

def search_by_aliases(_db_conn: PostgreSQLConnection, search_term: str, limit: int = 50, sort_clause: str = "ORDER BY r.artist, r.year") -> pd.DataFrame:
    """Search for releases by artist aliases."""
    
    # Handle RANDOM() sort for DISTINCT queries
    if "RANDOM()" in sort_clause:
        query = """
        WITH alias_matches AS (
            SELECT DISTINCT
                r.release_id,
                r.title,
                r.artist,
                r.year,
                r.label,
                r.format,
                r.country,
                r.rating,
                'alias' as result_type,
                a.local_file_path,
                a.thumbnail_file_path,
                a.original_url,
                art.artist_name as alias_artist_name,
                STRING_AGG(DISTINCT alias_value, ', ') as found_alias
            FROM releases r
            LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
            JOIN artists art ON lower(r.artist) = lower(art.artist_name)
            CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(art.aliases, '[]'::jsonb)) AS alias_value
            WHERE lower(alias_value) LIKE lower(%s)
                AND alias_value IS NOT NULL
                AND alias_value != ''
            GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.format, r.country, r.rating,
                     a.local_file_path, a.thumbnail_file_path, a.original_url, art.artist_name
        )
        SELECT *, RANDOM() as random_col
        FROM alias_matches
        ORDER BY random_col
        LIMIT %s
        """
    else:
        query = """
        SELECT DISTINCT
            r.release_id,
            r.title,
            r.artist,
            r.year,
            r.label,
            r.format,
            r.country,
            r.rating,
            'alias' as result_type,
            a.local_file_path,
            a.thumbnail_file_path,
            a.original_url,
            art.artist_name as alias_artist_name,
            STRING_AGG(DISTINCT alias_value, ', ') as found_alias
        FROM releases r
        LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
        JOIN artists art ON lower(r.artist) = lower(art.artist_name)
        CROSS JOIN LATERAL jsonb_array_elements_text(COALESCE(art.aliases, '[]'::jsonb)) AS alias_value
        WHERE lower(alias_value) LIKE lower(%s)
            AND alias_value IS NOT NULL
            AND alias_value != ''
        GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.format, r.country, r.rating,
                 a.local_file_path, a.thumbnail_file_path, a.original_url, art.artist_name
        {sort_clause}
        LIMIT %s
        """
    
    result = _db_conn.execute_query(query.format(sort_clause=sort_clause), (f'%{search_term}%', limit))
    return pd.DataFrame(result) if result else pd.DataFrame()

@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_available_decades(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load available decades from the collection."""
    result = _db_conn.execute_query(AVAILABLE_DECADES_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_random_releases(_db_conn: PostgreSQLConnection, count: int = 25, decade_start: int | None = None, rand_token: int = 0) -> pd.DataFrame:
    """Load random releases with optional decade filter."""
    # Set random seed for consistent results
    if rand_token:
        _db_conn.execute_query(f"SELECT setseed({rand_token / 1000.0})")
    
    # Build decade filter
    decade_filter = ""
    params = [count]
    
    if decade_start is not None:
        decade_end = decade_start + 9
        decade_filter = "AND r.year BETWEEN %s AND %s"
        params = [decade_start, decade_end, count]
    
    query = RANDOM_RELEASES_QUERY % (decade_filter, "%s")
    result = _db_conn.execute_query(query, params)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_releases(_db_conn: PostgreSQLConnection, limit: int = 1000) -> pd.DataFrame:
    """Load releases with artwork information."""
    query = """
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
    GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
             r.genres, r.styles, r.producers, r.country, r.rating, r.condition, r.sleeve_condition,
             r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids,
             r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
    ORDER BY r.artist, r.year
    LIMIT %s
    """
    result = _db_conn.execute_query(query, (limit,))
    return pd.DataFrame(result) if result else pd.DataFrame()

def search_collection(_db_conn: PostgreSQLConnection, search_term: str) -> pd.DataFrame:
    """Search the collection with optimized full-text search if available."""
    # Try optimized full-text search first
    try:
        optimized_query = "SELECT * FROM search_releases_optimized(%s)"
        result = _db_conn.execute_query(optimized_query, (search_term,))
        if result:
            return pd.DataFrame(result)
    except Exception:
        # Fallback to basic search if optimized function doesn't exist
        pass
    
    # Fallback to original LIKE-based search
    search_pattern = f"%{search_term}%"
    result = _db_conn.execute_query(COLLECTION_SEARCH_QUERY, (search_pattern, search_pattern))
    return pd.DataFrame(result) if result else pd.DataFrame()

def fetch_release_stats(_db_conn: PostgreSQLConnection, discogs_id: int) -> Optional[Dict]:
    """Fetch release statistics including community and marketplace data."""
    result = _db_conn.execute_query(RELEASE_STATS_QUERY, (discogs_id,))
    return result[0] if result else None

def load_community_stats_check(_db_conn: PostgreSQLConnection) -> Optional[Dict]:
    """Load community statistics check data."""
    result = _db_conn.execute_query(COMMUNITY_STATS_CHECK_QUERY)
    return result[0] if result else None

def load_most_popular_releases(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load most popular releases by have count."""
    result = _db_conn.execute_query(MOST_POPULAR_RELEASES_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_most_wanted_releases(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load most wanted releases by want count."""
    result = _db_conn.execute_query(MOST_WANTED_RELEASES_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_highest_rated_releases(_db_conn: PostgreSQLConnection) -> pd.DataFrame:
    """Load highest rated releases by community rating."""
    result = _db_conn.execute_query(HIGHEST_RATED_RELEASES_QUERY)
    return pd.DataFrame(result) if result else pd.DataFrame()

def load_community_insights(_db_conn: PostgreSQLConnection) -> Optional[Dict]:
    """Load community insights data."""
    query = """
    SELECT 
        AVG(community_have_count) as avg_have_count,
        AVG(community_want_count) as avg_want_count,
        AVG(community_average_rating) as avg_community_rating,
        COUNT(CASE WHEN community_have_count > 1000 THEN 1 END) as popular_releases,
        COUNT(CASE WHEN community_want_count > 100 THEN 1 END) as highly_wanted_releases,
        COUNT(CASE WHEN community_average_rating > 4.0 AND community_rating_count >= 10 THEN 1 END) as highly_rated_releases
    FROM releases 
    WHERE community_have_count > 0 OR community_want_count > 0
    """
    result = _db_conn.execute_query(query)
    return result[0] if result else None
