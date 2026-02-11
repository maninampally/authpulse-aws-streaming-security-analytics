-- AuthPulse - Iceberg Table DDL Statements
-- Creates Apache Iceberg tables in AWS Glue Data Catalog

-- Database
CREATE DATABASE IF NOT EXISTS authpulse
LOCATION 's3://authpulse-lakehouse/iceberg/'
COMMENT 'AuthPulse streaming lakehouse database';

-- TODO: CREATE TABLE auth_events_raw
-- TODO: CREATE TABLE auth_events_curated (with partitioning)
-- TODO: Add table properties for Iceberg format
