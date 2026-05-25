#!/usr/bin/env python3
"""
Streamlit app for browsing Discogs collection with artwork display.
This app connects to PostgreSQL and displays your collection with image galleries.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import matplotlib  # Ensure matplotlib available for pandas Styler gradients
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import psycopg2
import psycopg2.extras
from dataclasses import dataclass

# Page config
st.set_page_config(
    page_title="🎵 Discogs Collection Browser",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme selection and CSS
def apply_theme_css():
    """Apply theme-aware CSS based on user selection."""
    # Theme selector in sidebar
    if 'theme_mode' not in st.session_state:
        st.session_state.theme_mode = 'auto'
    
    with st.sidebar:
        st.markdown("### 🎨 Theme")
        theme_mode = st.selectbox(
            "Choose theme:",
            options=['auto', 'light', 'dark'],
            index=['auto', 'light', 'dark'].index(st.session_state.theme_mode),
            key='theme_selector'
        )
        st.session_state.theme_mode = theme_mode

    # Determine effective theme
    if theme_mode == 'auto':
        # Default to light since Streamlit doesn't support system detection
        effective_theme = 'light'
        st.sidebar.caption("ℹ️ Auto mode defaults to light theme")
    else:
        effective_theme = theme_mode

    # Apply theme-specific CSS
    if effective_theme == 'dark':
        css = """
        <style>
            .stApp {
                background-color: #0e1117;
                color: #e0e0e0;
            }
            .release-card { 
                background-color: #1e222b !important; 
                border: 1px solid #2a2f3a !important;
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }
            .genre-tag { 
                background-color: #243447 !important; 
                color: #9ecbff !important;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
                margin: 2px;
                display: inline-block;
            }
            .artwork-container { 
                background-color: #141823 !important; 
                border: 2px solid #2a2f3a !important;
                border-radius: 8px;
                padding: 5px;
                text-align: center;
            }
            .main-header {
                font-size: 2.5rem;
                color: #58a6ff;
                text-align: center;
                padding: 1rem 0;
                border-bottom: 2px solid #58a6ff;
                margin-bottom: 2rem;
            }
            .image-counter {
                font-size: 0.8rem;
                color: #8b949e;
                margin-top: 5px;
            }
        </style>
        """
    else:  # light theme
        css = """
        <style>
            .stApp {
                background-color: #ffffff;
                color: #222222;
            }
            .release-card { 
                background-color: #fafafa !important; 
                border: 1px solid #dddddd !important;
                border-radius: 10px;
                padding: 15px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .genre-tag { 
                background-color: #e1ecf4 !important; 
                color: #39739d !important;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
                margin: 2px;
                display: inline-block;
            }
            .artwork-container { 
                background-color: #ffffff !important; 
                border: 2px solid #dddddd !important;
                border-radius: 8px;
                padding: 5px;
                text-align: center;
            }
            .main-header {
                font-size: 2.5rem;
                color: #1f77b4;
                text-align: center;
                padding: 1rem 0;
                border-bottom: 2px solid #1f77b4;
                margin-bottom: 2rem;
            }
            .image-counter {
                font-size: 0.8rem;
                color: #666;
                margin-top: 5px;
            }
        </style>
        """
    
    st.markdown(css, unsafe_allow_html=True)

# Apply theme CSS
apply_theme_css()

@dataclass
class PostgreSQLConfig:
    """Configuration for PostgreSQL connection."""
    host: str = "localhost"
    port: int = 5432
    database: str = "discogs_collection"
    username: str = "postgres"
    password: str = "postgres"
    schema: str = "collection_data"

class PostgreSQLConnection:
    """Manages PostgreSQL database connection."""
    
    def __init__(self, config: Optional[PostgreSQLConfig] = None):
        self.config = config or get_postgres_config_from_secrets_env()
        self.connection = None
        self.connect()
    
    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self.connection.set_session(autocommit=True)
            
            # Set search path to our schema
            with self.connection.cursor() as cursor:
                cursor.execute(f"SET search_path TO {self.config.schema}, public")
                
        except Exception as e:
            st.error(f"Failed to connect to PostgreSQL: {e}")
            self.connection = None
    
    def execute_query(self, query: str, params=None):
        """Execute a query and return results as DataFrame."""
        if not self.connection:
            return pd.DataFrame()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                columns = [desc[0] for desc in cursor.description]
                data = cursor.fetchall()
                return pd.DataFrame(data, columns=columns)
        except Exception as e:
            st.error(f"Query failed: {e}")
            return pd.DataFrame()

def get_postgres_config_from_secrets_env() -> PostgreSQLConfig:
    """Build PostgreSQLConfig from (priority): secrets.toml → discogs_config.json → env vars."""
    # Defaults
    cfg = PostgreSQLConfig()
    # Prefer secrets.toml
    def _to_int(val, default):
        try:
            return int(val)
        except Exception:
            return default
    try:
        secrets_obj = st.secrets  # Streamlit auto-loads .streamlit/secrets.toml
        # Prefer [postgres] section; fall back to flat keys
        pg = {}
        if isinstance(secrets_obj, dict) and 'postgres' in secrets_obj:
            pg = secrets_obj['postgres']
        elif hasattr(secrets_obj, 'get'):
            pg = secrets_obj.get('postgres', {})

        # Support multiple key aliases
        if pg:
            cfg.host = pg.get('host', cfg.host)
            cfg.port = _to_int(pg.get('port', cfg.port), cfg.port)
            cfg.database = pg.get('database', pg.get('db', pg.get('dbname', cfg.database)))
            cfg.username = pg.get('user', pg.get('username', cfg.username))
            cfg.password = pg.get('password', pg.get('pwd', cfg.password))
            cfg.schema = pg.get('schema', cfg.schema)
        else:
            cfg.host = secrets_obj.get('PGHOST', cfg.host)
            cfg.port = _to_int(secrets_obj.get('PGPORT', cfg.port), cfg.port)
            cfg.database = secrets_obj.get('PGDATABASE', cfg.database)
            cfg.username = secrets_obj.get('PGUSER', cfg.username)
            cfg.password = secrets_obj.get('PGPASSWORD', cfg.password)
            cfg.schema = secrets_obj.get('POSTGRES_SCHEMA', secrets_obj.get('PGSCHEMA', cfg.schema))
    except Exception:
        pass

    # 2) discogs_config.json fallback (if any field still default)
    try:
        from pathlib import Path as _P
        jpath = _P('discogs_config.json')
        if jpath.exists():
            import json as _json
            with open(jpath, 'r') as jf:
                jc = _json.load(jf)
            p = jc.get('postgres') if isinstance(jc.get('postgres'), dict) else jc
            if isinstance(p, dict):
                cfg.host = p.get('host', cfg.host)
                cfg.port = _to_int(p.get('port', cfg.port), cfg.port)
                cfg.database = p.get('database', p.get('db', p.get('dbname', cfg.database)))
                cfg.username = p.get('user', p.get('username', cfg.username))
                cfg.password = p.get('password', p.get('pwd', cfg.password))
                cfg.schema = p.get('schema', cfg.schema)
    except Exception:
        pass

    # 3) Env vars (last resort)
    cfg.host = os.getenv("PGHOST", cfg.host)
    cfg.port = _to_int(os.getenv("PGPORT", cfg.port), cfg.port)
    cfg.database = os.getenv("PGDATABASE", cfg.database)
    cfg.username = os.getenv("PGUSER", cfg.username)
    cfg.password = os.getenv("PGPASSWORD", cfg.password)
    cfg.schema = os.getenv("POSTGRES_SCHEMA", os.getenv("PGSCHEMA", cfg.schema))
    # Default username if still not provided
    if not cfg.username or str(cfg.username).strip() == "":
        cfg.username = "discogs_user"
    return cfg

# Safe missing-value check that won't error on arrays/lists
def is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, dict, tuple, set)):
        return False
    try:
        return pd.isna(value)
    except Exception:
        return False

def get_color_map(items, color_scheme):
    """Generate color map based on selected color scheme."""
    n = max(len(items), 1)
    
    if color_scheme == "Rainbow":
        from plotly import colors as pcolors
        color_list = pcolors.sample_colorscale('Rainbow', [i/(n-1) if n>1 else 0.5 for i in range(n)])
        return {items[i]: color_list[i] for i in range(n)}
    else:
        # Single color schemes
        color_maps = {
            "Blue": "Blues",
            "Green": "Greens", 
            "Red": "Reds",
            "Purple": "Purples",
            "Orange": "Oranges"
        }
        from plotly import colors as pcolors
        colorscale = color_maps.get(color_scheme, "Blues")
        # For single colors, use gradient from light to dark
        color_list = pcolors.sample_colorscale(colorscale, [0.3 + 0.7*i/(n-1) if n>1 else 0.7 for i in range(n)])
        return {items[i]: color_list[i] for i in range(n)}

# Safe Styler background gradient without hard dependency on matplotlib
def style_with_background(df: pd.DataFrame, subset: list, cmap: str, low: float = 0.3, high: float = 0.9, format_map: dict | None = None):
    try:
        styler = df.style
        if format_map:
            styler = styler.format(format_map)
        # background_gradient requires matplotlib; guard with try
        try:
            return styler.background_gradient(subset=subset, cmap=cmap, low=low, high=high)
        except ImportError:
            # Fall back to formatted styler without gradient
            return styler
    except Exception:
        # Fall back to plain DataFrame
        return df

# Database query functions
@st.cache_data
def load_collection_stats(_db_conn):
    """Load collection statistics."""
    query = """
    SELECT 
        COUNT(*) as total_items,
        COUNT(*) as downloaded_items,
        COUNT(DISTINCT artist) as unique_artists,
        COUNT(DISTINCT label) as unique_labels,
        COUNT(DISTINCT country) as countries,
        MIN(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as earliest_year,
        MAX(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) as latest_year,
        (MAX(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END) - 
         MIN(CASE WHEN year IS NOT NULL AND year >= 1930 THEN year END)) as years_span,
        AVG(rating) as avg_rating,
        COUNT(CASE WHEN rating IS NOT NULL AND rating > 0 THEN 1 END) as rated_items,
        (SELECT COUNT(*) FROM artwork) as artwork_count,
        (SELECT COALESCE(SUM(file_size), 0) FROM artwork) as total_artwork_size_bytes
    FROM releases
    WHERE title IS NOT NULL
    """
    return _db_conn.execute_query(query)

@st.cache_data
def load_genre_analysis(_db_conn):
    """Load genre analysis data."""
    query = """
    SELECT 
        genre,
        COUNT(*) as release_count,
        AVG(year) as avg_year,
        COUNT(DISTINCT artist) as unique_artists,
        AVG(rating) as avg_rating
    FROM (
        SELECT 
            r.*,
            jsonb_array_elements_text(r.genres) as genre
        FROM releases r 
        WHERE r.genres IS NOT NULL AND jsonb_array_length(r.genres) > 0
    ) genre_releases
    GROUP BY genre
    ORDER BY release_count DESC
    LIMIT 20
    """
    return _db_conn.execute_query(query)

@st.cache_data
def load_style_analysis(_db_conn):
    """Load style analysis data."""
    query = """
    SELECT 
        style,
        COUNT(*) as release_count,
        AVG(year) as avg_year,
        COUNT(DISTINCT artist) as unique_artists,
        AVG(rating) as avg_rating
    FROM (
        SELECT 
            r.*,
            jsonb_array_elements_text(r.styles) as style
        FROM releases r 
        WHERE r.styles IS NOT NULL AND jsonb_array_length(r.styles) > 0
    ) style_releases
    GROUP BY style
    ORDER BY release_count DESC
    LIMIT 20
    """
    return _db_conn.execute_query(query)

@st.cache_data
def load_styles_for_genre(_db_conn, genre: str):
    """Load styles breakdown for a specific genre."""
    query = """
    SELECT 
        style,
        COUNT(*) as release_count,
        AVG(year) as avg_year,
        COUNT(DISTINCT artist) as unique_artists,
        AVG(rating) as avg_rating
    FROM (
        SELECT 
            r.*,
            jsonb_array_elements_text(r.styles) as style
        FROM releases r 
        WHERE r.genres IS NOT NULL AND jsonb_array_length(r.genres) > 0
        AND r.styles IS NOT NULL AND jsonb_array_length(r.styles) > 0
        AND r.genres @> to_jsonb(%s)
    ) style_releases
    GROUP BY style
    ORDER BY release_count DESC
    """
    return _db_conn.execute_query(query, (genre,))

@st.cache_data
def load_genres_for_style(_db_conn, style: str):
    """Load genres breakdown for a specific style."""
    query = """
    SELECT 
        genre,
        COUNT(*) as release_count,
        AVG(year) as avg_year,
        COUNT(DISTINCT artist) as unique_artists,
        AVG(rating) as avg_rating
    FROM (
        SELECT 
            r.*,
            jsonb_array_elements_text(r.genres) as genre
        FROM releases r 
        WHERE r.genres IS NOT NULL AND jsonb_array_length(r.genres) > 0
        AND r.styles IS NOT NULL AND jsonb_array_length(r.styles) > 0
        AND r.styles @> to_jsonb(%s)
    ) genre_releases
    GROUP BY genre
    ORDER BY release_count DESC
    """
    return _db_conn.execute_query(query, (style,))

@st.cache_data
def load_releases_for_genre(_db_conn, genre: str, offset: int = 0, limit: int = 25, random_seed: int = 0):
    """Load releases for a specific genre with pagination and randomization."""
    query = """
    SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format,
           r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition,
           r.date_added, r.artwork_urls, r.local_artwork_paths,
           r.copies_count, r.instance_ids,
           r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count,
           COALESCE(
               JSON_AGG(
                   JSON_BUILD_OBJECT(
                       'artwork_id', a.artwork_id,
                       'image_type', a.image_type,
                       'original_url', a.original_url,
                       'local_file_path', a.local_file_path,
                       'thumbnail_file_path', a.thumbnail_file_path,
                       'file_size', a.file_size,
                       'image_width', a.image_width,
                       'image_height', a.image_height
                   ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END, a.artwork_id
               ) FILTER (WHERE a.artwork_id IS NOT NULL),
               '[]'::json
           ) as artwork_files
    FROM releases r
    LEFT JOIN artwork a ON r.release_id = a.release_id
    WHERE r.genres IS NOT NULL AND jsonb_array_length(r.genres) > 0
    AND r.genres @> to_jsonb(%s)
    GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format,
             r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition,
             r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids,
             r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
    ORDER BY RANDOM()
    LIMIT %s OFFSET %s
    """
    return _db_conn.execute_query(query, (genre, limit, offset))

@st.cache_data
def load_releases_for_style(_db_conn, style: str, offset: int = 0, limit: int = 25, random_seed: int = 0):
    """Load releases for a specific style with pagination and randomization."""
    query = """
    SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format,
           r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition,
           r.date_added, r.artwork_urls, r.local_artwork_paths,
           r.copies_count, r.instance_ids,
           r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count,
           COALESCE(
               JSON_AGG(
                   JSON_BUILD_OBJECT(
                       'artwork_id', a.artwork_id,
                       'image_type', a.image_type,
                       'original_url', a.original_url,
                       'local_file_path', a.local_file_path,
                       'thumbnail_file_path', a.thumbnail_file_path,
                       'file_size', a.file_size,
                       'image_width', a.image_width,
                       'image_height', a.image_height
                   ) ORDER BY CASE a.image_type WHEN 'primary' THEN 0 ELSE 1 END, a.artwork_id
               ) FILTER (WHERE a.artwork_id IS NOT NULL),
               '[]'::json
           ) as artwork_files
    FROM releases r
    LEFT JOIN artwork a ON r.release_id = a.release_id
    WHERE r.styles IS NOT NULL AND jsonb_array_length(r.styles) > 0
    AND r.styles @> to_jsonb(%s)
    GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format,
             r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition,
             r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids,
             r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
    ORDER BY RANDOM()
    LIMIT %s OFFSET %s
    """
    return _db_conn.execute_query(query, (style, limit, offset))

@st.cache_data
def get_total_releases_for_genre(_db_conn, genre: str):
    """Get total count of releases for a genre."""
    query = """
    SELECT COUNT(*) as total
    FROM releases r
    WHERE r.genres IS NOT NULL AND jsonb_array_length(r.genres) > 0
    AND r.genres @> to_jsonb(%s)
    """
    result = _db_conn.execute_query(query, (genre,))
    return result[0]['total'] if result else 0

@st.cache_data
def get_total_releases_for_style(_db_conn, style: str):
    """Get total count of releases for a style."""
    query = """
    SELECT COUNT(*) as total
    FROM releases r
    WHERE r.styles IS NOT NULL AND jsonb_array_length(r.styles) > 0
    AND r.styles @> to_jsonb(%s)
    """
    result = _db_conn.execute_query(query, (style,))
    return result[0]['total'] if result else 0

@st.cache_data
def load_decade_analysis(_db_conn):
    """Load decade analysis data with gaps filled."""
    query = """
    WITH decade_range AS (
        SELECT generate_series(1950, EXTRACT(YEAR FROM CURRENT_DATE)::int, 10) as decade
    ),
    decade_data AS (
        SELECT 
            (year / 10) * 10 as decade,
            COUNT(*) as release_count,
            COUNT(DISTINCT artist) as unique_artists
    FROM releases 
    WHERE year IS NOT NULL AND year >= 1950
    GROUP BY decade
    )
    SELECT 
        dr.decade,
        COALESCE(dd.release_count, 0) as release_count,
        COALESCE(dd.unique_artists, 0) as unique_artists
    FROM decade_range dr
    LEFT JOIN decade_data dd ON dr.decade = dd.decade
    ORDER BY dr.decade
    """
    return _db_conn.execute_query(query)

@st.cache_data
def load_year_breakdown(_db_conn, decade_start: int):
    query = """
    WITH year_range AS (
        SELECT generate_series(%s, %s) as year
    ),
    year_data AS (
        SELECT year, COUNT(*) AS release_count
        FROM releases
        WHERE year IS NOT NULL AND year BETWEEN %s AND %s
        GROUP BY year
    )
    SELECT 
        yr.year,
        COALESCE(yd.release_count, 0) as release_count
    FROM year_range yr
    LEFT JOIN year_data yd ON yr.year = yd.year
    ORDER BY yr.year
    """
    decade_end = decade_start + 9
    return _db_conn.execute_query(query, (decade_start, decade_end, decade_start, decade_end))

@st.cache_data
def load_releases_for_year(_db_conn, year: int, limit: int, offset: int):
    query = """
    SELECT r.release_id, r.title, r.artist, r.label,
           COALESCE(a.thumbnail_file_path, a.local_file_path) AS thumb,
           COALESCE(a.original_url, r.artwork_urls->>0) AS url
    FROM releases r
    LEFT JOIN LATERAL (
        SELECT * FROM artwork a
        WHERE a.release_id = r.release_id AND a.image_type = 'primary'
        ORDER BY a.download_date DESC NULLS LAST
        LIMIT 1
    ) a ON TRUE
    WHERE r.year = %s
    ORDER BY r.title
    LIMIT %s OFFSET %s
    """
    return _db_conn.execute_query(query, (year, limit, offset))

@st.cache_data
def load_collection_valuation(_db_conn):
    """Load collection valuation stats from release_prices."""
    query = """
    SELECT currency,
           COUNT(*) AS num_priced,
           SUM(lowest_price) AS total_low_value,
           AVG(lowest_price) AS avg_price,
           MIN(lowest_price) AS min_price,
           MAX(lowest_price) AS max_price
    FROM release_prices
    WHERE lowest_price IS NOT NULL
    GROUP BY currency
    ORDER BY num_priced DESC
    """
    return _db_conn.execute_query(query)

@st.cache_data
def load_random_covers(_db_conn, count: int = 10, seed: int = 0):
    """Load random primary covers for the wall."""
    query = """
    SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, r.title, r.artist
    FROM artwork a
    JOIN releases r ON r.release_id = a.release_id
    WHERE a.image_type = 'primary'
      AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
    ORDER BY RANDOM()
    LIMIT %s
    """
    return _db_conn.execute_query(query, (count,))

@st.cache_data
def load_available_decades(_db_conn):
    """Return available decades present in the collection."""
    query = """
    SELECT DISTINCT (year / 10) * 10 AS decade
    FROM releases
    WHERE year IS NOT NULL
    ORDER BY decade
    """
    return _db_conn.execute_query(query)

@st.cache_data
def load_random_releases(_db_conn, count: int = 25, decade_start: int | None = None, rand_token: int = 0):
    """Load a random sample of releases, optionally filtered to a decade.

    rand_token is unused in SQL but influences caching so each refresh returns a new sample.
    """
    base_select = """
    SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format,
           r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition,
           r.date_added, r.artwork_urls, r.local_artwork_paths,
           r.copies_count, r.instance_ids,
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
    """
    params = []
    where_clauses = []
    if decade_start is not None:
        where_clauses.append("r.year BETWEEN %s AND %s + 9")
        params.extend([decade_start, decade_start])
    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    query = f"""
    {base_select}
    {where_sql}
    GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format,
             r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition,
             r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids,
             r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
    ORDER BY RANDOM()
    LIMIT %s
    """
    params.append(count)
    # Include rand_token in cache key effect
    _ = rand_token
    return _db_conn.execute_query(query, tuple(params))

@st.cache_data
def load_releases(_db_conn, limit: int = 1000):
    """Load releases data with artwork information."""
    query = f"""
    SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
           r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition, 
           r.date_added, r.artwork_urls, r.local_artwork_paths,
           r.copies_count, r.instance_ids,
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
             r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition, 
             r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids,
             r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
    ORDER BY r.date_added DESC 
    LIMIT {limit}
    """
    return _db_conn.execute_query(query)

@st.cache_data
def search_collection(_db_conn, search_term: str):
    """Search the collection with basic text matching."""
    query = """
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
        UPPER(r.artist) LIKE UPPER(%s) OR
        UPPER(r.label) LIKE UPPER(%s) OR
        r.genres::text ILIKE %s OR
        r.styles::text ILIKE %s OR
        COALESCE(r.producers::text,'') ILIKE %s OR
        EXISTS (
            SELECT 1 FROM tracks t 
            WHERE t.release_id = r.release_id 
              AND (
                    UPPER(t.title) LIKE UPPER(%s) OR 
                    t.artists::text ILIKE %s
                  )
        )
    GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
             r.genres, r.styles, r.country, r.rating, r.condition, r.sleeve_condition, 
             r.date_added, r.artwork_urls, r.local_artwork_paths, r.copies_count, r.instance_ids,
             r.community_have_count, r.community_want_count, r.community_average_rating, r.community_rating_count
    ORDER BY r.artist, r.year
    """
    search_pattern = f"%{search_term}%"
    return _db_conn.execute_query(query, (
        search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern,
        search_pattern, search_pattern
    ))

def display_artwork_gallery(artwork_files: List[Dict], release_id: str, release_title: str):
    """Display an interactive artwork gallery for a release with full-size viewing capability."""
    if not artwork_files:
        st.image("https://via.placeholder.com/150x150?text=No+Image", width=150)
        return

    gallery_key = f"gallery_{release_id}"
    fullsize_key = f"fs_state_{release_id}"
    if gallery_key not in st.session_state:
        st.session_state[gallery_key] = 0
    if fullsize_key not in st.session_state:
        st.session_state[fullsize_key] = False

    current_idx = st.session_state[gallery_key]
    current_artwork = artwork_files[current_idx]

    if st.session_state[fullsize_key]:
        st.subheader(f"🖼️ {release_title} - {current_artwork.get('image_type', 'Image')}")

        image_displayed = False
        if current_artwork.get('local_file_path'):
            p = Path(current_artwork['local_file_path'])
            if p.exists():
                st.image(str(p), caption=f"{current_artwork.get('image_type', 'Image')} - Full Size")
                image_displayed = True
                if current_artwork.get('image_width') and current_artwork.get('image_height'):
                    st.caption(f"📐 {current_artwork['image_width']}×{current_artwork['image_height']} pixels")
                if current_artwork.get('file_size'):
                    file_size_mb = current_artwork['file_size'] / (1024 * 1024)
                    st.caption(f"💾 {file_size_mb:.1f} MB")
        if not image_displayed and current_artwork.get('original_url'):
            st.image(current_artwork['original_url'], caption=f"{current_artwork.get('image_type', 'Image')} - Full Size")
            image_displayed = True
        if not image_displayed:
            st.warning("Image not available")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("◀ Previous", key=f"fullprev_{release_id}"):
                st.session_state[gallery_key] = (current_idx - 1) % len(artwork_files)
                st.rerun()
        with c2:
            if st.button("🔙 Back to Gallery", key=f"back_{release_id}"):
                st.session_state[fullsize_key] = False
                st.rerun()
        with c3:
            if st.button("Next ▶", key=f"fullnext_{release_id}"):
                st.session_state[gallery_key] = (current_idx + 1) % len(artwork_files)
                st.rerun()
        return

    # Thumbnail view
    image_displayed = False
    thumb_path = current_artwork.get('thumbnail_file_path') or current_artwork.get('local_file_path')
    if thumb_path and Path(thumb_path).exists():
        st.image(str(Path(thumb_path)), width=150, caption=f"{current_artwork.get('image_type', 'Image')}")
        image_displayed = True
    if not image_displayed and current_artwork.get('original_url'):
        st.image(current_artwork['original_url'], width=150, caption=f"{current_artwork.get('image_type', 'Image')}")
        image_displayed = True
    if not image_displayed:
        st.image("https://via.placeholder.com/150x150?text=No+Image", width=150)

    if len(artwork_files) > 1:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("◀", key=f"prev_{release_id}"):
                st.session_state[gallery_key] = (current_idx - 1) % len(artwork_files)
                st.rerun()
        with c2:
            st.markdown(f"<div class='image-counter'>{current_idx + 1} of {len(artwork_files)}</div>", unsafe_allow_html=True)
            image_type = current_artwork.get('image_type', 'Unknown')
            if image_type != 'primary':
                st.caption(f"📷 {image_type}")
        with c3:
            if st.button("▶", key=f"next_{release_id}"):
                st.session_state[gallery_key] = (current_idx + 1) % len(artwork_files)
                st.rerun()

    if st.button("🔍 View Full Size", key=f"btn_fullsize_{release_id}"):
        st.session_state[fullsize_key] = True
        st.rerun()

def display_collection_overview(db_conn):
    """Display collection overview with key metrics."""
    st.markdown('<h1 class="main-header">🚀 Enhanced Overview</h1>', unsafe_allow_html=True)
    
    # Load collection statistics
    stats_df = load_collection_stats(db_conn)
    
    if stats_df.empty:
        st.warning("No collection data found. Please run the downloader first.")
        return
    
    stats = stats_df.iloc[0]
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Albums",
            value=int(stats['total_items']),
            delta=f"{int(stats['downloaded_items'])} downloaded"
        )
    
    with col2:
        st.metric(
            label="Unique Artists",
            value=int(stats['unique_artists'])
        )
    
    with col3:
        try:
            earliest = int(stats['earliest_year']) if pd.notna(stats['earliest_year']) else None
            latest = int(stats['latest_year']) if pd.notna(stats['latest_year']) else None
        except Exception:
            earliest, latest = None, None
        # Enforce floor at 1930 and skip zeros
        if earliest is not None and earliest < 1930:
            earliest = 1930
        if latest is not None and latest < 1930:
            latest = 1930
        if earliest is None or latest is None:
            st.metric(label="Year Range", value="N/A")
        else:
            span = max(0, latest - earliest)
        st.metric(
            label="Year Range",
                value=f"{earliest}-{latest}",
                delta=f"{span} years"
        )
    
    with col4:
        rating = stats['avg_rating']
        st.metric(
            label="Average Rating",
            value=f"{rating:.1f}/5" if pd.notna(rating) else "N/A"
        )
    
    # Additional metrics
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric(
            label="Countries",
            value=int(stats['countries'])
        )
    
    with col6:
        st.metric(
            label="Labels",
            value=int(stats['unique_labels'])
        )
    
    with col7:
        artwork_count = stats['artwork_count']
        st.metric(
            label="Artwork Files",
            value=int(artwork_count) if pd.notna(artwork_count) else 0
        )
    
    with col8:
        size_bytes = stats['total_artwork_size_bytes']
        if pd.notna(size_bytes) and size_bytes > 0:
            size_mb = size_bytes / (1024 * 1024)
            st.metric(
                label="Artwork Size",
                value=f"{size_mb:.1f} MB"
            )
        else:
            st.metric(
                label="Artwork Size",
                value="0 MB"
            )

    st.subheader("💰 Collection Valuation")
    val_df = load_collection_valuation(db_conn)
    if val_df.empty:
        st.info("No pricing data yet. Run the price refresher to populate values.")
    else:
        row = val_df.iloc[0]
        currency = row.get('currency') or ''
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Low Total Value", f"{row['total_low_value']:.2f} {currency}")
        with c2:
            st.metric("Average Price", f"{row['avg_price']:.2f} {currency}")
        with c3:
            st.metric("Highest Single Price", f"{row['max_price']:.2f} {currency}")
        with c4:
            st.metric("Priced Releases", int(row['num_priced']))

    st.subheader("🎴 Random Cover Wall")
    # Refresh button to rotate covers
    if 'cover_wall_refresh' not in st.session_state:
        st.session_state['cover_wall_refresh'] = 0
    if st.button("🔄 Refresh Covers", key="refresh_covers_btn"):
        st.session_state['cover_wall_refresh'] += 1
    covers = load_random_covers(db_conn, seed=st.session_state['cover_wall_refresh'])
    if covers.empty:
        st.info("No artwork yet. Download artwork to populate covers.")
    else:
        # Two rows of five
        for start in (0, 5):
            cols = st.columns(5)
            for idx in range(5):
                j = start + idx
                if j >= len(covers):
                    break
                with cols[idx]:
                    rec = covers.iloc[j]
                    # Prefer thumbnail, then local, then URL
                    path = rec.get('thumbnail_file_path') or rec.get('local_file_path')
                    caption = f"{rec.get('title','')}\n{rec.get('artist','')}"
                    if path and Path(str(path)).exists():
                        st.image(str(path), use_container_width=True, caption=caption)
                    elif rec.get('original_url'):
                        st.image(rec['original_url'], use_container_width=True, caption=caption)
                    else:
                        st.image("https://via.placeholder.com/300x300?text=No+Image", use_container_width=True)

def display_genre_style_analysis(db_conn):
    """Display enhanced genre and style analysis with drilldown capabilities."""
    st.header("🎭 Genre & Style Analysis")
    st.markdown("Explore your collection by genres and styles with clickable drilldown charts.")
    
    # Initialize session state for navigation
    if 'gs_view' not in st.session_state:
        st.session_state['gs_view'] = 'main'  # main, genre_drill, style_drill, releases
    if 'gs_selected_genre' not in st.session_state:
        st.session_state['gs_selected_genre'] = None
    if 'gs_selected_style' not in st.session_state:
        st.session_state['gs_selected_style'] = None
    if 'gs_page' not in st.session_state:
        st.session_state['gs_page'] = 0
    if 'gs_random_seed' not in st.session_state:
        st.session_state['gs_random_seed'] = 0
    
    # Control panel
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        analysis_type = st.selectbox(
            "Analysis Type:",
            ["Genre", "Style"],
            help="Choose whether to start with Genre or Style analysis"
        )
    
    with col2:
        if st.button("🏠 Reset View"):
            st.session_state['gs_view'] = 'main'
            st.session_state['gs_selected_genre'] = None
            st.session_state['gs_selected_style'] = None
            st.session_state['gs_page'] = 0
            st.rerun()
    
    with col3:
        color_scheme = st.selectbox(
            "Color Scheme:",
            ["Rainbow", "Blue", "Green", "Red", "Purple", "Orange"],
            help="Choose color scheme for the graphs"
        )
    
    # Main view - show genre or style overview
    if st.session_state['gs_view'] == 'main':
        if analysis_type == "Genre":
            _display_genre_overview(db_conn, color_scheme)
        else:
            _display_style_overview(db_conn, color_scheme)
    
    # Genre drill view - show styles for selected genre
    elif st.session_state['gs_view'] == 'genre_drill':
        _display_style_drill_for_genre(db_conn, st.session_state['gs_selected_genre'], color_scheme)
    
    # Style drill view - show genres for selected style
    elif st.session_state['gs_view'] == 'style_drill':
        _display_genre_drill_for_style(db_conn, st.session_state['gs_selected_style'], color_scheme)
    
    # Releases view - show paginated releases
    elif st.session_state['gs_view'] == 'releases':
        if st.session_state['gs_selected_genre']:
            _display_releases_for_genre(db_conn, st.session_state['gs_selected_genre'])
        elif st.session_state['gs_selected_style']:
            _display_releases_for_style(db_conn, st.session_state['gs_selected_style'])

def _display_genre_overview(db_conn, color_scheme):
    """Display genre overview with clickable chart."""
    st.subheader("🎵 Top Genres by Release Count")
    
    df = pd.DataFrame(load_genre_analysis(db_conn))
    if df.empty:
        st.warning("No genre data found")
        return
    
    # Create color map
    color_map = get_color_map(df['genre'].tolist(), color_scheme)
    
    # Create clickable bar chart
    fig = px.bar(
        df,
        x='genre', y='release_count',
        hover_data=['unique_artists', 'avg_year', 'avg_rating'],
        color='genre', color_discrete_map=color_map,
        text='release_count',
        title="Click a genre to see its styles"
    )
    fig.update_layout(
        xaxis=dict(type='category'),
        showlegend=False,
        yaxis=dict(range=[0, max(df['release_count'].max(), 1) * 1.1])
    )
    fig.update_traces(textposition='outside', cliponaxis=False)
    
    clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key='genre_click', override_height=500)
    
    if clicked:
        try:
            genre = str(clicked[0].get('x'))
            st.session_state['gs_selected_genre'] = genre
            st.session_state['gs_view'] = 'genre_drill'
            st.session_state['gs_page'] = 0
            st.rerun()
        except Exception:
            pass
    
    # Show detailed table
    st.subheader("Genre Details")
    st.dataframe(
        df.style.format({
            'avg_year': '{:.0f}',
            'avg_rating': '{:.1f}'
        }),
        use_container_width=True
    )

def _display_style_overview(db_conn, color_scheme):
    """Display style overview with clickable chart."""
    st.subheader("🎨 Top Styles by Release Count")
    
    df = pd.DataFrame(load_style_analysis(db_conn))
    if df.empty:
        st.warning("No style data found")
        return
    
    # Create color map
    color_map = get_color_map(df['style'].tolist(), color_scheme)
    
    # Create clickable bar chart
    fig = px.bar(
        df,
        x='style', y='release_count',
        hover_data=['unique_artists', 'avg_year', 'avg_rating'],
        color='style', color_discrete_map=color_map,
        text='release_count',
        title="Click a style to see its genres"
    )
    fig.update_layout(
        xaxis=dict(type='category'),
        showlegend=False,
        yaxis=dict(range=[0, max(df['release_count'].max(), 1) * 1.1])
    )
    fig.update_traces(textposition='outside', cliponaxis=False)
    
    clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key='style_click', override_height=500)
    
    if clicked:
        try:
            style = str(clicked[0].get('x'))
            st.session_state['gs_selected_style'] = style
            st.session_state['gs_view'] = 'style_drill'
            st.session_state['gs_page'] = 0
            st.rerun()
        except Exception:
            pass
    
    # Show detailed table
    st.subheader("Style Details")
    st.dataframe(
        df.style.format({
            'avg_year': '{:.0f}',
            'avg_rating': '{:.1f}'
        }),
        use_container_width=True
    )

def _display_style_drill_for_genre(db_conn, genre, color_scheme):
    """Display styles breakdown for a selected genre."""
    st.subheader(f"🎨 Styles in Genre: {genre}")
    
    # Back button
    if st.button("← Back to Genres"):
        st.session_state['gs_view'] = 'main'
        st.session_state['gs_selected_genre'] = None
        st.rerun()
    
    df = pd.DataFrame(load_styles_for_genre(db_conn, genre))
    if df.empty:
        st.warning(f"No styles found for genre '{genre}'")
        return
    
    # Create color map
    color_map = get_color_map(df['style'].tolist(), color_scheme)
    
    # Create clickable bar chart
    fig = px.bar(
        df,
        x='style', y='release_count',
        hover_data=['unique_artists', 'avg_year', 'avg_rating'],
        color='style', color_discrete_map=color_map,
        text='release_count',
        title=f"Click a style to see releases in {genre}"
    )
    fig.update_layout(
        xaxis=dict(type='category'),
        showlegend=False,
        yaxis=dict(range=[0, max(df['release_count'].max(), 1) * 1.1])
    )
    fig.update_traces(textposition='outside', cliponaxis=False)
    
    clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key=f'style_drill_{genre}', override_height=500)
    
    if clicked:
        try:
            style = str(clicked[0].get('x'))
            st.session_state['gs_selected_style'] = style
            st.session_state['gs_view'] = 'releases'
            st.session_state['gs_page'] = 0
            st.rerun()
        except Exception:
            pass
    
    # Show detailed table
    st.dataframe(
        df.style.format({
            'avg_year': '{:.0f}',
            'avg_rating': '{:.1f}'
        }),
        use_container_width=True
    )

def _display_genre_drill_for_style(db_conn, style, color_scheme):
    """Display genres breakdown for a selected style."""
    st.subheader(f"🎵 Genres in Style: {style}")
    
    # Back button
    if st.button("← Back to Styles"):
        st.session_state['gs_view'] = 'main'
        st.session_state['gs_selected_style'] = None
        st.rerun()
    
    df = pd.DataFrame(load_genres_for_style(db_conn, style))
    if df.empty:
        st.warning(f"No genres found for style '{style}'")
        return
    
    # Create color map
    color_map = get_color_map(df['genre'].tolist(), color_scheme)
    
    # Create clickable bar chart
    fig = px.bar(
        df,
        x='genre', y='release_count',
        hover_data=['unique_artists', 'avg_year', 'avg_rating'],
        color='genre', color_discrete_map=color_map,
        text='release_count',
        title=f"Click a genre to see releases in {style}"
    )
    fig.update_layout(
        xaxis=dict(type='category'),
        showlegend=False,
        yaxis=dict(range=[0, max(df['release_count'].max(), 1) * 1.1])
    )
    fig.update_traces(textposition='outside', cliponaxis=False)
    
    clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key=f'genre_drill_{style}', override_height=500)
    
    if clicked:
        try:
            genre = str(clicked[0].get('x'))
            st.session_state['gs_selected_genre'] = genre
            st.session_state['gs_view'] = 'releases'
            st.session_state['gs_page'] = 0
            st.rerun()
        except Exception:
            pass
    
    # Show detailed table
    st.dataframe(
        df.style.format({
            'avg_year': '{:.0f}',
            'avg_rating': '{:.1f}'
        }),
        use_container_width=True
    )

def _display_releases_for_genre(db_conn, genre):
    """Display paginated releases for a selected genre."""
    st.subheader(f"📀 Releases in Genre: {genre}")
    
    # Back button and controls
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← Back"):
            st.session_state['gs_view'] = 'genre_drill' if st.session_state.get('gs_selected_style') else 'main'
            st.session_state['gs_selected_genre'] = None
            st.rerun()
    
    with col2:
        if st.button("🎲 Randomize"):
            st.session_state['gs_random_seed'] += 1
            st.session_state['gs_page'] = 0
            st.rerun()
    
    # Get total count and calculate pagination
    total_releases = get_total_releases_for_genre(db_conn, genre)
    releases_per_page = 25
    total_pages = (total_releases + releases_per_page - 1) // releases_per_page
    current_page = st.session_state.get('gs_page', 0)
    
    st.markdown(f"**Total releases:** {total_releases:,} • **Page:** {current_page + 1} of {total_pages}")
    
    # Load and display releases
    releases = load_releases_for_genre(
        db_conn, genre, 
        offset=current_page * releases_per_page, 
        limit=releases_per_page,
        random_seed=st.session_state.get('gs_random_seed', 0)
    )
    
    if not releases:
        st.warning(f"No releases found for genre '{genre}'")
        return
    
    # Display releases
    for release in releases:
        _display_release_card(release)
    
    # Pagination controls
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("◀ Previous", disabled=current_page == 0):
            st.session_state['gs_page'] = max(0, current_page - 1)
            st.rerun()
    
    with col2:
        st.markdown(f"Page {current_page + 1} of {total_pages}")
    
    with col3:
        if st.button("Next ▶", disabled=current_page >= total_pages - 1):
            st.session_state['gs_page'] = min(total_pages - 1, current_page + 1)
            st.rerun()

def _display_releases_for_style(db_conn, style):
    """Display paginated releases for a selected style."""
    st.subheader(f"📀 Releases in Style: {style}")
    
    # Back button and controls
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← Back"):
            st.session_state['gs_view'] = 'style_drill' if st.session_state.get('gs_selected_genre') else 'main'
            st.session_state['gs_selected_style'] = None
            st.rerun()
    
    with col2:
        if st.button("🎲 Randomize"):
            st.session_state['gs_random_seed'] += 1
            st.session_state['gs_page'] = 0
            st.rerun()
    
    # Get total count and calculate pagination
    total_releases = get_total_releases_for_style(db_conn, style)
    releases_per_page = 25
    total_pages = (total_releases + releases_per_page - 1) // releases_per_page
    current_page = st.session_state.get('gs_page', 0)
    
    st.markdown(f"**Total releases:** {total_releases:,} • **Page:** {current_page + 1} of {total_pages}")
    
    # Load and display releases
    releases = load_releases_for_style(
        db_conn, style, 
        offset=current_page * releases_per_page, 
        limit=releases_per_page,
        random_seed=st.session_state.get('gs_random_seed', 0)
    )
    
    if not releases:
        st.warning(f"No releases found for style '{style}'")
        return
    
    # Display releases
    for release in releases:
        _display_release_card(release)
    
    # Pagination controls
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("◀ Previous", disabled=current_page == 0):
            st.session_state['gs_page'] = max(0, current_page - 1)
            st.rerun()
    
    with col2:
        st.markdown(f"Page {current_page + 1} of {total_pages}")
    
    with col3:
        if st.button("Next ▶", disabled=current_page >= total_pages - 1):
            st.session_state['gs_page'] = min(total_pages - 1, current_page + 1)
            st.rerun()

def _display_release_card(release):
    """Display a compact release card."""
    with st.container():
        col1, col2, col3 = st.columns([1, 3, 2])
        
        with col1:
            # Display artwork thumbnail
            artwork_files = release.get('artwork_files', [])
            if artwork_files and isinstance(artwork_files, list) and len(artwork_files) > 0:
                primary_art = next((art for art in artwork_files if art.get('image_type') == 'primary'), artwork_files[0])
                thumbnail_path = primary_art.get('thumbnail_file_path') or primary_art.get('local_file_path')
                if thumbnail_path and os.path.exists(thumbnail_path):
                    st.image(thumbnail_path, width=80)
                else:
                    st.image("https://via.placeholder.com/80?text=No+Image", width=80)
            else:
                st.image("https://via.placeholder.com/80?text=No+Image", width=80)
        
        with col2:
            st.markdown(f"**{release.get('title', 'Unknown Title')}**")
            st.markdown(f"*by {release.get('artist', 'Unknown Artist')}*")
            
            details = []
            if release.get('year') is not None and not is_missing(release.get('year')):
                details.append(f"Year: {int(release['year'])}")
            if release.get('label') is not None and not is_missing(release.get('label')):
                details.append(f"Label: {release['label']}")
            if release.get('catno') is not None and not is_missing(release.get('catno')):
                details.append(f"Cat#: {release['catno']}")
            
            if details:
                st.markdown(" • ".join(details))
            
            # Show genres and styles
            genres = release.get('genres', [])
            styles = release.get('styles', [])
            if genres and not is_missing(genres):
                if isinstance(genres, str):
                    try:
                        genres = json.loads(genres)
                    except:
                        genres = [genres]
                st.markdown(f"**Genres:** {', '.join(genres)}")
            
            if styles and not is_missing(styles):
                if isinstance(styles, str):
                    try:
                        styles = json.loads(styles)
                    except:
                        styles = [styles]
                st.markdown(f"**Styles:** {', '.join(styles)}")
        
        with col3:
            if release.get('rating') is not None and not is_missing(release.get('rating')) and release['rating'] > 0:
                rating = int(release['rating'])
                st.markdown("⭐" * rating + "☆" * (5 - rating))
            
            if release.get('condition') is not None and not is_missing(release.get('condition')):
                st.markdown(f"**Condition:** {release['condition']}")
            
            # Show community statistics if available
            if (release.get('community_have_count', 0) > 0 or 
                release.get('community_want_count', 0) > 0 or 
                release.get('community_rating_count', 0) > 0):
                
                st.markdown("**Community Stats:**")
                community_parts = []
                
                if release.get('community_have_count', 0) > 0:
                    community_parts.append(f"👥 {release['community_have_count']:,} have")
                
                if release.get('community_want_count', 0) > 0:
                    community_parts.append(f"🎯 {release['community_want_count']:,} want")
                
                if release.get('community_rating_count', 0) > 0:
                    avg_rating = release.get('community_average_rating', 0)
                    community_parts.append(f"⭐ {avg_rating:.1f} ({release['community_rating_count']:,} votes)")
                
                if community_parts:
                    st.markdown(" • ".join(community_parts))
        
        st.divider()

def display_decade_analysis(db_conn):
    """Display decade analysis."""
    st.header("📅 Decade Timeline")
    
    # Color scheme selection
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("")  # Spacer
    with col2:
        color_scheme = st.selectbox(
            "Color Scheme:",
            ["Rainbow", "Blue", "Green", "Red", "Purple", "Orange"],
            help="Choose color scheme for the graphs"
        )
    
    # State for drilldown
    if 'decade_view' not in st.session_state:
        st.session_state['decade_view'] = 'decades'  # 'decades' | 'years'
    if 'selected_decade' not in st.session_state:
        st.session_state['selected_decade'] = None
    if 'selected_year' not in st.session_state:
        st.session_state['selected_year'] = None
    if 'year_page' not in st.session_state:
        st.session_state['year_page'] = 0

    if st.session_state['decade_view'] == 'decades':
        df = load_decade_analysis(db_conn)
        # Ensure a DataFrame and required columns
        if df is None:
            df = pd.DataFrame()
        if not isinstance(df, pd.DataFrame):
            try:
                df = pd.DataFrame(df)
            except Exception:
                df = pd.DataFrame()
        required_cols = {'decade', 'release_count', 'unique_artists'}
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0
        # Guard empty
        if df.empty:
            st.warning("No decade data found")
            return
        # Normalize types and filter out invalid rows
        try:
            df['decade'] = pd.to_numeric(df['decade'], errors='coerce')
            df['release_count'] = pd.to_numeric(df['release_count'], errors='coerce')
        except Exception:
            pass
        df = df.dropna(subset=['decade', 'release_count'])
        try:
            df['decade'] = df['decade'].astype(int)
        except Exception:
            pass
        try:
            df['release_count'] = df['release_count'].astype(int)
        except Exception:
            pass
        df = df.sort_values('decade')  # Keep all decades, including zeros
        if df.empty:
            st.warning("No decade data found")
            return
        # Build decade labels and color each bar distinctly
        labels = (df['decade'].astype(str) + 's').tolist()
        df['decade_label'] = labels
        color_map = get_color_map(labels, color_scheme)
        st.subheader("Releases by Decade (click a bar)")
        fig = px.bar(
            df,
            x='decade_label', y='release_count',
            hover_data=['unique_artists'],
            color='decade_label', color_discrete_map=color_map,
            text='release_count'
        )
        fig.update_layout(
            xaxis=dict(type='category', categoryorder='array', categoryarray=labels),
            showlegend=False,
            yaxis=dict(range=[0, max(df['release_count'].max(), 1) * 1.1]),  # Ensure zero bars are visible
            title="Releases by Decade (click a bar) - Empty decades shown with 0"
        )
        fig.update_traces(textposition='outside', cliponaxis=False)
        clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key='decade_click', override_height=500)
        if clicked:
            # Map label back to integer decade
            try:
                label = str(clicked[0].get('x'))
                decade_int = int(label.rstrip('s')) if label.endswith('s') else int(label)
                st.session_state['selected_decade'] = decade_int
                st.session_state['decade_view'] = 'years'
                st.session_state['selected_year'] = None
                st.session_state['year_page'] = 0
                st.rerun()
            except Exception:
                pass
        # No additional table in this view
    else:
        # Year breakdown for selected decade
        decade_int = st.session_state['selected_decade']
        st.subheader(f"Releases in the {decade_int}s by Year")
        year_df = load_year_breakdown(db_conn, decade_int)
        
        # Debug info
        st.write(f"Debug: Looking for years {decade_int} to {decade_int + 9}")
        st.write(f"Debug: Found {len(year_df)} year records")
        
        if year_df.empty:
            st.info(f"No year data found for the {decade_int}s decade.")
        else:
            # Ensure correct types for plotting
            try:
                year_df['year'] = year_df['year'].astype(int)
            except Exception:
                pass
            # Build colors per year using selected scheme
            try:
                years_sorted = sorted(year_df['year'].unique())
                color_map = get_color_map(years_sorted, color_scheme)
            except Exception:
                color_map = {}
            fig = px.bar(
                year_df,
                x='year', y='release_count', title="Click a year to see releases (empty years shown with 0)",
                color='year', color_discrete_map=color_map,
                text='release_count'
            )
            fig.update_layout(
                xaxis=dict(type='category'), 
                showlegend=False,
                yaxis=dict(range=[0, max(year_df['release_count'].max(), 1) * 1.1])  # Ensure zero bars are visible
            )
            fig.update_traces(textposition='outside', cliponaxis=False)
            clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key=f'year_click_{decade_int}', override_height=500)
            if clicked:
                try:
                    year_selected = int(clicked[0]['x'])
                    st.session_state['selected_year'] = year_selected
                    st.session_state['year_page'] = 0
                    st.rerun()
                except Exception:
                    pass

            # Back button to decades
            if st.button("⬅ Back to Decades"):
                st.session_state['decade_view'] = 'decades'
                st.session_state['selected_decade'] = None
                st.session_state['selected_year'] = None
                st.session_state['year_page'] = 0
                st.rerun()

            # If a year is selected, show paginated releases
            if st.session_state['selected_year'] is not None:
                st.markdown(f"### {st.session_state['selected_year']} Releases")
                per_page = 25
                page = st.session_state['year_page']
                offset = page * per_page
                rels = load_releases_for_year(db_conn, st.session_state['selected_year'], per_page, offset)
                if rels.empty:
                    st.info("No releases found for this year.")
                else:
                    # Display grid list
                    for _, row in rels.iterrows():
                        with st.container():
                            cols = st.columns([1, 4])
                            with cols[0]:
                                thumb = row.get('thumb')
                                if thumb and Path(str(thumb)).exists():
                                    st.image(str(thumb), width=80)
                                elif row.get('url'):
                                    st.image(row['url'], width=80)
                                else:
                                    st.image("https://via.placeholder.com/80?text=No+Image", width=80)
                            with cols[1]:
                                st.markdown(f"**{row.get('title','Unknown')}**")
                                st.caption(f"{row.get('artist','Unknown')} — {row.get('label','')}" )
                    # Pagination controls
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        if st.button("◀ Previous", disabled=page==0):
                            st.session_state['year_page'] = max(0, page - 1)
                            st.rerun()
                    with c2:
                        st.write(f"Page {page+1}")
                    with c3:
                        if len(rels) == per_page and st.button("Next ▶"):
                            st.session_state['year_page'] = page + 1
                            st.rerun()

def display_collection_browser(db_conn):
    """Display collection browser with search and filtering."""
    st.header("🔍 Browse Collection")
    
    # Search functionality
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        search_term = st.text_input("Search your collection", placeholder="Enter artist or album...")
    
    with col2:
        limit = st.selectbox("Records to show", [25, 50, 100, 500, 1000], index=0)
    
    with col3:
        show_search = st.button("🔍 Search", type="primary")

    with col4:
        # Random mode controls
        # Decade options
        decades_df = load_available_decades(db_conn)
        decade_options = ["All"]
        if not decades_df.empty and 'decade' in decades_df.columns:
            decade_options += [int(d) for d in decades_df['decade'].sort_values().tolist()]
        selected_decade_label = st.selectbox("Random decade", options=decade_options, index=0, help="Pick a decade to sample from")
        if 'rand_seed' not in st.session_state:
            st.session_state['rand_seed'] = 0
        refresh_random = st.button("🎲 Refresh Random")
        if refresh_random:
            st.session_state['rand_seed'] += 1
    
    # Load and display data
    if search_term and show_search:
        df = search_collection(db_conn, search_term)
        st.subheader(f"Search Results for '{search_term}'")
    else:
        # Default to random 25 releases; allow decade filter
        dec = None if selected_decade_label == "All" else int(selected_decade_label)
        df = load_random_releases(db_conn, count=25, decade_start=dec, rand_token=st.session_state.get('rand_seed', 0))
        st.subheader("Random Selection" + (f" — {dec}s" if dec is not None else ""))
    
    if df.empty:
        st.warning("No releases found")
        return
    
    # Display results count
    st.write(f"Showing {len(df)} releases")
    
    # Minimal rows with artist — title and a More info button
    for _, release in df.iterrows():
        with st.container():
            cols = st.columns([6, 1])
            with cols[0]:
                st.markdown(f"**{release.get('artist','Unknown Artist')} — {release.get('title','Unknown Title')}**")
            with cols[1]:
                key = f"more_{release['release_id']}"
                if st.button("More info", key=key):
                    st.session_state[key] = not st.session_state.get(key, False)
            if st.session_state.get(f"more_{release['release_id']}"):
                _display_release_details_block(db_conn, release)
            st.divider()

def _display_release_details_block(db_conn, release_row):
    """Show a tabular details block similar to a Discogs release page, with stats and refresh button."""
    # Resolve fields
    discogs_id = release_row.get('discogs_id') or release_row.get('basic_information', {}).get('id')
    if not discogs_id:
        st.info("No Discogs ID available for this release.")
        return
    # Fetch stats and marketplace
    stats = _fetch_release_stats(db_conn, discogs_id)
    # Build table rows
    kv = []
    kv.append(("Title", release_row.get('title')))
    kv.append(("Artist", release_row.get('artist')))
    if release_row.get('year'):
        kv.append(("Year", release_row.get('year')))
    if release_row.get('label'):
        kv.append(("Label", release_row.get('label')))
    if release_row.get('catno'):
        kv.append(("Catalog #", release_row.get('catno')))
    if release_row.get('format'):
        kv.append(("Format", release_row.get('format')))
    # Genres / Styles
    def _fmt_list(val):
        try:
            if isinstance(val, str):
                val = json.loads(val)
            if isinstance(val, list):
                return ", ".join([str(x) for x in val])
        except Exception:
            pass
        return val
    if release_row.get('genres'):
        kv.append(("Genres", _fmt_list(release_row.get('genres'))))
    if release_row.get('styles'):
        kv.append(("Styles", _fmt_list(release_row.get('styles'))))
    # Community stats
    if stats:
        kv.append(("Community Have", stats.get('community_have_count')))
        kv.append(("Community Want", stats.get('community_want_count')))
        if stats.get('community_average_rating') is not None:
            kv.append(("Community Avg Rating", f"{stats.get('community_average_rating'):.2f}"))
        kv.append(("Community Ratings Count", stats.get('community_rating_count')))
        if stats.get('stats_last_updated'):
            kv.append(("Community As Of", str(stats.get('stats_last_updated'))))
        # Marketplace dim
        if stats.get('marketplace_as_of'):
            kv.append(("Marketplace As Of", str(stats.get('marketplace_as_of'))))
        if stats.get('low_sold_price') is not None:
            kv.append(("Lowest (sold/listing)", f"{stats.get('low_sold_price')} {stats.get('currency') or ''}"))
        if stats.get('high_sold_price') is not None:
            kv.append(("Highest Sold", f"{stats.get('high_sold_price')} {stats.get('currency') or ''}"))
        if stats.get('num_for_sale') is not None:
            kv.append(("Num For Sale", stats.get('num_for_sale')))
        if stats.get('lowest_price_current') is not None:
            kv.append(("Lowest Listing", f"{stats.get('lowest_price_current')} {stats.get('currency_current') or ''}"))
    # Render as table
    if kv:
        df = pd.DataFrame(kv, columns=["Field", "Value"])
        st.table(df)
    # Refresh button
    colr1, colr2 = st.columns([1,4])
    with colr1:
        if st.button("Update statistics", key=f"upd_{release_row['release_id']}"):
            with st.spinner("Refreshing stats..."):
                import subprocess, sys, os
                try:
                    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'discogs_downloader.py'), '--refresh-release-stats', str(int(discogs_id))], check=True, capture_output=True, text=True)
                    st.success("Updated. Please expand again or reload to see changes.")
                except Exception as e:
                    st.error(f"Failed to update stats: {e}")

def _fetch_release_stats(db_conn, discogs_id: int):
    q = """
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
    rows = db_conn.execute_query(q, (discogs_id,))
    return rows[0] if rows else None

def display_community_statistics(db_conn):
    """Display community statistics from Discogs for the collection."""
    st.header("📊 Community Statistics")
    st.markdown("""
    View how your collection compares to the broader Discogs community. 
    These statistics show how many people **have** and **want** each release, 
    plus community ratings and marketplace data.
    """)
    
    # Check if we have community and marketplace statistics data
    stats_check_query = """
    SELECT 
        COUNT(*) as total_releases,
        COUNT(CASE WHEN community_have_count > 0 OR community_want_count > 0 OR community_rating_count > 0 THEN 1 END) as releases_with_stats,
        MAX(stats_last_updated) as last_updated,
        (SELECT MAX(as_of) FROM marketplace_stats_dim) as marketplace_as_of
    FROM releases 
    WHERE discogs_id IS NOT NULL
    """
    
    try:
        stats_check = db_conn.execute_query(stats_check_query)
        if not stats_check:
            st.error("Unable to check community statistics data")
            return
            
        check_data = stats_check[0]
        total_releases = check_data.get('total_releases', 0)
        releases_with_stats = check_data.get('releases_with_stats', 0)
        last_updated = check_data.get('last_updated')
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Releases", f"{total_releases:,}")

        with col2:
            st.metric("With Community Stats", f"{releases_with_stats:,}")
        
        with col3:
            coverage_pct = (releases_with_stats / total_releases * 100) if total_releases > 0 else 0
            st.metric("Coverage", f"{coverage_pct:.1f}%")
        
        with col4:
            if last_updated:
                st.metric("Community As Of", last_updated.strftime("%Y-%m-%d"))
            else:
                st.metric("Community As Of", "Never")
        
        marketplace_as_of = check_data.get('marketplace_as_of')
        if marketplace_as_of:
            st.caption(f"Marketplace stats as of: {pd.to_datetime(marketplace_as_of).strftime('%Y-%m-%d %H:%M')}")
        
        if releases_with_stats == 0:
            st.warning("""
            No community statistics found in your collection. 
            
            **To get community statistics:**
            1. Run: `python discogs_downloader.py --refresh-stats`
            2. Or re-download your collection to automatically fetch stats
            
            This will add have/want counts, community ratings, and marketplace data to your releases.
            """)
            return
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["Most Popular", "Most Wanted", "Highest Rated", "Marketplace Insights"])
        
        with tab1:
            st.subheader("🔥 Most Popular Releases (Have Count)")
            popular_query = """
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
            
            popular_df = pd.DataFrame(db_conn.execute_query(popular_query))
            if not popular_df.empty:
                popular_df.columns = ['Title', 'Artist', 'Year', 'Have Count', 'Want Count', 'Avg Rating', 'Rating Count', 'Want/Have %']
                st.dataframe(
                    popular_df.style.format({
                        'Have Count': '{:,}',
                        'Want Count': '{:,}',
                        'Avg Rating': '{:.2f}',
                        'Rating Count': '{:,}',
                        'Want/Have %': '{:.1f}%'
                    }),
                    use_container_width=True
                )
            else:
                st.info("No popularity data available")
        
        with tab2:
            st.subheader("🎯 Most Wanted Releases")
            wanted_query = """
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
            
            wanted_df = pd.DataFrame(db_conn.execute_query(wanted_query))
            if not wanted_df.empty:
                wanted_df.columns = ['Title', 'Artist', 'Year', 'Want Count', 'Have Count', 'Avg Rating', 'Rating Count', 'Want/Have %']
                st.dataframe(
                    wanted_df.style.format({
                        'Want Count': '{:,}',
                        'Have Count': '{:,}',
                        'Avg Rating': '{:.2f}',
                        'Rating Count': '{:,}',
                        'Want/Have %': '{:.1f}%'
                    }),
                    use_container_width=True
                )
            else:
                st.info("No want data available")
        
        with tab3:
            st.subheader("⭐ Highest Rated Releases")
            rated_query = """
            SELECT 
                title, artist, year, community_average_rating, community_rating_count,
                community_have_count, community_want_count
            FROM releases 
            WHERE community_rating_count >= 10  -- Only show releases with meaningful rating counts
            ORDER BY community_average_rating DESC, community_rating_count DESC
            LIMIT 20
            """
            
            rated_df = pd.DataFrame(db_conn.execute_query(rated_query))
            if not rated_df.empty:
                rated_df.columns = ['Title', 'Artist', 'Year', 'Avg Rating', 'Rating Count', 'Have Count', 'Want Count']
                st.dataframe(
                    rated_df.style.format({
                        'Avg Rating': '{:.2f}',
                        'Rating Count': '{:,}',
                        'Have Count': '{:,}',
                        'Want Count': '{:,}'
                    }),
                    use_container_width=True
                )
            else:
                st.info("No rating data available")
        
        with tab4:
            st.subheader("💰 Marketplace Insights")
            st.markdown("*Note: Marketplace data derived from current listings; historical sold data is not available via public API.*")
            
            # Show some basic statistics about the collection's community standing
            insights_query = """
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
            
            insights_data = db_conn.execute_query(insights_query)
            if insights_data:
                data = insights_data[0]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Avg Have Count", 
                        f"{data.get('avg_have_count', 0):.0f}",
                        help="Average number of people who own releases in your collection"
                    )
                    st.metric(
                        "Popular Releases", 
                        f"{data.get('popular_releases', 0)}",
                        help="Releases owned by 1000+ people"
                    )
                
                with col2:
                    st.metric(
                        "Avg Want Count", 
                        f"{data.get('avg_want_count', 0):.0f}",
                        help="Average number of people who want releases in your collection"
                    )
                    st.metric(
                        "Highly Wanted", 
                        f"{data.get('highly_wanted_releases', 0)}",
                        help="Releases wanted by 100+ people"
                    )
            
            with col3:
                    st.metric(
                        "Avg Community Rating", 
                        f"{data.get('avg_community_rating', 0):.2f}",
                        help="Average community rating for your collection"
                    )
                    st.metric(
                        "Highly Rated", 
                        f"{data.get('highly_rated_releases', 0)}",
                        help="Releases rated 4.0+ with 10+ votes"
                    )
        
        # Add refresh button (SCD1 overwrite)
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🔄 Refresh Stats", help="Refresh community and marketplace stats (overwrites SCD1 dim)"):
                with st.spinner("Refreshing stats (community + marketplace)..."):
                    import subprocess, sys, os
                    try:
                        # Community stats
                        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'discogs_downloader.py'), '--refresh-stats', '--stats-batch-limit', '200'], check=True, capture_output=True, text=True)
                        # Prices (which also feeds marketplace dim during full run), so call full-run minimal path:
                        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'discogs_downloader.py'), '--refresh-prices', '--price-batch-limit', '200'], check=True, capture_output=True, text=True)
                        st.success("Stats refresh requested. Please reload the page in a moment.")
                    except Exception as e:
                        st.error(f"Failed to refresh stats: {e}")
        
        with col2:
            st.markdown(f"**Coverage:** {coverage_pct:.1f}% of releases have community stats")
        
        with col3:
            if last_updated:
                st.markdown(f"**Community as of:** {last_updated.strftime('%Y-%m-%d %H:%M')}")
    
    except Exception as e:
        st.error(f"Error loading community statistics: {e}")

def main():
    """Main Streamlit app."""
    # Initialize database connection
    db_conn = PostgreSQLConnection()
    
    if not db_conn.connection:
        st.error("Cannot connect to database. Please check your configuration.")
        st.stop()
    
    # Sidebar navigation
    st.sidebar.title("🎵 Navigation")
    page = st.sidebar.radio(
        "Choose a view:",
        [
            "Enhanced Overview",
            "Browse Collection",
            "Genre & Style Analysis",
            "Decade Timeline",
            "Collection Insights",
            "Community Statistics",
            "Deals",
            "Availability Alerts",
            "Master Release Tracking",
            "Buying Guide"
        ]
    )
    
    # Sidebar info
    with st.sidebar:
        st.markdown("---")
        st.markdown("### About")
        st.markdown("This app displays your Discogs collection data stored in PostgreSQL.")
        st.markdown("Browse your collection with **interactive artwork galleries** - click the arrows to switch between multiple images per album!")
        
        st.markdown("### Features")
        st.markdown("📷 **Multi-image support** - Navigate through all artwork per release")
        st.markdown("🔍 **Smart search** - Find releases by artist, title, label, or genre")
        st.markdown("📊 **Analytics** - View genre and decade breakdowns")
        
        st.markdown("### Data Refresh")
        if st.button("🔄 Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")
        
        st.markdown("---")
        st.markdown("*Built with Streamlit & PostgreSQL* 🐘")
    
    # Main content based on selected page
    if page == "Enhanced Overview":
        display_collection_overview(db_conn)
    elif page == "Browse Collection":
        display_collection_browser(db_conn)
    elif page == "Genre & Style Analysis":
        display_genre_style_analysis(db_conn)
    elif page == "Decade Timeline":
        display_decade_analysis(db_conn)
    elif page == "Collection Insights":
        display_artist_insights(db_conn)
    elif page == "Community Statistics":
        display_community_statistics(db_conn)
    elif page == "Producer Insights":
        display_producer_insights(db_conn)
    elif page == "Master Release Tracking":
        display_master_release_tracking(db_conn)
    elif page == "Deals":
        display_deals(db_conn)
    elif page == "Availability Alerts":
        display_availability_alerts(db_conn)
    elif page == "Buying Guide":
        display_buying_guide(db_conn)

def display_master_release_tracking(db_conn):
    """Display master release tracking with version and copy analysis."""
    st.header("🎛️ Master Release Tracking")
    
    st.markdown("""
    Track your collection by **master releases** - albums that have been released in multiple versions.
    See how many different versions of each album you own and identify duplicates or missing versions.
    """)
    
    # Analysis options
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_mode = st.radio(
            "Analysis Mode:",
            ["Master Release Overview", "Detailed Version Analysis", "Duplicate Detection"],
            help="Choose how you want to analyze your master releases"
        )
    
    with col2:
        sort_option = st.selectbox(
            "Sort by:",
            ["Most Versions Owned", "Fewest Versions Owned", "Most Duplicates", "Alphabetical"],
            help="How to order the results"
        )
    
    # Master release analysis
    if analysis_mode == "Master Release Overview":
        st.subheader("📀 Albums with Multiple Versions")
        
        # Query to find master releases with multiple versions
        query = """
        WITH master_analysis AS (
            SELECT 
                -- Extract master_id from basic_information JSON
                CASE 
                    WHEN basic_information->>'master_id' IS NOT NULL 
                    THEN CAST(basic_information->>'master_id' AS INTEGER)
                    ELSE NULL
                END as master_id,
                -- Use a combination of title and artist as fallback grouping
                COALESCE(
                    basic_information->>'master_url',
                    CONCAT(LOWER(TRIM(title)), ' - ', LOWER(TRIM(artist)))
                ) as master_key,
                title,
                artist,
                year,
                label,
                catno,
                format,
                country,
                condition,
                sleeve_condition,
                rating,
                discogs_id,
                release_id,
                instance_id,
                basic_information
            FROM releases
            WHERE title IS NOT NULL AND artist IS NOT NULL
        ),
        grouped_masters AS (
            SELECT 
                COALESCE(CAST(master_id AS TEXT), master_key) as master_group,
                title as master_title,
                artist as master_artist,
                COUNT(*) as versions_owned,
                COUNT(DISTINCT instance_id) as total_copies,
                COUNT(*) - COUNT(DISTINCT release_id) as duplicate_releases,
                STRING_AGG(DISTINCT format, ', ') as formats_owned,
                STRING_AGG(DISTINCT country, ', ') as countries,
                STRING_AGG(DISTINCT CAST(year AS TEXT), ', ') as years,
                ROUND(AVG(rating), 1) as avg_rating,
                MIN(year) as earliest_year,
                MAX(year) as latest_year,
                STRING_AGG(
                    CONCAT(
                        format, ' (', country, ', ', year, 
                        CASE WHEN catno IS NOT NULL THEN ', ' || catno ELSE '' END,
                        ')'
                    ), 
                    ' | ' 
                    ORDER BY year, format
                ) as version_details
            FROM master_analysis
            WHERE master_id IS NOT NULL OR master_key IS NOT NULL
            GROUP BY 
                COALESCE(CAST(master_id AS TEXT), master_key),
                title, artist
            HAVING COUNT(*) > 1  -- Only show albums with multiple versions
        )
        SELECT *
        FROM grouped_masters
        ORDER BY 
            CASE 
                WHEN '{}' = 'Most Versions Owned' THEN versions_owned
                WHEN '{}' = 'Most Duplicates' THEN duplicate_releases
                ELSE 0
            END DESC,
            CASE 
                WHEN '{}' = 'Fewest Versions Owned' THEN versions_owned
                WHEN '{}' = 'Alphabetical' THEN 0
                ELSE 999
            END ASC,
            CASE WHEN '{}' = 'Alphabetical' THEN master_title ELSE '' END
        LIMIT 50
        """.format(sort_option, sort_option, sort_option, sort_option, sort_option)
        
        df = db_conn.execute_query(query)
        
        if df.empty:
            st.info("No albums with multiple versions found. This could mean:\n- You have unique versions of each album\n- Master release data isn't available\n- Collection needs to be re-downloaded with enhanced tracking")
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Albums with Multiple Versions", len(df))
            with col2:
                total_versions = df['versions_owned'].sum()
                st.metric("Total Versions", total_versions)
            with col3:
                total_copies = df['total_copies'].sum()
                st.metric("Total Copies", total_copies)
            with col4:
                duplicates = df['duplicate_releases'].sum()
                st.metric("Duplicate Releases", duplicates)
            
            # Visualization
            col1, col2 = st.columns(2)
            
            with col1:
                # Bar chart of albums by version count
                fig = px.bar(
                    df.head(15),
                    x='versions_owned',
                    y='master_title',
                    orientation='h',
                    title="Albums by Number of Versions Owned",
                    labels={'versions_owned': 'Versions Owned', 'master_title': 'Album'},
                    color='versions_owned',
                    color_continuous_scale='viridis'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Scatter plot of versions vs copies
                fig = px.scatter(
                    df,
                    x='versions_owned',
                    y='total_copies',
                    size='duplicate_releases',
                    hover_data=['master_title', 'master_artist', 'formats_owned'],
                    title="Versions vs Total Copies",
                    labels={'versions_owned': 'Different Versions', 'total_copies': 'Total Copies'},
                    color='avg_rating',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Detailed table
            st.subheader("Detailed Master Release Analysis")
            
            # Format the dataframe for display
            display_df = df.copy()
            display_df.columns = [
                'Master Group', 'Album Title', 'Artist', 'Versions Owned', 'Total Copies',
                'Duplicate Releases', 'Formats', 'Countries', 'Years', 'Avg Rating',
                'Earliest Year', 'Latest Year', 'Version Details'
            ]
            
            # Style the dataframe
            styled_df = style_with_background(
                display_df[['Album Title', 'Artist', 'Versions Owned', 'Total Copies', 
                            'Duplicate Releases', 'Formats', 'Years', 'Avg Rating', 'Version Details']],
                subset=['Versions Owned'], cmap='YlOrRd', low=0.3, high=0.9,
                format_map={'Versions Owned': '{:,}', 'Total Copies': '{:,}', 'Duplicate Releases': '{:,}', 'Avg Rating': '{:.1f}'}
            )
            st.dataframe(styled_df, use_container_width=True)
    
    elif analysis_mode == "Detailed Version Analysis":
        st.subheader("🔍 Detailed Version Breakdown")
        
        # Let user select a specific master release to analyze
        master_query = """
        WITH master_summary AS (
            SELECT 
                COALESCE(
                    basic_information->>'master_url',
                    CONCAT(LOWER(TRIM(title)), ' - ', LOWER(TRIM(artist)))
                ) as master_key,
                title,
                artist,
                COUNT(*) as version_count
            FROM releases
            WHERE title IS NOT NULL AND artist IS NOT NULL
            GROUP BY master_key, title, artist
            HAVING COUNT(*) > 1
            ORDER BY version_count DESC, title
            LIMIT 100
        )
        SELECT CONCAT(title, ' - ', artist) as display_name, master_key
        FROM master_summary
        """
        
        masters_df = db_conn.execute_query(master_query)
        
        if masters_df.empty:
            st.warning("No albums with multiple versions found for detailed analysis.")
        else:
            selected_master = st.selectbox(
                "Select an album to analyze:",
                masters_df['display_name'].tolist(),
                help="Choose an album to see all versions you own"
            )
            
            if selected_master:
                # Get the master_key for the selected album
                master_key = masters_df[masters_df['display_name'] == selected_master]['master_key'].iloc[0]
                
                # Query for all versions of this master release
                versions_query = """
                SELECT 
                    title,
                    artist,
                    year,
                    label,
                    catno,
                    format,
                    country,
                    condition,
                    sleeve_condition,
                    rating,
                    discogs_id,
                    instance_id,
                    date_added,
                    notes,
                    basic_information->>'master_id' as master_id,
                    basic_information->>'thumb' as thumbnail_url
                FROM releases
                WHERE COALESCE(
                    basic_information->>'master_url',
                    CONCAT(LOWER(TRIM(title)), ' - ', LOWER(TRIM(artist)))
                ) = %s
                ORDER BY year, format, country
                """
                
                versions_df = db_conn.execute_query(versions_query, (master_key,))
                
                if not versions_df.empty:
                    st.write(f"**Found {len(versions_df)} versions of this album:**")
                    
                    # Display each version as a card
                    for idx, version in versions_df.iterrows():
                        with st.expander(f"{version['format']} - {version['country']} ({version['year']}) - {version['label']}"):
                            col1, col2, col3 = st.columns([1, 2, 1])
                            
                            with col1:
                                if version.get('thumbnail_url') is not None and not is_missing(version.get('thumbnail_url')):
                                    st.image(version['thumbnail_url'], width=100)
                                else:
                                    st.write("🎵 No Image")
                            
                            with col2:
                                st.write(f"**Catalog #:** {version.get('catno', 'N/A')}")
                                st.write(f"**Condition:** {version.get('condition', 'N/A')}")
                                st.write(f"**Sleeve:** {version.get('sleeve_condition', 'N/A')}")
                                if version.get('rating') is not None and not is_missing(version.get('rating')):
                                    st.write(f"**Rating:** {'⭐' * int(version['rating'])}")
                                if version.get('notes') is not None and not is_missing(version.get('notes')):
                                    st.write(f"**Notes:** {version['notes']}")
                            
                            with col3:
                                st.write(f"**Discogs ID:** {version['discogs_id']}")
                                st.write(f"**Instance ID:** {version['instance_id']}")
                                if version.get('date_added') is not None and not is_missing(version.get('date_added')):
                                    try:
                                        val = version['date_added']
                                        if hasattr(val, 'strftime'):
                                            date_str = val.strftime('%Y-%m-%d')
                                        else:
                                            date_str = str(val)[:10]
                                    except Exception:
                                        date_str = str(version.get('date_added'))[:10]
                                    st.write(f"**Added:** {date_str}")
    
    elif analysis_mode == "Duplicate Detection":
        st.subheader("🔄 Duplicate Detection")
        
        # Find duplicates using copies_count or instance_ids array length
        duplicates_query = """
        WITH dup_calc AS (
            SELECT 
                discogs_id,
                title,
                artist,
                year,
                label,
                catno,
                format,
                country,
                GREATEST(
                    COALESCE(copies_count, 1),
                    COALESCE(jsonb_array_length(instance_ids), 1)
                ) AS copy_count,
                CASE 
                    WHEN instance_ids IS NULL THEN NULL
                    ELSE array_to_string(ARRAY(SELECT jsonb_array_elements_text(instance_ids)), ', ')
                END AS instance_ids,
                condition,
                CAST(rating AS TEXT) AS ratings,
                MIN(date_added) OVER (PARTITION BY discogs_id) AS first_added,
                MAX(date_added) OVER (PARTITION BY discogs_id) AS last_added
            FROM releases
        )
        SELECT DISTINCT ON (discogs_id)
            discogs_id, title, artist, year, label, catno, format, country,
            copy_count, instance_ids, condition, ratings, first_added, last_added
        FROM dup_calc
        WHERE copy_count > 1
        ORDER BY discogs_id, copy_count DESC, title
        """
        
        duplicates_df = db_conn.execute_query(duplicates_query)
        
        if duplicates_df.empty:
            st.success("🎉 No exact duplicates found! Each release in your collection is unique.")
        else:
            st.warning(f"Found {len(duplicates_df)} releases with multiple copies:")
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_duplicates = duplicates_df['copy_count'].sum() - len(duplicates_df)
                st.metric("Extra Copies", total_duplicates)
            
            with col2:
                avg_copies = duplicates_df['copy_count'].mean()
                st.metric("Avg Copies per Release", f"{avg_copies:.1f}")
            
            with col3:
                max_copies = duplicates_df['copy_count'].max()
                st.metric("Most Copies of One Release", max_copies)
            
            # Duplicates table
            display_df = duplicates_df.copy()
            display_df.columns = [
                'Discogs ID', 'Title', 'Artist', 'Year', 'Label', 'Cat#', 'Format',
                'Country', 'Copies', 'Instance IDs', 'Conditions', 'Ratings',
                'First Added', 'Last Added'
            ]
            
            styled_df = style_with_background(
                display_df,
                subset=['Copies'], cmap='Reds', low=0.3, high=0.9,
                format_map={'Copies': '{:,}', 'Year': '{:.0f}'}
            )
            st.dataframe(styled_df, use_container_width=True)
            
            # Option to show potential cleanup actions
            if st.button("💡 Show Cleanup Suggestions"):
                st.subheader("Cleanup Suggestions")
                st.markdown("""
                **What this does:** Analyzes your duplicate releases and suggests cleanup actions based on:
                - Number of copies you own
                - Condition differences between copies
                - Potential redundancy in your collection
                """)
                
                for _, dup in duplicates_df.iterrows():
                    if dup['copy_count'] > 2:
                        st.warning(f"**{dup['title']}** by {dup['artist']}: {dup['copy_count']} copies - Consider keeping best condition copy")
                    elif dup['copy_count'] == 2:
                        # Handle condition comparison safely
                        condition_val = dup.get('condition', 'Unknown')
                        if condition_val and not is_missing(condition_val):
                            # If it's a single condition, it means both copies have same condition
                            st.info(f"**{dup['title']}**: Condition: {condition_val} - You have 2 copies with same condition. Consider keeping one unless there are other differences (pressing, year, etc.)")
                        else:
                            st.info(f"**{dup['title']}**: Multiple copies - Check individual conditions and keep the best one")

def display_artist_insights(db_conn):
    """Display enhanced collection insights (artists, labels, producers) with completeness analysis."""
    st.header("📚 Collection Insights")
    
    # Analysis type selection
    analysis_type = st.radio(
        "Analysis Type:",
        ["Artists", "Labels", "Producers"],
        horizontal=True
    )
    
    # Completeness type selection
    completeness_type = st.radio(
        "Show:",
        ["Most Complete Collections", "Least Complete Collections"],
        horizontal=True
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if analysis_type == "Artists":
            # Artist completeness analysis
            # Extra filters
            artist_filter = st.text_input("Filter by artist name", placeholder="e.g., Miles Davis")
            threshold = st.slider("Completeness threshold (%)", min_value=0, max_value=100, value=50, step=1)
            threshold_dir = st.radio("Threshold", ["Above or equal", "Below or equal"], horizontal=True, key="artist_completeness_threshold")
            comp_op = ">=" if threshold_dir == "Above or equal" else "<="

            # Build query with optional filters
            query = f"""
            WITH artist_stats AS (
                SELECT 
                    r.artist,
                    COUNT(*) as owned_releases,
                    COUNT(DISTINCT r.label) as labels_worked_with,
                    MIN(r.year) as first_year,
                    MAX(r.year) as last_year,
                    ROUND(AVG(r.rating), 2) as avg_rating,
                    -- Estimate total discography (this is approximate)
                    COUNT(*) * 3 as estimated_total_releases
                FROM releases r
                WHERE r.artist IS NOT NULL
                GROUP BY r.artist
                HAVING COUNT(*) >= 2  -- Only artists with multiple releases
            ),
            completeness_calc AS (
                SELECT *,
                    ROUND(((owned_releases::DOUBLE PRECISION / NULLIF(estimated_total_releases,0)::DOUBLE PRECISION) * 100)::NUMERIC, 1) as completeness_percentage,
                    (last_year - first_year + 1) as active_years
                FROM artist_stats
            )
            SELECT 
                artist,
                owned_releases,
                estimated_total_releases,
                completeness_percentage,
                labels_worked_with,
                active_years,
                first_year,
                last_year,
                avg_rating
            FROM completeness_calc
            WHERE completeness_percentage > 0
              AND (%s IS NULL OR artist ILIKE %s)
              AND completeness_percentage {comp_op} %s
            ORDER BY {{}}
            LIMIT 20
            """.format(
                "completeness_percentage DESC, owned_releases DESC" if completeness_type == "Most Complete Collections"
                else "completeness_percentage ASC, owned_releases ASC"
            )
            params = []
            name_pattern = f"%{artist_filter}%" if artist_filter else None
            params.extend([name_pattern, name_pattern, threshold])
        elif analysis_type == "Labels":
            # Label completeness analysis
            query = """
            WITH label_stats AS (
                SELECT 
                    r.label,
                    COUNT(*) as owned_releases,
                    COUNT(DISTINCT r.artist) as artists_on_label,
                    MIN(r.year) as first_release_year,
                    MAX(r.year) as last_release_year,
                    ROUND(AVG(r.rating), 2) as avg_rating,
                    -- Estimate label catalog size
                    COUNT(*) * 2 as estimated_catalog_size
                FROM releases r
                WHERE r.label IS NOT NULL AND r.label != ''
                GROUP BY r.label
                HAVING COUNT(*) >= 2  -- Only labels with multiple releases
            ),
            completeness_calc AS (
                SELECT *,
                    ROUND(((owned_releases::DOUBLE PRECISION / NULLIF(estimated_catalog_size,0)::DOUBLE PRECISION) * 100)::NUMERIC, 1) as completeness_percentage,
                    (last_release_year - first_release_year + 1) as active_years
                FROM label_stats
            )
            SELECT 
                label,
                owned_releases,
                estimated_catalog_size,
                completeness_percentage,
                artists_on_label,
                active_years,
                first_release_year,
                last_release_year,
                avg_rating
            FROM completeness_calc
            WHERE completeness_percentage > 0
            ORDER BY {}
            LIMIT 20
            """.format(
                "completeness_percentage DESC, owned_releases DESC" if completeness_type == "Most Complete Collections"
                else "completeness_percentage ASC, owned_releases ASC"
            )
        else:
            # Producers completeness analysis
            producer_filter = st.text_input("Filter by producer name", placeholder="e.g., Quincy Jones")
            p_threshold = st.slider("Completeness threshold (%)", min_value=0, max_value=100, value=50, step=1, key="producer_threshold")
            p_threshold_dir = st.radio("Threshold", ["Above or equal", "Below or equal"], horizontal=True, key="producer_threshold_dir")
            p_comp_op = ">=" if p_threshold_dir == "Above or equal" else "<="

            query = f"""
            WITH producer_stats AS (
                SELECT 
                    prod::text AS producer,
                    COUNT(*) as owned_releases,
                    COUNT(DISTINCT r.label) as labels_worked_with,
                    MIN(r.year) as first_year,
                    MAX(r.year) as last_year,
                    ROUND(AVG(r.rating), 2) as avg_rating,
                    COUNT(*) * 2 as estimated_total_releases
                FROM releases r,
                     LATERAL jsonb_array_elements_text(r.producers) AS prod
                WHERE r.producers IS NOT NULL
                GROUP BY prod
                HAVING COUNT(*) >= 2
            ),
            completeness_calc AS (
                SELECT *,
                    ROUND(((owned_releases::DOUBLE PRECISION / NULLIF(estimated_total_releases,0)::DOUBLE PRECISION) * 100)::NUMERIC, 1) as completeness_percentage,
                    (last_year - first_year + 1) as active_years
                FROM producer_stats
            )
            SELECT 
                producer,
                owned_releases,
                estimated_total_releases,
                completeness_percentage,
                labels_worked_with,
                active_years,
                first_year,
                last_year,
                avg_rating
            FROM completeness_calc
            WHERE completeness_percentage > 0
              AND (%s IS NULL OR producer ILIKE %s)
              AND completeness_percentage {p_comp_op} %s
            ORDER BY {{}}
            LIMIT 20
            """.format(
                "completeness_percentage DESC, owned_releases DESC" if completeness_type == "Most Complete Collections"
                else "completeness_percentage ASC, owned_releases ASC"
            )
            params = []
            prod_name = f"%{producer_filter}%" if producer_filter else None
            params.extend([prod_name, prod_name, p_threshold])
    
    with col2:
        show_analysis = st.button("📊 Analyze", type="primary")
    
    if show_analysis:
        if analysis_type in ("Artists", "Producers"):
            df = db_conn.execute_query(query, tuple(params))
        else:
            df = db_conn.execute_query(query)
        
        if df.empty:
            st.warning(f"No {analysis_type.lower()} data available")
            return
        
        # Display results
        st.subheader(f"{completeness_type} - {analysis_type}")
        
        # Create visualization
        if analysis_type == "Artists":
            # Artist visualization
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    df.head(10),
                    x='completeness_percentage',
                    y='artist',
                    orientation='h',
                    title=f"Top 10 {analysis_type} by Completeness",
                    labels={'completeness_percentage': 'Collection Completeness (%)', 'artist': 'Artist'},
                    color='completeness_percentage',
                    color_continuous_scale='RdYlGn' if completeness_type == "Most Complete Collections" else 'RdYlGn_r'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Scatter plot of completeness vs collection size
                fig = px.scatter(
                    df,
                    x='owned_releases',
                    y='completeness_percentage',
                    size='active_years',
                    hover_data=['artist', 'first_year', 'last_year', 'avg_rating'],
                    title="Collection Size vs Completeness",
                    labels={'owned_releases': 'Owned Releases', 'completeness_percentage': 'Completeness (%)'},
                    color='completeness_percentage',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        elif analysis_type == "Labels":
            # Label visualization
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    df.head(10),
                    x='completeness_percentage',
                    y='label',
                    orientation='h',
                    title=f"Top 10 {analysis_type} by Completeness",
                    labels={'completeness_percentage': 'Collection Completeness (%)', 'label': 'Label'},
                    color='completeness_percentage',
                    color_continuous_scale='RdYlGn' if completeness_type == "Most Complete Collections" else 'RdYlGn_r'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Scatter plot of completeness vs artists count
                fig = px.scatter(
                    df,
                    x='artists_on_label',
                    y='completeness_percentage',
                    size='owned_releases',
                    hover_data=['label', 'first_release_year', 'last_release_year', 'avg_rating'],
                    title="Label Diversity vs Completeness",
                    labels={'artists_on_label': 'Artists on Label', 'completeness_percentage': 'Completeness (%)'},
                    color='completeness_percentage',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
        elif analysis_type == "Producers":
            # Producers visualization
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    df.head(10),
                    x='completeness_percentage',
                    y='producer',
                    orientation='h',
                    title=f"Top 10 {analysis_type} by Completeness",
                    labels={'completeness_percentage': 'Collection Completeness (%)', 'producer': 'Producer'},
                    color='completeness_percentage',
                    color_continuous_scale='RdYlGn' if completeness_type == "Most Complete Collections" else 'RdYlGn_r'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.scatter(
                    df,
                    x='owned_releases',
                    y='completeness_percentage',
                    size='active_years',
                    hover_data=['producer', 'first_year', 'last_year', 'avg_rating'],
                    title="Collection Size vs Completeness",
                    labels={'owned_releases': 'Owned Releases', 'completeness_percentage': 'Completeness (%)'},
                    color='completeness_percentage',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)

        # Detailed table
        st.subheader("Detailed Analysis")
        
        if analysis_type == "Artists":
            # Format artist data
            display_df = df.copy()
            display_df.columns = [
                'Artist', 'Owned Releases', 'Est. Total Releases', 'Completeness (%)',
                'Labels Worked With', 'Active Years', 'First Year', 'Last Year', 'Avg Rating'
            ]
            
            # Style the dataframe
            styled_df = style_with_background(
                display_df,
                subset=['Completeness (%)'], cmap='RdYlGn', low=0.3, high=0.9,
                format_map={'Owned Releases': '{:,}','Est. Total Releases': '{:,}','Completeness (%)': '{:.1f}%','Labels Worked With': '{:,}','Active Years': '{:,}','First Year': '{:.0f}','Last Year': '{:.0f}','Avg Rating': '{:.1f}'}
            )
        elif analysis_type == "Labels":
            # Format label data
            display_df = df.copy()
            display_df.columns = [
                'Label', 'Owned Releases', 'Est. Catalog Size', 'Completeness (%)',
                'Artists on Label', 'Active Years', 'First Year', 'Last Year', 'Avg Rating'
            ]
            
            # Style the dataframe
            styled_df = style_with_background(
                display_df,
                subset=['Completeness (%)'], cmap='RdYlGn', low=0.3, high=0.9,
                format_map={'Owned Releases': '{:,}','Est. Catalog Size': '{:,}','Completeness (%)': '{:.1f}%','Artists on Label': '{:,}','Active Years': '{:,}','First Year': '{:.0f}','Last Year': '{:.0f}','Avg Rating': '{:.1f}'}
            )
        elif analysis_type == "Producers":
            display_df = df.copy()
            display_df.columns = [
                'Producer', 'Owned Releases', 'Est. Total Releases', 'Completeness (%)',
                'Labels Worked With', 'Active Years', 'First Year', 'Last Year', 'Avg Rating'
            ]
            styled_df = style_with_background(
                display_df,
                subset=['Completeness (%)'], cmap='RdYlGn', low=0.3, high=0.9,
                format_map={'Owned Releases': '{:,}','Est. Total Releases': '{:,}','Completeness (%)': '{:.1f}%','Labels Worked With': '{:,}','Active Years': '{:,}','First Year': '{:.0f}','Last Year': '{:.0f}','Avg Rating': '{:.1f}'}
            )
        st.dataframe(styled_df, use_container_width=True)


def display_producer_insights(db_conn):
    # Deprecated; functionality merged into Artist Insights under the "Producers" option.
    st.info("Producer Insights is now available under 'Artist Insights' → 'Producers'.")


def display_deals(db_conn):
    """Show inexpensive missing releases with filters."""
    st.header("💸 Deals: Inexpensive Missing Releases")
    # Load filter choices
    labels_df = db_conn.execute_query("SELECT DISTINCT label FROM releases WHERE label IS NOT NULL ORDER BY label LIMIT 1000")
    artists_df = db_conn.execute_query("SELECT DISTINCT artist FROM releases WHERE artist IS NOT NULL ORDER BY artist LIMIT 1000")
    producers_df = db_conn.execute_query(
        """
        SELECT DISTINCT p::text AS producer
        FROM releases, LATERAL jsonb_array_elements_text(producers) p
        WHERE producers IS NOT NULL
        ORDER BY 1 LIMIT 1000
        """
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        max_price = st.number_input("Max price", min_value=0.0, value=20.0, step=1.0)
    with col2:
        min_year = st.number_input("Min year", min_value=1900, max_value=2100, value=1970, step=1)
    with col3:
        limit = st.selectbox("Max results", [50, 100, 200], index=0)

    col4, col5, col6 = st.columns(3)
    with col4:
        selected_labels = st.multiselect(
            "Filter by label", labels_df['label'].dropna().tolist() if not labels_df.empty else []
        )
    with col5:
        selected_artists = st.multiselect(
            "Filter by artist", artists_df['artist'].dropna().tolist() if not artists_df.empty else []
        )
    with col6:
        selected_producers = st.multiselect(
            "Filter by producer", producers_df['producer'].dropna().tolist() if not producers_df.empty else []
        )

    # NOTE: requires release_prices table (added in setup.sql)
    base_sql = """
    WITH missing AS (
      SELECT ad.discogs_release_id, ad.title, ad.year
      FROM artist_discography ad
      WHERE ad.in_collection = false
    )
    SELECT m.discogs_release_id, r.title, r.year, r.label, r.format,
           p.lowest_price, p.currency, p.num_for_sale
    FROM missing m
    JOIN releases r ON r.discogs_id = m.discogs_release_id
    JOIN release_prices p ON p.discogs_release_id = m.discogs_release_id
    WHERE p.lowest_price IS NOT NULL
      AND p.lowest_price <= %s
      AND COALESCE(r.year,0) >= %s
    """

    params = [max_price, min_year]

    if selected_labels:
        base_sql += " AND r.label = ANY(%s)"
        params.append(selected_labels)

    if selected_artists:
        # ensure release belongs to one of selected artists via artist_discography
        base_sql += " AND EXISTS (SELECT 1 FROM artist_discography ad2 WHERE ad2.discogs_release_id = m.discogs_release_id AND ad2.artist_name = ANY(%s))"
        params.append(selected_artists)

    if selected_producers:
        base_sql += " AND EXISTS (SELECT 1 FROM jsonb_array_elements_text(r.producers) pr WHERE pr = ANY(%s))"
        params.append(selected_producers)

    base_sql += " ORDER BY p.lowest_price ASC, r.year DESC LIMIT %s"
    params.append(limit)

    df = db_conn.execute_query(base_sql, tuple(params))
    if df.empty:
        st.info("No deals found for the current filters.")
        return

    st.dataframe(
        df.style.format({
            'lowest_price': '{:.2f}',
            'year': '{:.0f}'
        }),
        use_container_width=True
    )


def display_availability_alerts(db_conn):
    """Show recent availability events (previously unavailable now available)."""
    st.header("🔔 Availability Alerts")
    hours = st.slider("Lookback hours", min_value=1, max_value=168, value=24)

    query = f"""
    SELECT e.event_time, e.discogs_release_id, r.title, r.artist, p.lowest_price, p.currency
    FROM availability_events e
    LEFT JOIN releases r ON r.discogs_id = e.discogs_release_id
    LEFT JOIN release_prices p ON p.discogs_release_id = e.discogs_release_id
    WHERE e.event_time >= NOW() - INTERVAL '{hours} hours'
    ORDER BY e.event_time DESC
    """
    df = db_conn.execute_query(query)
    if df.empty:
        st.info("No availability changes in the selected window.")
        return

    st.dataframe(
        df.style.format({'lowest_price': '{:.2f}'}),
        use_container_width=True
    )


def display_buying_guide(db_conn):
    """Roadmap for buying: inexpensive missing and wantlist prices."""
    st.header("🧭 Buying Guide")
    st.caption("Cheapest missing releases and your wantlist snapshot.")

    tab1, tab2 = st.tabs(["Inexpensive Missing", "Wantlist Overview"])

    with tab1:
        display_deals(db_conn)

    with tab2:
        # Require wantlist table
        wl_df = db_conn.execute_query("SELECT discogs_release_id, title, artist, year, label, format, rating, notes FROM wantlist ORDER BY year NULLS LAST, title LIMIT 200")
        if wl_df.empty:
            st.info("No wantlist items found. Run the downloader with --wantlist-only.")
        else:
            st.subheader("Your Wantlist")
            st.dataframe(
                wl_df.style.format({'year': '{:.0f}'}),
                use_container_width=True
            )

if __name__ == "__main__":
    main()