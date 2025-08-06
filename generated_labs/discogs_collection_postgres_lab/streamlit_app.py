#!/usr/bin/env python3
"""
Discogs Collection Viewer - Streamlit App (PostgreSQL Version)
Interactive web interface for viewing and exploring your Discogs collection stored in PostgreSQL.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import base64
from typing import Dict, List, Optional
import psycopg2
import psycopg2.extras
import os

# Page configuration
st.set_page_config(
    page_title="Discogs Collection Viewer",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #ff6b35;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .album-card {
        border: 1px solid #ddd;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #fafafa;
    }
    .genre-tag {
        background-color: #ff6b35;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        margin: 0.1rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

class PostgreSQLConnection:
    """Manages PostgreSQL database connection and queries."""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Establish connection to PostgreSQL."""
        try:
            # Get connection parameters from Streamlit secrets or environment
            if hasattr(st, 'secrets') and 'postgres' in st.secrets:
                config = st.secrets['postgres']
                self.connection = psycopg2.connect(
                    host=config['host'],
                    port=config.get('port', 5432),
                    database=config['database'],
                    user=config['user'],
                    password=config['password']
                )
            else:
                # Fall back to environment variables
                self.connection = psycopg2.connect(
                    host=os.getenv('POSTGRES_HOST', 'localhost'),
                    port=int(os.getenv('POSTGRES_PORT', '5432')),
                    database=os.getenv('POSTGRES_DATABASE', 'discogs_collection'),
                    user=os.getenv('POSTGRES_USER'),
                    password=os.getenv('POSTGRES_PASSWORD')
                )
            
            # Set search path
            with self.connection.cursor() as cursor:
                schema = os.getenv('POSTGRES_SCHEMA', 'collection_data')
                cursor.execute(f"SET search_path TO {schema}, public")
            self.connection.commit()
            
            st.success("✅ Connected to PostgreSQL")
        except Exception as e:
            st.error(f"❌ Failed to connect to PostgreSQL: {e}")
            self.connection = None
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """Execute query and return as DataFrame."""
        if not self.connection:
            st.error("No PostgreSQL connection available")
            return pd.DataFrame()
        
        try:
            cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert to DataFrame
            if results:
                return pd.DataFrame([dict(row) for row in results])
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Query execution failed: {e}")
            return pd.DataFrame()

@st.cache_data
def load_collection_stats(_db_conn):
    """Load collection statistics."""
    query = "SELECT * FROM collection_stats"
    return _db_conn.execute_query(query)

@st.cache_data
def load_genre_analysis(_db_conn):
    """Load genre analysis data."""
    query = "SELECT * FROM genre_analysis ORDER BY release_count DESC LIMIT 20"
    return _db_conn.execute_query(query)

@st.cache_data
def load_decade_analysis(_db_conn):
    """Load decade analysis data."""
    query = "SELECT * FROM decade_analysis ORDER BY decade"
    return _db_conn.execute_query(query)

@st.cache_data
def load_releases(_db_conn, limit: int = 1000):
    """Load releases data."""
    query = f"""
    SELECT release_id, title, artist, year, label, catno, format, 
           genres, styles, country, rating, condition, sleeve_condition, date_added
    FROM releases 
    ORDER BY date_added DESC 
    LIMIT {limit}
    """
    return _db_conn.execute_query(query)

@st.cache_data
def search_collection(_db_conn, search_term: str):
    """Search the collection."""
    query = "SELECT * FROM search_collection(%s)"
    return _db_conn.execute_query(query, (search_term,))

@st.cache_data
def search_collection_fulltext(_db_conn, search_term: str):
    """Search the collection using full-text search."""
    query = "SELECT * FROM search_collection_fulltext(%s)"
    return _db_conn.execute_query(query, (search_term,))

