# Boost Mobile Cortex Analyst Lab

## Overview
Build an AI-powered analytics assistant for Boost Mobile using Snowflake Cortex Analyst. This 15-minute lab demonstrates natural language querying over Boost Mobile's sales data.

## Prerequisites
- Snowflake account with Cortex Analyst enabled
- Basic understanding of SQL and analytics

## Lab Steps

### Step 1: Database Setup (2 minutes)
Execute `setup.sql` to create database and insert sample data:
```sql
-- Creates BOOST MOBILE_CORTEX_ANALYST_DEMO database
-- Inserts 2000 sample records
```

### Step 2: Create Semantic Model (3 minutes)
1. Upload `semantic_model.yaml` to a stage
2. Create the semantic model:
```sql
CREATE OR REPLACE CORTEX SEARCH APPLICATION BOOST MOBILE_ANALYST_APP
ON sales_table
WAREHOUSE = COMPUTE_WH
SEMANTIC_MODEL = '@MODELS_STAGE/semantic_model.yaml';
```

### Step 3: Test Natural Language Queries (5 minutes)
```sql
-- Ask questions in plain English
SELECT SNOWFLAKE.CORTEX.ANALYST_QUERY(
    'BOOST MOBILE_ANALYST_APP',
    'What are the top 5 sales by revenue?'
);
```

### Step 4: Deploy Analytics Dashboard (5 minutes)
1. Create Streamlit app with `streamlit_app.py`
2. Test with sample questions:
   - "What are the monthly sales trends by plan type?"
   - "Which regions have the highest device sales?"

## Expected Results
- Natural language interface for Boost Mobile analytics
- Automated chart generation and insights
- Understanding of Cortex Analyst capabilities

## Sample Queries to Try
- "Show me monthly trends"
- "What are the top performers?"
- "Compare performance by category"
- "Identify any anomalies or outliers"
