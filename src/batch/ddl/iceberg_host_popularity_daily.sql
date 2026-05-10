-- AuthPulse - Host Popularity Daily Table DDL
-- Run each statement separately in Athena Query Editor (engine v3).

-- Statement 1: database (skip if already created)
CREATE DATABASE IF NOT EXISTS authpulse
COMMENT 'AuthPulse streaming lakehouse database';

-- Statement 2: host popularity daily aggregates
CREATE TABLE IF NOT EXISTS authpulse.host_popularity_daily (
  event_date     DATE,
  host_id        VARCHAR,
  distinct_users BIGINT,
  total_events   BIGINT
)
LOCATION 's3://authpulse-dev-lakehouse-604743481383/curated/host_popularity_daily/'
TBLPROPERTIES ('table_type' = 'ICEBERG', 'format' = 'parquet');
