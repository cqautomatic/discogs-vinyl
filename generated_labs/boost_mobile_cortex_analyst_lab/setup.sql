-- Boost Mobile Cortex Analyst Lab Setup
-- Creates database with sample sales data

-- Create database and schema
CREATE OR REPLACE DATABASE BOOST MOBILE_CORTEX_ANALYST_DEMO;
CREATE OR REPLACE SCHEMA ANALYTICS;
USE DATABASE BOOST MOBILE_CORTEX_ANALYST_DEMO;
USE SCHEMA ANALYTICS;

-- Create sales table
CREATE OR REPLACE TABLE sales_table (
    id INTEGER,
    date DATE,
    category VARCHAR(50),
    amount DECIMAL(10,2),
    region VARCHAR(50),
    customer_segment VARCHAR(50),
    product_line VARCHAR(50)
);

-- Insert sample data
INSERT INTO sales_table VALUES
(1, '2023-08-08', 'Prepaid Plans', 4547.92, 'South', 'Enterprise', 'Product 3'),
(2, '2023-02-17', 'Postpaid Plans', 9564.21, 'North', 'Enterprise', 'Product 1'),
(3, '2023-05-08', 'Accessories', 3898.26, 'South', 'SMB', 'Product 3'),
(4, '2023-12-28', 'Accessories', 3696.87, 'East', 'Consumer', 'Product 3'),
(5, '2023-05-01', 'Accessories', 7793.28, 'West', 'Enterprise', 'Product 1'),
(6, '2023-06-17', 'Prepaid Plans', 8724.56, 'North', 'SMB', 'Product 2'),
(7, '2023-10-14', 'Devices', 3730.89, 'West', 'SMB', 'Product 2'),
(8, '2023-12-14', 'Devices', 5615.18, 'East', 'SMB', 'Product 2'),
(9, '2023-03-27', 'Prepaid Plans', 1674.73, 'East', 'Enterprise', 'Product 1'),
(10, '2023-04-04', 'Prepaid Plans', 6528.27, 'East', 'Enterprise', 'Product 2'),
(11, '2023-08-31', 'Accessories', 332.11, 'South', 'Enterprise', 'Product 1'),
(12, '2023-04-25', 'Devices', 1246.1, 'West', 'Consumer', 'Product 3'),
(13, '2023-07-17', 'Postpaid Plans', 1115.6, 'West', 'Enterprise', 'Product 2'),
(14, '2023-01-13', 'Prepaid Plans', 3089.25, 'North', 'Consumer', 'Product 1'),
(15, '2023-01-21', 'Postpaid Plans', 7257.47, 'East', 'SMB', 'Product 3'),
(16, '2023-10-29', 'Devices', 3947.47, 'West', 'SMB', 'Product 3'),
(17, '2023-02-04', 'Accessories', 279.33, 'North', 'Enterprise', 'Product 3'),
(18, '2023-08-06', 'Postpaid Plans', 9020.21, 'East', 'SMB', 'Product 1'),
(19, '2023-04-29', 'Accessories', 2217.7, 'North', 'Enterprise', 'Product 1'),
(20, '2023-09-20', 'Prepaid Plans', 8650.96, 'West', 'Enterprise', 'Product 3'),
(21, '2023-10-03', 'Accessories', 8575.79, 'East', 'Consumer', 'Product 1'),
(22, '2023-03-07', 'Prepaid Plans', 8789.15, 'North', 'Enterprise', 'Product 3'),
(23, '2023-12-06', 'Postpaid Plans', 5526.22, 'South', 'Consumer', 'Product 2'),
(24, '2023-11-26', 'Prepaid Plans', 7964.01, 'West', 'Enterprise', 'Product 1'),
(25, '2023-11-09', 'Devices', 2705.81, 'East', 'Consumer', 'Product 1'),
(26, '2023-11-27', 'Postpaid Plans', 7060.08, 'West', 'Enterprise', 'Product 3'),
(27, '2023-04-17', 'Prepaid Plans', 4145.48, 'North', 'SMB', 'Product 2'),
(28, '2023-07-01', 'Accessories', 8521.71, 'East', 'Consumer', 'Product 1'),
(29, '2023-10-03', 'Prepaid Plans', 7096.4, 'South', 'SMB', 'Product 2'),
(30, '2023-04-06', 'Postpaid Plans', 3910.71, 'North', 'SMB', 'Product 3'),
(31, '2023-03-14', 'Postpaid Plans', 5220.96, 'East', 'Consumer', 'Product 2'),
(32, '2023-06-03', 'Prepaid Plans', 7698.0, 'East', 'SMB', 'Product 1'),
(33, '2023-04-15', 'Devices', 8312.9, 'West', 'Consumer', 'Product 2'),
(34, '2023-03-12', 'Postpaid Plans', 7297.63, 'South', 'Enterprise', 'Product 2'),
(35, '2023-08-22', 'Devices', 5003.46, 'East', 'Enterprise', 'Product 2'),
(36, '2023-06-30', 'Accessories', 2957.58, 'West', 'SMB', 'Product 2'),
(37, '2023-12-03', 'Accessories', 2260.1, 'West', 'Consumer', 'Product 1'),
(38, '2023-04-29', 'Devices', 6428.62, 'West', 'Consumer', 'Product 3'),
(39, '2023-05-21', 'Prepaid Plans', 4314.85, 'East', 'SMB', 'Product 1'),
(40, '2023-03-15', 'Accessories', 9117.0, 'East', 'Consumer', 'Product 1'),
(41, '2023-12-31', 'Devices', 4383.79, 'South', 'SMB', 'Product 3'),
(42, '2023-06-04', 'Postpaid Plans', 203.19, 'East', 'Consumer', 'Product 3'),
(43, '2023-08-18', 'Accessories', 8085.77, 'South', 'Consumer', 'Product 1'),
(44, '2023-06-17', 'Devices', 9506.5, 'North', 'SMB', 'Product 1'),
(45, '2023-01-02', 'Postpaid Plans', 2194.47, 'West', 'SMB', 'Product 2'),
(46, '2023-08-01', 'Postpaid Plans', 2081.81, 'North', 'Consumer', 'Product 2'),
(47, '2023-12-04', 'Devices', 5565.35, 'East', 'Consumer', 'Product 3'),
(48, '2023-08-09', 'Devices', 8419.49, 'South', 'SMB', 'Product 3'),
(49, '2023-09-12', 'Devices', 4543.47, 'North', 'Consumer', 'Product 1'),
(50, '2023-08-04', 'Devices', 8488.25, 'East', 'Enterprise', 'Product 1');

-- Create stage for semantic model
CREATE OR REPLACE STAGE models_stage;

-- Create warehouse
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH 
WITH WAREHOUSE_SIZE = 'SMALL' 
     AUTO_SUSPEND = 300 
     AUTO_RESUME = TRUE;

-- Grant permissions
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE PUBLIC;
GRANT ALL ON DATABASE BOOST MOBILE_CORTEX_ANALYST_DEMO TO ROLE PUBLIC;
GRANT ALL ON SCHEMA ANALYTICS TO ROLE PUBLIC;
GRANT ALL ON TABLE sales_table TO ROLE PUBLIC;
GRANT ALL ON STAGE models_stage TO ROLE PUBLIC;

SELECT 'Setup completed! Sample data loaded successfully.' as status;
SELECT COUNT(*) as record_count FROM sales_table;
