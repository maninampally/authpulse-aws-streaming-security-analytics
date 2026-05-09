-- AuthPulse - Iceberg Table DDL Statements
-- Creates Apache Iceberg tables in AWS Glue Data Catalog
-- Run these in Athena (query engine v3) or via Glue Terraform module.

-- Database
CREATE DATABASE IF NOT EXISTS authpulse
COMMENT 'AuthPulse streaming lakehouse database';

-- ============================================================
-- TABLE: auth_events_raw
-- Purpose: Unmodified events landed from Kinesis Flink raw sink.
-- Partition: event_date (yyyy-MM-dd)
-- ============================================================
CREATE TABLE IF NOT EXISTS authpulse.auth_events_raw (
  event_time  TIMESTAMP,
  user_id     STRING,
  computer_id STRING,
  event_id    STRING,
  event_date  STRING
)
PARTITIONED BY (event_date)
LOCATION 's3://authpulse-dev-lakehouse-289591071327/raw/auth_events/'
TBLPROPERTIES (
  'table_type'                      = 'ICEBERG',
  'format'                          = 'parquet',
  'write_compression'               = 'snappy',
  'optimize_rewrite_delete_file_threshold' = '10'
);

-- ============================================================
-- TABLE: auth_events_curated
-- Purpose: Risk-enriched events with feature window values.
-- Partition: event_date (yyyy-MM-dd)
-- ============================================================
CREATE TABLE IF NOT EXISTS authpulse.auth_events_curated (
  event_time              TIMESTAMP,
  user_id                 STRING,
  src_host                STRING,
  dst_host                STRING,
  success                 BOOLEAN,
  window_1h_event_count   BIGINT,
  window_1h_unique_hosts  BIGINT,
  window_24h_unique_hosts BIGINT,
  has_new_device          BOOLEAN,
  risk_score              INT,
  risk_flags              ARRAY<STRING>,
  event_date              STRING
)
PARTITIONED BY (event_date)
LOCATION 's3://authpulse-dev-lakehouse-289591071327/curated/auth_events_curated/'
TBLPROPERTIES (
  'table_type'                      = 'ICEBERG',
  'format'                          = 'parquet',
  'write_compression'               = 'snappy',
  'optimize_rewrite_delete_file_threshold' = '10'
);
