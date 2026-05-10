-- AuthPulse - Auth Events Curated Table DDL
-- Canonical copy of the curated table definition.
-- Prefer iceberg_auth_events.sql which creates both raw + curated in one file.
-- Run each statement separately in Athena Query Editor (engine v3).

-- Statement 1: database (skip if already created)
CREATE DATABASE IF NOT EXISTS authpulse
COMMENT 'AuthPulse streaming lakehouse database';

-- Statement 2: curated events with risk enrichment
CREATE TABLE IF NOT EXISTS authpulse.auth_events_curated (
  event_time              TIMESTAMP(6),
  user_id                 VARCHAR,
  src_host                VARCHAR,
  dst_host                VARCHAR,
  success                 BOOLEAN,
  window_1h_event_count   BIGINT,
  window_1h_unique_hosts  BIGINT,
  window_24h_unique_hosts BIGINT,
  has_new_device          BOOLEAN,
  risk_score              INT,
  risk_flags              ARRAY(VARCHAR),
  event_date              VARCHAR
)
LOCATION 's3://authpulse-dev-lakehouse-604743481383/curated/auth_events_curated/'
TBLPROPERTIES ('table_type' = 'ICEBERG', 'format' = 'parquet');
