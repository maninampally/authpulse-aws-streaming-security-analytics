-- Day 8: Athena + Glue Catalog (Iceberg)
-- Creates the curated, risk-enriched auth events table.

CREATE DATABASE IF NOT EXISTS lakehouse;

CREATE TABLE IF NOT EXISTS lakehouse.auth_events_curated (
  event_time               timestamp,
  user_id                  string,
  src_host                 string,
  dst_host                 string,
  success                  boolean,
  window_1h_event_count    bigint,
  window_1h_unique_hosts   bigint,
  window_24h_unique_hosts  bigint,
  has_new_device           boolean,
  risk_score               int,
  risk_flags               array<string>
)
PARTITIONED BY (
  day(event_time)
)
LOCATION 's3://authpulse-dev-curated/auth_events_curated/'
TBLPROPERTIES (
  'table_type'='ICEBERG',
  'format'='parquet'
);
