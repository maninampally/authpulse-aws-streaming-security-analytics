-- AuthPulse - Iceberg Table DDL Statements
-- Creates Apache Iceberg tables in AWS Glue Data Catalog
-- Run each query separately in Athena (one at a time)

-- Database
CREATE DATABASE IF NOT EXISTS authpulse
COMMENT 'AuthPulse streaming lakehouse database';

-- ============================================================
-- TABLE: auth_events_raw
-- Purpose: Unmodified events landed from Kinesis Flink raw sink.
-- ============================================================
CREATE TABLE IF NOT EXISTS authpulse.auth_events_raw (
  event_time  TIMESTAMP,
  user_id     STRING,
  computer_id STRING,
  event_id    STRING,
  event_date  STRING
)
WITH (
  format = 'ICEBERG',
  external_location = 's3://authpulse-dev-lakehouse-604743481383/raw/auth_events/'
);

-- ============================================================
-- TABLE: auth_events_curated
-- Purpose: Risk-enriched events with feature window values.
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
WITH (
  format = 'ICEBERG',
  external_location = 's3://authpulse-dev-lakehouse-604743481383/curated/auth_events_curated/'
);
