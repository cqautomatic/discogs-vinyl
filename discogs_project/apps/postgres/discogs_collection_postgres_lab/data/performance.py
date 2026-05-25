"""
Performance optimization utilities for the Discogs collection application.
"""

import streamlit as st
import pandas as pd
from typing import Optional
from core.database import PostgreSQLConnection

def create_performance_indexes(db_conn: PostgreSQLConnection) -> bool:
    """Create performance indexes for better query performance."""
    indexes = [
        # GIN indexes for JSONB columns
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_genres_gin ON releases USING GIN (genres)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_styles_gin ON releases USING GIN (styles)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_producers_gin ON releases USING GIN (producers)",
        
        # Text search indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_title_gin ON releases USING GIN (to_tsvector('english', title))",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_artist_gin ON releases USING GIN (to_tsvector('english', artist))",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_label_gin ON releases USING GIN (to_tsvector('english', label))",
        
        # Regular indexes for common queries
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_year ON releases (year) WHERE year IS NOT NULL",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_rating ON releases (rating) WHERE rating > 0",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_discogs_id ON releases (discogs_id) WHERE discogs_id IS NOT NULL",
        
        # Community stats indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_community_have ON releases (community_have_count) WHERE community_have_count > 0",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_community_want ON releases (community_want_count) WHERE community_want_count > 0",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_releases_community_rating ON releases (community_average_rating) WHERE community_rating_count >= 10",
        
        # Artwork indexes
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_artwork_release_id ON artwork (release_id)",
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_artwork_image_type ON artwork (image_type)",
    ]
    
    try:
        for index_sql in indexes:
            db_conn.execute_query(index_sql)
        return True
    except Exception as e:
        st.error(f"Failed to create performance indexes: {e}")
        return False

