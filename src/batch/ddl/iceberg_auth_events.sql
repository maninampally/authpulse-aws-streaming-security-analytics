-- AuthPulse - Iceberg Table DDL
-- Run each statement separately in Athena Query Editor (engine v3).

-- Statement 1: database
CREATE DATABASE IF NOT EXISTS authpulse
COMMENT 'AuthPulse streaming lakehouse database';

-- Statement 2: raw events (unmodified from Kinesis)
CREATE TABLE IF NOT EXISTS authpulse.auth_events_raw (
  event_time  TIMESTAMP(6),
  user_id     VARCHAR,
  computer_id VARCHAR,
  event_id    VARCHAR,
  event_date  VARCHAR
)
LOCATION 's3://authpulse-dev-lakehouse-604743481383/raw/auth_events/'
TBLPROPERTIES ('table_type' = 'ICEBERG', 'format' = 'parquet');

-- Statement 3: curated events with risk enrichment
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
