-- Boost Mobile Cortex Search Lab Setup
-- Creates database, schema, stage, and table structure

-- Create database and schema
CREATE OR REPLACE DATABASE BOOST MOBILE_CORTEX_SEARCH_DEMO;
CREATE OR REPLACE SCHEMA DOCS;
USE DATABASE BOOST MOBILE_CORTEX_SEARCH_DEMO;
USE SCHEMA DOCS;

-- Create stage for document uploads
CREATE OR REPLACE STAGE docs_stage
  FILE_FORMAT = (TYPE = 'JSON' STRIP_OUTER_ARRAY = FALSE);

-- Create table to hold document content
CREATE OR REPLACE TABLE docs_table (
    relative_path VARCHAR,
    file_content VARCHAR
);

-- Create warehouse if not exists
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH 
WITH WAREHOUSE_SIZE = 'SMALL' 
     AUTO_SUSPEND = 300 
     AUTO_RESUME = TRUE;

-- Grant permissions
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PUBLIC;
GRANT ALL ON DATABASE BOOST MOBILE_CORTEX_SEARCH_DEMO TO ROLE PUBLIC;
GRANT ALL ON SCHEMA DOCS TO ROLE PUBLIC;
GRANT ALL ON TABLE docs_table TO ROLE PUBLIC;
GRANT ALL ON STAGE docs_stage TO ROLE PUBLIC;

SELECT 'Setup completed! Ready to upload documents to stage.' as status;
