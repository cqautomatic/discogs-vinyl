#!/usr/bin/env python3
"""
Enhanced Discogs Collection Viewer - Streamlit App (PostgreSQL Version)
Enhanced with track-level detail and artist discography features.
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
    page_title="Enhanced Discogs Collection Viewer",
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
    .track-card {
        border-left: 3px solid #ff6b35;
        padding: 0.5rem;
        margin: 0.2rem 0;
        background-color: #f9f9f9;
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
    .artist-tag {
        background-color: #4a90e2;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        margin: 0.1rem;
        display: inline-block;
    }
    .missing-release {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.3rem;
        padding: 0.5rem;
        margin: 0.2rem 0;
    }
    .owned-release {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.3rem;
        padding: 0.5rem;
        margin: 0.2rem 0;
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
def load_various_artists_analysis(_db_conn):
    """Load Various Artists album analysis."""
    query = "SELECT * FROM various_artists_analysis ORDER BY unique_artist_count DESC LIMIT 20"
    return _db_conn.execute_query(query)

@st.cache_data
def load_artist_discography_summary(_db_conn):
    """Load artist discography summary."""
    query = "SELECT * FROM artist_discography_summary WHERE total_releases > 0 ORDER BY collection_completeness_percent ASC LIMIT 50"
    return _db_conn.execute_query(query)

@st.cache_data
def get_tracks_for_release(_db_conn, release_id: str):
    """Get track listing for a specific release."""
    query = """
    SELECT track_id, track_number, title, artists, extraartists, duration
    FROM tracks 
    WHERE release_id = %s 
    ORDER BY track_number
    """
    return _db_conn.execute_query(query, (release_id,))

@st.cache_data
def get_artist_missing_releases(_db_conn, artist_name: str):
    """Get missing releases for an artist."""
    query = "SELECT * FROM get_artist_missing_releases(%s) ORDER BY year DESC"
    return _db_conn.execute_query(query, (artist_name,))

@st.cache_data
def search_tracks(_db_conn, search_term: str):
    """Search tracks."""
    query = "SELECT * FROM search_tracks(%s) LIMIT 100"
    return _db_conn.execute_query(query, (search_term,))

def display_enhanced_overview(db_conn):
    """Display enhanced overview with new features."""
    st.markdown('<h1 class="main-header">🎵 Enhanced Discogs Collection</h1>', unsafe_allow_html=True)
    
    # Load collection statistics
    stats_df = load_collection_stats(db_conn)
    
    if stats_df.empty:
        st.warning("No collection data found. Please run the enhanced downloader first.")
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
        # Get track count
        track_count = db_conn.execute_query("SELECT COUNT(*) as count FROM tracks")
        track_count_val = track_count.iloc[0]['count'] if not track_count.empty else 0
        st.metric(
            label="Total Tracks",
            value=int(track_count_val)
        )
    
    with col4:
        rating = stats['avg_rating']
        st.metric(
            label="Average Rating",
            value=f"{rating:.1f}/5" if pd.notna(rating) else "N/A"
        )

def display_various_artists_analysis(db_conn):
    """Display analysis of Various Artists albums."""
    st.header("🎭 Various Artists & Compilation Analysis")
    
    various_df = load_various_artists_analysis(db_conn)
    
    if various_df.empty:
        st.info("No Various Artists albums found in your collection.")
        return
    
    # Various Artists overview
    col1, col2 = st.columns(2)
    
    with col1:
        # Top compilations by artist count
        fig = px.bar(
            various_df.head(10),
            x='unique_artist_count',
            y='album_title',
            orientation='h',
            title="Top Compilations by Artist Diversity",
            labels={'unique_artist_count': 'Number of Unique Artists', 'album_title': 'Album'}
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Track count vs artist count scatter
        fig = px.scatter(
            various_df,
            x='track_count',
            y='unique_artist_count',
            size='track_count',
            hover_data=['album_title', 'year'],
            title="Track Count vs Artist Diversity",
            labels={'track_count': 'Number of Tracks', 'unique_artist_count': 'Unique Artists'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Various Artists table
    st.subheader("Various Artists Albums Details")
    
    # Allow user to select an album to see track details
    selected_album = st.selectbox(
        "Select album to view track details:",
        options=various_df['album_title'].tolist(),
        index=0
    )
    
    if selected_album:
        # Get release_id for selected album
        selected_release = various_df[various_df['album_title'] == selected_album].iloc[0]
        release_id = selected_release['release_id']
        
        # Display album info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Year", selected_release['year'])
        with col2:
            st.metric("Total Tracks", selected_release['track_count'])
        with col3:
            st.metric("Unique Artists", selected_release['unique_artist_count'])
        
        # Get and display track listing
        tracks_df = get_tracks_for_release(db_conn, release_id)
        
        if not tracks_df.empty:
            st.subheader(f"Track Listing - {selected_album}")
            
            for _, track in tracks_df.iterrows():
                with st.container():
                    st.markdown(f'<div class="track-card">', unsafe_allow_html=True)
                    
                    # Track number and title
                    track_info = f"**{track.get('track_number', '')}. {track.get('title', 'Unknown Track')}**"
                    if track.get('duration'):
                        track_info += f" ({track['duration']})"
                    st.markdown(track_info)
                    
                    # Track artists
                    if track.get('artists') is not None and not pd.isna(track.get('artists')):
                        try:
                            artists = json.loads(track['artists']) if isinstance(track['artists'], str) else track['artists']
                            if artists:
                                artist_tags = "".join([f'<span class="artist-tag">{artist}</span>' for artist in artists])
                                st.markdown(f"Artists: {artist_tags}", unsafe_allow_html=True)
                        except:
                            pass
                    
                    # Extra artists (featuring, remix, etc.)
                    if track.get('extraartists') is not None and not pd.isna(track.get('extraartists')):
                        try:
                            extra_artists = json.loads(track['extraartists']) if isinstance(track['extraartists'], str) else track['extraartists']
                            if extra_artists:
                                extra_info = []
                                for extra in extra_artists:
                                    if isinstance(extra, dict):
                                        role = extra.get('role', '')
                                        name = extra.get('name', '')
                                        if name and role:
                                            extra_info.append(f"{name} ({role})")
                                if extra_info:
                                    st.markdown(f"*{', '.join(extra_info)}*")
                        except:
                            pass
                    
                    st.markdown('</div>', unsafe_allow_html=True)

def display_artist_discography_analysis(db_conn):
    """Display artist discography completeness analysis."""
    st.header("🎤 Artist Discography Analysis")
    
    discography_df = load_artist_discography_summary(db_conn)
    
    if discography_df.empty:
        st.info("No artist discography data available. Run the enhanced downloader to collect this information.")
        return
    
    # Artist completeness overview
    col1, col2 = st.columns(2)
    
    with col1:
        # Collection completeness distribution
        fig = px.histogram(
            discography_df,
            x='collection_completeness_percent',
            nbins=20,
            title="Collection Completeness Distribution",
            labels={'collection_completeness_percent': 'Completeness %', 'count': 'Number of Artists'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top incomplete artists (lowest completeness)
        incomplete_df = discography_df[discography_df['collection_completeness_percent'] < 100].head(10)
        fig = px.bar(
            incomplete_df,
            x='collection_completeness_percent',
            y='artist_name',
            orientation='h',
            title="Most Incomplete Artists",
            labels={'collection_completeness_percent': 'Collection Completeness %', 'artist_name': 'Artist'}
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    # Artist selection for detailed analysis
    st.subheader("Detailed Artist Analysis")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        completeness_filter = st.slider(
            "Show artists with completeness below:",
            min_value=0,
            max_value=100,
            value=80,
            step=5
        )
    
    with col2:
        min_releases = st.slider(
            "Minimum total releases:",
            min_value=1,
            max_value=50,
            value=5
        )
    
    with col3:
        show_count = st.selectbox("Show top:", [10, 20, 30, 50], index=1)
    
    # Apply filters
    filtered_df = discography_df[
        (discography_df['collection_completeness_percent'] <= completeness_filter) &
        (discography_df['total_releases'] >= min_releases)
    ].head(show_count)
    
    # Display filtered results
    if not filtered_df.empty:
        for _, artist in filtered_df.iterrows():
            with st.expander(f"🎵 {artist['artist_name']} - {artist['collection_completeness_percent']:.1f}% complete"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Releases", int(artist['total_releases']))
                with col2:
                    st.metric("Owned", int(artist['owned_releases']))
                with col3:
                    st.metric("Missing", int(artist['missing_releases']))
                with col4:
                    st.metric("Completeness", f"{artist['collection_completeness_percent']:.1f}%")
                
                # Show missing releases
                missing_df = get_artist_missing_releases(db_conn, artist['artist_name'])
                
                if not missing_df.empty:
                    st.subheader("Missing Releases")
                    
                    for _, release in missing_df.head(10).iterrows():
                        with st.container():
                            st.markdown(f'<div class="missing-release">', unsafe_allow_html=True)
                            
                            # Release info
                            year_info = f" ({int(release['year'])})" if release.get('year') is not None and not pd.isna(release['year']) else ""
                            st.markdown(f"**{release.get('title', 'Unknown Title')}{year_info}**")
                            
                            # Additional details
                            details = []
                            if release.get('label') is not None and not pd.isna(release.get('label')):
                                details.append(f"Label: {release['label']}")
                            if release.get('format') is not None and not pd.isna(release.get('format')):
                                details.append(f"Format: {release['format']}")
                            if release.get('role') is not None and not pd.isna(release.get('role')) and release['role'] != 'Main':
                                details.append(f"Role: {release['role']}")
                            
                            if details:
                                st.markdown(" • ".join(details))
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                    
                    if len(missing_df) > 10:
                        st.info(f"Showing 10 of {len(missing_df)} missing releases...")

def display_track_search(db_conn):
    """Display track search functionality."""
    st.header("🔍 Track Search")
    
    st.markdown("Search individual tracks across your collection, especially useful for Various Artists albums.")
    
    # Search functionality
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input(
            "Search tracks", 
            placeholder="Enter track title, artist name, or keyword..."
        )
    
    with col2:
        search_button = st.button("🔍 Search Tracks", type="primary")
    
    if search_term and search_button:
        tracks_df = search_tracks(db_conn, search_term)
        
        if not tracks_df.empty:
            st.subheader(f"Found {len(tracks_df)} tracks matching '{search_term}'")
            
            for _, track in tracks_df.iterrows():
                with st.container():
                    st.markdown(f'<div class="track-card">', unsafe_allow_html=True)
                    
                    # Track and album info
                    st.markdown(f"**{track.get('track_title', 'Unknown Track')}**")
                    st.markdown(f"*from {track.get('release_title', 'Unknown Album')}*")
                    
                    # Track details
                    details = []
                    if track.get('track_number'):
                        details.append(f"Track {track['track_number']}")
                    if track.get('duration'):
                        details.append(f"Duration: {track['duration']}")
                    
                    if details:
                        st.markdown(" • ".join(details))
                    
                    # Track artists
                    if track.get('track_artists') is not None and not pd.isna(track.get('track_artists')):
                        try:
                            artists = json.loads(track['track_artists']) if isinstance(track['track_artists'], str) else track['track_artists']
                            if artists:
                                artist_tags = "".join([f'<span class="artist-tag">{artist}</span>' for artist in artists])
                                st.markdown(f"Artists: {artist_tags}", unsafe_allow_html=True)
                        except:
                            pass
                    
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info(f"No tracks found matching '{search_term}'")

def main():
    """Main Streamlit app."""
    # Initialize database connection
    db_conn = PostgreSQLConnection()
    
    if not db_conn.connection:
        st.error("Cannot connect to database. Please check your configuration.")
        st.stop()
    
    # Sidebar navigation
    st.sidebar.title("🎵 Enhanced Navigation")
    page = st.sidebar.radio(
        "Choose a view:",
        [
            "Enhanced Overview", 
            "Various Artists Analysis", 
            "Artist Discography", 
            "Track Search",
            "Standard Views"
        ]
    )
    
    # Standard views submenu
    if page == "Standard Views":
        sub_page = st.sidebar.radio(
            "Standard views:",
            ["Collection Overview", "Genre Analysis", "Decade Timeline", "Browse Collection", "Artist Insights"]
        )
    
    # Sidebar info
    with st.sidebar:
        st.markdown("---")
        st.markdown("### New Features")
        st.markdown("✨ **Track-level details** for Various Artists albums")
        st.markdown("📊 **Artist discography completeness** analysis")
        st.markdown("🔍 **Track search** across your collection")
        st.markdown("📈 **Enhanced analytics** and insights")
        
        st.markdown("### Data Refresh")
        if st.button("🔄 Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")
        
        st.markdown("---")
        st.markdown("*Enhanced Discogs Collection with PostgreSQL* 🐘")
    
    # Main content based on selected page
    if page == "Enhanced Overview":
        display_enhanced_overview(db_conn)
    elif page == "Various Artists Analysis":
        display_various_artists_analysis(db_conn)
    elif page == "Artist Discography":
        display_artist_discography_analysis(db_conn)
    elif page == "Track Search":
        display_track_search(db_conn)
    elif page == "Standard Views":
        # Import and use functions from original streamlit_app.py
        if sub_page == "Collection Overview":
            from streamlit_app import display_collection_overview
            display_collection_overview(db_conn)
        elif sub_page == "Genre Analysis":
            from streamlit_app import display_genre_analysis
            display_genre_analysis(db_conn)
        elif sub_page == "Decade Timeline":
            from streamlit_app import display_decade_analysis
            display_decade_analysis(db_conn)
        elif sub_page == "Browse Collection":
            from streamlit_app import display_collection_browser
            display_collection_browser(db_conn)
        elif sub_page == "Artist Insights":
            from streamlit_app import display_artist_insights
            display_artist_insights(db_conn)

if __name__ == "__main__":
    main()