def create_materialized_views(db_conn: PostgreSQLConnection) -> bool:
    """Create materialized views for expensive queries."""
    views = [
        # Collection statistics materialized view
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS collection_stats_mv AS
        SELECT 
            COUNT(*) as total_items,
            COUNT(CASE WHEN discogs_id IS NOT NULL THEN 1 END) as downloaded_items,
            COUNT(DISTINCT artist) as unique_artists,
            COUNT(DISTINCT label) as unique_labels,
            COUNT(DISTINCT country) as countries,
            MIN(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as earliest_year,
            MAX(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as latest_year,
            AVG(CASE WHEN rating > 0 THEN rating END) as avg_rating,
            COUNT(CASE WHEN rating > 0 THEN 1 END) as rated_items
        FROM releases
        """,
        
        # Artwork statistics materialized view
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS artwork_stats_mv AS
        SELECT 
            COUNT(*) as artwork_count,
            COALESCE(SUM(file_size), 0) as total_artwork_size_bytes
        FROM artwork
        """,
        
        # Decade analysis materialized view
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS decade_analysis_mv AS
        WITH decade_series AS (
            SELECT generate_series(1950, EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER, 10) AS decade
        ),
        decade_counts AS (
            SELECT 
                (year / 10) * 10 AS decade,
                COUNT(*) as release_count
            FROM releases 
            WHERE year IS NOT NULL AND year >= 1950
            GROUP BY (year / 10) * 10
        )
        SELECT 
            ds.decade,
            COALESCE(dc.release_count, 0) as release_count
        FROM decade_series ds
        LEFT JOIN decade_counts dc ON ds.decade = dc.decade
        ORDER BY ds.decade
        """,
        
        # Genre analysis materialized view
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS genre_analysis_mv AS
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
        """,
        
        # Style analysis materialized view
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS style_analysis_mv AS
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
        """
    ]
    
    try:
        for view_sql in views:
            db_conn.execute_query(view_sql)
        return True
    except Exception as e:
        st.error(f"Failed to create materialized views: {e}")
        return False

def refresh_materialized_views(db_conn: PostgreSQLConnection) -> bool:
    """Refresh all materialized views."""
    views = [
        "collection_stats_mv",
        "artwork_stats_mv", 
        "decade_analysis_mv",
        "genre_analysis_mv",
        "style_analysis_mv"
    ]
    
    try:
        for view in views:
            db_conn.execute_query(f"REFRESH MATERIALIZED VIEW {view}")
        return True
    except Exception as e:
        st.error(f"Failed to refresh materialized views: {e}")
        return False

def create_optimized_functions(db_conn: PostgreSQLConnection) -> bool:
    """Create optimized database functions."""
    functions = [
        # Optimized search function using full-text search
        """
        CREATE OR REPLACE FUNCTION search_releases_optimized(search_term text)
        RETURNS TABLE(
            release_id integer,
            title text,
            artist text,
            year integer,
            label text,
            catno text,
            format text,
            genres jsonb,
            styles jsonb,
            country text,
            rating integer,
            condition text,
            community_have_count integer,
            community_want_count integer,
            community_average_rating numeric,
            community_rating_count integer,
            artwork_files json
        ) AS $$
        BEGIN
            RETURN QUERY
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
                           ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END
                       ) FILTER (WHERE a.artwork_id IS NOT NULL),
                       '[]'::json
                   ) as artwork_files
            FROM releases r
            LEFT JOIN artwork a ON r.release_id = a.release_id
            WHERE 
                to_tsvector('english', r.title) @@ plainto_tsquery('english', search_term) OR
                to_tsvector('english', r.artist) @@ plainto_tsquery('english', search_term) OR
                to_tsvector('english', COALESCE(r.label, '')) @@ plainto_tsquery('english', search_term)
            GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
                     r.genres, r.styles, r.country, r.rating, r.condition,
                     r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
            ORDER BY r.artist, r.year;
        END;
        $$ LANGUAGE plpgsql;
        """,
        
        # Function to refresh all performance views
        """
        CREATE OR REPLACE FUNCTION refresh_performance_views() RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW collection_stats_mv;
            REFRESH MATERIALIZED VIEW artwork_stats_mv;
            REFRESH MATERIALIZED VIEW decade_analysis_mv;
            REFRESH MATERIALIZED VIEW genre_analysis_mv;
            REFRESH MATERIALIZED VIEW style_analysis_mv;
        END;
        $$ LANGUAGE plpgsql;
        """
    ]
    
    try:
        for function_sql in functions:
            db_conn.execute_query(function_sql)
        return True
    except Exception as e:
        st.error(f"Failed to create optimized functions: {e}")
        return False

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_performance_stats(db_conn: PostgreSQLConnection) -> Optional[pd.DataFrame]:
    """Load database performance statistics."""
    query = """
    SELECT 
        'Total Relations' as metric,
        COUNT(*) as value
    FROM information_schema.tables 
    WHERE table_schema = 'collection_data'
    
    UNION ALL
    
    SELECT 
        'Total Indexes' as metric,
        COUNT(*) as value
    FROM pg_indexes 
    WHERE schemaname = 'collection_data'
    
    UNION ALL
    
    SELECT 
        'Database Size' as metric,
        pg_size_pretty(pg_database_size(current_database()))::text as value
    """
    
    try:
        result = db_conn.execute_query(query)
        return pd.DataFrame(result) if result else None
    except Exception:
        return None

def setup_performance_optimizations(db_conn: PostgreSQLConnection) -> dict:
    """Set up all performance optimizations and return status."""
    results = {
        'indexes': False,
        'views': False,
        'functions': False
    }
    
    with st.spinner("Creating performance indexes..."):
        results['indexes'] = create_performance_indexes(db_conn)
    
    with st.spinner("Creating materialized views..."):
        results['views'] = create_materialized_views(db_conn)
    
    with st.spinner("Creating optimized functions..."):
        results['functions'] = create_optimized_functions(db_conn)
    
    if all(results.values()):
        with st.spinner("Refreshing materialized views..."):
            refresh_materialized_views(db_conn)
    
    return results

def display_performance_dashboard(db_conn: PostgreSQLConnection):
    """Display performance optimization dashboard."""
    st.header("⚡ Performance Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Setup Performance Optimizations"):
            results = setup_performance_optimizations(db_conn)
            
            if all(results.values()):
                st.success("✅ All performance optimizations applied successfully!")
            else:
                st.warning("⚠️ Some optimizations failed. Check logs for details.")
                for key, success in results.items():
                    status = "✅" if success else "❌"
                    st.write(f"{status} {key.title()}")
    
    with col2:
        if st.button("🔄 Refresh Materialized Views"):
            if refresh_materialized_views(db_conn):
                st.success("✅ Materialized views refreshed!")
            else:
                st.error("❌ Failed to refresh materialized views")
    
    # Performance statistics
    stats_df = load_performance_stats(db_conn)
    if stats_df is not None:
        st.subheader("📊 Database Statistics")
        
        # Display stats as cards instead of table
        for idx, row in stats_df.iterrows():
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Metric", row.get('metric', 'Unknown'))
                with col2:
                    st.metric("Value", row.get('value', 'N/A'))
                with col3:
                    st.metric("Unit", row.get('unit', ''))
                st.divider()
    
    # Cache statistics
    st.subheader("💾 Cache Statistics")
    cache_stats = st.cache_data.get_stats()
    if cache_stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Cache Hits", cache_stats[0].cache_hits)
        with col2:
            st.metric("Cache Misses", cache_stats[0].cache_misses)
        with col3:
            hit_rate = cache_stats[0].cache_hits / (cache_stats[0].cache_hits + cache_stats[0].cache_misses) * 100
            st.metric("Hit Rate", f"{hit_rate:.1f}%")
