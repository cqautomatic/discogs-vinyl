"""
Collection view functions for the Discogs Streamlit app.
Contains all the major section displays.
"""

import streamlit as st

import pandas as pd

# Standard thumbnail setting for consistent display
# Use container width for responsive sizing that's consistent across all containers
USE_CONTAINER_WIDTH = True
import plotly.express as px
from typing import Optional
try:
    from streamlit_plotly_events import plotly_events
except ImportError:
    plotly_events = None

from core.database import PostgreSQLConnection

# Country code to flag emoji mapping
COUNTRY_FLAGS = {
    'US': '🇺🇸', 'USA': '🇺🇸', 'United States': '🇺🇸',
    'UK': '🇬🇧', 'United Kingdom': '🇬🇧', 'England': '🇬🇧', 'GB': '🇬🇧',
    'Germany': '🇩🇪', 'DE': '🇩🇪',
    'France': '🇫🇷', 'FR': '🇫🇷',
    'Japan': '🇯🇵', 'JP': '🇯🇵',
    'Canada': '🇨🇦', 'CA': '🇨🇦',
    'Australia': '🇦🇺', 'AU': '🇦🇺',
    'Netherlands': '🇳🇱', 'NL': '🇳🇱',
    'Italy': '🇮🇹', 'IT': '🇮🇹',
    'Spain': '🇪🇸', 'ES': '🇪🇸',
    'Sweden': '🇸🇪', 'SE': '🇸🇪',
    'Norway': '🇳🇴', 'NO': '🇳🇴',
    'Denmark': '🇩🇰', 'DK': '🇩🇰',
    'Finland': '🇫🇮', 'FI': '🇫🇮',
    'Belgium': '🇧🇪', 'BE': '🇧🇪',
    'Switzerland': '🇨🇭', 'CH': '🇨🇭',
    'Austria': '🇦🇹', 'AT': '🇦🇹',
    'Brazil': '🇧🇷', 'BR': '🇧🇷',
    'Mexico': '🇲🇽', 'MX': '🇲🇽',
    'Argentina': '🇦🇷', 'AR': '🇦🇷',
    'Russia': '🇷🇺', 'RU': '🇷🇺',
    'Poland': '🇵🇱', 'PL': '🇵🇱',
    'Czech Republic': '🇨🇿', 'CZ': '🇨🇿',
    'Hungary': '🇭🇺', 'HU': '🇭🇺',
    'Portugal': '🇵🇹', 'PT': '🇵🇹',
    'Greece': '🇬🇷', 'GR': '🇬🇷',
    'Turkey': '🇹🇷', 'TR': '🇹🇷',
    'South Korea': '🇰🇷', 'KR': '🇰🇷',
    'China': '🇨🇳', 'CN': '🇨🇳',
    'India': '🇮🇳', 'IN': '🇮🇳',
    'Israel': '🇮🇱', 'IL': '🇮🇱',
    'South Africa': '🇿🇦', 'ZA': '🇿🇦',
    'New Zealand': '🇳🇿', 'NZ': '🇳🇿',
    'Ireland': '🇮🇪', 'IE': '🇮🇪',
    'Iceland': '🇮🇸', 'IS': '🇮🇸',
    'Chile': '🇨🇱', 'CL': '🇨🇱',
    'Colombia': '🇨🇴', 'CO': '🇨🇴',
    'Venezuela': '🇻🇪', 'VE': '🇻🇪',
    'Peru': '🇵🇪', 'PE': '🇵🇪',
    'Uruguay': '🇺🇾', 'UY': '🇺🇾',
    'Slovenia': '🇸🇮', 'SI': '🇸🇮',
    'Croatia': '🇭🇷', 'HR': '🇭🇷',
    'Serbia': '🇷🇸', 'RS': '🇷🇸',
    'Ukraine': '🇺🇦', 'UA': '🇺🇦',
    'Romania': '🇷🇴', 'RO': '🇷🇴',
    'Bulgaria': '🇧🇬', 'BG': '🇧🇬'
}

def get_country_flag(country_name):
    """Get flag emoji for country name with proper styling."""
    if not country_name or country_name.lower() == 'unknown':
        return '🌍', 'Unknown'
    
    # Clean up country name
    country_clean = country_name.strip()
    
    # Look up flag
    flag = COUNTRY_FLAGS.get(country_clean, '🌍')
    
    return flag, country_clean
from data.loaders import (
    load_collection_stats, load_genre_analysis, load_style_analysis,
    load_decade_analysis, load_random_releases, load_collection_valuation,
    load_community_stats_check, load_releases, load_random_covers,
    load_styles_for_genre, load_genres_for_style, load_releases_for_genre,
    load_releases_for_style, load_releases_for_genre_and_style, load_releases_for_year, load_year_breakdown,
    search_by_aliases
)

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