def display_collection_overview(db_conn):
    """Display collection overview with key metrics."""
    st.markdown('<h1 class="main-header">🎵 Your Discogs Collection</h1>', unsafe_allow_html=True)
    
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
        st.metric(
            label="Year Range",
            value=f"{int(stats['earliest_year'])}-{int(stats['latest_year'])}",
            delta=f"{int(stats['years_span'])} years"
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

def display_genre_analysis(db_conn):
    """Display genre analysis charts."""
    st.header("📊 Genre Analysis")
    
    genre_df = load_genre_analysis(db_conn)
    
    if genre_df.empty:
        st.warning("No genre data available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Genre distribution pie chart
        fig_pie = px.pie(
            genre_df.head(10),
            values='release_count',
            names='genre',
            title="Top 10 Genres by Release Count"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Genre bar chart
        fig_bar = px.bar(
            genre_df.head(15),
            x='release_count',
            y='genre',
            orientation='h',
            title="Top 15 Genres",
            labels={'release_count': 'Number of Releases', 'genre': 'Genre'}
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # Genre details table
    st.subheader("Genre Statistics")
    st.dataframe(
        genre_df.style.format({
            'release_count': '{:,}',
            'artist_count': '{:,}',
            'avg_year': '{:.0f}',
            'avg_rating': '{:.1f}'
        }),
        use_container_width=True
    )

def display_decade_analysis(db_conn):
    """Display decade analysis."""
    st.header("📅 Decade Analysis")
    
    decade_df = load_decade_analysis(db_conn)
    
    if decade_df.empty:
        st.warning("No decade data available")
        return
    
    # Decade timeline chart
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Releases by Decade', 'Average Rating by Decade'),
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
    )
    
    # Releases by decade
    fig.add_trace(
        go.Bar(
            x=decade_df['decade'],
            y=decade_df['release_count'],
            name='Releases',
            marker_color='lightblue'
        ),
        row=1, col=1
    )
    
    # Average rating by decade
    fig.add_trace(
        go.Scatter(
            x=decade_df['decade'],
            y=decade_df['avg_rating'],
            mode='lines+markers',
            name='Avg Rating',
            line=dict(color='orange', width=3),
            marker=dict(size=8)
        ),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Decade", row=2, col=1)
    fig.update_yaxes(title_text="Number of Releases", row=1, col=1)
    fig.update_yaxes(title_text="Average Rating", row=2, col=1)
    
    fig.update_layout(height=600, title_text="Collection Timeline")
    st.plotly_chart(fig, use_container_width=True)
    
    # Decade details table
    st.subheader("Decade Statistics")
    st.dataframe(
        decade_df.style.format({
            'decade': '{:.0f}s',
            'release_count': '{:,}',
            'artist_count': '{:,}',
            'avg_rating': '{:.1f}'
        }),
        use_container_width=True
    )

def display_collection_browser(db_conn):
    """Display collection browser with search and filtering."""
    st.header("🔍 Browse Collection")
    
    # Search functionality
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        search_term = st.text_input("Search your collection", placeholder="Enter artist, album, label, or genre...")
    
    with col2:
        limit = st.selectbox("Records to show", [50, 100, 500, 1000], index=1)
    
    with col3:
        search_type = st.selectbox("Search Type", ["Basic", "Full-text"], index=0)
    
    with col4:
        show_search = st.button("🔍 Search", type="primary")
    
    # Load and display data
    if search_term and show_search:
        if search_type == "Full-text":
            df = search_collection_fulltext(db_conn, search_term)
        else:
            df = search_collection(db_conn, search_term)
        st.subheader(f"Search Results for '{search_term}'")
    else:
        df = load_releases(db_conn, limit)
        st.subheader("Recent Additions")
    
    if df.empty:
        st.warning("No releases found")
        return
    
    # Filters
    with st.expander("🎛️ Filters"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            year_range = st.slider(
                "Year Range",
                min_value=int(df['year'].min()) if 'year' in df and not df['year'].isna().all() else 1950,
                max_value=int(df['year'].max()) if 'year' in df and not df['year'].isna().all() else 2024,
                value=(
                    int(df['year'].min()) if 'year' in df and not df['year'].isna().all() else 1950,
                    int(df['year'].max()) if 'year' in df and not df['year'].isna().all() else 2024
                )
            )
        
        with col2:
            if 'country' in df:
                countries = ['All'] + sorted(df['country'].dropna().unique().tolist())
                selected_country = st.selectbox("Country", countries)
            else:
                selected_country = 'All'
        
        with col3:
            if 'condition' in df:
                conditions = ['All'] + sorted(df['condition'].dropna().unique().tolist())
                selected_condition = st.selectbox("Condition", conditions)
            else:
                selected_condition = 'All'
        
        with col4:
            if 'rating' in df:
                min_rating = st.slider("Minimum Rating", 0, 5, 0)
            else:
                min_rating = 0
    
    # Apply filters
    filtered_df = df.copy()
    
    if 'year' in filtered_df:
        filtered_df = filtered_df[
            (filtered_df['year'].between(year_range[0], year_range[1])) |
            (filtered_df['year'].isna())
        ]
    
    if selected_country != 'All' and 'country' in filtered_df:
        filtered_df = filtered_df[filtered_df['country'] == selected_country]
    
    if selected_condition != 'All' and 'condition' in filtered_df:
        filtered_df = filtered_df[filtered_df['condition'] == selected_condition]
    
    if min_rating > 0 and 'rating' in filtered_df:
        filtered_df = filtered_df[
            (filtered_df['rating'] >= min_rating) | 
            (filtered_df['rating'].isna())
        ]
    
    # Display results
    st.write(f"Showing {len(filtered_df)} of {len(df)} releases")
    
    # Release cards
    for _, release in filtered_df.iterrows():
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 1])
            
            with col1:
                # Placeholder for artwork (if available)
                st.image("https://via.placeholder.com/150x150?text=No+Image", width=100)
            
            with col2:
                st.markdown(f"**{release.get('title', 'Unknown Title')}**")
                st.markdown(f"*by {release.get('artist', 'Unknown Artist')}*")
                
                details = []
                if pd.notna(release.get('year')):
                    details.append(f"Year: {int(release['year'])}")
                if pd.notna(release.get('label')):
                    details.append(f"Label: {release['label']}")
                if pd.notna(release.get('catno')):
                    details.append(f"Cat#: {release['catno']}")
                if pd.notna(release.get('format')):
                    details.append(f"Format: {release['format']}")
                
                if details:
                    st.markdown(" • ".join(details))
                
                # Genres as tags
                if pd.notna(release.get('genres')):
                    try:
                        # Handle both string JSON and list formats
                        if isinstance(release['genres'], str):
                            genres = json.loads(release['genres'])
                        else:
                            genres = release['genres']
                        
                        if genres and isinstance(genres, list):
                            genre_tags = "".join([f'<span class="genre-tag">{genre}</span>' for genre in genres[:3]])
                            st.markdown(genre_tags, unsafe_allow_html=True)
                    except:
                        pass
            
            with col3:
                if pd.notna(release.get('rating')) and release['rating'] > 0:
                    rating = int(release['rating'])
                    st.markdown("⭐" * rating + "☆" * (5 - rating))
                
                if pd.notna(release.get('condition')):
                    st.markdown(f"**Condition:** {release['condition']}")
            
            st.divider()

def display_artist_insights(db_conn):
    """Display artist-related insights."""
    st.header("🎤 Artist Insights")
    
    # Top artists by release count
    query = """
    SELECT artist, COUNT(*) as release_count, 
           ROUND(AVG(rating), 2) as avg_rating,
           MIN(year) as first_year,
           MAX(year) as last_year
    FROM releases 
    WHERE artist IS NOT NULL
    GROUP BY artist 
    ORDER BY release_count DESC 
    LIMIT 20
    """
    
    artists_df = db_conn.execute_query(query)
    
    if artists_df.empty:
        st.warning("No artist data available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top artists bar chart
        fig = px.bar(
            artists_df.head(10),
            x='release_count',
            y='artist',
            orientation='h',
            title="Top 10 Artists by Release Count",
            labels={'release_count': 'Number of Releases', 'artist': 'Artist'}
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Artist ratings scatter plot
        fig = px.scatter(
            artists_df,
            x='release_count',
            y='avg_rating',
            size='release_count',
            hover_data=['artist', 'first_year', 'last_year'],
            title="Artist Ratings vs Collection Size",
            labels={'release_count': 'Releases in Collection', 'avg_rating': 'Average Rating'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Artists table
    st.subheader("Top Artists")
    st.dataframe(
        artists_df.style.format({
            'release_count': '{:,}',
            'avg_rating': '{:.1f}',
            'first_year': '{:.0f}',
            'last_year': '{:.0f}'
        }),
        use_container_width=True
    )

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
        ["Overview", "Genre Analysis", "Decade Timeline", "Browse Collection", "Artist Insights"]
    )
    
    # Sidebar info
    with st.sidebar:
        st.markdown("---")
        st.markdown("### About")
        st.markdown("This app displays your Discogs collection data stored in PostgreSQL.")
        st.markdown("Use the navigation above to explore different views of your music collection.")
        
        st.markdown("### Data Refresh")
        if st.button("🔄 Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")
        
        st.markdown("---")
        st.markdown("*Built with Streamlit & PostgreSQL* 🐘")
    
    # Main content based on selected page
    if page == "Overview":
        display_collection_overview(db_conn)
    elif page == "Genre Analysis":
        display_genre_analysis(db_conn)
    elif page == "Decade Timeline":
        display_decade_analysis(db_conn)
    elif page == "Browse Collection":
        display_collection_browser(db_conn)
    elif page == "Artist Insights":
        display_artist_insights(db_conn)

if __name__ == "__main__":
    main()