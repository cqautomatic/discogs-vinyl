-- Ericsson Geospatial Analytics Lab Setup

-- Create database and schema
CREATE OR REPLACE DATABASE ERICSSON_GEOSPATIAL_DEMO;
CREATE OR REPLACE SCHEMA LOCATIONS;
USE DATABASE ERICSSON_GEOSPATIAL_DEMO;
USE SCHEMA LOCATIONS;

-- Create location data table
CREATE OR REPLACE TABLE tower_locations (
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
INSERT INTO tower_locations 
SELECT 
    ROW_NUMBER() OVER (ORDER BY RANDOM()) as id,
    'Ericsson ' || SUBSTR('ABCDEFGHIJKLMNOPQRSTUVWXYZ', UNIFORM(1, 26, RANDOM()), 1) || 
    UNIFORM(1, 999, RANDOM()) as name,
    'Cell Tower' as category,
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
FROM TABLE(GENERATOR(ROWCOUNT => 200));

-- Update location_point and h3_index based on lat/lon
UPDATE tower_locations 
SET 
    location_point = ST_POINT(lon, lat),
    h3_index = H3_POINT_TO_CELL_STRING(ST_POINT(lon, lat), 8);

-- Create sample boundary data
INSERT INTO service_boundaries VALUES
(1, 'Ericsson Primary Service Area', 'service_area', 
 ST_POLYGON('POLYGON((-74.5 40.0, -71.0 40.0, -71.0 42.0, -74.5 42.0, -74.5 40.0))'), 
 ARRAY_CONSTRUCT()),
(2, 'Ericsson Emergency Zone', 'emergency', 
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
    'Automated event generated for Ericsson location monitoring' as description,
    H3_POINT_TO_CELL_STRING(ST_POINT(UNIFORM(-74.5, -71.0, RANDOM()), UNIFORM(40.0, 42.0, RANDOM())), 8) as h3_index
FROM TABLE(GENERATOR(ROWCOUNT => 100));

-- Create warehouse
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH 
WITH WAREHOUSE_SIZE = 'SMALL' 
     AUTO_SUSPEND = 300 
     AUTO_RESUME = TRUE;

-- Grant permissions
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PUBLIC;
GRANT ALL ON DATABASE ERICSSON_GEOSPATIAL_DEMO TO ROLE PUBLIC;
GRANT ALL ON SCHEMA LOCATIONS TO ROLE PUBLIC;
GRANT ALL ON ALL TABLES IN SCHEMA LOCATIONS TO ROLE PUBLIC;

-- Verify setup
SELECT 'Geospatial lab setup completed!' as status;
SELECT COUNT(*) as location_count FROM tower_locations;
SELECT COUNT(*) as event_count FROM location_events;
