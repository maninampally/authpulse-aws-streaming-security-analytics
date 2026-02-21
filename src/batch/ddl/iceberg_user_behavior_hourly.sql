-- Day 8: Athena + Glue Catalog (Iceberg)
-- Creates the per-user behavior feature table (hourly / windowed features).

CREATE DATABASE IF NOT EXISTS lakehouse;

CREATE TABLE IF NOT EXISTS lakehouse.user_behavior_hourly (
  window_start   timestamp,
  window_end     timestamp,
  user_id        string,
  window_size    string,      -- e.g. '1h' | '24h'
  unique_hosts   bigint,
  event_count    bigint,
  has_new_device boolean
)
PARTITIONED BY (
  day(window_start),
  window_size
)
LOCATION 's3://authpulse-dev-curated/auth_user_features/'
TBLPROPERTIES (
  'table_type'='ICEBERG',
  'format'='parquet'
);