def display_enhanced_overview(db_conn: PostgreSQLConnection):
    """Enhanced collection overview with stats and charts."""
    st.header("📊 Enhanced Overview")
    
    # Load collection stats
    stats_df = load_collection_stats(db_conn)
    if stats_df.empty:
        st.warning("No collection statistics available")
        return
    
    stats = stats_df.iloc[0]
    
    # Display key metrics - Top row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Albums", int(stats['total_items']))
    with col2:
        st.metric("Unique Artists", int(stats['unique_artists']))
    with col3:
        st.metric("Countries", int(stats['countries']))
    with col4:
        if stats['avg_rating']:
            st.metric("Avg Rating", f"{float(stats['avg_rating']):.1f}")
        else:
            st.metric("Avg Rating", "N/A")
    
    # Second row - Year range, Collection value, and Price statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if stats['earliest_year']:
            st.metric("Earliest Year", int(stats['earliest_year']))
    with col2:
        if stats['latest_year']:
            st.metric("Latest Year", int(stats['latest_year']))
    with col3:
        # Collection value display - using high-quality condition pricing
        min_price = stats.get('min_price')
        max_price = stats.get('max_price') 
        total_value = stats.get('total_value')  # Conservative (lowest prices) - partial collection
        high_quality_value = stats.get('high_quality_value')  # 30% premium - partial collection
        excellent_condition_value = stats.get('excellent_condition_value')  # 50% premium - partial collection
        extrapolated_total_value = stats.get('extrapolated_total_value')  # Full collection estimate
        extrapolated_high_quality_value = stats.get('extrapolated_high_quality_value')  # Full collection high-quality
        avg_price = stats.get('avg_price')
        priced_items = stats.get('priced_items', 0)
        total_items = stats.get('total_items', 0)
        
        if extrapolated_high_quality_value and priced_items:
            # Use extrapolated high-quality pricing for full collection estimate
            extrapolated_hq_val = float(extrapolated_high_quality_value)
            partial_val = float(high_quality_value) if high_quality_value else 0
            priced_count = int(priced_items)
            total_count = int(total_items)
            coverage_pct = (priced_count / total_count * 100) if total_count > 0 else 0
            
            # Show extrapolated value for full collection
            st.metric(
                "Est. Collection Value (Full)", 
                f"${extrapolated_hq_val:,.0f}", 
                f"Extrapolated from {priced_count:,} priced items ({coverage_pct:.1f}%)"
            )
        elif high_quality_value and priced_items:
            # Fallback to partial collection value
            high_quality_val = float(high_quality_value)
            conservative_val = float(total_value) if total_value else 0
            priced_count = int(priced_items)
            total_count = int(total_items)
            coverage_pct = (priced_count / total_count * 100) if total_count > 0 else 0
            
            premium_amount = high_quality_val - conservative_val
            st.metric(
                "Collection Value (Partial)", 
                f"${high_quality_val:,.0f}", 
                f"Only {priced_count:,} of {total_count:,} items priced ({coverage_pct:.1f}%)"
            )
        elif priced_items and priced_items > 0:
            # Has some pricing but no total value (shouldn't happen but fallback)
            st.metric("Collection Value", f"{priced_items:,} items priced", "Partial pricing data")
        else:
            # No pricing data available
            st.metric("Collection Value", "No pricing data", "Pricing data not available")
    
    with col4:
        # Additional pricing statistics with condition estimates
        if min_price and max_price and avg_price:
            min_val = float(min_price)
            max_val = float(max_price)
            avg_val = float(avg_price)
            
            # Calculate extrapolated excellent condition (50% premium for full collection)
            if extrapolated_total_value:
                extrapolated_excellent = float(extrapolated_total_value) * 1.5
                st.metric("Est. Excellent Condition", f"${extrapolated_excellent:,.0f}", f"50% premium • Full collection estimate")
            elif excellent_condition_value:
                excellent_val = float(excellent_condition_value)
                st.metric("Excellent Condition (Partial)", f"${excellent_val:,.0f}", f"50% premium • ${avg_val:.0f} avg price")
            else:
                st.metric("Price Range", f"${min_val:.0f} - ${max_val:.0f}", f"${avg_val:.0f} average")
        elif priced_items and priced_items > 0:
            st.metric("Price Data", f"{priced_items:,} items", "Refreshing prices...")
        else:
            st.metric("Price Data", "Not available", "No pricing data")
    

    # Refresh token to force re-run and bypass cache for random covers
    if 'random_covers_token' not in st.session_state:
        st.session_state.random_covers_token = 0
    
    # Title and refresh button on same line
    col_title, col_spacer, col_refresh = st.columns([3, 2, 1])
    with col_title:
        st.subheader("🎴 Random Album Thumbnails")
    with col_refresh:
        if st.button("🔄 Refresh"):
            st.session_state.random_covers_token += 1
            # Clear collection stats cache to show updated pricing data
            load_collection_stats.clear()
    
    # Load 10 random covers; we pass a seed via setseed by using token
    covers_df = load_random_covers(db_conn, count=10, seed=st.session_state.random_covers_token)
    
    if not covers_df.empty:
        cols = st.columns(5)
        for idx, row in covers_df.head(10).iterrows():
            with cols[idx % 5]:
                # Use container to ensure consistent spacing
                with st.container():
                    thumb_path = row.get('thumbnail_file_path') or row.get('local_file_path')
                    artist = row.get('artist', 'Unknown Artist')
                    title = row.get('title', 'Unknown Title')
                    year = row.get('year', '')
                    
                    # Truncate long text to prevent layout issues
                    artist_short = artist[:20] + "..." if len(artist) > 20 else artist
                    title_short = title[:25] + "..." if len(title) > 25 else title
                    
                    if thumb_path:
                        try:
                            st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                            # Fixed height caption area
                            st.markdown(f"""
                            <div style="height: 80px; overflow: hidden;">
                                <small><strong>{artist_short}</strong><br>
                                {title_short}<br>
                                {year}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        except Exception:
                            st.write("🎵")
                            st.markdown(f"""
                            <div style="height: 80px; overflow: hidden;">
                                <small><strong>{artist_short}</strong><br>
                                {title_short}<br>
                                {year}</small>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.write("🎵")
                        st.markdown(f"""
                        <div style="height: 80px; overflow: hidden;">
                            <small><strong>{artist_short}</strong><br>
                            {title_short}<br>
                            {year}</small>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("No artwork available yet. Try running the artwork downloader.")



def _create_smart_expander(title: str, preview_info: str, section_key: str, default_expanded: bool = False):
    """Create smart expandable section with preview info and session state memory."""
    # Initialize session state for this section  
    state_key = f"browse_section_{section_key}"
    if state_key not in st.session_state:
        st.session_state[state_key] = default_expanded
    
    # Create header with preview info when collapsed
    header = f"{title} • {preview_info}"
    
    # Create expander with remembered state
    return st.expander(header, expanded=st.session_state[state_key])

def _display_artwork_section(db_conn: PostgreSQLConnection, row: dict, idx: int):
    """Display artwork section with full navigation and quick album info."""
    artwork_files = row.get('artwork_files', [])
    if isinstance(artwork_files, str):
        try:
            import json
            artwork_files = json.loads(artwork_files)
        except:
            artwork_files = []
    
    # Quick album info at top
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Format", row.get('format', 'Unknown'))
    with col_info2:
        if row.get('rating'):
            st.metric("Rating", f"⭐ {row.get('rating')}/5")
        else:
            st.metric("Rating", "Not rated")
    with col_info3:
        if row.get('condition'):
            st.metric("Condition", row.get('condition', 'Unknown'))
    
    st.divider()
    
    # Use release_id for unique keys to prevent conflicts with random functionality
    release_id = row.get('release_id', f"unknown_{idx}")
    
    # Artwork navigation
    if artwork_files and len(artwork_files) > 1:
        # Multiple images - full navigation with unique keys
        artwork_key = f"compact_artwork_index_{release_id}"
        if artwork_key not in st.session_state:
            st.session_state[artwork_key] = 0
        
        current_index = st.session_state[artwork_key]
        current_artwork = artwork_files[current_index]
        
        # Navigation controls
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        
        with col_prev:
            if st.button("◀️", key=f"compact_prev_{release_id}", help="Previous image"):
                st.session_state[artwork_key] = (current_index - 1) % len(artwork_files)
                # Clear any full-size state when navigating
                fullsize_key = f"compact_fullsize_{release_id}"
                if fullsize_key in st.session_state:
                    del st.session_state[fullsize_key]
                st.rerun()
        
        with col_info:
            st.caption(f"📸 Image {current_index + 1} of {len(artwork_files)}")
            image_type = current_artwork.get('image_type', 'Unknown')
            if image_type != 'primary':
                st.caption(f"Type: {image_type.title()}")
        
        with col_next:
            if st.button("▶️", key=f"compact_next_{release_id}", help="Next image"):
                st.session_state[artwork_key] = (current_index + 1) % len(artwork_files)
                # Clear any full-size state when navigating
                fullsize_key = f"compact_fullsize_{release_id}"
                if fullsize_key in st.session_state:
                    del st.session_state[fullsize_key]
                st.rerun()
        
        # Display current artwork
        full_size_path = current_artwork.get('local_file_path')
        thumb_path = current_artwork.get('thumbnail_file_path') or full_size_path
        
        if thumb_path:
            try:
                fullsize_key = f"compact_fullsize_{release_id}"
                
                if not st.session_state.get(fullsize_key, False):
                    st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                    
                    # Full size viewing
                    if full_size_path and full_size_path != thumb_path:
                        if st.button("🔍 View Full Size", key=f"compact_fullsize_btn_{release_id}"):
                            st.session_state[fullsize_key] = True
                            st.rerun()
                else:
                    st.image(full_size_path, use_container_width=True)
                    if st.button("📷 Back to Thumbnail", key=f"compact_thumb_btn_{release_id}"):
                        st.session_state[fullsize_key] = False
                        st.rerun()
                        
            except Exception:
                st.info("🖼️ Image not available")
                
    elif artwork_files and len(artwork_files) == 1:
        # Single artwork
        artwork = artwork_files[0]
        full_size_path = artwork.get('local_file_path')
        thumb_path = artwork.get('thumbnail_file_path') or full_size_path
        
        st.caption("📸 Single image")
        image_type = artwork.get('image_type', 'Unknown')
        if image_type != 'primary':
            st.caption(f"Type: {image_type.title()}")
        
        if thumb_path:
            try:
                fullsize_key = f"compact_single_fullsize_{release_id}"
                
                if not st.session_state.get(fullsize_key, False):
                    st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                    
                    if full_size_path and full_size_path != thumb_path:
                        if st.button("🔍 View Full Size", key=f"compact_single_fullsize_btn_{release_id}"):
                            st.session_state[fullsize_key] = True
                            st.rerun()
                else:
                    st.image(full_size_path, use_container_width=True)
                    if st.button("📷 Back to Thumbnail", key=f"compact_single_thumb_btn_{release_id}"):
                        st.session_state[fullsize_key] = False
                        st.rerun()
                        
            except Exception:
                st.info("🖼️ Image not available")
    else:
        st.info("📷 No artwork available for this release")

def _display_release_detail_view(db_conn: PostgreSQLConnection, row: dict, idx: int):
    """Display release details in a horizontal layout optimized for viewing."""
    release_id = row.get('release_id')
    if not release_id:
        st.error("No release ID available for detailed view")
        return
    
    from data.loaders import load_release_details
    details = load_release_details(db_conn, release_id)
    
    # Parse artwork files
    artwork_files = row.get('artwork_files', [])
    if isinstance(artwork_files, str):
        try:
            import json
            artwork_files = json.loads(artwork_files)
        except:
            artwork_files = []
    
    # Main header with release info
    st.markdown("---")
    st.markdown(f"### 🎵 {row.get('artist', 'Unknown Artist')} — {row.get('title', 'Unknown Title')}")
    
    # Quick stats row
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    with stat_col1:
        st.metric("Year", row.get('year', 'Unknown'))
    with stat_col2:
        st.metric("Format", row.get('format', 'Unknown'))
    with stat_col3:
        if row.get('rating'):
            st.metric("Rating", f"⭐ {row.get('rating')}/5")
        else:
            st.metric("Rating", "Not rated")
    with stat_col4:
        artwork_count = len(artwork_files) if artwork_files else 0
        st.metric("Images", artwork_count)
    
    st.markdown("---")
    
    # Horizontal layout: Artwork on left, Details on right
    artwork_col, details_col = st.columns([2, 3])
    
    with artwork_col:
        st.markdown("#### 🖼️ Artwork")
        _display_improved_artwork_viewer(row, idx)
    
    with details_col:
        st.markdown("#### 📋 Release Information")
        
        # Tabs for different detail sections
        tab1, tab2, tab3 = st.tabs(["📀 Album Details", "🎵 Tracklist", "💿 Physical Info"])
        
        with tab1:
            _display_album_details_section(details)
        
        with tab2:
            _display_tracklist_section(db_conn, release_id)
        
        with tab3:
            _display_physical_details_section(details)

def _display_improved_artwork_viewer(row: dict, idx: int):
    """Improved artwork viewer with fixed navigation and full-size view."""
    artwork_files = row.get('artwork_files', [])
    if isinstance(artwork_files, str):
        try:
            import json
            artwork_files = json.loads(artwork_files)
        except:
            artwork_files = []
    
    if not artwork_files:
        st.info("📷 No artwork available for this release")
        return
    
    release_id = row.get('release_id', f"unknown_{idx}")
    
    # Use release_id for unique session state keys to prevent conflicts
    artwork_index_key = f"detail_artwork_index_{release_id}"
    fullsize_key = f"detail_fullsize_{release_id}"
    
    # Initialize artwork index
    if artwork_index_key not in st.session_state:
        st.session_state[artwork_index_key] = 0
    
    current_index = st.session_state[artwork_index_key]
    current_artwork = artwork_files[current_index]
    
    if len(artwork_files) > 1:
        # Navigation controls for multiple images
        nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
        
        with nav_col1:
            if st.button("◀️ Previous", key=f"detail_prev_art_{release_id}", use_container_width=True):
                st.session_state[artwork_index_key] = (current_index - 1) % len(artwork_files)
                # Clear full-size state when navigating
                if fullsize_key in st.session_state:
                    del st.session_state[fullsize_key]
                st.rerun()
        
        with nav_col2:
            st.write(f"**Image {current_index + 1} of {len(artwork_files)}**")
            image_type = current_artwork.get('image_type', 'Unknown')
            if image_type != 'primary':
                st.caption(f"Type: {image_type.title()}")
        
        with nav_col3:
            if st.button("▶️ Next", key=f"detail_next_art_{release_id}", use_container_width=True):
                st.session_state[artwork_index_key] = (current_index + 1) % len(artwork_files)
                # Clear full-size state when navigating
                if fullsize_key in st.session_state:
                    del st.session_state[fullsize_key]
                st.rerun()
    
    # Display current image
    full_size_path = current_artwork.get('local_file_path')
    thumb_path = current_artwork.get('thumbnail_file_path') or full_size_path
    
    if thumb_path:
        try:
            # Show thumbnail
            if not st.session_state.get(fullsize_key, False):
                st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                
                # Full size button
                if full_size_path and full_size_path != thumb_path:
                    if st.button("🔍 View Full Size", key=f"detail_fullsize_btn_{release_id}", use_container_width=True):
                        st.session_state[fullsize_key] = True
                        st.rerun()
            else:
                # Show full size image
                st.image(full_size_path, use_container_width=True)
                if st.button("📷 Back to Thumbnail", key=f"detail_thumb_btn_{release_id}", use_container_width=True):
                    st.session_state[fullsize_key] = False
                    st.rerun()
                    
        except Exception as e:
            st.error(f"🖼️ Error loading image: {str(e)}")
    else:
        st.info("🖼️ Image file not available")

def _display_tracklist_section(db_conn: PostgreSQLConnection, release_id: str):
    """Display rich tracklist with all track details."""
    from data.loaders import load_tracks_for_release
    
    tracks_df = load_tracks_for_release(db_conn, release_id)
    
    if not tracks_df.empty:
        st.write(f"🎵 **{len(tracks_df)} Tracks**")
        
        for idx, track in tracks_df.iterrows():
            # Track header
            col_num, col_title, col_duration = st.columns([0.5, 3, 1])
            
            with col_num:
                track_num = track.get('track_number', '?')
                st.write(f"**{track_num}**")
            
            with col_title:
                track_title = track.get('title', 'Unknown Track')
                st.write(track_title)
            
            with col_duration:
                duration = track.get('duration', '')
                if duration:
                    st.write(f"`{duration}`")
            
            # Track artists (for Various Artists compilations)
            track_artists = track.get('artists')
            if track_artists:
                try:
                    import json
                    if isinstance(track_artists, str):
                        artists_list = json.loads(track_artists)
                    else:
                        artists_list = track_artists
                    
                    if artists_list and len(artists_list) > 0:
                        artist_names = [artist.get('name', '') for artist in artists_list if artist.get('name')]
                        if artist_names:
                            st.caption(f"👤 {', '.join(artist_names)}")
                except:
                    pass
            
            # Extra artists (featuring, remix, etc.)
            extra_artists = track.get('extraartists')
            if extra_artists:
                try:
                    import json
                    if isinstance(extra_artists, str):
                        extra_list = json.loads(extra_artists)
                    else:
                        extra_list = extra_artists
                    
                    if extra_list and len(extra_list) > 0:
                        extra_info = []
                        for extra in extra_list:
                            name = extra.get('name', '')
                            role = extra.get('role', '')
                            if name and role:
                                extra_info.append(f"{name} ({role})")
                            elif name:
                                extra_info.append(name)
                        
                        if extra_info:
                            st.caption(f"🎭 {', '.join(extra_info)}")
                except:
                    pass
            
            if idx < len(tracks_df) - 1:  # Don't add divider after last track
                st.divider()
    else:
        st.info("🎵 No track listing available for this release")

def _display_album_details_section(details: dict):
    """Display complete album metadata and credits."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📀 Release Information**")
        
        # Basic info
        if details.get('catno'):
            st.write(f"**Catalog #:** {details['catno']}")
        if details.get('country'):
            st.write(f"**Country:** {details['country']}")
        if details.get('date_added'):
            st.write(f"**Added:** {details['date_added']}")
        
        # Community stats
        if details.get('community_have_count'):
            st.write(f"**Have:** {details['community_have_count']:,} users")
        if details.get('community_want_count'):
            st.write(f"**Want:** {details['community_want_count']:,} users")
        if details.get('community_average_rating'):
            rating = float(details['community_average_rating'])
            st.write(f"**Avg Rating:** {rating:.1f}/5.0 ({details.get('community_rating_count', 0)} votes)")
    
    with col2:
        st.write("**🎨 Credits & Production**")
        
        # Genres and Styles
        genres = details.get('genres')
        if genres:
            try:
                import json
                if isinstance(genres, str):
                    genre_list = json.loads(genres)
                else:
                    genre_list = genres
                if genre_list:
                    st.write(f"**Genres:** {', '.join(genre_list)}")
            except:
                pass
        
        styles = details.get('styles')
        if styles:
            try:
                import json
                if isinstance(styles, str):
                    style_list = json.loads(styles)
                else:
                    style_list = styles
                if style_list:
                    st.write(f"**Styles:** {', '.join(style_list)}")
            except:
                pass
        
        # Producers
        producers = details.get('producers')
        if producers:
            try:
                import json
                if isinstance(producers, str):
                    producer_list = json.loads(producers)
                else:
                    producer_list = producers
                if producer_list:
                    producer_names = [p.get('name', '') for p in producer_list if p.get('name')]
                    if producer_names:
                        st.write(f"**Producers:** {', '.join(producer_names)}")
            except:
                pass
        
        # Notes
        if details.get('notes'):
            st.write(f"**Notes:** {details['notes']}")

def _display_physical_details_section(details: dict):
    """Display physical condition and marketplace information."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**💿 Physical Condition**")
        
        if details.get('condition'):
            st.write(f"**Media:** {details['condition']}")
        if details.get('sleeve_condition'):
            st.write(f"**Sleeve:** {details['sleeve_condition']}")
        if details.get('copies_count', 1) > 1:
            st.write(f"**Copies:** {details['copies_count']}")
        
        # Instance details
        instance_ids = details.get('instance_ids')
        if instance_ids:
            try:
                import json
                if isinstance(instance_ids, str):
                    ids = json.loads(instance_ids)
                else:
                    ids = instance_ids
                if ids:
                    st.write(f"**Instance IDs:** {', '.join(map(str, ids))}")
            except:
                pass
    
    with col2:
        st.write("**💰 Marketplace Data**")
        
        if details.get('lowest_price'):
            currency = details.get('currency', 'USD')
            price = details['lowest_price']
            st.write(f"**Lowest Price:** {currency} {price}")
        
        if details.get('num_for_sale'):
            st.write(f"**For Sale:** {details['num_for_sale']} copies")
        
        if details.get('price_last_seen'):
            st.write(f"**Price Updated:** {details['price_last_seen']}")
        
        # Marketplace stats from JSONB
        marketplace_stats = details.get('marketplace_stats')
        if marketplace_stats:
            try:
                import json
                if isinstance(marketplace_stats, str):
                    stats = json.loads(marketplace_stats)
                else:
                    stats = marketplace_stats
                
                if stats and isinstance(stats, dict):
                    for key, value in stats.items():
                        if key not in ['updated', 'timestamp']:
                            st.write(f"**{key.title()}:** {value}")
            except:
                pass

def display_browse_collection(db_conn: PostgreSQLConnection):
    """Browse collection with search and filters."""
    st.header("🔍 Browse Collection")
    
    # Enhanced Search functionality with remixer support
    col_search, col_type = st.columns([3, 1])
    
    with col_search:
        search_term = st.text_input("Search by artist, title, label, or remixer:", placeholder="e.g., Miles Davis, David Morales, Frankie Knuckles")
    
    with col_type:
        search_type = st.selectbox("Search In:", ["All", "Artists/Albums", "Remixers Only", "Aliases"], index=0)
    
    col1, col2 = st.columns(2)
    with col1:
        limit = st.selectbox("Results per page", [20, 50, 100], index=0)
    with col2:
        sort_by = st.selectbox("Sort by", ["Artist", "Year Up", "Year Down", "Title", "Random"], index=0)
    
    # Helper function to get ORDER BY clause based on sort selection
    def get_sort_clause(sort_by_option, table_prefix="r", for_union=False):
        if for_union:
            # For UNION queries, use column positions or bare column names
            # Note: RANDOM() needs special handling in UNION queries
            if sort_by_option == "Artist":
                return "ORDER BY artist, year"
            elif sort_by_option == "Year Up":
                return "ORDER BY year ASC, artist"
            elif sort_by_option == "Year Down":
                return "ORDER BY year DESC, artist"
            elif sort_by_option == "Title":
                return "ORDER BY title, artist"
            elif sort_by_option == "Random":
                # For UNION with RANDOM(), we need to add a random column to each SELECT
                return "ORDER BY random_col"
            else:
                return "ORDER BY artist, year"
        else:
            # For regular queries with table aliases
            if sort_by_option == "Artist":
                return f"ORDER BY {table_prefix}.artist, {table_prefix}.year"
            elif sort_by_option == "Year Up":
                return f"ORDER BY {table_prefix}.year ASC, {table_prefix}.artist"
            elif sort_by_option == "Year Down":
                return f"ORDER BY {table_prefix}.year DESC, {table_prefix}.artist"
            elif sort_by_option == "Title":
                return f"ORDER BY {table_prefix}.title, {table_prefix}.artist"
            elif sort_by_option == "Random":
                return "ORDER BY RANDOM()"
            else:
                return f"ORDER BY {table_prefix}.artist, {table_prefix}.year"
    
    if search_term:
        # Handle different search types
        if search_type == "Remixers Only":
            # Search specifically in remixer/producer data
            from data.loaders import search_by_remixer
            try:
                # Convert sort option for remixer search (uses different column names)
                if sort_by == "Artist":
                    remixer_sort = "ORDER BY artist, year"
                elif sort_by == "Year Up":
                    remixer_sort = "ORDER BY year ASC, artist"
                elif sort_by == "Year Down":
                    remixer_sort = "ORDER BY year DESC, artist"
                elif sort_by == "Title":
                    remixer_sort = "ORDER BY title, artist"
                elif sort_by == "Random":
                    remixer_sort = "ORDER BY RANDOM()"
                else:
                    remixer_sort = "ORDER BY year DESC, artist"
                
                remixer_results_df = search_by_remixer(db_conn, search_term, limit, remixer_sort)
                
                if not remixer_results_df.empty:
                    st.write(f"🎛️ Found {len(remixer_results_df)} remix/production credits for '{search_term}'")
                    
                    # Display remixer results using same grid layout as other searches
                    cols = st.columns(5)
                    for idx, row in remixer_results_df.iterrows():
                        with cols[idx % 5]:
                            # Use container to ensure consistent spacing (same as other search results)
                            with st.container():
                                # Get artwork info from search results
                                thumb_path = row.get('thumbnail_file_path') or row.get('local_file_path')
                                
                                artist = row.get('artist', 'Unknown Artist')
                                title = row.get('title', 'Unknown Title')
                                year = row.get('year', '')
                                
                                # Truncate long text to prevent layout issues
                                artist_short = artist[:20] + "..." if len(artist) > 20 else artist
                                title_short = title[:25] + "..." if len(title) > 25 else title
                                
                                # Show remix indicator
                                type_icon = "🎛️"
                                
                                if thumb_path:
                                    try:
                                        st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                                    except Exception:
                                        st.write(type_icon)
                                else:
                                    st.write(type_icon)
                                
                                # Fixed height caption area (same as other searches)
                                remixer_name = row.get('remixer_name', '')
                                remixer_role = row.get('remixer_role', '')
                                remixer_info = f"{remixer_name} ({remixer_role})" if remixer_name and remixer_role else ""
                                
                                st.markdown(f"""
                                <div style="height: 80px; overflow: hidden;">
                                    <small><strong>{artist_short}</strong><br>
                                    {title_short}<br>
                                    {year}<br>
                                    <em>🎛️ {remixer_info[:30]}{"..." if len(remixer_info) > 30 else ""}</em></small>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Add View Details button (same as other searches)
                                if st.button("🔍 Details", key=f"remixer_btn_{idx}", use_container_width=True):
                                    st.query_params["release_id"] = str(row.get('release_id', ''))
                                    st.query_params["source_page"] = "Browse Collection"
                                    st.rerun()
                else:
                    st.info(f"No remix/production credits found for '{search_term}'. Try a different remixer name or check spelling.")
                    
            except Exception as e:
                st.error(f"Error searching remixers: {e}")
                
        elif search_type == "Aliases":
            # Search specifically in artist aliases
            try:
                aliases_results_df = search_by_aliases(db_conn, search_term, limit, get_sort_clause(sort_by))
                
                if not aliases_results_df.empty:
                    st.write(f"🎭 Found {len(aliases_results_df)} releases by artists with alias '{search_term}'")
                    
                    # Display aliases results using same grid layout as other searches
                    cols = st.columns(5)
                    for idx, row in aliases_results_df.iterrows():
                        with cols[idx % 5]:
                            # Use container to ensure consistent spacing (same as other search results)
                            with st.container():
                                # Get artwork info from search results
                                thumb_path = row.get('thumbnail_file_path') or row.get('local_file_path')
                                
                                artist = row.get('artist', 'Unknown Artist')
                                title = row.get('title', 'Unknown Title')
                                year = row.get('year', '')
                                found_alias = row.get('found_alias', '')
                                
                                # Truncate long text to prevent layout issues
                                artist_short = artist[:20] + "..." if len(artist) > 20 else artist
                                title_short = title[:25] + "..." if len(title) > 25 else title
                                
                                # Show alias indicator
                                type_icon = "🎭"
                                
                                if thumb_path:
                                    try:
                                        st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                                    except Exception:
                                        st.write(type_icon)
                                else:
                                    st.write(type_icon)
                                
                                # Fixed height caption area (same as other searches)
                                st.markdown(f"""
                                <div style="height: 80px; overflow: hidden;">
                                    <small><strong>{artist_short}</strong><br>
                                    {title_short}<br>
                                    {year}<br>
                                    <em>🎭 Alias: {found_alias[:25]}{"..." if len(found_alias) > 25 else ""}</em></small>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Add View Details button (same as other searches)
                                if st.button("🔍 Details", key=f"alias_btn_{idx}", use_container_width=True):
                                    st.query_params["release_id"] = str(row.get('release_id', ''))
                                    st.query_params["source_page"] = "Browse Collection"
                                    st.rerun()
                else:
                    st.info(f"No releases found for artists with alias '{search_term}'. Try a different alias or check spelling.")
                    
            except Exception as e:
                st.error(f"Error searching aliases: {e}")
                
        else:
            # Standard search (All or Artists/Albums)
            if search_type == "All":
                # Search both releases and remixers with artwork
                if sort_by == "Random":
                    # Special handling for RANDOM() in UNION queries with deduplication
                    search_query = f"""
                    WITH combined_results AS (
                        SELECT DISTINCT r.release_id, r.title, r.artist, r.year, r.label, r.format, r.country, r.rating,
                               'release' as result_type, a.local_file_path, a.thumbnail_file_path, a.original_url
                        FROM releases r
                        LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
                        WHERE UPPER(r.title) LIKE UPPER('%{search_term}%') 
                           OR UPPER(r.artist) LIKE UPPER('%{search_term}%')
                           OR UPPER(r.label) LIKE UPPER('%{search_term}%')
                        
                        UNION
                        
                        SELECT DISTINCT r.release_id, r.title, r.artist, r.year, r.label, r.format, r.country, r.rating,
                               'remix' as result_type, a.local_file_path, a.thumbnail_file_path, a.original_url
                        FROM releases r
                        JOIN tracks t ON r.release_id = t.release_id
                        LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
                        WHERE t.extraartists IS NOT NULL 
                          AND t.extraartists != '[]'::jsonb
                          AND UPPER(t.extraartists::text) LIKE UPPER('%{search_term}%')
                    ),
                    deduplicated AS (
                        SELECT release_id, title, artist, year, label, format, country, rating,
                               result_type, local_file_path, thumbnail_file_path, original_url, RANDOM() as random_col,
                               ROW_NUMBER() OVER (PARTITION BY release_id ORDER BY result_type) as rn
                        FROM combined_results
                    )
                    SELECT release_id, title, artist, year, label, format, country, rating,
                           result_type, local_file_path, thumbnail_file_path, original_url, random_col
                    FROM deduplicated 
                    WHERE rn = 1
                    {get_sort_clause(sort_by, for_union=True)}
                    LIMIT {limit}
                    """
                else:
                    # Regular UNION query without random column with deduplication
                    search_query = f"""
                    WITH combined_results AS (
                        SELECT DISTINCT r.release_id, r.title, r.artist, r.year, r.label, r.format, r.country, r.rating,
                               'release' as result_type, a.local_file_path, a.thumbnail_file_path, a.original_url
                        FROM releases r
                        LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
                        WHERE UPPER(r.title) LIKE UPPER('%{search_term}%') 
                           OR UPPER(r.artist) LIKE UPPER('%{search_term}%')
                           OR UPPER(r.label) LIKE UPPER('%{search_term}%')
                        
                        UNION
                        
                        SELECT DISTINCT r.release_id, r.title, r.artist, r.year, r.label, r.format, r.country, r.rating,
                               'remix' as result_type, a.local_file_path, a.thumbnail_file_path, a.original_url
                        FROM releases r
                        JOIN tracks t ON r.release_id = t.release_id
                        LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
                        WHERE t.extraartists IS NOT NULL 
                          AND t.extraartists != '[]'::jsonb
                          AND UPPER(t.extraartists::text) LIKE UPPER('%{search_term}%')
                    ),
                    deduplicated AS (
                        SELECT release_id, title, artist, year, label, format, country, rating,
                               result_type, local_file_path, thumbnail_file_path, original_url,
                               ROW_NUMBER() OVER (PARTITION BY release_id ORDER BY result_type) as rn
                        FROM combined_results
                    )
                    SELECT release_id, title, artist, year, label, format, country, rating,
                           result_type, local_file_path, thumbnail_file_path, original_url
                    FROM deduplicated 
                    WHERE rn = 1
                    {get_sort_clause(sort_by, for_union=True)}
                    LIMIT {limit}
                    """
            else:
                # Artists/Albums only search with artwork
                search_query = f"""
                SELECT r.release_id, r.title, r.artist, r.year, r.label, r.format, r.country, r.rating,
                       'release' as result_type, a.local_file_path, a.thumbnail_file_path, a.original_url
                FROM releases r
                LEFT JOIN artwork a ON r.release_id = a.release_id AND a.image_type = 'primary'
                WHERE UPPER(r.title) LIKE UPPER('%{search_term}%') 
                   OR UPPER(r.artist) LIKE UPPER('%{search_term}%')
                   OR UPPER(r.label) LIKE UPPER('%{search_term}%')
                {get_sort_clause(sort_by)}
                LIMIT {limit}
                """
            
            try:
                results = db_conn.execute_query(search_query)
                if results:
                    results_df = pd.DataFrame(results)
                    st.write(f"Found {len(results_df)} results")
                
                    # Display results using Enhanced Overview template (same as random releases)
                    cols = st.columns(5)
                    for idx, row in results_df.iterrows():
                        with cols[idx % 5]:
                            # Use container to ensure consistent spacing (Enhanced Overview template)
                            with st.container():
                                # Get artwork info from search results
                                thumb_path = row.get('thumbnail_file_path') or row.get('local_file_path')
                                
                                artist = row.get('artist', 'Unknown Artist')
                                title = row.get('title', 'Unknown Title')
                                year = row.get('year', '')
                                result_type = row.get('result_type', 'release')
                                
                                # Truncate long text to prevent layout issues (Enhanced Overview template)
                                artist_short = artist[:20] + "..." if len(artist) > 20 else artist
                                title_short = title[:25] + "..." if len(title) > 25 else title
                                
                                # Show result type indicator
                                type_icon = "🎛️" if result_type == 'remix' else "🎵"
                                
                                if thumb_path:
                                    try:
                                        st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                                    except Exception:
                                        st.write(type_icon)
                                else:
                                    st.write(type_icon)
                                
                                # Fixed height caption area (Enhanced Overview template)
                                st.markdown(f"""
                                <div style="height: 80px; overflow: hidden;">
                                    <small><strong>{artist_short}</strong><br>
                                    {title_short}<br>
                                    {year}</small>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Add View Details button (same as random releases)
                                if st.button("🔍 Details", key=f"search_btn_{idx}", use_container_width=True):
                                    st.query_params["release_id"] = str(row.get('release_id', ''))
                                    st.query_params["source_page"] = "Browse Collection"
                                    st.rerun()
                else:
                    st.info("No results found")
            except Exception as e:
                st.error(f"Search error: {e}")
    else:
        # Collection Browser - using Enhanced Overview template
        col_title, col_spacer, col_refresh = st.columns([3, 2, 1])
        with col_title:
            st.subheader("🎴 Browse Collection")
        with col_refresh:
            if st.button("🔄 Random"):
                if 'browse_random_token' not in st.session_state:
                    st.session_state.browse_random_token = 0
                st.session_state.browse_random_token += 1
        
        # Initialize random token
        if 'browse_random_token' not in st.session_state:
            st.session_state.browse_random_token = 0
        
        # Load random covers using the same simple approach as Enhanced Overview
        # Use selected sort order, but override with RANDOM() if Random is selected OR if random button was clicked
        if sort_by == "Random" or st.session_state.browse_random_token > 0:
            browse_sort = "ORDER BY RANDOM()"
        else:
            browse_sort = get_sort_clause(sort_by)
        covers_df = load_random_covers(db_conn, count=limit, seed=st.session_state.browse_random_token, sort_clause=browse_sort)
        
        if not covers_df.empty:
            cols = st.columns(5)
            for idx, row in covers_df.iterrows():
                with cols[idx % 5]:
                    # Use container to ensure consistent spacing (Enhanced Overview template)
                    with st.container():
                        thumb_path = row.get('thumbnail_file_path') or row.get('local_file_path')
                        artist = row.get('artist', 'Unknown Artist')
                        title = row.get('title', 'Unknown Title')
                        year = row.get('year', '')
                        
                        # Truncate long text to prevent layout issues (Enhanced Overview template)
                        artist_short = artist[:20] + "..." if len(artist) > 20 else artist
                        title_short = title[:25] + "..." if len(title) > 25 else title
                        
                        if thumb_path:
                            try:
                                st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                                # Fixed height caption area (Enhanced Overview template)
                                st.markdown(f"""
                                <div style="height: 80px; overflow: hidden;">
                                    <small><strong>{artist_short}</strong><br>
                                    {title_short}<br>
                                    {year}</small>
                                </div>
                                """, unsafe_allow_html=True)
                            except Exception:
                                st.write("🎵")
                                st.markdown(f"""
                                <div style="height: 80px; overflow: hidden;">
                                    <small><strong>{artist_short}</strong><br>
                                    {title_short}<br>
                                    {year}</small>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.write("🎵")
                            st.markdown(f"""
                            <div style="height: 80px; overflow: hidden;">
                                <small><strong>{artist_short}</strong><br>
                                {title_short}<br>
                                {year}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # Add View Details button (new addition to Enhanced Overview template)
                        if st.button("🔍 Details", key=f"detail_btn_{idx}", use_container_width=True):
                            st.query_params["release_id"] = str(row.get('release_id', ''))
                            st.query_params["source_page"] = "Browse Collection"
                            st.rerun()
        else:
            st.info("No artwork available yet. Try running the artwork downloader.")

def display_genre_style_analysis(db_conn: PostgreSQLConnection):
    """Interactive genre and style analysis with drill-down and thumbnail galleries."""
    st.header("🎵 Genre & Style Analysis")
    st.markdown("Explore your collection by genres and styles with clickable drilldown charts.")
    
    # Initialize session state
    if 'gs_view' not in st.session_state:
        st.session_state.gs_view = 'overview'
    if 'gs_selected_genre' not in st.session_state:
        st.session_state.gs_selected_genre = None
    if 'gs_selected_style' not in st.session_state:
        st.session_state.gs_selected_style = None
    if 'gs_page' not in st.session_state:
        st.session_state.gs_page = 0
    if 'gs_random_seed' not in st.session_state:
        st.session_state.gs_random_seed = 0
    
    # Control panel
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        analysis_type = st.selectbox(
            "Analysis Type:",
            ["Genre", "Style", "🎛️ Remix Trends"],
            index=0
        )
    
    with col2:
        color_scheme = st.selectbox(
            "Color Scheme:",
            ["Rainbow", "Blue", "Green", "Red", "Purple", "Orange"],
            index=0
        )
    
    with col3:
        if st.button("🔄 Reset View"):
            st.session_state.gs_view = 'overview'
            st.session_state.gs_selected_genre = None
            st.session_state.gs_selected_style = None
            st.session_state.gs_page = 0
            st.rerun()
    
    # Navigation breadcrumb
    nav_col1, nav_col2 = st.columns([3, 1])
    with nav_col1:
        if st.session_state.gs_view == 'overview':
            st.caption("🏠 Genre & Style Overview")
        elif st.session_state.gs_view == 'genre_drill':
            st.caption(f"🏠 Overview > 🎭 {st.session_state.gs_selected_genre}")
        elif st.session_state.gs_view == 'style_drill':
            st.caption(f"🏠 Overview > 🎨 {st.session_state.gs_selected_style}")
        elif st.session_state.gs_view == 'releases':
            genre = st.session_state.gs_selected_genre or "Any"
            style = st.session_state.gs_selected_style or "Any"
            st.caption(f"🏠 Overview > 🎭 {genre} > 🎨 {style} > 🎵 Releases")
    
    with nav_col2:
        if st.session_state.gs_view != 'overview':
            if st.button("⬅ Back"):
                if st.session_state.gs_view == 'releases':
                    st.session_state.gs_view = 'genre_drill' if st.session_state.gs_selected_genre else 'style_drill'
                else:
                    st.session_state.gs_view = 'overview'
                st.session_state.gs_page = 0
                st.rerun()
    
    if st.session_state.gs_view == 'overview':
        if analysis_type == "Genre":
            _display_genre_overview(db_conn, color_scheme)
        elif analysis_type == "Style":
            _display_style_overview(db_conn, color_scheme)
        else:  # Remix Trends
            _display_remix_trends_overview(db_conn, color_scheme)
    elif st.session_state.gs_view == 'genre_drill':
        _display_style_drill_for_genre(db_conn, st.session_state.gs_selected_genre, color_scheme)
    elif st.session_state.gs_view == 'style_drill':
        _display_genre_drill_for_style(db_conn, st.session_state.gs_selected_style, color_scheme)
    elif st.session_state.gs_view == 'releases':
        # Check if both genre and style are selected (drill-down scenario)
        if st.session_state.get('gs_selected_genre') and st.session_state.get('gs_selected_style'):
            _display_releases_for_genre_and_style(db_conn, st.session_state.gs_selected_genre, st.session_state.gs_selected_style)
        elif st.session_state.gs_selected_genre:
            _display_releases_for_genre(db_conn, st.session_state.gs_selected_genre)
        elif st.session_state.gs_selected_style:
            _display_releases_for_style(db_conn, st.session_state.gs_selected_style)

def _display_genre_overview(db_conn: PostgreSQLConnection, color_scheme: str):
    """Display genre overview with clickable chart."""
    st.subheader("🎵 Top Genres by Release Count")
    
    df = pd.DataFrame(load_genre_analysis(db_conn))
    if df.empty:
        st.warning("No genre data found")
        return
    
    # Create color map
    color_map = get_color_map(df['genre'].tolist(), color_scheme)
    
    # Create go.Bar chart with colors (like decade/year fix)
    import plotly.graph_objects as go
    
    # Reset index and prepare data
    df_clean = df.reset_index(drop=True).copy()
    genre_labels = df_clean['genre'].tolist()
    colors = [color_map.get(label, '#1f77b4') for label in genre_labels]
    
    fig = go.Figure(data=[
        go.Bar(
            x=genre_labels,
            y=df_clean['release_count'].tolist(),
            name='Releases',
            marker=dict(color=colors)
        )
    ])
    fig.update_layout(
        title="Click a genre to see its styles",
        showlegend=False,
        height=500
    )
    
    if plotly_events:
        clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key='genre_click', override_height=500)
        if clicked:
            try:
                genre = str(clicked[0].get('x'))
                st.session_state.gs_selected_genre = genre
                st.session_state.gs_view = 'genre_drill'
                st.session_state.gs_page = 0
                st.rerun()
            except Exception:
                pass
    else:
        st.plotly_chart(fig, use_container_width=True)
        # Fallback selector
        selected_genre = st.selectbox("Select a genre to drill down:", df['genre'].tolist())
        if st.button("View Styles", key="genre_fallback"):
            st.session_state.gs_selected_genre = selected_genre
            st.session_state.gs_view = 'genre_drill'
            st.rerun()
    
    # Show genre random sample
    if not df.empty:
        st.subheader(f"🎵 Random {df.iloc[0]['genre']} Albums")
        _display_release_thumbnail_gallery(db_conn, genre=df.iloc[0]['genre'])

def _display_style_overview(db_conn: PostgreSQLConnection, color_scheme: str):
    """Display style overview with clickable chart."""
    st.subheader("🎨 Top Styles by Release Count")
    
    df = pd.DataFrame(load_style_analysis(db_conn))
    if df.empty:
        st.warning("No style data found")
        return
    
    # Create color map
    color_map = get_color_map(df['style'].tolist(), color_scheme)
    
    # Create go.Bar chart with colors (like decade/year fix)
    import plotly.graph_objects as go
    
    # Reset index and prepare data
    df_clean = df.reset_index(drop=True).copy()
    style_labels = df_clean['style'].tolist()
    colors = [color_map.get(label, '#1f77b4') for label in style_labels]
    
    fig = go.Figure(data=[
        go.Bar(
            x=style_labels,
            y=df_clean['release_count'].tolist(),
            name='Releases',
            marker=dict(color=colors)
        )
    ])
    fig.update_layout(
        title="Click a style to see its genres",
        showlegend=False,
        height=500
    )
    
    if plotly_events:
        clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key='style_click', override_height=500)
        if clicked:
            try:
                style = str(clicked[0].get('x'))
                st.session_state.gs_selected_style = style
                st.session_state.gs_view = 'style_drill'
                st.session_state.gs_page = 0
                st.rerun()
            except Exception:
                pass
    else:
        st.plotly_chart(fig, use_container_width=True)
        # Fallback selector
        selected_style = st.selectbox("Select a style to drill down:", df['style'].tolist())
        if st.button("View Genres", key="style_fallback"):
            st.session_state.gs_selected_style = selected_style
            st.session_state.gs_view = 'style_drill'
            st.rerun()
    
    # Show style random sample
    if not df.empty:
        st.subheader(f"🎵 Random {df.iloc[0]['style']} Albums")
        _display_release_thumbnail_gallery(db_conn, style=df.iloc[0]['style'])

def _display_remix_trends_overview(db_conn: PostgreSQLConnection, color_scheme: str):
    """Display remix trends analysis with interactive charts."""
    st.subheader("🎛️ Remix Trends by Genre")
    st.caption("Explore which genres in your collection have the most remix activity.")
    
    try:
        from data.loaders import load_remix_by_genre, load_remix_timeline, load_most_remixed_tracks
        
        # Two-column layout for multiple analyses
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📊 Genre Remix Density**")
            
            remix_genre_df = load_remix_by_genre(db_conn)
            
            if not remix_genre_df.empty:
                # Create interactive bar chart
                import plotly.graph_objects as go
                
                # Prepare data
                genre_labels = remix_genre_df['genre'].tolist()[:12]  # Top 12 genres
                remix_percentages = remix_genre_df['remix_percentage'].tolist()[:12]
                
                # Create color map
                color_map = get_color_map(genre_labels, color_scheme)
                colors = [color_map.get(label, '#1f77b4') for label in genre_labels]
                
                fig = go.Figure(data=[
                    go.Bar(
                        x=genre_labels,
                        y=remix_percentages,
                        name='Remix %',
                        marker=dict(color=colors),
                        text=[f"{val:.1f}%" for val in remix_percentages],
                        textposition='auto'
                    )
                ])
                fig.update_layout(
                    title="Click a genre to explore its remix culture",
                    showlegend=False,
                    height=400,
                    yaxis_title="Remix Percentage (%)"
                )
                fig.update_xaxes(tickangle=45)
                
                # Make chart clickable (optional)
                if plotly_events:
                    clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key='remix_genre_click', override_height=400)
                    if clicked:
                        try:
                            genre = str(clicked[0].get('x'))
                            st.info(f"🎛️ **{genre}** has {remix_genre_df[remix_genre_df['genre']==genre]['remix_percentage'].iloc[0]:.1f}% remix activity")
                        except Exception:
                            pass
                else:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Show top remix-heavy genres
                st.write("**🔥 Most Remix-Heavy Genres:**")
                for idx, row in remix_genre_df.head(5).iterrows():
                    genre = row['genre']
                    percentage = row['remix_percentage']
                    total_tracks = row['total_tracks']
                    remix_tracks = row['tracks_with_remixes']
                    
                    with st.container():
                        remix_col1, remix_col2, remix_col3 = st.columns([2, 1, 1])
                        
                        with remix_col1:
                            st.write(f"**🎵 {genre}**")
                            if percentage >= 60:
                                st.success(f"🔥 {percentage:.1f}% remix-heavy")
                            elif percentage >= 30:
                                st.info(f"🎛️ {percentage:.1f}% remix activity")
                            else:
                                st.caption(f"📻 {percentage:.1f}% remix activity")
                        
                        with remix_col2:
                            st.metric("Total", f"{total_tracks}")
                        
                        with remix_col3:
                            st.metric("Remixed", f"{remix_tracks}")
                        
                        st.divider()
                        
            else:
                st.info("No remix genre data found. Make sure track data with extraartists is imported.")
        
        with col2:
            st.write("**⏰ Remix Timeline Peaks**")
            
            timeline_df = load_remix_timeline(db_conn)
            
            if not timeline_df.empty:
                # Show decade summary
                decade_summary = timeline_df.groupby('decade_label').agg({
                    'remix_percentage': 'mean',
                    'total_tracks': 'sum',
                    'remix_tracks': 'sum'
                }).reset_index().sort_values('remix_percentage', ascending=False)
                
                st.write("**📅 Peak Remix Decades:**")
                
                for idx, row in decade_summary.head(4).iterrows():
                    decade = row['decade_label']
                    percentage = row['remix_percentage']
                    total = row['total_tracks']
                    
                    with st.container():
                        decade_col1, decade_col2 = st.columns([2, 1])
                        
                        with decade_col1:
                            st.write(f"**📅 {decade}**")
                            if percentage >= 50:
                                st.success(f"🔥 Golden Era: {percentage:.1f}%")
                            elif percentage >= 30:
                                st.info(f"🎛️ Active Period: {percentage:.1f}%")
                            else:
                                st.caption(f"📻 {percentage:.1f}% remix activity")
                        
                        with decade_col2:
                            st.metric("Tracks", f"{total:,}")
                        
                        st.divider()
                
                # Show recent trend
                recent_data = timeline_df.tail(5)  # Last 5 years
                if not recent_data.empty:
                    recent_avg = recent_data['remix_percentage'].mean()
                    st.write("**📈 Recent Trend (Last 5 Years):**")
                    if recent_avg >= 40:
                        st.success(f"🔥 High remix activity: {recent_avg:.1f}% average")
                    elif recent_avg >= 20:
                        st.info(f"🎛️ Moderate activity: {recent_avg:.1f}% average")
                    else:
                        st.caption(f"📻 Low activity: {recent_avg:.1f}% average")
            else:
                st.info("No remix timeline data available.")
        
        # Bottom section - Most remixed tracks
        st.markdown("---")
        st.write("**🎵 Most Remixed Tracks in Your Collection**")
        
        remixed_tracks_df = load_most_remixed_tracks(db_conn, limit=8)
        
        if not remixed_tracks_df.empty:
            cols = st.columns(min(4, len(remixed_tracks_df)))
            
            for idx, row in remixed_tracks_df.head(4).iterrows():
                with cols[idx % 4]:
                    track_name = row['track_name']
                    artist = row['artist']
                    total_remixes = row['total_remixes']
                    versions = row['versions_in_collection']
                    
                    with st.container():
                        st.write(f"**🎵 {track_name}**")
                        st.caption(f"👤 {artist}")
                        
                        track_col1, track_col2 = st.columns(2)
                        with track_col1:
                            st.metric("Remixes", f"{total_remixes}")
                        with track_col2:
                            st.metric("Versions", f"{versions}")
                        
                        if total_remixes >= 5:
                            st.success("🔥 Remix Classic")
                        elif total_remixes >= 3:
                            st.info("🎛️ Well Remixed")
        else:
            st.info("No multi-remix tracks found in your collection.")
            
    except Exception as e:
        st.error(f"Error loading remix trends: {e}")

