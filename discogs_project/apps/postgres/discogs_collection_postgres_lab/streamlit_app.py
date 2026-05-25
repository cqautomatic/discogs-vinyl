#!/usr/bin/env python3
"""
Modular Streamlit app for browsing Discogs collection.
This is the new, clean main application file using the modular architecture.
"""

import streamlit as st
import pandas as pd
import json

# Import modular components
from core.database import PostgreSQLConnection
from core.theme import apply_theme_css
from data.loaders import load_collection_stats
from data.performance import create_materialized_views, refresh_materialized_views
from views.collection_views import (
    display_enhanced_overview, display_browse_collection, display_genre_style_analysis,
    display_decade_timeline, display_collection_insights, display_community_statistics,
    display_deals, display_master_release_tracking, display_buying_guide, display_release_detail
)

# Page configuration
st.set_page_config(
    page_title="🎵 Discogs Collection Browser",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply theme CSS
apply_theme_css()

@st.cache_resource
def get_database_connection():
    """Get cached database connection."""
    return PostgreSQLConnection()

def main():
    """Main Streamlit app."""
    
    # Initialize database connection
    db_conn = get_database_connection()
    
    if not db_conn.connection:
        st.error("Cannot connect to database. Please check your configuration.")
        st.stop()
    
    # Check for detail view query parameters
    query_params = st.query_params
    release_id = query_params.get("release_id")
    
    if release_id:
        # Display detail view (back button is now inside the detail view)
        display_release_detail(db_conn, release_id)
        return
    
    # Normal main app view
    st.title("🎵 Discogs Collection Browser")
    
    # Create materialized views for performance optimization
    try:
        create_materialized_views(db_conn)
    except Exception:
        pass

    # Sidebar navigation
    st.sidebar.title("🎵 Navigation")
    
    # Get default page from session state or default to first option
    default_page = st.session_state.get("selected_page", "Enhanced Overview")
    page_options = [
        "Enhanced Overview",
        "Browse Collection", 
        "Genre & Style Analysis",
        "Decade Timeline",
        "Collection Insights", 
        "Community Statistics",
        "Deals",
        "Master Release Tracking",
        "Buying Guide",
        "Alerts"
    ]
    
    # Find index of default page
    try:
        default_index = page_options.index(default_page)
    except ValueError:
        default_index = 0
    
    page = st.sidebar.radio(
        "Choose a view:",
        page_options,
        index=default_index
    )
    
    # Update session state with current selection
    st.session_state["selected_page"] = page
    
    # Sidebar info and controls
    with st.sidebar:
        st.markdown("---")
        st.markdown("### About")
        st.markdown("Browse your Discogs collection with **interactive analytics** and **smart search**.")
        
        st.markdown("### Features")
        st.markdown("📊 **Enhanced Analytics** - Deep insights into your collection")
        st.markdown("🔍 **Smart Search** - Find releases by artist, title, or genre")
        st.markdown("📈 **Market Data** - Track values and community stats")
        
        st.markdown("### Data Controls")
        if st.button("🔄 Refresh Data Views"):
            with st.spinner("Refreshing materialized views..."):
                if refresh_materialized_views(db_conn):
                    st.success("✅ Data refreshed!")
                else:
                    st.error("❌ Refresh failed")
                    
        if st.button("🗑️ Clear Cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")
        
        st.markdown("---")
        st.markdown("*Built with Streamlit & PostgreSQL* 🐘")
    
    # Main content based on selected page
    if page == "Enhanced Overview":
        display_enhanced_overview(db_conn)
    elif page == "Browse Collection":
        display_browse_collection(db_conn)
    elif page == "Genre & Style Analysis":
        display_genre_style_analysis(db_conn)
    elif page == "Decade Timeline":
        display_decade_timeline(db_conn)
    elif page == "Collection Insights":
        display_collection_insights(db_conn)
    elif page == "Community Statistics":
        display_community_statistics(db_conn)
    elif page == "Deals":
        display_deals(db_conn)
    elif page == "Master Release Tracking":
        display_master_release_tracking(db_conn)
    elif page == "Buying Guide":
        display_buying_guide(db_conn)
    elif page == "Alerts":
        display_alerts_center(db_conn)

def display_alerts_center(db_conn):
    st.header("🔔 Alerts")
    st.info("Set up alerts for new releases by your favorite artists, labels, or genres.")
    
    tab1, tab2, tab3 = st.tabs(["Subscriptions", "Notifications", "Collection Watchlist"])
    
    with tab1:
        _display_subscriptions(db_conn)
    
    with tab2:
        _display_notifications(db_conn)
    
    with tab3:
        _display_collection_watchlist(db_conn)

def _display_subscriptions(db_conn):
    """Display and manage alert subscriptions."""
    st.subheader("📮 Alert Subscriptions")
    
    # Subscription form
    st.write("**Add New Subscription:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        sub_type = st.selectbox("Type", ["artist", "label", "style", "genre"], help="What type of alert do you want?") 
    with col2:
        subject = st.text_input("Subject (e.g., artist name)", placeholder="Miles Davis", help="Enter the exact name")
    with col3:
        if st.button("➕ Add Subscription") and subject:
            try:
                db_conn.execute_query(
                    "INSERT INTO alerts_subscription(type, subject_id, criteria_json) VALUES (%s, %s, %s)",
                    (sub_type, subject, "{}")
                )
                st.success(f"✅ Added {sub_type} alert for '{subject}'")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding subscription: {e}")
    
    # Display existing subscriptions
    try:
        subs = db_conn.execute_query("SELECT subscription_id, type, subject_id, active, created_at FROM alerts_subscription ORDER BY created_at DESC")
        if subs:
            st.write("**Your Active Subscriptions:**")
            subs_df = pd.DataFrame(subs)
            subs_df['created_at'] = pd.to_datetime(subs_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Display as nice cards instead of table
            for idx, row in subs_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        status = "🟢 Active" if row['active'] else "🔴 Inactive"
                        st.write(f"{status} **{row['type'].title()}**: {row['subject_id']}")
                        st.caption(f"Created: {row['created_at']}")
                    with col2:
                        if st.button("Toggle", key=f"toggle_{row['subscription_id']}"):
                            new_status = not row['active']
                            db_conn.execute_query(
                                "UPDATE alerts_subscription SET active = %s WHERE subscription_id = %s",
                                (new_status, row['subscription_id'])
                            )
                            st.rerun()
                    with col3:
                        if st.button("Delete", key=f"delete_{row['subscription_id']}"):
                            db_conn.execute_query(
                                "DELETE FROM alerts_subscription WHERE subscription_id = %s",
                                (row['subscription_id'],)
                            )
                            st.rerun()
                    st.divider()
        else:
            st.info("No subscriptions yet. Add your first alert above!")
    except Exception as e:
        st.error(f"Error loading subscriptions: {e}")

def _display_notifications(db_conn):
    """Display notifications and alerts."""
    st.subheader("🔔 Notifications")
    
    try:
        notes = db_conn.execute_query("SELECT notification_id, type, payload_json, created_at, seen FROM notifications ORDER BY created_at DESC LIMIT 200")
        if notes:
            notes_df = pd.DataFrame(notes)
            notes_df['created_at'] = pd.to_datetime(notes_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            
            # Show counts
            col1, col2, col3 = st.columns(3)
            with col1:
                total_notes = len(notes_df)
                st.metric("Total Notifications", total_notes)
            with col2:
                unseen_count = len(notes_df[~notes_df['seen']])
                st.metric("Unread", unseen_count)
            with col3:
                if unseen_count > 0 and st.button("📖 Mark All as Read"):
                    db_conn.execute_query("UPDATE notifications SET seen=TRUE WHERE seen=FALSE")
                    st.success("All notifications marked as read")
                    st.rerun()
            
            # Display notifications
            st.write("**Recent Notifications:**")
            for idx, row in notes_df.iterrows():
                status_icon = "📩" if not row['seen'] else "📧"
                with st.expander(f"{status_icon} {row['type'].title()} - {row['created_at']}"):
                    try:
                        payload = json.loads(row['payload_json']) if isinstance(row['payload_json'], str) else row['payload_json']
                        st.json(payload)
                    except:
                        st.write(row['payload_json'])
                    
                    if not row['seen']:
                        if st.button("Mark as Read", key=f"read_{row['notification_id']}"):
                            db_conn.execute_query(
                                "UPDATE notifications SET seen=TRUE WHERE notification_id = %s",
                                (row['notification_id'],)
                            )
                            st.rerun()
        else:
            st.info("No notifications yet. Set up some subscriptions to start receiving alerts!")
    except Exception as e:
        st.error(f"Error loading notifications: {e}")

def _display_collection_watchlist(db_conn):
    """Display collection watchlist and price tracking."""
    st.subheader("👀 Collection Watchlist")
    st.info("Track specific releases you want to buy and get notified about price changes.")
    
    # Add to watchlist form
    st.write("**Add Release to Watchlist:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        discogs_id = st.number_input("Discogs Release ID", min_value=1, help="Enter the Discogs release ID number")
    with col2:
        target_price = st.number_input("Target Price ($)", min_value=0.01, step=0.01, help="Get alerted when price drops below this")
    with col3:
        if st.button("➕ Add to Watchlist") and discogs_id:
            try:
                db_conn.execute_query(
                    "INSERT INTO watchlist(discogs_release_id, target_price, target_grade, region) VALUES (%s, %s, %s, %s) ON CONFLICT (discogs_release_id, user_id) DO UPDATE SET target_price = EXCLUDED.target_price",
                    (int(discogs_id), target_price, "VG+", "US")
                )
                st.success(f"✅ Added release {discogs_id} to watchlist")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding to watchlist: {e}")
    
    # Display watchlist
    try:
        watchlist = db_conn.execute_query("""
            SELECT w.discogs_release_id, w.target_price, w.target_grade, w.region, w.created_at,
                   r.title, r.artist, r.year, r.label
            FROM watchlist w
            LEFT JOIN releases r ON r.discogs_id = w.discogs_release_id
            WHERE w.active = TRUE
            ORDER BY w.created_at DESC
        """)
        
        if watchlist:
            st.write("**Your Watchlist:**")
            watchlist_df = pd.DataFrame(watchlist)
            watchlist_df['created_at'] = pd.to_datetime(watchlist_df['created_at']).dt.strftime('%Y-%m-%d')
            
            for idx, row in watchlist_df.iterrows():
                title = row.get('title', f'Release {row["discogs_release_id"]}')
                artist = row.get('artist', 'Unknown')
                with st.expander(f"🎵 {artist} - {title}"): 
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**Discogs ID:** {row['discogs_release_id']}")
                        if row.get('year'):
                            st.write(f"**Year:** {row['year']}")
                        if row.get('label'):
                            st.write(f"**Label:** {row['label']}")
                        st.write(f"**Target Price:** ${row['target_price']}")
                        st.write(f"**Added:** {row['created_at']}")
                    with col2:
                        if st.button("Remove", key=f"remove_watch_{row['discogs_release_id']}"):
                            db_conn.execute_query(
                                "UPDATE watchlist SET active = FALSE WHERE discogs_release_id = %s",
                                (row['discogs_release_id'],)
                            )
                            st.rerun()
        else:
            st.info("No items in your watchlist yet. Add some releases above!")
    except Exception as e:
        st.error(f"Error loading watchlist: {e}")

if __name__ == "__main__":
    main()
