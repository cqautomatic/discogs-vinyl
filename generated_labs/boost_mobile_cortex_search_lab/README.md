# Boost Mobile Cortex Search Lab

## Overview
Learn how to build an intelligent search assistant for Boost Mobile using Snowflake Cortex Search. This 15-minute hands-on lab will guide you through creating a semantic search application over Boost Mobile's customer support documents and service policies.

## Prerequisites
- Snowflake account with Cortex Search enabled
- Basic familiarity with SQL and Streamlit

## Lab Steps

### Step 1: Environment Setup (3 minutes)
1. Open Snowsight and run the setup script:
```sql
-- Execute setup.sql to create database and stage
```

### Step 2: Upload Sample Documents (2 minutes)
1. Navigate to Data > Databases > BOOST MOBILE_CORTEX_SEARCH_DEMO > DOCS > Stages > DOCS_STAGE
2. Upload all files from the `sample_docs/` folder
3. Verify files are uploaded successfully

### Step 3: Create Cortex Search Service (3 minutes)
```sql
-- Create the search service over uploaded documents
CREATE OR REPLACE CORTEX SEARCH APPLICATION BOOST MOBILE_SEARCH_APP
ON docs_table
WAREHOUSE = COMPUTE_WH
ATTRIBUTES = (relative_path, file_content)
SERVICE_NAME = 'boost mobile_search_service';
```

### Step 4: Test Search Functionality (2 minutes)
```sql
-- Test semantic search
SELECT relative_path, file_content
FROM TABLE(BOOST MOBILE_SEARCH_APP!SEARCH('mobile plan features'));
```

### Step 5: Deploy Streamlit App (5 minutes)
1. Create new Streamlit app in Snowsight
2. Copy code from `streamlit_app.py`
3. Run the app and test with sample queries:
   - "What are the available mobile plans?"
   - "How do I upgrade my device?"

## Expected Results
- Functional semantic search over Boost Mobile documents
- Interactive Streamlit interface for querying company knowledge
- Understanding of Cortex Search capabilities

## Next Steps
- Add more company-specific documents
- Implement advanced filtering and ranking
- Integrate with existing Boost Mobile systems