def _display_genre_style_overview(db_conn: PostgreSQLConnection):
    """Display genre and style overview with clickable charts."""
    tab1, tab2 = st.tabs(["Genres", "Styles"])
    
    with tab1:
        st.subheader("Top Genres (Click to explore)")
        genre_df = load_genre_analysis(db_conn)
        if not genre_df.empty:
            df_top = genre_df.head(15)
            # Create go.Bar with colors (like decade/year fix)
            import plotly.graph_objects as go
            df_clean = df_top.reset_index(drop=True).copy()
            genre_labels = df_clean['genre'].tolist()
            
            # Create color map for these genres
            color_map_local = get_color_map(genre_labels, 'rainbow')
            colors = [color_map_local.get(label, '#1f77b4') for label in genre_labels]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=genre_labels,
                    y=df_clean['release_count'].tolist(),
                    name='Releases',
                    marker=dict(color=colors)
                )
            ])
            fig.update_layout(
                title="Click a genre to see its styles",
                showlegend=False,
                height=500
            )
            
            if plotly_events:
                clicked = plotly_events(fig, click_event=True, hover_event=False, 
                                      select_event=False, key='genre_click', override_height=500)
                if clicked:
                    try:
                        genre = str(clicked[0].get('x'))
                        st.session_state.gs_selected_genre = genre
                        st.session_state.gs_selected_style = None
                        st.session_state.gs_view = 'genre_drill'
                        st.session_state.gs_page = 0
                        st.rerun()
                    except Exception:
                        pass
            else:
                st.plotly_chart(fig, use_container_width=True)
                # Fallback: select box for genre
                selected_genre = st.selectbox("Select a genre to explore:", 
                                             [""] + df_top['genre'].tolist())
                if selected_genre:
                    st.session_state.gs_selected_genre = selected_genre
                    st.session_state.gs_selected_style = None
                    st.session_state.gs_view = 'genre_drill'
                    st.session_state.gs_page = 0
                    st.rerun()
            
            # Show random sample for top genre
            if not df_top.empty:
                top_genre = df_top.iloc[0]['genre']
                st.subheader(f"🎵 Random {top_genre} Albums")
                _display_release_thumbnail_gallery(db_conn, genre=top_genre)
        else:
            st.info("No genre data available")
    
    with tab2:
        st.subheader("Top Styles (Click to explore)")
        style_df = load_style_analysis(db_conn)
        if not style_df.empty:
            df_top = style_df.head(15)
            # Create go.Bar with colors (like decade/year fix)
            import plotly.graph_objects as go
            df_clean = df_top.reset_index(drop=True).copy()
            style_labels = df_clean['style'].tolist()
            
            # Create color map for these styles
            color_map_local = get_color_map(style_labels, 'rainbow')
            colors = [color_map_local.get(label, '#1f77b4') for label in style_labels]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=style_labels,
                    y=df_clean['release_count'].tolist(),
                    name='Releases',
                    marker=dict(color=colors)
                )
            ])
            fig.update_layout(
                title="Click a style to see its genres",
                showlegend=False,
                height=500
            )
            
            if plotly_events:
                clicked = plotly_events(fig, click_event=True, hover_event=False,
                                      select_event=False, key='style_click', override_height=500)
                if clicked:
                    try:
                        style = str(clicked[0].get('x'))
                        st.session_state.gs_selected_style = style
                        st.session_state.gs_selected_genre = None
                        st.session_state.gs_view = 'style_drill'
                        st.session_state.gs_page = 0
                        st.rerun()
                    except Exception:
                        pass
            else:
                st.plotly_chart(fig, use_container_width=True)
                # Fallback: select box for style
                selected_style = st.selectbox("Select a style to explore:", 
                                            [""] + df_top['style'].tolist())
                if selected_style:
                    st.session_state.gs_selected_style = selected_style
                    st.session_state.gs_selected_genre = None
                    st.session_state.gs_view = 'style_drill'
                    st.session_state.gs_page = 0
                    st.rerun()
            
            # Show random sample for top style
            if not df_top.empty:
                top_style = df_top.iloc[0]['style']
                st.subheader(f"🎵 Random {top_style} Albums")
                _display_release_thumbnail_gallery(db_conn, style=top_style)
        else:
            st.info("No style data available")

