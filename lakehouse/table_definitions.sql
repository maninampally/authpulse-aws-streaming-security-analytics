-- AuthPulse - Complete Table Definitions
-- Reference schemas for all lakehouse tables (mirrors iceberg_ddl.sql with column docs).

-- ============================================================
-- TABLE: auth_events_raw
-- Purpose: Unmodified events landed from Kinesis via Flink raw sink.
-- Source columns match the Flink S3 filesystem sink schema.
-- ============================================================
CREATE TABLE IF NOT EXISTS authpulse.auth_events_raw (
  event_time  TIMESTAMP   COMMENT 'UTC event timestamp from record',
  user_id     STRING      COMMENT 'Authenticated user identifier',
  computer_id STRING      COMMENT 'Destination host identifier',
  event_id    STRING      COMMENT 'SHA-256 dedup key (first 32 hex chars)',
  event_date  STRING      COMMENT 'Partition column yyyy-MM-dd'
)
PARTITIONED BY (event_date)
LOCATION 's3://authpulse-dev-lakehouse-289591071327/raw/auth_events/'
TBLPROPERTIES (
  'table_type' = 'ICEBERG',
  'format'     = 'parquet',
  'write_compression' = 'snappy'
);

-- ============================================================
-- TABLE: auth_events_curated
-- Purpose: Risk-enriched events with window features and risk score.
-- Partition: event_date (yyyy-MM-dd)
-- ============================================================
CREATE TABLE IF NOT EXISTS authpulse.auth_events_curated (
  event_time              TIMESTAMP  COMMENT 'UTC event timestamp',
  user_id                 STRING     COMMENT 'Authenticated user identifier',
  src_host                STRING     COMMENT 'Source host (null in LANL dataset)',
  dst_host                STRING     COMMENT 'Destination host (computer_id)',
  success                 BOOLEAN    COMMENT 'Auth success flag',
  window_1h_event_count   BIGINT     COMMENT 'Total events for user in last 1h window',
  window_1h_unique_hosts  BIGINT     COMMENT 'Distinct hosts for user in last 1h window',
  window_24h_unique_hosts BIGINT     COMMENT 'Distinct hosts for user in last 24h window',
  has_new_device          BOOLEAN    COMMENT 'True if computer_id is first-ever seen for user',
  risk_score              INT        COMMENT 'Aggregate risk score 0-100',
  risk_flags              ARRAY<STRING> COMMENT 'Triggered rule IDs e.g. [lateral_movement]',
  event_date              STRING     COMMENT 'Partition column yyyy-MM-dd'
)
PARTITIONED BY (event_date)
LOCATION 's3://authpulse-dev-lakehouse-289591071327/curated/auth_events_curated/'
TBLPROPERTIES (
  'table_type' = 'ICEBERG',
  'format'     = 'parquet',
  'write_compression' = 'snappy'
);

-- ============================================================
-- TABLE: user_behavior_hourly
-- Purpose: Per-user windowed feature aggregations (1h and 24h).
-- Produced by Flink user features sink.
-- Partition: window_size ('1h' or '24h')
-- ============================================================
CREATE TABLE IF NOT EXISTS authpulse.user_behavior_hourly (
  window_start  TIMESTAMP  COMMENT 'Window open time',
  window_end    TIMESTAMP  COMMENT 'Window close time',
  user_id       STRING     COMMENT 'User identifier',
  window_size   STRING     COMMENT 'Window label: 1h or 24h',
  unique_hosts  BIGINT     COMMENT 'Distinct hosts seen in window',
  event_count   BIGINT     COMMENT 'Total auth events in window',
  has_new_device BOOLEAN   COMMENT 'Any new device seen in window'
)
PARTITIONED BY (window_size)
LOCATION 's3://authpulse-dev-lakehouse-289591071327/features/auth_user_features/'
TBLPROPERTIES (
  'table_type' = 'ICEBERG',
  'format'     = 'parquet',
  'write_compression' = 'snappy'
);

-- ============================================================
-- TABLE: host_popularity_daily
-- Purpose: Daily host access statistics for rare-host detection.
-- Note: populated by the batch job (run_daily_batch.py).
-- ============================================================
CREATE TABLE IF NOT EXISTS authpulse.host_popularity_daily (
  event_date     STRING   COMMENT 'Partition column yyyy-MM-dd',
  computer_id    STRING   COMMENT 'Host identifier',
  access_count   BIGINT   COMMENT 'Total auth events to this host on event_date',
  unique_users   BIGINT   COMMENT 'Distinct users accessing this host on event_date',
  is_rare        BOOLEAN  COMMENT 'True if access_count below rarity threshold'
)
PARTITIONED BY (event_date)
LOCATION 's3://authpulse-dev-lakehouse-289591071327/curated/host_popularity_daily/'
TBLPROPERTIES (
  'table_type' = 'ICEBERG',
  'format'     = 'parquet',
  'write_compression' = 'snappy'
);
