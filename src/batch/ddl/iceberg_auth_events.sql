-- Iceberg DDL placeholder
-- Create curated auth events table

CREATE TABLE IF NOT EXISTS auth_events_curated (
  event_time timestamp,
  user_id string,
  computer_id string,
  risk_flags array<string>,
  risk_score int
)
PARTITIONED BY (date(event_time));