def _display_genre_drill_down(db_conn: PostgreSQLConnection):
    """Display styles within selected genre."""
    genre = st.session_state.gs_selected_genre
    st.subheader(f"Styles in {genre}")
    
    styles_df = load_styles_for_genre(db_conn, genre)
    if not styles_df.empty:
        df_top = styles_df.head(15)
        # Create go.Bar with colors (like decade/year fix)
        import plotly.graph_objects as go
        df_clean = df_top.reset_index(drop=True).copy()
        style_labels = df_clean['style'].tolist()
        
        # Create color map for these styles
        color_map_local = get_color_map(style_labels, 'rainbow')
        colors = [color_map_local.get(label, '#1f77b4') for label in style_labels]
        
        fig = go.Figure(data=[
            go.Bar(
                x=style_labels,
                y=df_clean['release_count'].tolist(),
                name='Releases',
                marker=dict(color=colors)
            )
        ])
        fig.update_layout(
            title=f"Click a style to see {genre} releases",
            showlegend=False,
            height=500
        )
        
        if plotly_events:
            clicked = plotly_events(fig, click_event=True, hover_event=False,
                                  select_event=False, key=f'style_drill_{genre}', override_height=500)
            if clicked:
                try:
                    style = str(clicked[0].get('x'))
                    st.session_state.gs_selected_style = style
                    st.session_state.gs_view = 'releases'
                    st.session_state.gs_page = 0
                    st.rerun()
                except Exception:
                    pass
        else:
            st.plotly_chart(fig, use_container_width=True)
            # Fallback: select box
            selected_style = st.selectbox("Select a style to see releases:", 
                                        [""] + df_top['style'].tolist())
            if selected_style:
                st.session_state.gs_selected_style = selected_style
                st.session_state.gs_view = 'releases'
                st.session_state.gs_page = 0
                st.rerun()
        
        # Show random sample
        st.subheader(f"🎵 Random {genre} Albums")
        _display_release_thumbnail_gallery(db_conn, genre=genre)
    else:
        st.info(f"No styles found for {genre}")

def _display_style_drill_down(db_conn: PostgreSQLConnection):
    """Display genres within selected style."""
    style = st.session_state.gs_selected_style
    st.subheader(f"Genres with {style}")
    
    genres_df = load_genres_for_style(db_conn, style)
    if not genres_df.empty:
        df_top = genres_df.head(15)
        # Create go.Bar with colors (like decade/year fix)
        import plotly.graph_objects as go
        df_clean = df_top.reset_index(drop=True).copy()
        genre_labels = df_clean['genre'].tolist()
        
        # Create color map for these genres
        color_map_local = get_color_map(genre_labels, 'rainbow')
        colors = [color_map_local.get(label, '#1f77b4') for label in genre_labels]
        
        fig = go.Figure(data=[
            go.Bar(
                x=genre_labels,
                y=df_clean['release_count'].tolist(),
                name='Releases',
                marker=dict(color=colors)
            )
        ])
        fig.update_layout(
            title=f"Click a genre to see {style} releases",
            showlegend=False,
            height=500
        )
        
        if plotly_events:
            clicked = plotly_events(fig, click_event=True, hover_event=False,
                                  select_event=False, key=f'genre_drill_{style}', override_height=500)
            if clicked:
                try:
                    genre = str(clicked[0].get('x'))
                    st.session_state.gs_selected_genre = genre
                    st.session_state.gs_view = 'releases'
                    st.session_state.gs_page = 0
                    st.rerun()
                except Exception:
                    pass
        else:
            st.plotly_chart(fig, use_container_width=True)
            # Fallback: select box
            selected_genre = st.selectbox("Select a genre to see releases:", 
                                        [""] + df_top['genre'].tolist())
            if selected_genre:
                st.session_state.gs_selected_genre = selected_genre
                st.session_state.gs_view = 'releases'
                st.session_state.gs_page = 0
                st.rerun()
        
        # Show random sample
        st.subheader(f"🎵 Random {style} Albums")
        _display_release_thumbnail_gallery(db_conn, style=style)
    else:
        st.info(f"No genres found for {style}")

def _display_genre_style_releases(db_conn: PostgreSQLConnection):
    """Display releases for selected genre/style combination with thumbnail gallery."""
    genre = st.session_state.gs_selected_genre
    style = st.session_state.gs_selected_style
    
    if genre and style:
        st.subheader(f"Releases: {genre} + {style}")
        # Load releases that match both genre and style
        releases_df = load_releases_for_genre(db_conn, genre, offset=st.session_state.gs_page * 20, limit=20)
        # Filter by style (basic filter for now)
        if not releases_df.empty and 'styles' in releases_df.columns:
            releases_df = releases_df[releases_df['styles'].astype(str).str.contains(style, na=False)]
    elif genre:
        st.subheader(f"Releases: {genre}")
        releases_df = load_releases_for_genre(db_conn, genre, offset=st.session_state.gs_page * 20, limit=20)
    elif style:
        st.subheader(f"Releases: {style}")
        releases_df = load_releases_for_style(db_conn, style, offset=st.session_state.gs_page * 20, limit=20)
    else:
        st.info("No genre or style selected")
        return
    
    if not releases_df.empty:
        _display_release_thumbnail_gallery(releases_df=releases_df)
        
        # Pagination
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.gs_page > 0:
                if st.button("⬅ Previous"):
                    st.session_state.gs_page -= 1
                    st.rerun()
        with col3:
            if len(releases_df) == 20:  # Assume more pages if we got full page
                if st.button("Next ➡"):
                    st.session_state.gs_page += 1
                    st.rerun()
        with col2:
            st.write(f"Page {st.session_state.gs_page + 1}")
    else:
        st.info("No releases found for this combination")

def _display_genre_style_random_sample(db_conn: PostgreSQLConnection, genre: str = None, style: str = None, title: str = "Random Sample"):
    """Display random sample of albums for genre/style."""
    st.markdown("---")
    st.subheader(title)
    
    if 'gs_random_token' not in st.session_state:
        st.session_state.gs_random_token = 0
    
    col_refresh, col_spacer = st.columns([1, 6])
    with col_refresh:
        if st.button("🔄 New Sample", key=f"refresh_gs_{genre}_{style}"):
            st.session_state.gs_random_token += 1
    
    if genre:
        releases_df = load_releases_for_genre(db_conn, genre, offset=0, limit=8, random_seed=st.session_state.gs_random_token)
    elif style:
        releases_df = load_releases_for_style(db_conn, style, offset=0, limit=8, random_seed=st.session_state.gs_random_token)
    else:
        return
    
    if not releases_df.empty:
        _display_release_thumbnail_gallery(releases_df=releases_df.head(8))
    else:
        st.info("No albums available for sample")

def _display_release_thumbnail_gallery(db_conn: PostgreSQLConnection = None, releases_df: pd.DataFrame = None, genre: str = None, style: str = None, force_refresh: bool = False):
    """Display releases as thumbnail gallery (similar to Browse Collection)."""
    
    import time
    import random
    
    # Create unique cache key for this genre/style combination with timestamp to force refresh
    timestamp_part = int(time.time()) if not force_refresh else int(time.time() * 1000)  # More granular when forcing refresh
    cache_key = f"genre_style_releases_{genre}_{style}_{timestamp_part // 60}"  # Cache for 1 minute intervals
    
    # Load data if not provided
    if releases_df is None and db_conn is not None:
        # Always query fresh data - remove caching for random samples to ensure true randomization
        # Query new data each time for truly random results
        if genre and style:
            # Both genre and style specified - drill-down scenario
            query = """
            SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, r.title, r.artist, r.year, r.label, r.release_id
            FROM artwork a
            JOIN releases r ON r.release_id = a.release_id,
            LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre_elem,
            LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style_elem
            WHERE a.image_type = 'primary'
                AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
                AND genre_elem = %s AND style_elem = %s
            ORDER BY RANDOM()
            LIMIT 10
            """
            result = db_conn.execute_query(query, (genre, style))
        elif genre:
            # Only genre specified - use proper JSONB array matching with simple randomization
            query = """
            SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, r.title, r.artist, r.year, r.label, r.release_id
            FROM artwork a
            JOIN releases r ON r.release_id = a.release_id,
            LATERAL jsonb_array_elements_text(COALESCE(r.genres, '[]'::jsonb)) AS genre_elem
            WHERE a.image_type = 'primary'
                AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
                AND genre_elem = %s
            ORDER BY RANDOM()
            LIMIT 10
            """
            result = db_conn.execute_query(query, (genre,))
        elif style:
            # Only style specified - use proper JSONB array matching with simple randomization
            query = """
            SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, r.title, r.artist, r.year, r.label, r.release_id
            FROM artwork a
            JOIN releases r ON r.release_id = a.release_id,
            LATERAL jsonb_array_elements_text(COALESCE(r.styles, '[]'::jsonb)) AS style_elem
            WHERE a.image_type = 'primary'
                AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
                AND style_elem = %s
            ORDER BY RANDOM()
            LIMIT 10
            """
            result = db_conn.execute_query(query, (style,))
        else:
            # Random releases with preference for those with artwork
            query = """
            SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, r.title, r.artist, r.year, r.label, r.release_id
            FROM artwork a
            JOIN releases r ON r.release_id = a.release_id
            WHERE a.image_type = 'primary'
                AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
            ORDER BY RANDOM()
            LIMIT 10
            """
            result = db_conn.execute_query(query)
        
        # If no results, try any releases with artwork (simplified)
        if not result:
            fallback_query = """
            SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, r.title, r.artist, r.year, r.label, r.release_id
            FROM artwork a
            JOIN releases r ON r.release_id = a.release_id
            WHERE a.image_type = 'primary'
                AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
            ORDER BY RANDOM()
            LIMIT 10
            """
            result = db_conn.execute_query(fallback_query)
        
        if result:
            releases_df = pd.DataFrame(result)
            # Don't cache for truly random results each time
        else:
            releases_df = pd.DataFrame()
    
    if releases_df is None or releases_df.empty:
        st.info("No releases found")
        return
    
    # Add randomize button to get new releases for this genre/style
    if genre or style:
        col_title, col_refresh = st.columns([4, 1])
        with col_refresh:
            if st.button("🔄 Randomize", key=f"randomize_{cache_key}"):
                # Clear the cache to get new random releases
                if cache_key in st.session_state:
                    del st.session_state[cache_key]
                st.rerun()
    
    cols = st.columns(5)
    for idx, row in releases_df.iterrows():
        col_idx = idx % 5
        with cols[col_idx]:
            # Get image path exactly like Browse Collection
            thumb_path = row.get('thumbnail_file_path') or row.get('local_file_path')
            artist = row.get('artist', 'Unknown Artist')
            title = row.get('title', 'Unknown Title')
            year = row.get('year', '')
            label = row.get('label', 'Unknown Label')
            
            # Display image exactly like Browse Collection
            if thumb_path:
                try:
                    st.image(thumb_path, use_container_width=USE_CONTAINER_WIDTH)
                except Exception:
                    st.write("🎵")
            else:
                st.write("🎵")
            
            # Show basic info with Details button (like Browse Collection)
            st.markdown(f"**{artist}**")
            st.caption(title)
            if year:
                st.caption(f"{year} • {label}")
            else:
                st.caption(label)
            
            # Add Details button to navigate to full release view (exactly like Browse Collection)
            if st.button("🔍 Details", key=f"genre_detail_{idx}", use_container_width=True):
                st.query_params["release_id"] = str(row.get('release_id', ''))
                st.query_params["source_page"] = "Genre & Style Analysis"
                st.rerun()

def display_decade_timeline(db_conn: PostgreSQLConnection):
    """Interactive decade analysis with drill-down and thumbnail galleries."""
    st.header("📅 Decade Timeline")
    st.markdown("Explore your collection through the decades with colorful clickable charts.")
    
    # Initialize session state
    if 'decade_view' not in st.session_state:
        st.session_state.decade_view = 'decades'
    if 'selected_decade' not in st.session_state:
        st.session_state.selected_decade = None
    if 'selected_year' not in st.session_state:
        st.session_state.selected_year = None
    if 'year_page' not in st.session_state:
        st.session_state.year_page = 0
    if 'decade_random_seed' not in st.session_state:
        st.session_state.decade_random_seed = 0
    
    # Create left sidebar layout for controls and navigation
    left_col, right_col = st.columns([1, 3])
    
    with left_col:
        st.markdown("### 🎛️ Controls")
        
        # Color scheme selector
        color_scheme = st.selectbox(
            "Color Scheme:",
            ["Rainbow", "Blue", "Green", "Red", "Purple", "Orange"],
            index=0,
            key="decade_color_scheme"
        )
        
        # Reset button
        if st.button("🔄 Reset View", key="decade_reset"):
            st.session_state.decade_view = 'decades'
            st.session_state.selected_decade = None
            st.session_state.selected_year = None
            st.session_state.year_page = 0
            st.rerun()
        
        st.divider()
        
        # Navigation breadcrumb and single back button
        st.markdown("### 🧭 Navigation")
        if st.session_state.decade_view == 'decades':
            st.write("🏠 **Decade Overview**")
        elif st.session_state.decade_view == 'years':
            st.write(f"🏠 Decades")
            st.write(f"📅 **{st.session_state.selected_decade}s**")
            if st.button("⬅ Back to Decades", key="back_to_decades"):
                st.session_state.decade_view = 'decades'
                st.session_state.selected_decade = None
                st.session_state.selected_year = None
                st.session_state.year_page = 0
                st.rerun()
        elif st.session_state.decade_view == 'releases':
            st.write(f"🏠 Decades")
            st.write(f"📅 {st.session_state.selected_decade}s")
            st.write(f"🎵 **{st.session_state.selected_year}**")
            if st.button("⬅ Back to Years", key="back_to_years"):
                st.session_state.decade_view = 'years'
                st.session_state.selected_year = None
                st.session_state.year_page = 0
                st.rerun()
        
        # Randomize button for releases view
        if st.session_state.decade_view == 'releases':
            st.divider()
            if st.button("🎲 Randomize Albums", key="randomize_year"):
                st.session_state.decade_random_seed += 1
                st.session_state.year_page = 0
                st.rerun()
    
    with right_col:
        # Display based on current view
        if st.session_state.decade_view == 'decades':
            _display_decade_overview(db_conn, color_scheme)
        elif st.session_state.decade_view == 'years':
            _display_year_breakdown(db_conn, color_scheme)
        elif st.session_state.decade_view == 'releases':
            _display_year_releases(db_conn)

def _display_decade_overview(db_conn: PostgreSQLConnection, color_scheme: str):
    """Display decade overview with clickable chart."""
    st.subheader("📅 Releases by Decade")
    
    decade_df = load_decade_analysis(db_conn)
    if decade_df.empty:
        st.warning("No decade data found")
        return
    
    # Minimal processing - just sort by decade
    decade_df = decade_df.sort_values('decade')
    
    if decade_df.empty:
        st.warning("No valid decade data found")
        return
    
    # Create decade labels and prepare data
    decade_df['decade_label'] = decade_df['decade'].astype(str) + 's'
    labels = decade_df['decade_label'].tolist()
    
    # Ensure release_count is proper integer type for Plotly
    decade_df['release_count'] = pd.to_numeric(decade_df['release_count'], errors='coerce').fillna(0).astype(int)
    
    # Create color map
    color_map = get_color_map(labels, color_scheme)
    
    # Reset index to ensure clean DataFrame for Plotly
    decade_df_clean = decade_df.reset_index(drop=True).copy()
    
    # Clean data ready for chart
    
    # Create go.Bar with color control
    import plotly.graph_objects as go
    
    # Get colors for each decade
    decade_labels = decade_df_clean['decade_label'].tolist()
    colors = [color_map.get(label, '#1f77b4') for label in decade_labels]
    
    fig = go.Figure(data=[
        go.Bar(
            x=decade_labels,
            y=decade_df_clean['release_count'].tolist(),
            name='Releases',
            marker=dict(color=colors)
        )
    ])
    fig.update_layout(
        title="Click a decade to explore years",
        showlegend=False,
        height=400
    )
    
    # Add minimal safe formatting
    fig.update_layout(
        showlegend=False,
        height=400,
        title="Click a decade to explore years"
    )
    
    if plotly_events:
        clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key='decade_click', override_height=400)
        if clicked:
            try:
                label = str(clicked[0].get('x', ''))
                decade_int = int(label.rstrip('s')) if label.endswith('s') else int(label)
                st.session_state.selected_decade = decade_int
                st.session_state.decade_view = 'years'
                st.session_state.selected_year = None
                st.session_state.year_page = 0
                st.rerun()
            except Exception as e:
                st.error(f"Error processing decade click: {e}")
    else:
        st.plotly_chart(fig, use_container_width=True)
        # Fallback: select box for decade
        decade_options = [f"{int(d)}s" for d in decade_df['decade'].tolist()]
        selected_decade = st.selectbox("Select a decade to explore:", 
                                     [""] + decade_options)
        if selected_decade:
            decade_int = int(selected_decade.rstrip('s'))
            st.session_state.selected_decade = decade_int
            st.session_state.decade_view = 'years'
            st.session_state.selected_year = None
            st.session_state.year_page = 0
            st.rerun()
    
    # Show random sample for most active decade
    if not decade_df.empty:
        most_active_decade = decade_df.loc[decade_df['release_count'].idxmax(), 'decade']
        st.subheader(f"🎵 Random {int(most_active_decade)}s Albums")
        _display_decade_random_sample(db_conn, decade=int(most_active_decade), title="")

def _display_year_breakdown(db_conn: PostgreSQLConnection, color_scheme: str):
    """Display year breakdown for selected decade."""
    decade_int = st.session_state.selected_decade
    st.subheader(f"📅 Releases in the {decade_int}s by Year")
    
    year_df = load_year_breakdown(db_conn, decade_int)
    
    if year_df.empty:
        st.info(f"No year data found for the {decade_int}s decade.")
        return
    
    # Create complete year range for the decade (fill missing years with 0)
    decade_start = decade_int
    decade_end = decade_int + 9
    all_years = list(range(decade_start, decade_end + 1))
    all_years_str = [str(y) for y in all_years]
    
    # Create complete DataFrame with all years in decade
    complete_year_data = []
    year_counts = dict(zip(year_df['year'].astype(int), year_df['release_count']))
    
    for year in all_years:
        complete_year_data.append({
            'year': year,
            'year_str': str(year),
            'release_count': year_counts.get(year, 0)  # 0 for missing years
        })
    
    year_df_complete = pd.DataFrame(complete_year_data)
    
    # Complete year data ready for chart
    
    # Prepare colors for all years
    color_map = get_color_map(all_years_str, color_scheme)
    colors = [color_map.get(year_str, '#1f77b4') for year_str in all_years_str]
    
    # Create go.Bar with proper year alignment and colors
    import plotly.graph_objects as go
    
    fig = go.Figure(data=[
        go.Bar(
            x=year_df_complete['year_str'].tolist(),
            y=year_df_complete['release_count'].tolist(),
            name='Releases',
            marker=dict(color=colors)
        )
    ])
    fig.update_layout(
        title=f"Click a year to see releases from the {decade_int}s",
        showlegend=False,
        height=400,
        xaxis=dict(
            categoryorder='array',
            categoryarray=all_years_str,
            type='category'
        )
    )
    
    # Minimal safe formatting
    fig.update_layout(
        showlegend=False,
        height=400
    )
    
    if plotly_events:
        clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key=f'year_click_{decade_int}', override_height=400)
        if clicked:
            try:
                year_str = str(clicked[0].get('x', ''))
                year_selected = int(year_str) if year_str.isdigit() else None
                if year_selected:
                    st.session_state.selected_year = year_selected
                    st.session_state.decade_view = 'releases'
                    st.session_state.year_page = 0
                    st.rerun()
            except Exception as e:
                st.error(f"Error processing year click: {e}")
    else:
        st.plotly_chart(fig, use_container_width=True)
        # Fallback: select box for year
        year_options = [int(y) for y in year_df['year'].tolist() if y > 0]
        if year_options:
            selected_year = st.selectbox("Select a year to see releases:", 
                                       [None] + year_options)
            if selected_year:
                st.session_state.selected_year = selected_year
                st.session_state.decade_view = 'releases'
                st.session_state.year_page = 0
                st.rerun()
    
    # Show random sample for this decade
    st.subheader(f"🎵 Random {decade_int}s Albums")
    _display_decade_random_sample(db_conn, decade=decade_int, title="")

