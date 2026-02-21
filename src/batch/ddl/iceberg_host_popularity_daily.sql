-- Day 8: Athena + Glue Catalog (Iceberg)
-- Creates the host popularity table (daily aggregates) for later population.

CREATE DATABASE IF NOT EXISTS lakehouse;

CREATE TABLE IF NOT EXISTS lakehouse.host_popularity_daily (
  event_date      date,
  host_id         string,
  distinct_users  bigint,
  total_events    bigint
)
PARTITIONED BY (
  event_date
)
LOCATION 's3://authpulse-dev-curated/host_popularity_daily/'
TBLPROPERTIES (
  'table_type'='ICEBERG',
  'format'='parquet'
);
