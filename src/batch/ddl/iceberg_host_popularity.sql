-- Iceberg DDL placeholder

CREATE TABLE IF NOT EXISTS host_popularity_daily (
  day_ts date,
  computer_id string,
  unique_users bigint,
  alert_count bigint
)
PARTITIONED BY (day_ts);