def _display_year_releases(db_conn: PostgreSQLConnection):
    """Display releases for selected year with thumbnail gallery."""
    year = st.session_state.selected_year
    st.subheader(f"Releases from {year}")
    
    releases_df = load_releases_for_year(db_conn, year, limit=20, offset=st.session_state.year_page * 20)
    
    if not releases_df.empty:
        _display_release_thumbnail_gallery(releases_df=releases_df)
        
        # Pagination
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.year_page > 0:
                if st.button("⬅ Previous"):
                    st.session_state.year_page -= 1
                    st.rerun()
        with col3:
            if len(releases_df) == 20:  # Assume more pages if we got full page
                if st.button("Next ➡"):
                    st.session_state.year_page += 1
                    st.rerun()
        with col2:
            st.write(f"Page {st.session_state.year_page + 1}")
    else:
        st.info(f"No releases found for {year}")

def _display_decade_random_sample(db_conn: PostgreSQLConnection, decade: int, title: str = "Random Sample"):
    """Display random sample of albums for decade."""
    st.markdown("---")
    st.subheader(title)
    
    if 'decade_random_token' not in st.session_state:
        st.session_state.decade_random_token = 0
    
    col_refresh, col_spacer = st.columns([1, 6])
    with col_refresh:
        if st.button("🔄 New Sample", key=f"refresh_decade_{decade}"):
            st.session_state.decade_random_token += 1
    
    # Load random releases from this decade
    releases_df = load_random_releases(db_conn, count=8, decade_start=decade, rand_token=st.session_state.decade_random_token)
    
    if not releases_df.empty:
        _display_release_thumbnail_gallery(releases_df=releases_df.head(8))
    else:
        st.info("No albums available for sample")

def display_collection_insights(db_conn: PostgreSQLConnection):
    """Collection insights and analytics."""
    st.header("🔬 Collection Insights")
    
    st.subheader("Artist Analysis")
    
    # Top artists by release count
    artist_query = """
    SELECT artist, COUNT(*) as release_count,
           COUNT(DISTINCT label) as label_count,
           AVG(CASE WHEN rating > 0 THEN rating END) as avg_rating
    FROM releases 
    WHERE artist IS NOT NULL 
    AND artist NOT IN ('Various', 'Various Artists', 'VA')
    GROUP BY artist
    ORDER BY release_count DESC
    LIMIT 20
    """
    
    try:
        artist_df = pd.DataFrame(db_conn.execute_query(artist_query))
        if not artist_df.empty:
            fig = px.bar(artist_df.head(10), x='artist', y='release_count',
                        title="Top Artists by Release Count")
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display as expandable artist cards
            st.subheader("Artist Details")
            for idx, row in artist_df.head(15).iterrows():
                with st.expander(f"🎤 **{row['artist']}** ({row['release_count']} releases)"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Releases", f"{row['release_count']:,}")
                    with col2:
                        st.metric("Labels", f"{row['label_count']:,}")
                    with col3:
                        if row['avg_rating']:
                            rating = float(row['avg_rating'])
                            stars = "⭐" * int(rating)
                            st.metric("Avg Rating", f"{rating:.1f} {stars}")
                        else:
                            st.metric("Avg Rating", "Not rated")
        else:
            st.info("No artist data available")
    except Exception as e:
        st.error(f"Error loading artist insights: {e}")

    # Remix & Production Analysis Section
    st.markdown("---")
    st.subheader("🎛️ Remix & Production Analysis")
    st.caption("Deep dive into your collection's remix culture and production credits.")
    
    # Create tabs for different remix analyses
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Top Remixers", 
        "📊 Genre Trends", 
        "⏰ Timeline", 
        "🔗 Collaborations"
    ])
    
    with tab1:
        _display_remixer_leaderboard(db_conn)
        
    with tab2:
        _display_remix_genre_analysis(db_conn)
        
    with tab3:
        _display_remix_timeline_analysis(db_conn)
        
    with tab4:
        _display_remix_collaborations(db_conn)

def _display_remixer_leaderboard(db_conn: PostgreSQLConnection):
    """Display comprehensive remixer leaderboard and analysis."""
    from data.loaders import load_top_remixers, load_most_remixed_tracks
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🏆 Top Remixers by Track Count**")
            remixers_df = load_top_remixers(db_conn, limit=12)
            
            if not remixers_df.empty:
                for idx, row in remixers_df.iterrows():
                    with st.container():
                        remixer_name = row['remixer_name']
                        role = row['role']
                        track_count = row['track_count']
                        release_count = row['release_count']
                        
                        # Remixer ranking card
                        rank_col, info_col, stats_col = st.columns([0.5, 2, 1])
                        
                        with rank_col:
                            st.write(f"**#{idx + 1}**")
                        
                        with info_col:
                            st.write(f"**🎛️ {remixer_name}**")
                            st.caption(f"{role}")
                            
                            # Show active years
                            earliest = row.get('earliest_year')
                            latest = row.get('latest_year')
                            if earliest and latest and earliest != latest:
                                st.caption(f"📅 Active: {earliest}-{latest}")
                        
                        with stats_col:
                            st.metric("Tracks", f"{track_count}")
                            st.metric("Releases", f"{release_count}")
                        
                        st.divider()
            else:
                st.info("No remix credits found in your collection.")
        
        with col2:
            st.write("**🎵 Most Remixed Tracks**")
            remixed_df = load_most_remixed_tracks(db_conn, limit=8)
            
            if not remixed_df.empty:
                for idx, row in remixed_df.iterrows():
                    track_name = row['track_name']
                    artist = row['artist']
                    year = row.get('year', '')
                    total_remixes = row['total_remixes']
                    versions = row['versions_in_collection']
                    
                    with st.container():
                        st.write(f"**🎵 {track_name}**")
                        st.caption(f"👤 {artist} • 📅 {year}")
                        
                        remix_col, version_col = st.columns(2)
                        with remix_col:
                            st.metric("Remixes", f"{total_remixes}")
                        with version_col:
                            st.metric("Versions", f"{versions}")
                        
                        st.divider()
            else:
                st.info("No multi-remix tracks found.")
                
    except Exception as e:
        st.error(f"Error loading remixer data: {e}")

def _display_remix_genre_analysis(db_conn: PostgreSQLConnection):
    """Display remix density analysis by genre."""
    from data.loaders import load_remix_by_genre
    
    try:
        st.write("**📊 Remix Density by Genre**")
        st.caption("Which genres in your collection have the highest remix activity?")
        
        remix_genre_df = load_remix_by_genre(db_conn)
        
        if not remix_genre_df.empty:
            # Create visualization
            fig = px.bar(
                remix_genre_df.head(12), 
                x='genre', 
                y='remix_percentage',
                title="Remix Percentage by Genre",
                labels={'remix_percentage': 'Remix %', 'genre': 'Genre'},
                color='remix_percentage',
                color_continuous_scale='viridis'
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed breakdown
            st.write("**Genre Breakdown:**")
            
            for idx, row in remix_genre_df.iterrows():
                genre = row['genre']
                total_tracks = row['total_tracks']
                remix_tracks = row['tracks_with_remixes']
                percentage = row['remix_percentage']
                
                with st.expander(f"🎵 **{genre}** - {percentage}% remixed"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Tracks", f"{total_tracks:,}")
                    
                    with col2:
                        st.metric("With Remixes", f"{remix_tracks:,}")
                    
                    with col3:
                        st.metric("Remix Rate", f"{percentage}%")
                        
                        # Interpretation
                        if percentage >= 60:
                            st.success("🔥 Remix Heavy Genre")
                        elif percentage >= 30:
                            st.info("🎛️ Moderate Remix Activity")
                        else:
                            st.caption("📻 Mostly Original Mixes")
        else:
            st.info("No genre remix data available.")
            
    except Exception as e:
        st.error(f"Error loading genre remix analysis: {e}")

def _display_remix_timeline_analysis(db_conn: PostgreSQLConnection):
    """Display remix activity timeline and trends."""
    from data.loaders import load_remix_timeline
    
    try:
        st.write("**⏰ Remix Activity Timeline**")
        st.caption("Discover the golden eras of remixing in your collection.")
        
        timeline_df = load_remix_timeline(db_conn)
        
        if not timeline_df.empty:
            # Decade summary
            decade_summary = timeline_df.groupby('decade_label').agg({
                'total_tracks': 'sum',
                'remix_tracks': 'sum',
                'remix_percentage': 'mean'
            }).reset_index()
            decade_summary = decade_summary.sort_values('remix_percentage', ascending=False)
            
            st.write("**🎯 Remix Peak Decades:**")
            
            cols = st.columns(min(4, len(decade_summary)))
            for idx, row in decade_summary.head(4).iterrows():
                with cols[idx % 4]:
                    decade = row['decade_label']
                    percentage = row['remix_percentage']
                    total_tracks = row['total_tracks']
                    
                    st.metric(
                        f"📅 {decade}",
                        f"{percentage:.1f}%",
                        delta=f"{total_tracks} tracks"
                    )
                    
                    if percentage >= 50:
                        st.success("🔥 Remix Golden Era")
                    elif percentage >= 30:
                        st.info("🎛️ Active Period")
            
            # Year-by-year chart
            st.write("**📈 Year-by-Year Remix Trends:**")
            
            fig = px.line(
                timeline_df.tail(20),  # Last 20 years
                x='year', 
                y='remix_percentage',
                title="Remix Percentage by Year (Recent)",
                labels={'remix_percentage': 'Remix %', 'year': 'Year'},
                markers=True
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # Insights
            st.write("**💡 Timeline Insights:**")
            
            peak_year = timeline_df.loc[timeline_df['remix_percentage'].idxmax()]
            low_year = timeline_df.loc[timeline_df['remix_percentage'].idxmin()]
            
            insight_col1, insight_col2 = st.columns(2)
            
            with insight_col1:
                st.info(f"🔥 **Peak Remix Year**: {peak_year['year']} with {peak_year['remix_percentage']:.1f}% remix rate")
                
            with insight_col2:
                st.info(f"📻 **Lowest Remix Year**: {low_year['year']} with {low_year['remix_percentage']:.1f}% remix rate")
            
        else:
            st.info("No timeline data available for remix analysis.")
            
    except Exception as e:
        st.error(f"Error loading remix timeline: {e}")

def _display_remix_collaborations(db_conn: PostgreSQLConnection):
    """Display producer collaboration networks and partnerships."""
    from data.loaders import load_producer_collaborations
    
    try:
        st.write("**🔗 Producer Collaboration Network**")
        st.caption("Discover which producers frequently work together in your collection.")
        
        collab_df = load_producer_collaborations(db_conn, limit=15)
        
        if not collab_df.empty:
            st.write("**🤝 Frequent Collaborations:**")
            
            for idx, row in collab_df.iterrows():
                producer1 = row['producer1']
                producer2 = row['producer2']
                collaborations = row['collaborations']
                
                with st.container():
                    # Collaboration card
                    collab_col, count_col = st.columns([3, 1])
                    
                    with collab_col:
                        st.write(f"**🔗 {producer1} & {producer2}**")
                        st.caption("Producer Partnership")
                    
                    with count_col:
                        st.metric("Tracks", f"{collaborations}")
                        
                        # Partnership strength indicator
                        if collaborations >= 5:
                            st.success("🔥 Strong Partnership")
                        elif collaborations >= 3:
                            st.info("🎛️ Regular Collaborators")
                        else:
                            st.caption("🤝 Occasional Team-up")
                    
                    st.divider()
            
            # Network insights
            st.write("**🧠 Collaboration Insights:**")
            
            # Most collaborative producer
            producer_counts = {}
            for _, row in collab_df.iterrows():
                p1, p2 = row['producer1'], row['producer2']
                producer_counts[p1] = producer_counts.get(p1, 0) + 1
                producer_counts[p2] = producer_counts.get(p2, 0) + 1
            
            if producer_counts:
                most_collaborative = max(producer_counts, key=producer_counts.get)
                collab_count = producer_counts[most_collaborative]
                
                st.info(f"👥 **Most Collaborative Producer**: {most_collaborative} appears in {collab_count} partnerships")
            
            # Total collaboration tracks
            total_collab_tracks = collab_df['collaborations'].sum()
            st.info(f"🎵 **Total Collaboration Tracks**: {total_collab_tracks} tracks feature producer partnerships")
                
        else:
            st.info("🤝 No frequent producer collaborations found in your collection.")
            st.caption("This analysis requires multiple tracks with the same producer pairs.")
            
    except Exception as e:
        st.error(f"Error loading collaboration data: {e}")

def display_community_statistics(db_conn: PostgreSQLConnection):
    """Community statistics and social features."""
    st.header("👥 Community Statistics")
    
    # Load community stats check
    community_check = load_community_stats_check(db_conn)
    if community_check:
        st.subheader("Community Data Overview")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Releases", community_check.get('total_releases', 'N/A'))
        with col2:
            st.metric("Releases with Stats", community_check.get('releases_with_stats', 'N/A'))
    else:
        st.info("Community statistics not available. Run community stats update in the downloader.")

def display_deals(db_conn: PostgreSQLConnection):
    """Deals and marketplace insights."""
    st.header("💸 Deals")
    
    # Collection valuation
    valuation_df = load_collection_valuation(db_conn)
    if not valuation_df.empty:
        st.subheader("Collection Valuation")
        
        # Display valuation as metrics cards
        for idx, row in valuation_df.iterrows():
            with st.container():
                st.write(f"**💰 {row.get('currency', 'USD')} Market**")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Releases", f"{row['total_releases']:,}")
                with col2:
                    st.metric("Priced Releases", f"{row['priced_releases']:,}")
                with col3:
                    if row['total_value']:
                        st.metric("Total Value", f"${row['total_value']:,.2f}")
                    else:
                        st.metric("Total Value", "N/A")
                with col4:
                    if row['avg_price']:
                        st.metric("Avg Price", f"${row['avg_price']:,.2f}")
                    else:
                        st.metric("Avg Price", "N/A")
                
                # Price range info
                if row['min_price'] and row['max_price']:
                    st.caption(f"💵 Price range: ${row['min_price']:.2f} - ${row['max_price']:,.2f} • Last updated: {row.get('price_date', 'Unknown')}")
                
                st.divider()
    else:
        st.info("Valuation data not available. Requires marketplace price data.")

def display_master_release_tracking(db_conn: PostgreSQLConnection):
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
            ["Master Release Overview", "Detailed Version Analysis", "🎛️ Remix Versions", "Duplicate Detection"],
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
        _display_master_release_overview(db_conn, sort_option)
    elif analysis_mode == "Detailed Version Analysis":
        _display_detailed_version_analysis(db_conn)
    elif analysis_mode == "🎛️ Remix Versions":
        _display_remix_versions_analysis(db_conn, sort_option)
    elif analysis_mode == "Duplicate Detection":
        _display_duplicate_detection_archive(db_conn)

def _display_duplicate_detection(db_conn: PostgreSQLConnection):
    """Display potential duplicates and multiple versions."""
    st.subheader("🔍 Potential Duplicates/Multiple Versions")
    
    # Enhanced duplicate detection query - FIXED GROUP BY
    duplicate_query = """
    SELECT 
        title, 
        artist, 
        COUNT(*) as version_count,
        STRING_AGG(DISTINCT format, ', ') as formats,
        STRING_AGG(DISTINCT country, ', ') as countries,
        MIN(year) as earliest_year,
        MAX(year) as latest_year
    FROM releases
    WHERE title IS NOT NULL AND artist IS NOT NULL
    GROUP BY title, artist
    HAVING COUNT(*) > 1
    ORDER BY version_count DESC
    LIMIT 20
    """
    
    try:
        duplicate_df = pd.DataFrame(db_conn.execute_query(duplicate_query))
        if not duplicate_df.empty:
            # Display as interactive table
            st.write("Click on any row to see all versions:")
            
            # Create clickable dataframe
            for idx, row in duplicate_df.iterrows():
                title = row['title']
                artist = row['artist']
                version_count = row['version_count']
                
                with st.expander(f"🎵 {artist} - {title} ({version_count} versions)"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**Formats:** {row['formats']}")
                        st.write(f"**Countries:** {row['countries']}")
                        st.write(f"**Years:** {row['earliest_year']} - {row['latest_year']}")
                    with col2:
                        if st.button("View All Versions", key=f"view_versions_{idx}"):
                            st.session_state.mrt_selected_title = title
                            st.session_state.mrt_selected_artist = artist
                            st.rerun()
            
            # Show versions if selected
            if st.session_state.mrt_selected_title and st.session_state.mrt_selected_artist:
                _display_release_versions(db_conn, st.session_state.mrt_selected_title, st.session_state.mrt_selected_artist)
        else:
            st.info("No duplicate releases detected - your collection has unique entries!")
    except Exception as e:
        st.error(f"Error checking duplicates: {e}")

def _display_version_analysis(db_conn: PostgreSQLConnection):
    """Display version analysis and statistics."""
    st.subheader("📊 Version Analysis")
    
    # Version statistics
    stats_query = """
    WITH version_stats AS (
        SELECT title, artist, COUNT(*) as version_count
        FROM releases
        WHERE title IS NOT NULL AND artist IS NOT NULL
        GROUP BY title, artist
    )
    SELECT 
        COUNT(*) as total_unique_albums,
        COUNT(CASE WHEN version_count > 1 THEN 1 END) as albums_with_multiple_versions,
        MAX(version_count) as max_versions,
        AVG(version_count) as avg_versions_per_album
    FROM version_stats
    """
    
    try:
        stats_result = db_conn.execute_query(stats_query)
        if stats_result:
            stats = stats_result[0]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Unique Albums", stats['total_unique_albums'])
            with col2:
                st.metric("With Multiple Versions", stats['albums_with_multiple_versions'])
            with col3:
                st.metric("Max Versions", stats['max_versions'])
            with col4:
                st.metric("Avg Versions/Album", f"{float(stats['avg_versions_per_album']):.1f}")
            
            # Most collected artists (by unique albums)
            artist_query = """
            SELECT artist, COUNT(DISTINCT title) as unique_albums,
                   COUNT(*) as total_releases,
                   ROUND(COUNT(*)::DECIMAL / COUNT(DISTINCT title), 1) as avg_versions_per_album
            FROM releases
            WHERE artist IS NOT NULL AND title IS NOT NULL
            AND artist NOT IN ('Various', 'Various Artists', 'VA')
            GROUP BY artist
            HAVING COUNT(DISTINCT title) >= 3
            ORDER BY unique_albums DESC
            LIMIT 10
            """
            
            artist_df = pd.DataFrame(db_conn.execute_query(artist_query))
            if not artist_df.empty:
                st.subheader("Top Artists by Unique Albums")
                
                # Display as nice cards
                for idx, row in artist_df.iterrows():
                    with st.container():
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.write(f"**🎤 {row['artist']}**")
                        with col2:
                            st.metric("Unique Albums", f"{row['unique_albums']:,}")
                        with col3:
                            st.metric("Total Releases", f"{row['total_releases']:,}")
                        with col4:
                            st.metric("Avg Versions/Album", f"{float(row['avg_versions_per_album']):.1f}")
                        st.divider()
    except Exception as e:
        st.error(f"Error analyzing versions: {e}")

def _display_collection_gaps(db_conn: PostgreSQLConnection):
    """Display potential collection gaps and recommendations."""
    st.subheader("🕳️ Collection Gaps")
    st.info("Artists where you might be missing albums (based on format diversity)")
    
    # Find artists with limited format diversity
    gaps_query = """
    SELECT artist, 
           COUNT(DISTINCT title) as albums,
           COUNT(DISTINCT format) as formats,
           STRING_AGG(DISTINCT format, ', ') as format_list,
           COUNT(*) as total_releases
    FROM releases
    WHERE artist IS NOT NULL AND title IS NOT NULL
    AND artist NOT IN ('Various', 'Various Artists', 'VA')
    GROUP BY artist
    HAVING COUNT(DISTINCT title) >= 5 AND COUNT(DISTINCT format) <= 2
    ORDER BY albums DESC
    LIMIT 10
    """
    
    try:
        gaps_df = pd.DataFrame(db_conn.execute_query(gaps_query))
        if not gaps_df.empty:
            for idx, row in gaps_df.iterrows():
                artist = row['artist']
                albums = row['albums']
                formats = row['format_list']
                
                with st.expander(f"🎤 {artist} ({albums} albums, only {formats})"):
                    st.write(f"You have {albums} albums by {artist}, but only in {formats} format(s).")
                    st.write("Consider exploring other formats like vinyl, CD, cassette, etc.")
                    
                    # Show sample of artist's releases
                    sample_query = """
                    SELECT title, year, format, label
                    FROM releases
                    WHERE artist = %s
                    ORDER BY year DESC
                    LIMIT 5
                    """
                    
                    sample_releases = db_conn.execute_query(sample_query, (artist,))
                    if sample_releases:
                        st.write("**Recent Releases:**")
                        for release in sample_releases:
                            title = release.get('title', 'Unknown')
                            year = f" ({release['year']})" if release.get('year') else ""
                            format_info = f" • {release['format']}" if release.get('format') else ""
                            label_info = f" • {release['label']}" if release.get('label') else ""
                            st.write(f"🎵 **{title}**{year}{format_info}{label_info}")
        else:
            st.info("No obvious format gaps detected - you have good format diversity!")
    except Exception as e:
        st.error(f"Error analyzing collection gaps: {e}")

def _display_release_versions(db_conn: PostgreSQLConnection, title: str, artist: str):
    """Display all versions of a specific release with thumbnail gallery."""
    st.markdown("---")
    st.subheader(f"All Versions: {artist} - {title}")
    
    # Get all versions
    versions_query = """
    SELECT r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
           r.country, r.condition, r.rating,
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
    WHERE r.title = %s AND r.artist = %s
    GROUP BY r.release_id, r.title, r.artist, r.year, r.label, r.catno, r.format, 
             r.country, r.condition, r.rating
    ORDER BY r.year, r.format
    """
    
    try:
        versions_df = pd.DataFrame(db_conn.execute_query(versions_query, (title, artist)))
        if not versions_df.empty:
            st.write(f"Found {len(versions_df)} version(s):")
            _display_release_thumbnail_gallery(versions_df)
            
            # Back button
            if st.button("⬅ Back to Duplicates"):
                st.session_state.mrt_selected_title = None
                st.session_state.mrt_selected_artist = None
                st.rerun()
        else:
            st.info("No versions found")
    except Exception as e:
        st.error(f"Error loading versions: {e}")

def display_buying_guide(db_conn: PostgreSQLConnection):
    """Comprehensive buying guide with intelligent recommendations and collection analysis."""
    st.header("🧭 Buying Guide")
    
    st.info("🎯 **Strategic collection building** with gap analysis, wantlist tracking, smart recommendations, and market intelligence.")
    
    # Create tabs for different buying guide sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Collection Gaps", 
        "💰 Wantlist & Budget", 
        "🎯 Smart Recommendations", 
        "🎛️ Missing Remixes",
        "📊 Market Intelligence"
    ])
    
    with tab1:
        _display_collection_gaps(db_conn)
        
    with tab2:
        _display_wantlist_budget(db_conn)
        
    with tab3:
        _display_smart_recommendations(db_conn)
        
    with tab4:
        _display_missing_remixes(db_conn)
        
    with tab5:
        _display_market_intelligence(db_conn)

def _display_collection_gaps(db_conn: PostgreSQLConnection):
    """Display comprehensive collection gap analysis."""
    st.subheader("📈 Collection Gaps Analysis")
    st.caption("Identify strategic areas for collection expansion based on your existing patterns.")
    
    # Gap analysis selector
    gap_type = st.selectbox(
        "Choose gap analysis type:",
        ["🎭 Artist Gaps", "🏷️ Label Gaps", "📅 Decade Coverage", "💿 Format Analysis"],
        help="Select which type of collection gap to analyze"
    )
    
    if gap_type == "🎭 Artist Gaps":
        _display_artist_gaps(db_conn)
    elif gap_type == "🏷️ Label Gaps":
        _display_label_gaps(db_conn)
    elif gap_type == "📅 Decade Coverage":
        _display_decade_gaps(db_conn)
    elif gap_type == "💿 Format Analysis":
        _display_format_gaps(db_conn)

def _display_artist_gaps(db_conn: PostgreSQLConnection):
    """Display missing albums from artists you already collect."""
    st.write("**🎤 Artists You Collect - Missing Albums**")
    st.caption("Find missing releases from artists where you already own 2+ albums.")
    
    from data.loaders import load_artist_gaps
    
    try:
        gaps_df = load_artist_gaps(db_conn, limit=15)
        
        if not gaps_df.empty:
            for idx, row in gaps_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        artist = row['artist']
                        completion = row['completion_percentage']
                        st.write(f"**🎵 {artist}**")
                        
                        # Progress bar for completion
                        progress_color = "🟢" if completion >= 75 else "🟡" if completion >= 50 else "🔴"
                        st.caption(f"{progress_color} {completion}% complete")
                        
                        # Show some missing years if available
                        missing_years = row.get('next_missing_years', [])
                        if missing_years and len(missing_years) > 0:
                            years_str = ', '.join([str(y) for y in missing_years[:3] if y])
                            if years_str:
                                st.caption(f"📅 Missing from: {years_str}")
                    
                    with col2:
                        owned = row['owned_releases']
                        missing = row['missing_count']
                        st.metric("Owned", f"{owned:,}")
                        st.metric("Missing", f"{missing:,}", delta=f"-{missing}")
                    
                    with col3:
                        total = row['total_releases']
                        st.metric("Total", f"{total:,}")
                        
                        # Priority indicator
                        if completion >= 75:
                            st.success("🔥 Nearly Complete!")
                        elif completion >= 50:
                            st.info("📈 Good Progress")
                        else:
                            st.warning("🎯 Early Stage")
                    
                    st.divider()
        else:
            st.info("🎉 Great! No significant artist gaps found, or not enough discography data available.")
            
    except Exception as e:
        st.error(f"Error analyzing artist gaps: {e}")

def _display_label_gaps(db_conn: PostgreSQLConnection):
    """Display labels you collect and their potential."""
    st.write("**🏷️ Label Collection Analysis**")
    st.caption("Discover labels you're already invested in and might want to explore further.")
    
    from data.loaders import load_label_gaps
    
    try:
        labels_df = load_label_gaps(db_conn, limit=12)
        
        if not labels_df.empty:
            for idx, row in labels_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        label = row['label']
                        status = row['collection_status']
                        st.write(f"**🏷️ {label}**")
                        st.caption(status)
                    
                    with col2:
                        releases = row['owned_releases']
                        artists = row['unique_artists']
                        st.metric("Releases", f"{releases:,}")
                        st.metric("Artists", f"{artists:,}")
                    
                    with col3:
                        avg_rating = row['avg_rating']
                        if pd.notna(avg_rating) and avg_rating > 0:
                            st.metric("Avg Rating", f"⭐ {avg_rating:.1f}")
                            
                            if avg_rating >= 4.0:
                                st.success("🔥 Love This Label!")
                            elif avg_rating >= 3.5:
                                st.info("👍 Quality Label")
                        else:
                            st.metric("Avg Rating", "Not rated")
                    
                    st.divider()
        else:
            st.info("No significant label patterns found yet. Keep building your collection!")
            
    except Exception as e:
        st.error(f"Error analyzing labels: {e}")

def _display_decade_gaps(db_conn: PostgreSQLConnection):
    """Display decade coverage analysis."""
    st.write("**📅 Decade Coverage Analysis**")
    st.caption("See which decades are well-covered and which have opportunities for growth.")
    
    from data.loaders import load_decade_gaps
    
    try:
        decades_df = load_decade_gaps(db_conn)
        
        if not decades_df.empty:
            for idx, row in decades_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 2])
                    
                    with col1:
                        decade = row['decade_label']
                        status = row['status']
                        st.write(f"**📅 {decade}**")
                        st.caption(status)
                    
                    with col2:
                        releases = row['releases_owned']
                        unique_years = row['unique_years']
                        st.metric("Releases", f"{releases:,}")
                        st.metric("Years Covered", f"{unique_years}")
                    
                    with col3:
                        coverage = row['coverage_percentage']
                        year_span = row['year_span']
                        
                        # Progress bar visualization
                        st.metric(
                            "Coverage", 
                            f"{coverage:.1f}%", 
                            delta=f"{unique_years}/{year_span} years"
                        )
                        
                        # Visual progress bar
                        progress = min(coverage / 100.0, 1.0)
                        st.progress(progress)
                        
                        if coverage >= 80:
                            st.success("✅ Well Covered")
                        elif coverage >= 50:
                            st.info("📈 Growing")
                        else:
                            st.warning("🎯 Opportunity")
                    
                    st.divider()
        else:
            st.info("Not enough data for decade analysis.")
            
    except Exception as e:
        st.error(f"Error analyzing decades: {e}")

