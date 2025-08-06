import streamlit as st
import snowflake.snowpark as snowpark
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.functions import *
import pandas as pd
import numpy as np
import pydeck as pdk
import json

def main():
    st.set_page_config(page_title="Ericsson Geospatial Analytics", layout="wide")
    
    st.title("🗺️ Ericsson Geospatial Analytics Dashboard")
    st.markdown("**Location Intelligence powered by Snowflake & Cortex AI**")
    
    # Get Snowflake session
    session = get_active_session()
    
    # Sidebar controls
    st.sidebar.header("📍 Analysis Controls")
    
    # Location type filter
    location_types = session.sql(f"""
        SELECT DISTINCT category 
        FROM ERICSSON_GEOSPATIAL_DEMO.LOCATIONS.tower_locations
    """).to_pandas()['CATEGORY'].tolist()
    
    selected_category = st.sidebar.selectbox(
        "Location Category:", 
        ['All'] + location_types
    )
    
    # Analysis radius
    analysis_radius = st.sidebar.slider(
        "Analysis Radius (km):", 
        min_value=1, 
        max_value=50, 
        value=10
    )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🌍 Interactive Location Map")
        
        # Build location query
        location_query = f"""
        SELECT 
            id,
            name,
            category,
            lat,
            lon,
            city,
            region,
            metadata:capacity::int as capacity,
            metadata:status::string as status
        FROM ERICSSON_GEOSPATIAL_DEMO.LOCATIONS.tower_locations
        """
        
        if selected_category != 'All':
            location_query += f" WHERE category = '{selected_category}'"
            
        locations_df = session.sql(location_query).to_pandas()
        
        if not locations_df.empty:
            # Create map layers
            locations_layer = pdk.Layer(
                'ScatterplotLayer',
                data=locations_df,
                get_position='[LON, LAT]',
                get_color='[200, 30, 0, 160]',
                get_radius=200,
                radius_scale=6,
                pickable=True,
                auto_highlight=True
            )
            
            # Map view
            view_state = pdk.ViewState(
                latitude=locations_df['LAT'].mean(),
                longitude=locations_df['LON'].mean(),
                zoom=9,
                pitch=0
            )
            
            # Render map
            map_chart = pdk.Deck(
                map_style='mapbox://styles/mapbox/light-v9',
                initial_view_state=view_state,
                layers=[locations_layer],
                tooltip={
                    'html': '<b>{{name}}</b><br/>Category: {{category}}<br/>Status: {{status}}<br/>Capacity: {{capacity}}',
                    'style': {
                        'backgroundColor': 'steelblue',
                        'color': 'white'
                    }
                }
            )
            
            st.pydeck_chart(map_chart)
            
            # Location statistics
            st.subheader("📊 Location Statistics")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                st.metric("Total Locations", len(locations_df))
            with col_b:
                active_count = len(locations_df[locations_df['STATUS'] == 'active'])
                st.metric("Active Locations", active_count)
            with col_c:
                avg_capacity = locations_df['CAPACITY'].mean()
                st.metric("Avg Capacity", f"{{avg_capacity:.0f}}")
            with col_d:
                unique_cities = locations_df['CITY'].nunique()
                st.metric("Cities Covered", unique_cities)
                
    with col2:
        st.subheader("🤖 AI Location Insights")
        
        if st.button("Generate Location Analysis", type="primary"):
            with st.spinner("Analyzing locations with Cortex AI..."):
                try:
                    # Create summary data for AI analysis
                    summary_query = f"""
                    SELECT 
                        category,
                        COUNT(*) as location_count,
                        AVG(metadata:capacity::int) as avg_capacity,
                        COUNT(CASE WHEN metadata:status::string = 'active' THEN 1 END) as active_count,
                        COUNT(DISTINCT city) as city_coverage
                    FROM ERICSSON_GEOSPATIAL_DEMO.LOCATIONS.tower_locations
                    GROUP BY category
                    """
                    
                    summary_df = session.sql(summary_query).to_pandas()
                    summary_json = summary_df.to_json(orient='records')
                    
                    # Generate AI insights
                    ai_query = f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'mixtral-8x7b',
                        'Analyze this Ericsson location data and provide 3 key insights and 2 recommendations. Data: ' || 
                        '{summary_json}' ||
                        ' Focus on operational efficiency, coverage optimization, and capacity utilization. Use bullet points and be concise.'
                    ) as insights
                    """
                    
                    ai_result = session.sql(ai_query).collect()
                    if ai_result:
                        st.markdown("### 💡 AI-Generated Insights")
                        st.write(ai_result[0]['INSIGHTS'])
                        
                except Exception as e:
                    st.error(f"AI analysis error: {{str(e)}}")
        
        st.subheader("🔍 Spatial Analysis Tools")
        
        # Distance analysis
        if st.button("Find Nearby Locations"):
            center_lat = locations_df['LAT'].mean()
            center_lon = locations_df['LON'].mean()
            
            nearby_query = f"""
            SELECT 
                name,
                city,
                ST_DISTANCE(
                    location_point,
                    ST_POINT({{center_lon}}, {{center_lat}})
                ) / 1000 as distance_km
            FROM ERICSSON_GEOSPATIAL_DEMO.LOCATIONS.tower_locations
            WHERE ST_DISTANCE(location_point, ST_POINT({{center_lon}}, {{center_lat}})) <= {{analysis_radius * 1000}}
            ORDER BY distance_km
            LIMIT 10
            """
            
            nearby_df = session.sql(nearby_query).to_pandas()
            st.dataframe(nearby_df, use_container_width=True)
        
        # Event analysis
        st.subheader("⚡ Recent Events")
        events_query = f"""
        SELECT 
            event_date,
            event_type,
            severity,
            COUNT(*) as event_count
        FROM ERICSSON_GEOSPATIAL_DEMO.LOCATIONS.location_events
        WHERE event_date >= DATEADD(day, -7, CURRENT_DATE())
        GROUP BY event_date, event_type, severity
        ORDER BY event_date DESC
        LIMIT 10
        """
        
        events_df = session.sql(events_query).to_pandas()
        if not events_df.empty:
            st.dataframe(events_df, use_container_width=True)
        else:
            st.write("No recent events found.")

if __name__ == "__main__":
    main()
