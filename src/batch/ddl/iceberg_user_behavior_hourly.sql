-- AuthPulse - User Behavior Hourly Table DDL
-- Run each statement separately in Athena Query Editor (engine v3).

-- Statement 1: database (skip if already created)
CREATE DATABASE IF NOT EXISTS authpulse
COMMENT 'AuthPulse streaming lakehouse database';

-- Statement 2: per-user hourly behavior features
CREATE TABLE IF NOT EXISTS authpulse.user_behavior_hourly (
  window_start   TIMESTAMP(6),
  window_end     TIMESTAMP(6),
  user_id        VARCHAR,
  window_size    VARCHAR,
  unique_hosts   BIGINT,
  event_count    BIGINT,
  has_new_device BOOLEAN
)
LOCATION 's3://authpulse-dev-lakehouse-604743481383/features/auth_user_features/'
TBLPROPERTIES ('table_type' = 'ICEBERG', 'format' = 'parquet');
