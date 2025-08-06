#!/usr/bin/env python3
"""
Enhanced Snowflake Lab Generator Agent
Generates multiple types of company-branded Snowflake quickstart labs.
"""

import os
import re
import yaml
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class LabType(Enum):
    CORTEX_SEARCH = "cortex_search"
    CORTEX_ANALYST = "cortex_analyst" 
    GEOSPATIAL = "geospatial"
    RAG_ASSISTANT = "rag_assistant"
    DBT_INTEGRATION = "dbt_integration"
    ML_FEATURE_STORE = "ml_feature_store"
    DISCOGS_COLLECTION = "discogs_collection"

@dataclass
class LabConfig:
    company_name: str
    lab_types: List[LabType]
    industry: str
    use_case: str
    data_domain: str
    
class EnhancedSnowflakeAgent:
    def __init__(self):
        self.templates_dir = Path("enhanced_templates")
        self.output_dir = Path("generated_labs")
        self.industry_contexts = self._load_industry_contexts()
        
    def interactive_mode(self):
        """Interactive CLI for lab generation."""
        print("🚀 Enhanced Snowflake Lab Generator")
        print("=" * 50)
        
        # Get company name
        company_name = input("Enter company name: ").strip()
        if not company_name:
            company_name = "YourCompany"
            
        # Select industry
        industries = list(self.industry_contexts.keys())
        print(f"\nAvailable industries:")
        for i, industry in enumerate(industries, 1):
            print(f"{i}. {industry.replace('_', ' ').title()}")
        
        industry_choice = input(f"Select industry (1-{len(industries)}): ").strip()
        try:
            industry = industries[int(industry_choice) - 1]
        except (ValueError, IndexError):
            industry = 'generic'
            
        # Select lab types
        print(f"\nAvailable lab types:")
        lab_types = list(LabType)
        for i, lab_type in enumerate(lab_types, 1):
            print(f"{i}. {lab_type.value.replace('_', ' ').title()}")
            
        selections = input("Select lab types (comma-separated numbers, e.g., 1,2,3): ").strip()
        selected_labs = []
        
        try:
            for selection in selections.split(','):
                idx = int(selection.strip()) - 1
                if 0 <= idx < len(lab_types):
                    selected_labs.append(lab_types[idx])
        except ValueError:
            selected_labs = [LabType.CORTEX_SEARCH]  # Default
            
        if not selected_labs:
            selected_labs = [LabType.CORTEX_SEARCH]
            
        # Create config and generate
        config = LabConfig(
            company_name=company_name,
            lab_types=selected_labs,
            industry=industry,
            use_case=f"{company_name} Analytics Platform",
            data_domain=self.industry_contexts[industry]['primary_entity']
        )
        
        self.generate_labs(config)
        
    def generate_labs(self, config: LabConfig):
        """Generate all requested lab types."""
        print(f"\n🎯 Generating {len(config.lab_types)} lab(s) for {config.company_name}...")
        
        for lab_type in config.lab_types:
            if lab_type == LabType.CORTEX_SEARCH:
                self._generate_cortex_search_lab(config)
            elif lab_type == LabType.CORTEX_ANALYST:
                self._generate_cortex_analyst_lab(config)
            elif lab_type == LabType.GEOSPATIAL:
                self._generate_geospatial_lab(config)
            elif lab_type == LabType.RAG_ASSISTANT:
                self._generate_rag_assistant_lab(config)
            elif lab_type == LabType.DBT_INTEGRATION:
                self._generate_dbt_integration_lab(config)
            elif lab_type == LabType.ML_FEATURE_STORE:
                self._generate_ml_feature_store_lab(config)
            elif lab_type == LabType.DISCOGS_COLLECTION:
                self._generate_discogs_collection_lab(config)
                
        print(f"\n✨ All labs generated successfully!")
        print(f"📁 Check the '{self.output_dir}' directory")
        
    def _generate_geospatial_lab(self, config: LabConfig):
        """Generate geospatial analytics lab."""
        safe_name = self._sanitize_name(config.company_name)
        lab_dir = self.output_dir / f"{safe_name}_geospatial_lab"
        lab_dir.mkdir(parents=True, exist_ok=True)
        
        context = self.industry_contexts[config.industry]
        
        # README
        readme = self._create_geospatial_readme(config, context)
        (lab_dir / "README.md").write_text(readme)
        
        # Setup SQL
        setup_sql = self._create_geospatial_setup(config, context)
        (lab_dir / "setup.sql").write_text(setup_sql)
        
        # Streamlit App
        streamlit_app = self._create_geospatial_streamlit(config, context)
        (lab_dir / "streamlit_app.py").write_text(streamlit_app)
        
        # Sample data generation script
        data_gen = self._create_geospatial_data_generator(config, context)
        (lab_dir / "generate_sample_data.py").write_text(data_gen)
        
        print(f"✅ Generated Geospatial lab: {lab_dir}")
        
    def _generate_rag_assistant_lab(self, config: LabConfig):
        """Generate RAG-based LLM assistant lab."""
        safe_name = self._sanitize_name(config.company_name)
        lab_dir = self.output_dir / f"{safe_name}_rag_assistant_lab"
        lab_dir.mkdir(parents=True, exist_ok=True)
        
        context = self.industry_contexts[config.industry]
        
        # README
        readme = self._create_rag_readme(config, context)
        (lab_dir / "README.md").write_text(readme)
        
        # Setup SQL
        setup_sql = self._create_rag_setup(config, context)
        (lab_dir / "setup.sql").write_text(setup_sql)
        
        # Streamlit App with RAG
        streamlit_app = self._create_rag_streamlit(config, context)
        (lab_dir / "streamlit_app.py").write_text(streamlit_app)
        
        # Knowledge base documents
        docs_dir = lab_dir / "knowledge_base"
        docs_dir.mkdir(exist_ok=True)
        self._create_rag_knowledge_base(docs_dir, config, context)
        
        print(f"✅ Generated RAG Assistant lab: {lab_dir}")
        
    def _generate_dbt_integration_lab(self, config: LabConfig):
        """Generate dbt integration lab."""
        safe_name = self._sanitize_name(config.company_name)
        lab_dir = self.output_dir / f"{safe_name}_dbt_integration_lab"
        lab_dir.mkdir(parents=True, exist_ok=True)
        
        context = self.industry_contexts[config.industry]
        
        # README
        readme = self._create_dbt_readme(config, context)
        (lab_dir / "README.md").write_text(readme)
        
        # dbt project structure
        dbt_dir = lab_dir / "dbt_project"
        dbt_dir.mkdir(exist_ok=True)
        
        # dbt_project.yml
        dbt_project = self._create_dbt_project_yml(config, context)
        (dbt_dir / "dbt_project.yml").write_text(dbt_project)
        
        # Models
        models_dir = dbt_dir / "models"
        models_dir.mkdir(exist_ok=True)
        self._create_dbt_models(models_dir, config, context)
        
        # Setup SQL
        setup_sql = self._create_dbt_setup(config, context)
        (lab_dir / "setup.sql").write_text(setup_sql)
        
        print(f"✅ Generated dbt Integration lab: {lab_dir}")
        
    def _generate_ml_feature_store_lab(self, config: LabConfig):
        """Generate ML Feature Store lab."""
        safe_name = self._sanitize_name(config.company_name)
        lab_dir = self.output_dir / f"{safe_name}_ml_feature_store_lab"
        lab_dir.mkdir(parents=True, exist_ok=True)
        
        context = self.industry_contexts[config.industry]
        
        # README
        readme = self._create_ml_readme(config, context)
        (lab_dir / "README.md").write_text(readme)
        
        # Setup SQL with feature engineering
        setup_sql = self._create_ml_setup(config, context)
        (lab_dir / "setup.sql").write_text(setup_sql)
        
        # Python notebook for ML workflow
        notebook = self._create_ml_notebook(config, context)
        (lab_dir / "ml_workflow.py").write_text(notebook)
        
        # Streamlit App for model monitoring
        streamlit_app = self._create_ml_streamlit(config, context)
        (lab_dir / "streamlit_app.py").write_text(streamlit_app)
        
        print(f"✅ Generated ML Feature Store lab: {lab_dir}")
        
    def _create_geospatial_readme(self, config: LabConfig, context: Dict) -> str:
        return f"""# {config.company_name} Geospatial Analytics Lab

## Overview
Build location-intelligent applications for {config.company_name} using Snowflake's geospatial capabilities, Cortex AI, and Streamlit visualization.

## What You'll Learn
- Geospatial data analysis in Snowflake
- H3 hexagonal indexing for location analytics  
- Cortex LLMs for location insights
- Interactive mapping with Streamlit and Pydeck
- {config.company_name}-specific location intelligence

## Lab Architecture
```
┌─────────────────────────────────────┐
│        Snowflake Geospatial        │
│  ┌─────────────────────────────────┐│
│  │     Location Data Sources       ││
│  │  • {context['geo_data_1']}      ││
│  │  • {context['geo_data_2']}      ││
│  │  • Weather & Events Data       ││
│  └─────────────────────────────────┘│
│  ┌─────────────────────────────────┐│
│  │    Geospatial Functions        ││
│  │  • ST_DISTANCE, ST_INTERSECTS   ││
│  │  • H3 Indexing & Aggregation   ││
│  │  • Cortex Location Analysis    ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│     Streamlit + Pydeck Maps        │
│  • Interactive Location Dashboard  │
│  • Real-time Location Insights     │
│  • AI-Generated Recommendations    │
└─────────────────────────────────────┘
```

## Prerequisites
- Snowflake account with Cortex enabled
- Access to Snowflake Marketplace datasets
- Basic understanding of geospatial concepts

## Lab Steps

### Step 1: Environment Setup (3 minutes)
```sql
-- Execute setup.sql
-- Creates {config.company_name.upper()}_GEOSPATIAL_DEMO database
-- Sets up geospatial data tables and functions
```

### Step 2: Load Sample Location Data (5 minutes)
- Generate {context['locations_count']} sample {context['location_type']} locations
- Create boundary analysis for {config.company_name} operations
- Set up H3 hexagonal indexing for spatial aggregation

### Step 3: Geospatial Analysis (4 minutes)
```sql
-- Find locations within radius
-- Calculate distances and coverage areas
-- Perform spatial joins and aggregations
```

### Step 4: AI-Enhanced Location Insights (3 minutes)
- Use Cortex to generate location summaries
- Create intelligent location recommendations
- Generate geospatial reports and alerts

## Sample Analysis Queries
- "Find all {context['location_type']} within 5km of target location"
- "Identify coverage gaps in {config.company_name} service area"
- "Generate weather impact report for operational locations"
- "Recommend optimal locations for new {context['expansion_type']}"

## Expected Results
- Interactive geospatial dashboard
- AI-powered location intelligence
- Spatial analysis capabilities for {config.company_name}
"""

    def _create_geospatial_setup(self, config: LabConfig, context: Dict) -> str:
        return f"""-- {config.company_name} Geospatial Analytics Lab Setup

-- Create database and schema
CREATE OR REPLACE DATABASE {config.company_name.upper()}_GEOSPATIAL_DEMO;
CREATE OR REPLACE SCHEMA LOCATIONS;
USE DATABASE {config.company_name.upper()}_GEOSPATIAL_DEMO;
USE SCHEMA LOCATIONS;

-- Create location data table
CREATE OR REPLACE TABLE {context['location_type']}_locations (
    id INTEGER,
    name VARCHAR(100),
    category VARCHAR(50),
    lat FLOAT,
    lon FLOAT,
    location_point GEOGRAPHY,
    address VARCHAR(200),
    city VARCHAR(50),
    region VARCHAR(50),
    h3_index VARCHAR(20),
    metadata VARIANT
);

-- Create boundary table for analysis
CREATE OR REPLACE TABLE service_boundaries (
    boundary_id INTEGER,
    boundary_name VARCHAR(100),
    boundary_type VARCHAR(50),
    boundary_polygon GEOGRAPHY,
    h3_coverage ARRAY
);

-- Create events/incidents table
CREATE OR REPLACE TABLE location_events (
    event_id INTEGER,
    event_date DATE,
    event_time TIME,
    location_point GEOGRAPHY,
    event_type VARCHAR(50),
    severity VARCHAR(20),
    description VARCHAR(500),
    h3_index VARCHAR(20)
);

-- Insert sample location data
INSERT INTO {context['location_type']}_locations 
SELECT 
    ROW_NUMBER() OVER (ORDER BY RANDOM()) as id,
    '{config.company_name} ' || SUBSTR('ABCDEFGHIJKLMNOPQRSTUVWXYZ', UNIFORM(1, 26, RANDOM()), 1) || 
    UNIFORM(1, 999, RANDOM()) as name,
    '{context["primary_category"]}' as category,
    -- Generate coordinates within realistic bounds
    UNIFORM(40.0, 42.0, RANDOM()) as lat,
    UNIFORM(-74.5, -71.0, RANDOM()) as lon,
    ST_POINT(UNIFORM(-74.5, -71.0, RANDOM()), UNIFORM(40.0, 42.0, RANDOM())) as location_point,
    UNIFORM(1, 999, RANDOM()) || ' ' || 
    ARRAY_TO_STRING(ARRAY_CONSTRUCT('Main St', 'Oak Ave', 'Park Blvd', 'Center Dr')[UNIFORM(0, 3, RANDOM())], '') as address,
    ARRAY_TO_STRING(ARRAY_CONSTRUCT('Boston', 'Cambridge', 'Newton', 'Quincy')[UNIFORM(0, 3, RANDOM())], '') as city,
    ARRAY_TO_STRING(ARRAY_CONSTRUCT('North', 'South', 'East', 'West')[UNIFORM(0, 3, RANDOM())], '') as region,
    H3_POINT_TO_CELL_STRING(ST_POINT(UNIFORM(-74.5, -71.0, RANDOM()), UNIFORM(40.0, 42.0, RANDOM())), 8) as h3_index,
    OBJECT_CONSTRUCT(
        'capacity', UNIFORM(50, 500, RANDOM()),
        'status', IFF(UNIFORM(0, 1, RANDOM()) > 0.1, 'active', 'maintenance'),
        'priority', UNIFORM(1, 5, RANDOM())
    ) as metadata
FROM TABLE(GENERATOR(ROWCOUNT => {context['locations_count']}));

-- Update location_point and h3_index based on lat/lon
UPDATE {context['location_type']}_locations 
SET 
    location_point = ST_POINT(lon, lat),
    h3_index = H3_POINT_TO_CELL_STRING(ST_POINT(lon, lat), 8);

-- Create sample boundary data
INSERT INTO service_boundaries VALUES
(1, '{config.company_name} Primary Service Area', 'service_area', 
 ST_POLYGON('POLYGON((-74.5 40.0, -71.0 40.0, -71.0 42.0, -74.5 42.0, -74.5 40.0))'), 
 ARRAY_CONSTRUCT()),
(2, '{config.company_name} Emergency Zone', 'emergency', 
 ST_POLYGON('POLYGON((-74.0 40.5, -72.0 40.5, -72.0 41.5, -74.0 41.5, -74.0 40.5))'), 
 ARRAY_CONSTRUCT());

-- Create sample events
INSERT INTO location_events 
SELECT 
    ROW_NUMBER() OVER (ORDER BY RANDOM()) as event_id,
    DATEADD(day, -UNIFORM(0, 30, RANDOM()), CURRENT_DATE()) as event_date,
    TIME_FROM_PARTS(UNIFORM(6, 22, RANDOM()), UNIFORM(0, 59, RANDOM()), 0) as event_time,
    ST_POINT(UNIFORM(-74.5, -71.0, RANDOM()), UNIFORM(40.0, 42.0, RANDOM())) as location_point,
    ARRAY_TO_STRING(ARRAY_CONSTRUCT('maintenance', 'incident', 'upgrade', 'inspection')[UNIFORM(0, 3, RANDOM())], '') as event_type,
    ARRAY_TO_STRING(ARRAY_CONSTRUCT('low', 'medium', 'high', 'critical')[UNIFORM(0, 3, RANDOM())], '') as severity,
    'Automated event generated for {config.company_name} location monitoring' as description,
    H3_POINT_TO_CELL_STRING(ST_POINT(UNIFORM(-74.5, -71.0, RANDOM()), UNIFORM(40.0, 42.0, RANDOM())), 8) as h3_index
FROM TABLE(GENERATOR(ROWCOUNT => 100));

-- Create warehouse
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH 
WITH WAREHOUSE_SIZE = 'SMALL' 
     AUTO_SUSPEND = 300 
     AUTO_RESUME = TRUE;

-- Grant permissions
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PUBLIC;
GRANT ALL ON DATABASE {config.company_name.upper()}_GEOSPATIAL_DEMO TO ROLE PUBLIC;
GRANT ALL ON SCHEMA LOCATIONS TO ROLE PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA LOCATIONS TO ROLE PUBLIC;

-- Verify setup
SELECT 'Geospatial lab setup completed!' as status;
SELECT COUNT(*) as location_count FROM {context['location_type']}_locations;
SELECT COUNT(*) as event_count FROM location_events;
"""

    def _create_geospatial_streamlit(self, config: LabConfig, context: Dict) -> str:
        company_upper = config.company_name.upper()
        location_type = context['location_type']
        
        return f"""import streamlit as st
import snowflake.snowpark as snowpark
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.functions import *
import pandas as pd
import numpy as np
import pydeck as pdk
import json

def main():
    st.set_page_config(page_title="{config.company_name} Geospatial Analytics", layout="wide")
    
    st.title("🗺️ {config.company_name} Geospatial Analytics Dashboard")
    st.markdown("**Location Intelligence powered by Snowflake & Cortex AI**")
    
    # Get Snowflake session
    session = get_active_session()
    
    # Sidebar controls
    st.sidebar.header("📍 Analysis Controls")
    
    # Location type filter
    location_types = session.sql(f\"\"\"
        SELECT DISTINCT category 
        FROM {company_upper}_GEOSPATIAL_DEMO.LOCATIONS.{location_type}_locations
    \"\"\").to_pandas()['CATEGORY'].tolist()
    
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
        location_query = f\"\"\"
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
        FROM {company_upper}_GEOSPATIAL_DEMO.LOCATIONS.{location_type}_locations
        \"\"\"
        
        if selected_category != 'All':
            location_query += f" WHERE category = '{{selected_category}}'"
            
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
                tooltip={{
                    'html': '<b>{{{{name}}}}</b><br/>Category: {{{{category}}}}<br/>Status: {{{{status}}}}<br/>Capacity: {{{{capacity}}}}',
                    'style': {{
                        'backgroundColor': 'steelblue',
                        'color': 'white'
                    }}
                }}
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
                st.metric("Avg Capacity", f"{{{{avg_capacity:.0f}}}}")
            with col_d:
                unique_cities = locations_df['CITY'].nunique()
                st.metric("Cities Covered", unique_cities)
                
    with col2:
        st.subheader("🤖 AI Location Insights")
        
        if st.button("Generate Location Analysis", type="primary"):
            with st.spinner("Analyzing locations with Cortex AI..."):
                try:
                    # Create summary data for AI analysis
                    summary_query = f\"\"\"
                    SELECT 
                        category,
                        COUNT(*) as location_count,
                        AVG(metadata:capacity::int) as avg_capacity,
                        COUNT(CASE WHEN metadata:status::string = 'active' THEN 1 END) as active_count,
                        COUNT(DISTINCT city) as city_coverage
                    FROM {company_upper}_GEOSPATIAL_DEMO.LOCATIONS.{location_type}_locations
                    GROUP BY category
                    \"\"\"
                    
                    summary_df = session.sql(summary_query).to_pandas()
                    summary_json = summary_df.to_json(orient='records')
                    
                    # Generate AI insights
                    ai_query = f\"\"\"
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'mixtral-8x7b',
                        'Analyze this {config.company_name} location data and provide 3 key insights and 2 recommendations. Data: ' || 
                        '{{summary_json}}' ||
                        ' Focus on operational efficiency, coverage optimization, and capacity utilization. Use bullet points and be concise.'
                    ) as insights
                    \"\"\"
                    
                    ai_result = session.sql(ai_query).collect()
                    if ai_result:
                        st.markdown("### 💡 AI-Generated Insights")
                        st.write(ai_result[0]['INSIGHTS'])
                        
                except Exception as e:
                    st.error(f"AI analysis error: {{{{str(e)}}}}")
        
        st.subheader("🔍 Spatial Analysis Tools")
        
        # Distance analysis
        if st.button("Find Nearby Locations"):
            center_lat = locations_df['LAT'].mean()
            center_lon = locations_df['LON'].mean()
            
            nearby_query = f\"\"\"
            SELECT 
                name,
                city,
                ST_DISTANCE(
                    location_point,
                    ST_POINT({{{{center_lon}}}}, {{{{center_lat}}}})
                ) / 1000 as distance_km
            FROM {company_upper}_GEOSPATIAL_DEMO.LOCATIONS.{location_type}_locations
            WHERE ST_DISTANCE(location_point, ST_POINT({{{{center_lon}}}}, {{{{center_lat}}}})) <= {{{{analysis_radius * 1000}}}}
            ORDER BY distance_km
            LIMIT 10
            \"\"\"
            
            nearby_df = session.sql(nearby_query).to_pandas()
            st.dataframe(nearby_df, use_container_width=True)
        
        # Event analysis
        st.subheader("⚡ Recent Events")
        events_query = f\"\"\"
        SELECT 
            event_date,
            event_type,
            severity,
            COUNT(*) as event_count
        FROM {company_upper}_GEOSPATIAL_DEMO.LOCATIONS.location_events
        WHERE event_date >= DATEADD(day, -7, CURRENT_DATE())
        GROUP BY event_date, event_type, severity
        ORDER BY event_date DESC
        LIMIT 10
        \"\"\"
        
        events_df = session.sql(events_query).to_pandas()
        if not events_df.empty:
            st.dataframe(events_df, use_container_width=True)
        else:
            st.write("No recent events found.")

if __name__ == "__main__":
    main()
"""

    def _create_rag_readme(self, config: LabConfig, context: Dict) -> str:
        return f"""# {config.company_name} RAG Assistant Lab

## Overview
Build an intelligent question-answering assistant for {config.company_name} using Retrieval Augmented Generation (RAG) with Snowflake Cortex Search and LLMs.

## Architecture
```
┌─────────────────────────────────────┐
│        Knowledge Base              │
│  ┌─────────────────────────────────┐│
│  │    {config.company_name} Documents    ││
│  │  • Policies & Procedures        ││
│  │  • {context['doc_type_1']}      ││
│  │  • {context['doc_type_2']}      ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
           ↓ (Cortex Search)
┌─────────────────────────────────────┐
│       Vector Retrieval             │
│  • Semantic document search        │
│  • Context ranking & filtering     │
│  • Relevance scoring              │
└─────────────────────────────────────┘
           ↓ (Context + Query)
┌─────────────────────────────────────┐
│        Cortex LLM                  │
│  • Context-aware responses         │
│  • Company-specific knowledge      │
│  • Factual, grounded answers      │
└─────────────────────────────────────┘
```

## What You'll Learn
- RAG implementation with Snowflake Cortex
- Document vectorization and semantic search
- Context-aware LLM responses
- Building knowledge-grounded AI assistants

## Lab Steps

### Step 1: Knowledge Base Setup (5 minutes)
- Upload {config.company_name} documents to Snowflake stage
- Create vector embeddings with Cortex
- Set up semantic search indexes

### Step 2: RAG Pipeline (5 minutes)
- Implement retrieval component
- Design context injection for LLMs
- Create response generation pipeline

### Step 3: Interactive Assistant (5 minutes)
- Deploy Streamlit chat interface
- Test question-answering capabilities
- Validate response accuracy and relevance

## Sample Questions
- "What is {config.company_name}'s {context['policy_area']} policy?"
- "How do I {context['common_task']}?"
- "What are the requirements for {context['requirement_area']}?"
- "Explain {config.company_name}'s {context['process_area']} process"

## Expected Results
- Intelligent document-based Q&A system
- Accurate, contextual responses about {config.company_name}
- RAG pipeline understanding and implementation
"""

    def _create_rag_setup(self, config: LabConfig, context: Dict) -> str:
        return f"""-- {config.company_name} RAG Assistant Lab Setup

-- Create database and schema
CREATE OR REPLACE DATABASE {config.company_name.upper()}_RAG_DEMO;
CREATE OR REPLACE SCHEMA KNOWLEDGE;
USE DATABASE {config.company_name.upper()}_RAG_DEMO;
USE SCHEMA KNOWLEDGE;

-- Create stage for documents
CREATE OR REPLACE STAGE knowledge_docs_stage
  FILE_FORMAT = (TYPE = 'TEXT');

-- Create table for document chunks
CREATE OR REPLACE TABLE document_chunks (
    chunk_id INTEGER AUTOINCREMENT,
    document_name VARCHAR(500),
    chunk_text VARCHAR(8000),
    chunk_index INTEGER,
    metadata VARIANT,
    embedding VECTOR(FLOAT, 768)  -- Cortex embedding dimension
);

-- Create table for chat history
CREATE OR REPLACE TABLE chat_history (
    session_id VARCHAR(100),
    timestamp TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    user_query VARCHAR(4000),
    assistant_response VARCHAR(8000),
    context_used VARCHAR(8000),
    confidence_score FLOAT
);

-- Create Cortex Search application for RAG
CREATE OR REPLACE CORTEX SEARCH APPLICATION {config.company_name.upper()}_RAG_SEARCH
ON document_chunks
WAREHOUSE = COMPUTE_WH
ATTRIBUTES = (document_name, chunk_text)
SERVICE_NAME = '{config.company_name.lower()}_rag_search';

-- Create warehouse
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH 
WITH WAREHOUSE_SIZE = 'SMALL' 
     AUTO_SUSPEND = 300 
     AUTO_RESUME = TRUE;

-- Sample document processing function
CREATE OR REPLACE FUNCTION PROCESS_DOCUMENT(doc_content STRING, doc_name STRING)
RETURNS TABLE(chunk_text STRING, chunk_index INTEGER)
LANGUAGE PYTHON
RUNTIME_VERSION = '3.8'
HANDLER = 'DocumentProcessor'
AS $$
class DocumentProcessor:
    def process(self, doc_content, doc_name):
        # Simple text chunking - split into ~500 character chunks
        chunk_size = 500
        chunks = []
        
        words = doc_content.split()
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for word in words:
            if current_length + len(word) + 1 > chunk_size and current_chunk:
                chunks.append((' '.join(current_chunk), chunk_index))
                current_chunk = [word]
                current_length = len(word)
                chunk_index += 1
            else:
                current_chunk.append(word)
                current_length += len(word) + 1
        
        if current_chunk:
            chunks.append((' '.join(current_chunk), chunk_index))
            
        return chunks
$$;

-- Sample knowledge base content
INSERT INTO document_chunks (document_name, chunk_text, chunk_index, metadata)
VALUES
('{config.company_name}_company_overview.txt', 
 '{config.company_name} is a leading {context["industry"]} company focused on {context["mission"]}. Our core values include innovation, customer satisfaction, and operational excellence. We serve {context["customer_base"]} worldwide with {context["service_offering"]}.',
 0, 
 OBJECT_CONSTRUCT('category', 'overview', 'importance', 'high')),

('{config.company_name}_policies.txt',
 'Employee Policy Guidelines: All {config.company_name} employees must follow our code of conduct. Working hours are 9 AM to 5 PM. Remote work is available with manager approval. All communications should be professional and respectful.',
 0,
 OBJECT_CONSTRUCT('category', 'policies', 'importance', 'high')),

('{config.company_name}_procedures.txt',
 'Standard Operating Procedures: To {context["common_task"]}, employees should follow these steps: 1) Submit request through portal, 2) Await manager approval, 3) Complete required training, 4) Begin implementation. For questions, contact support.',
 0,
 OBJECT_CONSTRUCT('category', 'procedures', 'importance', 'medium')),

('{config.company_name}_benefits.txt',
 '{config.company_name} Employee Benefits: We offer comprehensive health insurance, 401k matching, flexible PTO, professional development budget, and employee wellness programs. All full-time employees are eligible after 90 days.',
 0,
 OBJECT_CONSTRUCT('category', 'benefits', 'importance', 'medium')),

('{config.company_name}_contact_info.txt',
 'Contact Information: For HR inquiries, email hr@{config.company_name.lower().replace(" ", "")}.com. IT support: it@{config.company_name.lower().replace(" ", "")}.com. General questions: info@{config.company_name.lower().replace(" ", "")}.com. Emergency: 911.',
 0,
 OBJECT_CONSTRUCT('category', 'contact', 'importance', 'high'));

-- Grant permissions
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PUBLIC;
GRANT ALL ON DATABASE {config.company_name.upper()}_RAG_DEMO TO ROLE PUBLIC;
GRANT ALL ON SCHEMA KNOWLEDGE TO ROLE PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA KNOWLEDGE TO ROLE PUBLIC;
GRANT ALL ON FUNCTION PROCESS_DOCUMENT(STRING, STRING) TO ROLE PUBLIC;

-- Verify setup
SELECT 'RAG Assistant lab setup completed!' as status;
SELECT COUNT(*) as document_chunks FROM document_chunks;
"""

    def _create_rag_streamlit(self, config: LabConfig, context: Dict) -> str:
        return f"""import streamlit as st
import snowflake.snowpark as snowpark
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark.functions import *
import json
import uuid

def main():
    st.set_page_config(page_title="{config.company_name} RAG Assistant", layout="wide")
    
    st.title("🤖 {config.company_name} Knowledge Assistant")
    st.markdown("**Intelligent Q&A powered by RAG and Snowflake Cortex**")
    
    # Initialize session state
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Get Snowflake session
    session = get_active_session()
    
    # Sidebar with knowledge base info
    st.sidebar.header("📚 Knowledge Base")
    
    # Show available documents
    docs_query = f'''
    SELECT 
        document_name,
        COUNT(*) as chunk_count,
        metadata:category::string as category
    FROM {config.company_name.upper()}_RAG_DEMO.KNOWLEDGE.document_chunks
    GROUP BY document_name, metadata:category::string
    ORDER BY document_name
    '''
    
    docs_df = session.sql(docs_query).to_pandas()
    for _, row in docs_df.iterrows():
        st.sidebar.write(f"📄 {{row['DOCUMENT_NAME']}}")
        st.sidebar.caption(f"Category: {{row['CATEGORY']}} | Chunks: {{row['CHUNK_COUNT']}}")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("💡 Try asking:")
    sample_questions = [
        f"What is {config.company_name}'s mission?",
        f"What are {config.company_name}'s working hours?",
        f"How do I {context['common_task']}?",
        f"What benefits does {config.company_name} offer?",
        "Who should I contact for IT support?"
    ]
    
    for question in sample_questions:
        if st.sidebar.button(question, key=f"sample_{{hash(question)}}"):
            st.session_state.user_input = question
    
    # Main chat interface
    st.subheader("💬 Ask me anything about {config.company_name}")
    
    # Display chat history
    for chat in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(chat["user"])
        with st.chat_message("assistant"):
            st.write(chat["assistant"])
            if chat.get("context"):
                with st.expander("📋 Source Context"):
                    st.write(chat["context"])
    
    # User input
    user_input = st.chat_input("Type your question here...")
    
    if user_input:
        # Add user message to chat
        with st.chat_message("user"):
            st.write(user_input)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching knowledge base..."):
                try:
                    # Step 1: Retrieve relevant context using Cortex Search
                    search_query = f'''
                    SELECT 
                        chunk_text,
                        document_name,
                        metadata:category::string as category
                    FROM TABLE({config.company_name.upper()}_RAG_DEMO.KNOWLEDGE.{config.company_name.upper()}_RAG_SEARCH!SEARCH('{{user_input}}'))
                    LIMIT 3
                    '''
                    
                    search_results = session.sql(search_query).collect()
                    
                    if search_results:
                        # Combine context from search results
                        context_pieces = []
                        source_docs = []
                        
                        for result in search_results:
                            context_pieces.append(result['CHUNK_TEXT'])
                            source_docs.append(result['DOCUMENT_NAME'])
                        
                        combined_context = "\\n\\n".join(context_pieces)
                        
                        # Step 2: Generate response using Cortex LLM with context
                        rag_prompt = f'''
                        You are a helpful assistant for {config.company_name}. 
                        Answer the user's question based on the provided context.
                        If the context doesn't contain enough information, say so politely.
                        Be accurate, helpful, and specific to {config.company_name}.
                        
                        Context:
                        {{combined_context}}
                        
                        Question: {{user_input}}
                        
                        Answer:
                        '''
                        
                        llm_query = f'''
                        SELECT SNOWFLAKE.CORTEX.COMPLETE(
                            'mixtral-8x7b',
                            '{{rag_prompt}}'
                        ) as response
                        '''
                        
                        llm_result = session.sql(llm_query).collect()
                        
                        if llm_result:
                            response = llm_result[0]['RESPONSE']
                            
                            # Display response
                            st.write(response)
                            
                            # Show source context
                            with st.expander("📋 Source Documents"):
                                for i, (context, doc) in enumerate(zip(context_pieces, source_docs)):
                                    st.write(f"**Source {{i+1}}: {{doc}}**")
                                    st.write(context[:200] + "..." if len(context) > 200 else context)
                                    st.write("---")
                            
                            # Save to chat history
                            chat_entry = {{
                                "user": user_input,
                                "assistant": response,
                                "context": combined_context[:500] + "..." if len(combined_context) > 500 else combined_context
                            }}
                            st.session_state.chat_history.append(chat_entry)
                            
                            # Save to Snowflake
                            save_query = f'''
                            INSERT INTO {config.company_name.upper()}_RAG_DEMO.KNOWLEDGE.chat_history 
                            (session_id, user_query, assistant_response, context_used, confidence_score)
                            VALUES (
                                '{{st.session_state.session_id}}',
                                '{{user_input.replace("'", "''")}}',
                                '{{response.replace("'", "''")}}',
                                '{{combined_context[:4000].replace("'", "''")}}',
                                0.8
                            )
                            '''
                            session.sql(save_query).collect()
                            
                        else:
                            st.error("Unable to generate response. Please try again.")
                    else:
                        st.write("I don't have information about that topic in my knowledge base. Please try asking about {config.company_name} policies, procedures, benefits, or contact information.")
                        
                except Exception as e:
                    st.error(f"Error processing question: {{str(e)}}")
    
    # Analytics section
    if st.sidebar.button("📊 Show Chat Analytics"):
        st.sidebar.subheader("Session Analytics")
        analytics_query = f'''
        SELECT 
            COUNT(*) as total_questions,
            COUNT(DISTINCT DATE(timestamp)) as active_days,
            AVG(confidence_score) as avg_confidence
        FROM {config.company_name.upper()}_RAG_DEMO.KNOWLEDGE.chat_history
        WHERE session_id = '{{st.session_state.session_id}}'
        '''
        
        analytics = session.sql(analytics_query).collect()
        if analytics:
            st.sidebar.metric("Questions Asked", analytics[0]['TOTAL_QUESTIONS'])
            st.sidebar.metric("Avg Confidence", f"{{analytics[0]['AVG_CONFIDENCE']:.2f}}")

if __name__ == "__main__":
    main()
"""

    def _load_industry_contexts(self) -> Dict:
        """Load industry-specific contexts for different lab types."""
        return {
            'telecommunications': {
                'primary_entity': 'network_sites',
                'location_type': 'tower',
                'locations_count': 200,
                'primary_category': 'Cell Tower',
                'geo_data_1': 'Cell Tower Locations',
                'geo_data_2': 'Coverage Area Polygons',
                'expansion_type': 'cell towers',
                'mission': 'connecting communities through reliable telecommunications',
                'customer_base': 'millions of subscribers',
                'service_offering': 'mobile and internet services',
                'industry': 'telecommunications',
                'doc_type_1': 'Network Procedures',
                'doc_type_2': 'Service Agreements',
                'policy_area': 'data privacy',
                'common_task': 'report network issues',
                'requirement_area': 'service installation',
                'process_area': 'customer onboarding'
            },
            'retail': {
                'primary_entity': 'store_locations',
                'location_type': 'store',
                'locations_count': 150,
                'primary_category': 'Retail Store',
                'geo_data_1': 'Store Locations',
                'geo_data_2': 'Customer Demographics',
                'expansion_type': 'retail stores',
                'mission': 'providing exceptional customer experiences',
                'customer_base': 'retail customers',
                'service_offering': 'quality products and services',
                'industry': 'retail',
                'doc_type_1': 'Product Catalogs',
                'doc_type_2': 'Customer Service Guides',
                'policy_area': 'return',
                'common_task': 'process returns',
                'requirement_area': 'employee onboarding',
                'process_area': 'inventory management'
            },
            'logistics': {
                'primary_entity': 'distribution_centers',
                'location_type': 'warehouse',
                'locations_count': 75,
                'primary_category': 'Distribution Center',
                'geo_data_1': 'Warehouse Locations',
                'geo_data_2': 'Delivery Routes',
                'expansion_type': 'distribution centers',
                'mission': 'delivering excellence in supply chain management',
                'customer_base': 'businesses and consumers',
                'service_offering': 'logistics and delivery solutions',
                'industry': 'logistics',
                'doc_type_1': 'Shipping Procedures',
                'doc_type_2': 'Safety Protocols',
                'policy_area': 'shipping',
                'common_task': 'track packages',
                'requirement_area': 'driver certification',
                'process_area': 'package handling'
            },
            'generic': {
                'primary_entity': 'business_locations',
                'location_type': 'office',
                'locations_count': 100,
                'primary_category': 'Business Location',
                'geo_data_1': 'Office Locations',
                'geo_data_2': 'Service Areas',
                'expansion_type': 'offices',
                'mission': 'delivering value to customers',
                'customer_base': 'clients',
                'service_offering': 'professional services',
                'industry': 'business',
                'doc_type_1': 'Procedures Manual',
                'doc_type_2': 'Training Materials',
                'policy_area': 'workplace',
                'common_task': 'submit requests',
                'requirement_area': 'compliance training',
                'process_area': 'project management'
            }
        }
    
    def _sanitize_name(self, name: str) -> str:
        """Convert name to safe directory name."""
        return re.sub(r'[^a-zA-Z0-9]', '_', name.lower()).strip('_')
    
    def _generate_cortex_search_lab(self, config: LabConfig):
        """Generate original Cortex Search lab (from previous implementation)."""
        # Implementation would be similar to the original generator
        pass
    
    def _generate_cortex_analyst_lab(self, config: LabConfig):
        """Generate original Cortex Analyst lab (from previous implementation)."""
        # Implementation would be similar to the original generator
        pass
    
    # Additional helper methods for other lab types would go here...
    def _create_dbt_readme(self, config: LabConfig, context: Dict) -> str:
        return f"# {config.company_name} dbt Integration Lab\\n\\nComing soon..."
    
    def _create_dbt_setup(self, config: LabConfig, context: Dict) -> str:
        return f"-- {config.company_name} dbt setup coming soon"
    
    def _create_dbt_project_yml(self, config: LabConfig, context: Dict) -> str:
        return f"name: {config.company_name.lower()}_analytics\\nversion: '1.0.0'"
    
    def _create_dbt_models(self, models_dir: Path, config: LabConfig, context: Dict):
        (models_dir / "example_model.sql").write_text("SELECT 1 as example")
    
    def _create_ml_readme(self, config: LabConfig, context: Dict) -> str:
        return f"# {config.company_name} ML Feature Store Lab\\n\\nComing soon..."
    
    def _create_ml_setup(self, config: LabConfig, context: Dict) -> str:
        return f"-- {config.company_name} ML setup coming soon"
    
    def _create_ml_notebook(self, config: LabConfig, context: Dict) -> str:
        return f"# {config.company_name} ML Workflow\\nprint('Coming soon')"
    
    def _create_ml_streamlit(self, config: LabConfig, context: Dict) -> str:
        return f"import streamlit as st\\nst.title('{config.company_name} ML Dashboard')"
    
    def _create_geospatial_data_generator(self, config: LabConfig, context: Dict) -> str:
        return f"# {config.company_name} Geospatial Data Generator\\nprint('Generate sample location data')"
    
    def _create_rag_knowledge_base(self, docs_dir: Path, config: LabConfig, context: Dict):
        (docs_dir / "sample_knowledge.txt").write_text(f"{config.company_name} knowledge base content")
    
    def _generate_discogs_collection_lab(self, config: LabConfig):
        """Generate Discogs Collection Management lab."""
        safe_name = self._sanitize_name(config.company_name)
        lab_dir = self.output_dir / f"{safe_name}_discogs_collection_lab"
        
        # Copy the pre-built Discogs lab to the company-specific directory
        source_lab_dir = self.output_dir / "discogs_collection_lab"
        
        if not source_lab_dir.exists():
            print(f"❌ Discogs collection lab template not found at {source_lab_dir}")
            print("   Please run the Discogs lab generator first")
            return
        
        # Create target directory
        lab_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files from source to target
        import shutil
        for item in source_lab_dir.iterdir():
            if item.is_file():
                target_file = lab_dir / item.name
                shutil.copy2(item, target_file)
                
                # Customize certain files for the company
                if item.name == "README.md":
                    content = target_file.read_text()
                    customized_content = content.replace(
                        "# Discogs Collection Lab",
                        f"# {config.company_name} Music Collection Lab"
                    ).replace(
                        "Discogs Collection Lab",
                        f"{config.company_name} Music Collection Lab"
                    ).replace(
                        "your personal music collection",
                        f"{config.company_name}'s music collection"
                    )
                    target_file.write_text(customized_content)
                
                elif item.name == "setup.sql":
                    content = target_file.read_text()
                    customized_content = content.replace(
                        "CREATE DATABASE IF NOT EXISTS DISCOGS_COLLECTION;",
                        f"CREATE DATABASE IF NOT EXISTS {safe_name.upper()}_MUSIC_COLLECTION;"
                    ).replace(
                        "USE DATABASE DISCOGS_COLLECTION;",
                        f"USE DATABASE {safe_name.upper()}_MUSIC_COLLECTION;"
                    ).replace(
                        "-- Discogs Collection Lab Setup",
                        f"-- {config.company_name} Music Collection Lab Setup"
                    )
                    target_file.write_text(customized_content)
                
                elif item.name == "streamlit_app.py":
                    content = target_file.read_text()
                    customized_content = content.replace(
                        'page_title="Discogs Collection Viewer"',
                        f'page_title="{config.company_name} Music Collection"'
                    ).replace(
                        '<h1 class="main-header">🎵 Your Discogs Collection</h1>',
                        f'<h1 class="main-header">🎵 {config.company_name} Music Collection</h1>'
                    ).replace(
                        "DISCOGS_COLLECTION",
                        f"{safe_name.upper()}_MUSIC_COLLECTION"
                    )
                    target_file.write_text(customized_content)
                
                elif item.name == "discogs_downloader.py":
                    content = target_file.read_text()
                    customized_content = content.replace(
                        'snowflake_database: str = "DISCOGS_COLLECTION"',
                        f'snowflake_database: str = "{safe_name.upper()}_MUSIC_COLLECTION"'
                    )
                    target_file.write_text(customized_content)
        
        print(f"✅ Generated Discogs Collection lab: {lab_dir}")
        print(f"   📝 Customized for {config.company_name}")

def main():
    """Main CLI interface."""
    agent = EnhancedSnowflakeAgent()
    agent.interactive_mode()

if __name__ == "__main__":
    main()