def _display_format_gaps(db_conn: PostgreSQLConnection):
    """Display format distribution analysis."""
    st.write("**💿 Format Collection Analysis**")
    st.caption("Understand your format preferences and potential areas to explore.")
    
    from data.loaders import load_format_gaps
    
    try:
        formats_df = load_format_gaps(db_conn)
        
        if not formats_df.empty:
            st.write("**Your Format Distribution:**")
            
            # Create format cards
            cols = st.columns(min(3, len(formats_df)))
            
            for idx, row in formats_df.iterrows():
                col_idx = idx % 3
                with cols[col_idx]:
                    format_name = row['format']
                    count = row['count']
                    unique_artists = row['unique_artists']
                    avg_rating = row.get('avg_rating', 0)
                    
                    # Format emoji mapping
                    format_emoji = {
                        'Vinyl': '💿',
                        'LP': '💿', 
                        'CD': '💽',
                        'Cassette': '📼',
                        'Digital': '💻',
                        'SACD': '💿',
                        'DVD': '📀'
                    }
                    
                    emoji = format_emoji.get(format_name, '🎵')
                    
                    with st.container():
                        st.write(f"**{emoji} {format_name}**")
                        st.metric("Releases", f"{count:,}")
                        st.metric("Artists", f"{unique_artists:,}")
                        
                        if pd.notna(avg_rating) and avg_rating > 0:
                            st.metric("Avg Rating", f"⭐ {avg_rating:.1f}")
                            
            # Format recommendations
            st.subheader("💡 Format Recommendations")
            
            vinyl_count = formats_df[formats_df['format'].str.contains('Vinyl|LP', case=False, na=False)]['count'].sum() if not formats_df.empty else 0
            cd_count = formats_df[formats_df['format'].str.contains('CD', case=False, na=False)]['count'].sum() if not formats_df.empty else 0
            cassette_count = formats_df[formats_df['format'].str.contains('Cassette', case=False, na=False)]['count'].sum() if not formats_df.empty else 0
            
            if vinyl_count > cd_count * 2:
                st.info("🎯 **Vinyl Collector** - You might enjoy exploring rare pressings and reissues")
            elif cd_count > vinyl_count * 2:
                st.info("🎯 **CD Enthusiast** - Consider exploring SACD and special editions")
            elif cassette_count > 10:
                st.info("🎯 **Format Diversity** - You appreciate multiple formats - great for completionist collecting!")
            else:
                st.info("🎯 **Balanced Collector** - Your format diversity gives you flexibility in the marketplace")
                
        else:
            st.info("Not enough format data for analysis.")
            
    except Exception as e:
        st.error(f"Error analyzing formats: {e}")

def _display_wantlist_budget(db_conn: PostgreSQLConnection):
    """Display wantlist items and budget planning tools."""
    st.subheader("💰 Wantlist & Budget Planning")
    st.caption("Track your wanted items with current pricing and plan your purchases strategically.")
    
    # Budget controls
    col1, col2 = st.columns([2, 1])
    with col1:
        max_budget = st.slider("💵 Budget Range", min_value=10, max_value=200, value=50, step=10)
        st.caption(f"Show items under ${max_budget}")
    
    with col2:
        show_available_only = st.checkbox("✅ Available Only", value=True, help="Only show currently available items")
    
    # Wantlist items
    from data.loaders import load_wantlist_items
    
    try:
        wantlist_df = load_wantlist_items(db_conn, limit=25)
        
        if not wantlist_df.empty:
            st.write(f"**🎯 Your Wantlist ({len(wantlist_df)} items)**")
            
            # Filter by budget and availability
            if show_available_only:
                wantlist_df = wantlist_df[wantlist_df['availability'] == True]
            
            # Filter by budget
            budget_filtered = wantlist_df[
                (wantlist_df['lowest_price'] <= max_budget) | 
                (wantlist_df['lowest_price'].isna())
            ]
            
            if not budget_filtered.empty:
                for idx, row in budget_filtered.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            title = row['title']
                            artist = row['artist']
                            year = row.get('year', '')
                            label = row.get('label', '')
                            
                            st.write(f"**🎵 {title}**")
                            st.caption(f"👤 {artist}")
                            if year:
                                st.caption(f"📅 {year} • 🏷️ {label}")
                            
                            # Show user notes if any
                            notes = row.get('notes', '')
                            if notes:
                                st.caption(f"📝 {notes}")
                        
                        with col2:
                            price = row.get('lowest_price')
                            currency = row.get('currency', 'USD')
                            availability = row.get('availability', False)
                            
                            if pd.notna(price):
                                st.metric("Price", f"{currency} {price:.2f}")
                                
                                # Budget indicator
                                if price <= max_budget * 0.5:
                                    st.success("💚 Great Deal!")
                                elif price <= max_budget * 0.8:
                                    st.info("💙 Good Value")
                                else:
                                    st.warning("💛 Budget Limit")
                            else:
                                st.metric("Price", "Unknown")
                        
                        with col3:
                            num_for_sale = row.get('num_for_sale', 0)
                            
                            if availability:
                                st.success("✅ Available")
                                if num_for_sale > 0:
                                    st.metric("For Sale", f"{num_for_sale:,}")
                            else:
                                st.error("❌ Not Available")
                            
                            # Priority rating if user rated it
                            rating = row.get('rating')
                            if pd.notna(rating) and rating > 0:
                                st.metric("Priority", f"⭐ {rating}/5")
                        
                        st.divider()
                
                # Budget summary
                available_total = budget_filtered[budget_filtered['availability'] == True]['lowest_price'].sum()
                if pd.notna(available_total) and available_total > 0:
                    st.info(f"💰 **Total for available items in budget: ${available_total:.2f}**")
            else:
                st.info(f"No wantlist items found within your ${max_budget} budget.")
        else:
            st.info("🎯 No wantlist items found. Run the downloader with `--wantlist-only` to populate your wantlist.")
            st.caption("Your Discogs wantlist will be imported and tracked with current market prices.")
            
    except Exception as e:
        st.error(f"Error loading wantlist: {e}")

def _display_smart_recommendations(db_conn: PostgreSQLConnection):
    """Display intelligent purchase recommendations."""
    st.subheader("🎯 Smart Recommendations")
    st.caption("AI-powered suggestions based on your collection patterns and preferences.")
    
    # Recommendation controls
    max_price = st.slider("💵 Maximum Price", min_value=10, max_value=100, value=30, step=5)
    
    from data.loaders import load_budget_recommendations
    
    try:
        recs_df = load_budget_recommendations(db_conn, max_price=max_price, limit=15)
        
        if not recs_df.empty:
            st.write(f"**🎯 Recommended Releases (Under ${max_price})**")
            
            for idx, row in recs_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        title = row['title']
                        artist = row['artist']
                        year = row.get('year', '')
                        label = row.get('label', '')
                        
                        st.write(f"**🎵 {title}**")
                        st.caption(f"👤 {artist}")
                        if year:
                            st.caption(f"📅 {year} • 🏷️ {label}")
                    
                    with col2:
                        price = row.get('lowest_price', 0)
                        currency = row.get('currency', 'USD')
                        community_rating = row.get('community_average_rating', 0)
                        
                        st.metric("Price", f"{currency} {price:.2f}")
                        
                        if community_rating and community_rating > 0:
                            stars = "⭐" * min(5, int(community_rating))
                            st.caption(f"{stars} {community_rating:.1f}")
                    
                    with col3:
                        have_count = row.get('community_have_count', 0)
                        want_count = row.get('community_want_count', 0)
                        
                        if have_count > 0:
                            st.metric("Have", f"{have_count:,}")
                        if want_count > 0:
                            st.metric("Want", f"{want_count:,}")
                        
                        # Popularity indicator
                        if want_count > have_count * 0.1:
                            st.info("🔥 High Demand")
                        elif have_count > 1000:
                            st.success("👥 Popular")
                    
                    st.divider()
        else:
            st.info(f"No recommendations found under ${max_price}. Try increasing your budget or check back after running price updates.")
            
    except Exception as e:
        st.error(f"Error loading recommendations: {e}")

def _display_missing_remixes(db_conn: PostgreSQLConnection):
    """Display recommendations for missing remix versions and producer catalogs."""
    st.subheader("🎛️ Missing Remix & Version Recommendations")
    st.caption("Discover missing remix versions from artists and producers you already collect.")
    
    # Control panel
    col1, col2 = st.columns([2, 1])
    
    with col1:
        recommendation_type = st.selectbox(
            "Recommendation Type:",
            ["🎤 Missing Artist Remixes", "🎛️ Producer Catalogs", "🔥 Popular Missing Versions"],
            help="Choose what type of remix recommendations to see"
        )
    
    with col2:
        max_budget = st.slider("💵 Budget Range", min_value=10, max_value=100, value=30, step=5)
    
    try:
        if recommendation_type == "🎤 Missing Artist Remixes":
            _display_missing_artist_remixes(db_conn, max_budget)
        elif recommendation_type == "🎛️ Producer Catalogs":
            _display_missing_producer_catalogs(db_conn, max_budget) 
        else:  # Popular Missing Versions
            _display_popular_missing_versions(db_conn, max_budget)
            
    except Exception as e:
        st.error(f"Error loading remix recommendations: {e}")

def _display_missing_artist_remixes(db_conn: PostgreSQLConnection, max_budget: float):
    """Show missing remixes from artists you already collect."""
    st.write("**🎤 Missing Artist Remixes**")
    st.caption("Find remix singles and versions from artists in your collection that you don't own yet.")
    
    try:
        # Find artists you collect who have remixes you might be missing
        artist_remixes_query = """
        WITH collected_artists AS (
            SELECT DISTINCT artist, COUNT(*) as owned_releases
            FROM releases 
            WHERE artist IS NOT NULL
            AND artist NOT IN ('Various', 'Various Artists', 'VA')
            GROUP BY artist
            HAVING COUNT(*) >= 2  -- Artists with 2+ releases
        ),
        artist_remix_activity AS (
            SELECT 
                r.artist,
                COUNT(DISTINCT t.track_id) as remix_tracks,
                STRING_AGG(DISTINCT extraartist->>'name', ', ') as remixers
            FROM releases r
            JOIN tracks t ON r.release_id = t.release_id
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(t.extraartists, '[]'::jsonb)) AS extraartist
            WHERE t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb
            AND extraartist->>'name' IS NOT NULL
            GROUP BY r.artist
        )
        SELECT 
            ca.artist,
            ca.owned_releases,
            ara.remix_tracks,
            ara.remixers
        FROM collected_artists ca
        JOIN artist_remix_activity ara ON ca.artist = ara.artist
        WHERE ara.remix_tracks >= 3  -- Artists with significant remix activity
        ORDER BY ara.remix_tracks DESC, ca.owned_releases DESC
        LIMIT 15
        """
        
        result = db_conn.execute_query(artist_remixes_query)
        if result:
            artists_df = pd.DataFrame(result)
            
            st.write(f"**🎯 {len(artists_df)} artists in your collection have remix versions to explore:**")
            
            for idx, row in artists_df.iterrows():
                artist = row['artist']
                owned_releases = row['owned_releases']
                remix_tracks = row['remix_tracks']
                remixers = row.get('remixers', '')[:100]  # Truncate long remixer lists
                
                with st.expander(f"🎤 **{artist}** - {remix_tracks} remix tracks"):
                    remix_col1, remix_col2 = st.columns([3, 1])
                    
                    with remix_col1:
                        st.write(f"**You own:** {owned_releases} releases")
                        st.write(f"**Remix tracks found:** {remix_tracks}")
                        if remixers:
                            st.caption(f"🎛️ **Key remixers:** {remixers}...")
                        
                        st.info(f"💡 **Recommendation:** Search Discogs for '{artist} remix' or '{artist} 12\"' to find singles and remix compilations you might be missing.")
                    
                    with remix_col2:
                        if remix_tracks >= 10:
                            st.success("🔥 Remix Heavy")
                        elif remix_tracks >= 5:
                            st.info("🎛️ Active Remixer")
                        else:
                            st.caption("📻 Some Remixes")
        else:
            st.info("No significant remix activity found for your collected artists.")
            
    except Exception as e:
        st.error(f"Error analyzing missing artist remixes: {e}")

