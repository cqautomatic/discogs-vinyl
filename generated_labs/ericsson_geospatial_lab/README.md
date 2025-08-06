# Ericsson Geospatial Analytics Lab

## Overview
Build location-intelligent applications for Ericsson using Snowflake's geospatial capabilities, Cortex AI, and Streamlit visualization.

## What You'll Learn
- Geospatial data analysis in Snowflake
- H3 hexagonal indexing for location analytics  
- Cortex LLMs for location insights
- Interactive mapping with Streamlit and Pydeck
- Ericsson-specific location intelligence

## Lab Architecture
```
┌─────────────────────────────────────┐
│        Snowflake Geospatial        │
│  ┌─────────────────────────────────┐│
│  │     Location Data Sources       ││
│  │  • Cell Tower Locations      ││
│  │  • Coverage Area Polygons      ││
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
-- Creates ERICSSON_GEOSPATIAL_DEMO database
-- Sets up geospatial data tables and functions
```

### Step 2: Load Sample Location Data (5 minutes)
- Generate 200 sample tower locations
- Create boundary analysis for Ericsson operations
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
- "Find all tower within 5km of target location"
- "Identify coverage gaps in Ericsson service area"
- "Generate weather impact report for operational locations"
- "Recommend optimal locations for new cell towers"

## Expected Results
- Interactive geospatial dashboard
- AI-powered location intelligence
- Spatial analysis capabilities for Ericsson
