-- AuthPulse - Athena JSON-backed tables (Lambda output path)
-- Run each statement separately in Athena Query Editor (engine v3).

-- Statement 1: raw events (JSONL.GZ from Lambda)
CREATE EXTERNAL TABLE IF NOT EXISTS authpulse.auth_events_raw_json (
  event_time_epoch  BIGINT,
  event_time        STRING,
  user_id           STRING,
  computer_id       STRING,
  event_id          STRING
)
PARTITIONED BY (event_date STRING)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
STORED AS TEXTFILE
LOCATION 's3://authpulse-dev-lakehouse/raw/auth_events/'
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.event_date.type' = 'date',
  'projection.event_date.format' = 'yyyy-MM-dd',
  'projection.event_date.range' = '1970-01-01,NOW',
  'storage.location.template' = 's3://authpulse-dev-lakehouse/raw/auth_events/event_date=${event_date}/'
);

-- Statement 2: curated risk-enriched events (JSONL.GZ from Lambda)
CREATE EXTERNAL TABLE IF NOT EXISTS authpulse.auth_events_curated_json (
  event_time_epoch         BIGINT,
  event_time               STRING,
  user_id                  STRING,
  src_host                 STRING,
  dst_host                 STRING,
  success                  BOOLEAN,
  window_1h_event_count    BIGINT,
  window_1h_unique_hosts   BIGINT,
  window_24h_unique_hosts  BIGINT,
  has_new_device           BOOLEAN,
  risk_score               INT,
  risk_flags               ARRAY<STRING>
)
PARTITIONED BY (event_date STRING)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
STORED AS TEXTFILE
LOCATION 's3://authpulse-dev-lakehouse/curated/auth_events_curated/'
TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.event_date.type' = 'date',
  'projection.event_date.format' = 'yyyy-MM-dd',
  'projection.event_date.range' = '1970-01-01,NOW',
  'storage.location.template' = 's3://authpulse-dev-lakehouse/curated/auth_events_curated/event_date=${event_date}/'
);

-- Statement 3 (validation): count rows
SELECT COUNT(*) AS total FROM authpulse.auth_events_curated_json;

-- Statement 4 (validation): top risk events
SELECT user_id, dst_host, risk_score, risk_flags
FROM authpulse.auth_events_curated_json
WHERE risk_score > 0
ORDER BY event_time_epoch DESC
LIMIT 20;