def _display_missing_producer_catalogs(db_conn: PostgreSQLConnection, max_budget: float):
    """Show missing releases from producers/remixers you already have."""
    st.write("**🎛️ Producer Catalog Gaps**")
    st.caption("Explore more releases from remixers and producers already in your collection.")
    
    try:
        # Find producers/remixers you have and suggest more of their work
        producer_gaps_query = """
        WITH your_producers AS (
            SELECT 
                extraartist->>'name' as producer_name,
                extraartist->>'role' as producer_role,
                COUNT(DISTINCT r.release_id) as releases_with_producer
            FROM releases r
            JOIN tracks t ON r.release_id = t.release_id
            CROSS JOIN LATERAL jsonb_array_elements(COALESCE(t.extraartists, '[]'::jsonb)) AS extraartist
            WHERE t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb
            AND extraartist->>'name' IS NOT NULL
            AND (
                lower(extraartist->>'role') LIKE '%remix%'
                OR lower(extraartist->>'role') LIKE '%producer%'
                OR lower(extraartist->>'role') LIKE '%mix%'
            )
            GROUP BY extraartist->>'name', extraartist->>'role'
            HAVING COUNT(DISTINCT r.release_id) >= 2  -- Producers on 2+ releases
        )
        SELECT 
            producer_name,
            producer_role,
            releases_with_producer
        FROM your_producers
        WHERE producer_name IS NOT NULL AND producer_name != ''
        ORDER BY releases_with_producer DESC
        LIMIT 12
        """
        
        result = db_conn.execute_query(producer_gaps_query)
        if result:
            producers_df = pd.DataFrame(result)
            
            st.write(f"**🎛️ Expand catalogs from {len(producers_df)} producers you already collect:**")
            
            # Display in grid
            cols = st.columns(2)
            for idx, row in producers_df.iterrows():
                with cols[idx % 2]:
                    producer_name = row['producer_name']
                    producer_role = row['producer_role']
                    release_count = row['releases_with_producer']
                    
                    with st.container():
                        st.write(f"**🎛️ {producer_name}**")
                        st.caption(f"{producer_role}")
                        
                        prod_col1, prod_col2 = st.columns([2, 1])
                        with prod_col1:
                            st.metric("In Collection", f"{release_count}")
                        with prod_col2:
                            if release_count >= 5:
                                st.success("🔥 Key Producer")
                            elif release_count >= 3:
                                st.info("🎛️ Regular")
                            else:
                                st.caption("📻 Occasional")
                        
                        st.info(f"💡 Search for more '{producer_name}' remixes and productions under ${max_budget}")
                        st.divider()
        else:
            st.info("No significant producer patterns found in your collection.")
            
    except Exception as e:
        st.error(f"Error analyzing producer catalogs: {e}")

def _display_popular_missing_versions(db_conn: PostgreSQLConnection, max_budget: float):
    """Show popular remix versions that might be missing from collection."""
    st.write("**🔥 Popular Missing Versions**")
    st.caption("Discover commonly collected remix versions and variants you might want to add.")
    
    try:
        # Show insights about remix version types to look for
        st.write("**💡 Common Remix Versions to Look For:**")
        
        version_types = [
            {
                "name": "12\" Extended Mixes", 
                "description": "Longer versions with extended intros/outros",
                "budget_tip": f"Often available under ${max_budget} for 90s house/dance",
                "search_terms": "12\", Extended, Club Mix"
            },
            {
                "name": "Dub Versions", 
                "description": "Instrumental or vocal-reduced versions", 
                "budget_tip": "Usually cheaper than vocal versions",
                "search_terms": "Dub, Instrumental, No Vocals"
            },
            {
                "name": "Radio Edits",
                "description": "Shorter versions for radio play",
                "budget_tip": "Often found on promotional releases",
                "search_terms": "Radio Edit, 7\", Promo"
            },
            {
                "name": "Remix Compilations", 
                "description": "Multiple remixer versions on one release",
                "budget_tip": "Great value for multiple versions",
                "search_terms": "Remixes, The Mixes, Remix Collection"
            }
        ]
        
        for version_type in version_types:
            with st.expander(f"🎛️ **{version_type['name']}**"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(version_type['description'])
                    st.caption(f"💰 {version_type['budget_tip']}")
                    st.caption(f"🔍 **Search terms:** {version_type['search_terms']}")
                
                with col2:
                    st.info("💡 Check your existing releases for these versions")
        
        # Show specific recommendations based on their collection
        st.markdown("---")
        st.write("**🎯 Personalized Version Recommendations:**")
        
        # Get genres from their collection to make targeted recommendations
        genre_query = """
        SELECT jsonb_array_elements_text(COALESCE(genres, '[]'::jsonb)) as genre, COUNT(*) as count
        FROM releases 
        WHERE genres IS NOT NULL
        GROUP BY genre
        ORDER BY count DESC
        LIMIT 5
        """
        
        genre_result = db_conn.execute_query(genre_query)
        if genre_result:
            genres_df = pd.DataFrame(genre_result)
            
            recommendations = []
            for _, row in genres_df.iterrows():
                genre = row['genre']
                count = row['count']
                
                if genre.lower() in ['electronic', 'house', 'techno', 'dance']:
                    recommendations.append(f"🎛️ **{genre}** ({count} releases): Look for 12\" singles with Club/Dub mixes under ${max_budget}")
                elif genre.lower() in ['hip hop', 'rap', 'hip-hop']:
                    recommendations.append(f"🎤 **{genre}** ({count} releases): Search for remix singles with Radio/Street versions")
                elif genre.lower() in ['pop', 'rock']:
                    recommendations.append(f"🎵 **{genre}** ({count} releases): Check for promotional CD singles with additional mixes")
                else:
                    recommendations.append(f"🎵 **{genre}** ({count} releases): Look for limited edition and promo versions")
            
            for rec in recommendations[:4]:  # Show top 4 recommendations
                st.write(f"- {rec}")
                
        st.markdown("---")
        st.info("💡 **Pro Tip**: Use your existing collection as a guide - if you own an album, search for the single versions which often have exclusive remixes!")
        
    except Exception as e:
        st.error(f"Error loading popular versions: {e}")

def _display_market_intelligence(db_conn: PostgreSQLConnection):
    """Display market data and trends."""
    st.subheader("📊 Market Intelligence")
    st.caption("Current market trends and pricing insights for strategic buying.")
    
    # This section would show market trends, price alerts, etc.
    st.info("🚧 **Coming Soon:** Market trend analysis, price drop alerts, and seasonal buying patterns.")
    
    # For now, show some basic market info
    st.write("**💡 Current Market Tips:**")
    
    tips = [
        "🎯 **End of Month**: Many sellers offer discounts to meet monthly goals",
        "📅 **Seasonal Patterns**: Vinyl prices often drop in January-February", 
        "🔍 **Condition Matters**: VG+ often offers the best value vs. Near Mint premiums",
        "⚡ **Quick Action**: Good deals on wantlist items usually sell within hours",
        "💰 **Bundle Opportunities**: Message sellers about multiple items for discounts"
    ]
    
    for tip in tips:
        st.write(f"- {tip}")
    
    st.divider()
    
    # Show some basic collection value info if available
    st.write("**📈 Your Collection Value Insights:**")
    
    try:
        value_query = """
        SELECT 
            COUNT(*) as total_releases,
            COUNT(CASE WHEN rp.lowest_price IS NOT NULL THEN 1 END) as priced_releases,
            AVG(rp.lowest_price) as avg_market_price,
            SUM(rp.lowest_price) as estimated_total_value
        FROM releases r
        LEFT JOIN release_prices rp ON r.discogs_id = rp.discogs_release_id
        """
        
        result = db_conn.execute_query(value_query)
        if result:
            data = result[0]
            total = data.get('total_releases', 0)
            priced = data.get('priced_releases', 0)
            avg_price = data.get('avg_market_price', 0)
            total_value = data.get('estimated_total_value', 0)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Items", f"{total:,}")
            
            with col2:
                if priced > 0:
                    coverage = (priced / total) * 100
                    st.metric("Price Coverage", f"{coverage:.1f}%")
                else:
                    st.metric("Price Coverage", "0%")
            
            with col3:
                if avg_price:
                    st.metric("Avg. Market Price", f"${avg_price:.2f}")
                else:
                    st.metric("Avg. Market Price", "Unknown")
            
            with col4:
                if total_value:
                    st.metric("Est. Collection Value", f"${total_value:,.2f}")
                else:
                    st.metric("Est. Collection Value", "Unknown")
                    
            if priced / total < 0.5:
                st.info("💡 Run price updates to get better market intelligence for your collection!")
                
    except Exception as e:
        st.warning(f"Could not load collection value data: {e}")

def _display_style_drill_for_genre(db_conn, genre, color_scheme):
    """Display styles breakdown for a selected genre."""
    st.subheader(f"🎨 Styles in Genre: {genre}")
    
    # Back button
    if st.button("← Back to Genres"):
        st.session_state.gs_view = 'overview'
        st.session_state.gs_selected_genre = None
        st.rerun()
    
    df = pd.DataFrame(load_styles_for_genre(db_conn, genre))
    if df.empty:
        st.warning(f"No styles found for genre '{genre}'")
        return
    
    # Create color map
    color_map = get_color_map(df['style'].tolist(), color_scheme)
    
    # Create go.Bar with colors (like decade/year fix)
    import plotly.graph_objects as go
    
    # Reset index and prepare data
    df_clean = df.reset_index(drop=True).copy()
    style_labels = df_clean['style'].tolist()
    colors = [color_map.get(label, '#1f77b4') for label in style_labels]
    
    fig = go.Figure(data=[
        go.Bar(
            x=style_labels,
            y=df_clean['release_count'].tolist(),
            name='Releases',
            marker=dict(color=colors)
        )
    ])
    fig.update_layout(
        title=f"Click a style to see releases in {genre}",
        showlegend=False,
        height=500
    )
    
    if plotly_events:
        clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key=f'style_drill_{genre}', override_height=500)
        if clicked:
            try:
                style = str(clicked[0].get('x'))
                st.session_state.gs_selected_style = style
                st.session_state.gs_view = 'releases'
                st.session_state.gs_page = 0
                st.rerun()
            except Exception:
                pass
    else:
        st.plotly_chart(fig, use_container_width=True)
        selected_style = st.selectbox("Select a style:", df['style'].tolist())
        if st.button("View Releases", key="style_drill_fallback"):
            st.session_state.gs_selected_style = selected_style
            st.session_state.gs_view = 'releases'
            st.rerun()
    
    # Show random sample with randomization button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"🎵 Random {genre} Albums")
    with col2:
        if st.button("🎲 Refresh", key=f"refresh_{genre}"):
            # Clear cache for this genre to force new random selection
            cache_key = f"genre_style_releases_{genre}_None"
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()
    
    _display_release_thumbnail_gallery(db_conn, genre=genre)

def _display_genre_drill_for_style(db_conn, style, color_scheme):
    """Display genres breakdown for a selected style."""
    st.subheader(f"🎵 Genres in Style: {style}")
    
    # Back button
    if st.button("← Back to Styles"):
        st.session_state.gs_view = 'overview'
        st.session_state.gs_selected_style = None
        st.rerun()
    
    df = pd.DataFrame(load_genres_for_style(db_conn, style))
    if df.empty:
        st.warning(f"No genres found for style '{style}'")
        return
    
    # Create color map
    color_map = get_color_map(df['genre'].tolist(), color_scheme)
    
    # Create go.Bar with colors (like decade/year fix)
    import plotly.graph_objects as go
    
    # Reset index and prepare data
    df_clean = df.reset_index(drop=True).copy()
    genre_labels = df_clean['genre'].tolist()
    colors = [color_map.get(label, '#1f77b4') for label in genre_labels]
    
    fig = go.Figure(data=[
        go.Bar(
            x=genre_labels,
            y=df_clean['release_count'].tolist(),
            name='Releases',
            marker=dict(color=colors)
        )
    ])
    fig.update_layout(
        title=f"Click a genre to see releases in {style}",
        showlegend=False,
        height=500
    )
    
    if plotly_events:
        clicked = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key=f'genre_drill_{style}', override_height=500)
        if clicked:
            try:
                genre = str(clicked[0].get('x'))
                st.session_state.gs_selected_genre = genre
                st.session_state.gs_view = 'releases'
                st.session_state.gs_page = 0
                st.rerun()
            except Exception:
                pass
    else:
        st.plotly_chart(fig, use_container_width=True)
        selected_genre = st.selectbox("Select a genre:", df['genre'].tolist())
        if st.button("View Releases", key="genre_drill_fallback"):
            st.session_state.gs_selected_genre = selected_genre
            st.session_state.gs_view = 'releases'
            st.rerun()
    
    # Show random sample with randomization button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"🎵 Random {style} Albums")
    with col2:
        if st.button("🎲 Refresh", key=f"refresh_{style}"):
            # Clear cache for this style to force new random selection
            cache_key = f"genre_style_releases_None_{style}"
            if cache_key in st.session_state:
                del st.session_state[cache_key]
            st.rerun()
    
    _display_release_thumbnail_gallery(db_conn, style=style)

def _display_releases_for_genre(db_conn, genre):
    """Display paginated releases for a selected genre."""
    st.subheader(f"📀 Releases in Genre: {genre}")
    
    # Controls (removed left back button as requested)
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("🎲 Randomize"):
            st.session_state.gs_random_seed += 1
            st.session_state.gs_page = 0
            st.rerun()
    
    # Load releases with pagination
    offset = st.session_state.gs_page * 20
    releases_df = load_releases_for_genre(db_conn, genre, offset=offset, limit=20, random_seed=st.session_state.gs_random_seed)
    
    if not releases_df.empty:
        st.write(f"Showing releases {offset + 1}-{offset + len(releases_df)}")
        
        # Convert releases_df to proper format for thumbnail gallery and pass it directly
        # This ensures pagination works and Details buttons show the correct releases
        thumbnail_df = _convert_releases_to_thumbnail_format(db_conn, releases_df)
        _display_release_thumbnail_gallery(releases_df=thumbnail_df)
        
        # Pagination
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.gs_page > 0:
                if st.button("⬅ Previous"):
                    st.session_state.gs_page -= 1
                    st.rerun()
        with col3:
            if len(releases_df) == 20:  # Assume more pages if we got full page
                if st.button("Next ➡"):
                    st.session_state.gs_page += 1
                    st.rerun()
        with col2:
            st.write(f"Page {st.session_state.gs_page + 1}")
    else:
        st.info("No releases found for this genre")

def _display_releases_for_style(db_conn, style):
    """Display paginated releases for a selected style."""
    st.subheader(f"📀 Releases in Style: {style}")
    
    # Controls (removed left back button as requested)
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("🎲 Randomize"):
            st.session_state.gs_random_seed += 1
            st.session_state.gs_page = 0
            st.rerun()
    
    # Load releases with pagination
    offset = st.session_state.gs_page * 20
    releases_df = load_releases_for_style(db_conn, style, offset=offset, limit=20, random_seed=st.session_state.gs_random_seed)
    
    if not releases_df.empty:
        st.write(f"Showing releases {offset + 1}-{offset + len(releases_df)}")
        
        # Convert releases_df to proper format for thumbnail gallery and pass it directly
        # This ensures pagination works and Details buttons show the correct releases
        thumbnail_df = _convert_releases_to_thumbnail_format(db_conn, releases_df)
        _display_release_thumbnail_gallery(releases_df=thumbnail_df)
        
        # Pagination
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.gs_page > 0:
                if st.button("⬅ Previous"):
                    st.session_state.gs_page -= 1
                    st.rerun()
        with col3:
            if len(releases_df) == 20:  # Assume more pages if we got full page
                if st.button("Next ➡"):
                    st.session_state.gs_page += 1
                    st.rerun()
        with col2:
            st.write(f"Page {st.session_state.gs_page + 1}")
    else:
        st.info("No releases found for this style")

def _convert_releases_to_thumbnail_format(db_conn, releases_df):
    """Convert paginated releases dataframe to thumbnail gallery format with artwork paths."""
    if releases_df.empty:
        return pd.DataFrame()
    
    # Get release IDs from the dataframe
    release_ids = releases_df['release_id'].tolist()
    
    # Query artwork for these specific releases
    placeholders = ','.join(['%s'] * len(release_ids))
    artwork_query = f"""
    SELECT a.local_file_path, a.thumbnail_file_path, a.original_url, 
           r.title, r.artist, r.year, r.label, r.release_id
    FROM artwork a
    JOIN releases r ON r.release_id = a.release_id
    WHERE a.image_type = 'primary'
        AND (a.local_file_path IS NOT NULL OR a.original_url IS NOT NULL)
        AND r.release_id IN ({placeholders})
    ORDER BY array_position(ARRAY[{placeholders}]::text[], r.release_id)
    """
    
    result = db_conn.execute_query(artwork_query, release_ids + release_ids)
    return pd.DataFrame(result) if result else pd.DataFrame()

def _display_releases_for_genre_and_style(db_conn, genre, style):
    """Display paginated releases for a selected genre AND style combination."""
    st.subheader(f"📀 Releases in {genre} + {style}")
    
    # Controls (removed left back button as requested)
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        if st.button("🎲 Randomize"):
            st.session_state.gs_random_seed += 1
            st.session_state.gs_page = 0
            st.rerun()
    
    # Load releases with pagination
    offset = st.session_state.gs_page * 20
    releases_df = load_releases_for_genre_and_style(db_conn, genre, style, offset=offset, limit=20, random_seed=st.session_state.gs_random_seed)
    
    if not releases_df.empty:
        st.write(f"Showing releases {offset + 1}-{offset + len(releases_df)}")
        
        # Convert releases_df to proper format for thumbnail gallery and pass it directly
        # This ensures pagination works and Details buttons show the correct releases
        thumbnail_df = _convert_releases_to_thumbnail_format(db_conn, releases_df)
        _display_release_thumbnail_gallery(releases_df=thumbnail_df)
        
        # Pagination
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.gs_page > 0:
                if st.button("⬅ Previous"):
                    st.session_state.gs_page -= 1
                    st.rerun()
        with col3:
            if len(releases_df) == 20:  # Assume more pages if we got full page
                if st.button("Next ➡"):
                    st.session_state.gs_page += 1
                    st.rerun()
        with col2:
            st.write(f"Page {st.session_state.gs_page + 1}")
    else:
        st.info("No releases found for this genre + style combination")


