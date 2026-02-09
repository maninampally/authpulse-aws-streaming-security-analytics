-- Iceberg DDL placeholder

CREATE TABLE IF NOT EXISTS user_behavior_hourly (
  hour_ts timestamp,
  user_id string,
  auth_count bigint,
  unique_machines bigint,
  anomaly_count bigint
)
PARTITIONED BY (date(hour_ts));