def _display_master_release_overview(db_conn: PostgreSQLConnection, sort_option: str):
    """Display master release overview with multiple versions."""
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
            WHEN %s = 'Most Versions Owned' THEN versions_owned
            WHEN %s = 'Most Duplicates' THEN duplicate_releases
            ELSE 0
        END DESC,
        CASE 
            WHEN %s = 'Fewest Versions Owned' THEN versions_owned
            WHEN %s = 'Alphabetical' THEN 0
            ELSE 999
        END ASC,
        CASE WHEN %s = 'Alphabetical' THEN master_title ELSE '' END
    LIMIT 50
    """
    
    try:
        df = pd.DataFrame(db_conn.execute_query(query, (sort_option, sort_option, sort_option, sort_option, sort_option)))
        
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
                # Fix size parameter to handle NaN values
                df_scatter = df.copy()
                df_scatter['size_value'] = df_scatter['avg_rating'].fillna(3.0)  # Default size for NaN ratings
                df_scatter['size_value'] = pd.to_numeric(df_scatter['size_value'], errors='coerce').fillna(3.0)
                
                fig = px.scatter(
                    df_scatter,
                    x='versions_owned',
                    y='total_copies',
                    size='size_value',
                    hover_data=['master_title', 'master_artist', 'formats_owned'],
                    title="Versions vs Total Copies",
                    labels={'versions_owned': 'Different Versions', 'total_copies': 'Total Copies'},
                    color='avg_rating',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Detailed display as cards
            st.subheader("Detailed Master Release Analysis")
            
            for idx, row in df.iterrows():
                with st.expander(f"🎵 {row['master_title']} - {row['master_artist']} ({row['versions_owned']} versions)"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Versions Owned", f"{row['versions_owned']:,}")
                        st.metric("Total Copies", f"{row['total_copies']:,}")
                    with col2:
                        st.metric("Duplicate Releases", f"{row['duplicate_releases']:,}")
                        if row['avg_rating'] and pd.notna(row['avg_rating']):
                            st.metric("Avg Rating", f"{row['avg_rating']:.1f}")
                    with col3:
                        st.write(f"**Formats:** {row['formats_owned']}")
                        st.write(f"**Countries:** {row['countries']}")
                        st.write(f"**Years:** {row['years']}")
                    
                    st.write("**Version Details:**")
                    st.caption(row['version_details'])
                    
    except Exception as e:
        st.error(f"Error loading master release data: {e}")

def _display_detailed_version_analysis(db_conn: PostgreSQLConnection):
    """Display detailed version breakdown for selected master release."""
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
    
    try:
        masters_df = pd.DataFrame(db_conn.execute_query(master_query))
        
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
                
                versions_df = pd.DataFrame(db_conn.execute_query(versions_query, (master_key,)))
                
                if not versions_df.empty:
                    st.write(f"**Found {len(versions_df)} versions of this album:**")
                    
                    # Display each version as a detailed card
                    for idx, version in versions_df.iterrows():
                        with st.container():
                            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
                            
                            with col1:
                                # Show thumbnail if available
                                thumb_url = version.get('thumbnail_url')
                                if thumb_url:
                                    try:
                                        st.image(thumb_url, use_container_width=USE_CONTAINER_WIDTH)
                                    except Exception:
                                        st.write("🎵")
                                else:
                                    st.write("🎵")
                            
                            with col2:
                                st.write(f"**{version['format']}** ({version['year'] or 'Unknown'})")
                                st.write(f"Label: {version['label'] or 'Unknown'}")
                                st.write(f"Cat#: {version['catno'] or 'Unknown'}")
                                st.write(f"Country: {version['country'] or 'Unknown'}")
                            
                            with col3:
                                st.write(f"Condition: {version['condition'] or 'Unknown'}")
                                st.write(f"Sleeve: {version['sleeve_condition'] or 'Unknown'}")
                                if version['rating']:
                                    st.write(f"Rating: {version['rating']}/5 ⭐")
                                st.write(f"Added: {version['date_added']}")
                            
                            with col4:
                                if version['discogs_id']:
                                    st.write(f"[View on Discogs](https://www.discogs.com/release/{version['discogs_id']})")
                                st.write(f"ID: {version['instance_id']}")
                            
                            if version.get('notes'):
                                st.write(f"**Notes:** {version['notes']}")
                            
                            st.divider()
    except Exception as e:
        st.error(f"Error loading version analysis: {e}")

def _display_remix_versions_analysis(db_conn: PostgreSQLConnection, sort_option: str):
    """Analyze and display remix versions across your collection."""
    st.subheader("🎛️ Remix Version Analysis")
    st.caption("Discover releases with multiple remix versions and identify missing variants.")
    
    try:
        # Query to find releases with multiple remix versions
        remix_versions_query = """
        WITH release_extraartists AS (
            SELECT 
                r.release_id,
                r.title,
                r.artist,
                r.year,
                r.label,
                r.format,
                t.track_id,
                t.title as track_title,
                remix_elem as extraartist
            FROM releases r
            JOIN tracks t ON r.release_id = t.release_id
            LEFT JOIN LATERAL jsonb_array_elements(COALESCE(t.extraartists, '[]'::jsonb)) AS remix_elem ON true
            WHERE t.extraartists IS NOT NULL 
                AND t.extraartists != '[]'::jsonb
        ),
        release_remixes AS (
            SELECT 
                release_id,
                title,
                artist,
                year,
                label,
                format,
                COUNT(DISTINCT track_id) as total_tracks,
                COUNT(DISTINCT extraartist) as remix_count,
                STRING_AGG(
                    DISTINCT (extraartist->>'name'), 
                    ', ' ORDER BY (extraartist->>'name')
                ) as remixers,
                array_agg(DISTINCT track_title) as track_titles
            FROM release_extraartists
            GROUP BY release_id, title, artist, year, label, format
            HAVING COUNT(DISTINCT extraartist) >= 2
        ),
        track_remix_details AS (
            SELECT 
                r.release_id,
                r.title as release_title,
                r.artist as release_artist,
                r.year,
                t.title as track_title,
                jsonb_array_elements(t.extraartists) as remix_credit
            FROM releases r
            JOIN tracks t ON r.release_id = t.release_id
            WHERE t.extraartists IS NOT NULL AND t.extraartists != '[]'::jsonb
        )
        SELECT 
            rr.*,
            COUNT(trd.release_id) as remix_credits_count
        FROM release_remixes rr
        LEFT JOIN track_remix_details trd ON rr.release_id = trd.release_id
        GROUP BY rr.release_id, rr.title, rr.artist, rr.year, rr.label, rr.format, 
                 rr.total_tracks, rr.remix_count, rr.remixers, rr.track_titles
        ORDER BY 
            CASE 
                WHEN %s = 'Most Versions Owned' THEN remix_count 
                ELSE 0 
            END DESC,
            CASE 
                WHEN %s = 'Alphabetical' THEN rr.artist 
                ELSE '' 
            END ASC,
            remix_count DESC
        LIMIT 50
        """
        
        results = db_conn.execute_query(remix_versions_query, (sort_option, sort_option))
        
        if results:
            remix_df = pd.DataFrame(results)
            
            st.write(f"**🎛️ Found {len(remix_df)} releases with multiple remix versions**")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_remix_releases = len(remix_df)
                st.metric("Multi-Remix Releases", f"{total_remix_releases}")
            
            with col2:
                avg_remixes = remix_df['remix_count'].mean() if not remix_df.empty else 0
                st.metric("Avg Remixes/Release", f"{avg_remixes:.1f}")
            
            with col3:
                top_remix_count = remix_df['remix_count'].max() if not remix_df.empty else 0
                st.metric("Most Remixed", f"{top_remix_count}")
            
            with col4:
                total_remixers = len(set(' '.join(remix_df['remixers'].fillna('').tolist()).split(', ')))
                st.metric("Unique Remixers", f"{total_remixers}")
            
            st.divider()
            
            # Detailed breakdown
            st.write("**📀 Remix Version Breakdown:**")
            
            for idx, row in remix_df.iterrows():
                with st.expander(f"🎛️ **{row['artist']} — {row['title']}** ({row['remix_count']} remix versions)"):
                    
                    remix_col1, remix_col2, remix_col3 = st.columns([2, 1, 1])
                    
                    with remix_col1:
                        st.write(f"**🎵 {row['title']}**")
                        st.caption(f"👤 {row['artist']}")
                        
                        # Show track titles if available
                        track_titles = row.get('track_titles', [])
                        if track_titles and len(track_titles) > 0:
                            # Clean up track titles
                            clean_titles = [t for t in track_titles if t and t != 'None'][:3]
                            if clean_titles:
                                st.caption(f"🎵 Tracks: {', '.join(clean_titles)}")
                        
                        # Show remixers
                        remixers = row.get('remixers', '')
                        if remixers:
                            st.caption(f"🎛️ Remixers: {remixers}")
                    
                    with remix_col2:
                        year = row.get('year', 'Unknown')
                        label = row.get('label', 'Unknown')
                        format_type = row.get('format', 'Unknown')
                        
                        st.metric("Year", str(year))
                        st.caption(f"🏷️ {label}")
                        st.caption(f"💿 {format_type}")
                    
                    with remix_col3:
                        remix_count = row['remix_count']
                        total_tracks = row['total_tracks']
                        
                        st.metric("Remix Versions", f"{remix_count}")
                        st.metric("Total Tracks", f"{total_tracks}")
                        
                        # Remix density indicator
                        remix_density = (remix_count / total_tracks) * 100 if total_tracks > 0 else 0
                        if remix_density >= 75:
                            st.success("🔥 Remix Heavy")
                        elif remix_density >= 50:
                            st.info("🎛️ Mixed Versions")
                        else:
                            st.caption("📻 Some Remixes")
                    
                    # Show potential missing versions insight
                    if remix_count >= 3:
                        st.info(f"💡 **Remix Classic**: This release has {remix_count} different remix versions - consider checking for additional variants!")
                    elif remix_count == 2:
                        st.info(f"🎯 **Dual Version**: Look for additional remixes by these producers or other versions of these tracks.")
        else:
            st.info("🎛️ No releases with multiple remix versions found.")
            st.caption("This analysis requires track data with extraartists information and multiple remix credits per release.")
        
        # Additional insights section
        st.markdown("---")
        st.write("**🧠 Remix Version Insights:**")
        
        insights = [
            "🎯 **12\" Singles** often contain multiple remix versions of the same track",
            "🎛️ **Popular tracks** from the 90s-2000s frequently have extensive remix catalogs",
            "💿 **Compilation albums** may include different versions than the original singles",
            "⚡ **Limited editions** and **promo releases** often feature exclusive remix versions",
            "🔍 **Check Discogs marketplace** for missing versions of your most remixed releases"
        ]
        
        for insight in insights:
            st.write(f"- {insight}")
            
    except Exception as e:
        st.error(f"Error loading remix versions analysis: {e}")

def _display_duplicate_detection_archive(db_conn: PostgreSQLConnection):
    """Display duplicate detection analysis using archive logic."""
    st.subheader("🔍 Duplicate Detection")
    
    duplicate_query = """
    SELECT 
        title, 
        artist, 
        COUNT(*) as version_count,
        STRING_AGG(DISTINCT format, ', ') as formats,
        STRING_AGG(DISTINCT country, ', ') as countries,
        MIN(year) as earliest_year,
        MAX(year) as latest_year,
        STRING_AGG(
            CONCAT(format, ' (', country, ', ', year, ')'), 
            ' | ' 
            ORDER BY year, format
        ) as version_list
    FROM releases
    WHERE title IS NOT NULL AND artist IS NOT NULL
    GROUP BY title, artist
    HAVING COUNT(*) > 1
    ORDER BY version_count DESC
    LIMIT 50
    """
    
    try:
        duplicate_df = pd.DataFrame(db_conn.execute_query(duplicate_query))
        if not duplicate_df.empty:
            st.write("Found potential duplicates or multiple versions:")
            
            for idx, row in duplicate_df.iterrows():
                with st.expander(f"🎵 {row['artist']} - {row['title']} ({row['version_count']} versions)"):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**Formats:** {row['formats']}")
                        st.write(f"**Countries:** {row['countries']}")
                        st.write(f"**Years:** {row['earliest_year']} - {row['latest_year']}")
                        st.write(f"**All Versions:** {row['version_list']}")
                    with col2:
                        st.metric("Total Versions", row['version_count'])
                        
        else:
            st.info("No potential duplicates found in your collection.")
    except Exception as e:
        st.error(f"Error checking duplicates: {e}")


def display_release_detail(db_conn: PostgreSQLConnection, release_id: str):
    """Display detailed view of a single release with full-size artwork navigation."""
    try:
        # Get release details
        release_query = """
        SELECT r.*, a.local_file_path, a.thumbnail_file_path, a.original_url, a.image_type
        FROM releases r
        LEFT JOIN artwork a ON r.release_id = a.release_id
        WHERE r.release_id = %s
        ORDER BY CASE WHEN a.image_type = 'primary' THEN 0 ELSE 1 END, a.image_type
        """
        
        results = db_conn.execute_query(release_query, (release_id,))
        if not results:
            st.error("Release not found")
            return
        
        # Group artwork by release
        release_data = results[0]
        artwork_files = []
        for row in results:
            if row.get('local_file_path') or row.get('original_url'):
                artwork_files.append({
                    'local_file_path': row.get('local_file_path'),
                    'thumbnail_file_path': row.get('thumbnail_file_path'),
                    'original_url': row.get('original_url'),
                    'image_type': row.get('image_type', 'unknown')
                })
        
        # Display release header with back button aligned to right edge of price stats
        header_col1, header_col2, header_col3, header_col4 = st.columns([1, 1, 1, 0.2])
        with header_col1:
            st.header(f"{release_data['artist']} - {release_data['title']}")
        with header_col2:
            st.write("")  # Empty space
        with header_col3:
            st.write("")  # Empty space
        with header_col4:
            st.write("")  # Add some vertical space
            # Determine return page from source_page parameter or default to Browse Collection
            source_page = st.query_params.get("source_page", "Browse Collection")
            if st.button("← Back", key="detail_back_button", help=f"Back to {source_page}"):
                # Clear release_id and source_page params, then set page appropriately
                del st.query_params["release_id"]
                if "source_page" in st.query_params:
                    del st.query_params["source_page"]
                st.session_state["selected_page"] = source_page
                st.rerun()
        
        # Release details in 3x2 grid layout
        col1, col2, col3 = st.columns(3)
        
        # Column 1: Label / Year
        with col1:
            st.write(f"**Label:** {release_data.get('label', 'Unknown')}")
            st.write(f"**Year:** {release_data.get('year', 'Unknown')}")
        
        # Column 2: Country / Format  
        with col2:
            country_flag, country_name = get_country_flag(release_data.get('country', 'Unknown'))
            st.markdown(f"""
            **Country:** <span title="{country_name}" style="font-size: 1.2em; cursor: pointer;">{country_flag}</span>
            """, unsafe_allow_html=True)
            st.write(f"**Format:** {release_data.get('format', 'Unknown')}")
        
        # Column 3: Price Stats
        with col3:
            # Get price statistics from release_prices table and marketplace_stats jsonb
            price_query = """
            SELECT 
                MIN(CASE WHEN rp.lowest_price > 0 THEN rp.lowest_price END) as min_price,
                MAX(rp.lowest_price) as max_price,
                AVG(CASE WHEN rp.lowest_price > 0 THEN rp.lowest_price END) as avg_price,
                COUNT(CASE WHEN rp.lowest_price > 0 THEN 1 END) as sales_count,
                r.marketplace_stats
            FROM collection_data.releases r
            LEFT JOIN collection_data.release_prices rp ON r.discogs_id = rp.discogs_release_id
            WHERE r.release_id = %s
            GROUP BY r.marketplace_stats
            """
            
            try:
                price_stats = db_conn.execute_query(price_query, (release_id,))
                if price_stats and price_stats[0]:
                    stats = price_stats[0]
                    
                    # Check if we have data from release_prices table
                    if stats.get('sales_count') and stats['sales_count'] > 0:
                        min_price = stats['min_price'] or 0
                        max_price = stats['max_price'] or 0
                        avg_price = stats['avg_price'] or 0
                        sales_count = stats['sales_count'] or 0
                        
                        st.write(f"**Low:** ${min_price:.2f}")
                        st.write(f"**High:** ${max_price:.2f}")
                        if sales_count > 1:
                            st.caption(f"Avg: ${avg_price:.2f} ({sales_count} listings)")
                        else:
                            st.caption(f"({sales_count} listing)")
                    
                    # Check marketplace_stats JSON as fallback
                    elif stats.get('marketplace_stats'):
                        marketplace_data = stats['marketplace_stats']
                        if isinstance(marketplace_data, dict):
                            lowest_price_data = marketplace_data.get('lowest_price', {})
                            if isinstance(lowest_price_data, dict) and 'value' in lowest_price_data:
                                price_value = lowest_price_data['value']
                                currency = lowest_price_data.get('currency', 'USD')
                                num_for_sale = marketplace_data.get('num_for_sale', 0)
                                
                                st.write(f"**Current Low:** ${price_value:.2f}")
                                if num_for_sale:
                                    st.caption(f"({num_for_sale} for sale)")
                                else:
                                    st.caption("(marketplace data)")
                            else:
                                st.write("**Price Stats**")
                                st.caption("No current data")
                        else:
                            st.write("**Price Stats**")
                            st.caption("No current data")
                    else:
                        st.write("**Price Stats**")
                        st.caption("No sales data")
                else:
                    st.write("**Price Stats**")
                    st.caption("No sales data")
            except Exception as e:
                st.write("**Price Stats**")
                st.caption("No sales data")
        
        # Additional row for Rating and Date Added
        if release_data.get('rating') or release_data.get('collection_date_added'):
            st.markdown("---")
            extra_col1, extra_col2, extra_col3 = st.columns(3)
            with extra_col1:
                if release_data.get('rating'):
                    st.write(f"**Rating:** ⭐ {release_data['rating']}/5")
            with extra_col2:
                if release_data.get('collection_date_added'):
                    st.write(f"**Added:** {release_data['collection_date_added']}")
            # extra_col3 left empty for balance
        
        st.markdown("---")
        
        # Main content: Tracks on left, Artwork on right
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Tracks section
            tracks_query = """
            SELECT * FROM tracks 
            WHERE release_id = %s 
            ORDER BY 
                CASE 
                    WHEN track_number ~ '^[0-9]+$' THEN track_number::int
                    ELSE 999
                END,
                track_number
            """
            tracks = db_conn.execute_query(tracks_query, (release_id,))
            
            if tracks:
                st.subheader(f"📀 Tracklist ({len(tracks)} tracks)")
                for track in tracks:
                    track_col1, track_col2, track_col3 = st.columns([1, 3, 1])
                    with track_col1:
                        st.write(f"**{track.get('track_number', '')}**")
                    with track_col2:
                        st.write(track.get('title', 'Unknown Title'))
                    with track_col3:
                        if track.get('duration'):
                            st.write(track['duration'])
            
            # Notes section if available
            if release_data.get('notes'):
                st.markdown("---")
                st.subheader("📝 Notes")
                st.write(release_data['notes'])
        
        with col2:
            # Artwork navigation
            if artwork_files:
                st.subheader("Artwork")
                
                # Initialize artwork index in session state
                artwork_key = f"detail_artwork_index_{release_id}"
                if artwork_key not in st.session_state:
                    st.session_state[artwork_key] = 0
                
                current_index = st.session_state[artwork_key]
                current_artwork = artwork_files[current_index]
                
                # Navigation controls for multiple images
                if len(artwork_files) > 1:
                    nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                    
                    with nav_col1:
                        if st.button("◀️", key="detail_prev_art", help="Previous image"):
                            st.session_state[artwork_key] = (current_index - 1) % len(artwork_files)
                            st.rerun()
                    
                    with nav_col2:
                        st.caption(f"📸 Image {current_index + 1} of {len(artwork_files)}")
                        image_type = current_artwork.get('image_type', 'Unknown')
                        if image_type != 'primary':
                            st.caption(f"Type: {image_type.title()}")
                    
                    with nav_col3:
                        if st.button("▶️", key="detail_next_art", help="Next image"):
                            st.session_state[artwork_key] = (current_index + 1) % len(artwork_files)
                            st.rerun()
                
                # Display full-size artwork
                full_size_path = current_artwork.get('local_file_path')
                if full_size_path:
                    try:
                        st.image(full_size_path, use_container_width=True)
                    except Exception:
                        # Fallback to original URL if local file fails
                        original_url = current_artwork.get('original_url')
                        if original_url:
                            try:
                                st.image(original_url, use_container_width=True)
                            except Exception:
                                st.write("🎵 Image not available")
                        else:
                            st.write("🎵 Image not available")
                elif current_artwork.get('original_url'):
                    try:
                        st.image(current_artwork['original_url'], use_container_width=True)
                    except Exception:
                        st.write("🎵 Image not available")
                else:
                    st.write("🎵 No artwork available")
            else:
                st.write("🎵 No artwork available")
        
    except Exception as e:
        st.error(f"Error loading release details: {e}")


