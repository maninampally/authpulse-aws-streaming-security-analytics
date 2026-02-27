-- AuthPulse - Athena Query Examples
-- Production queries for security analytics and investigations.
-- All queries target the authpulse Glue catalog (Iceberg tables).
-- Replace '<TODAY>' with the current date string, e.g. '2026-02-26'.

-- ============================================================
-- QUERY 1: High-Risk Users (Last 24 Hours)
-- Returns users with the highest aggregate risk scores, ordered
-- by max risk_score descending. Use to triage top threats.
-- SLA tie: feeds the "top risky users" KPI on the dashboard.
-- ============================================================
SELECT
    user_id,
    COUNT(*)                          AS event_count,
    MAX(risk_score)                   AS max_risk_score,
    SUM(risk_score)                   AS total_risk_score,
    ARRAY_AGG(DISTINCT risk_flag)     AS triggered_rules
FROM authpulse.auth_events_curated
CROSS JOIN UNNEST(risk_flags) AS t(risk_flag)
WHERE event_date >= DATE_FORMAT(DATE_ADD('day', -1, CURRENT_DATE), '%Y-%m-%d')
  AND risk_score  > 0
GROUP BY user_id
ORDER BY max_risk_score DESC, total_risk_score DESC
LIMIT 50;


-- ============================================================
-- QUERY 2: Top Risky Hosts (Last 24 Hours)
-- Ranks destination hosts by number of high-risk events (score >= 35).
-- Useful for identifying compromised or targeted machines.
-- ============================================================
SELECT
    dst_host,
    COUNT(*)                       AS high_risk_events,
    COUNT(DISTINCT user_id)        AS distinct_users,
    MAX(risk_score)                AS max_risk_score,
    ARRAY_AGG(DISTINCT risk_flag)  AS triggered_rules
FROM authpulse.auth_events_curated
CROSS JOIN UNNEST(risk_flags) AS t(risk_flag)
WHERE event_date >= DATE_FORMAT(DATE_ADD('day', -1, CURRENT_DATE), '%Y-%m-%d')
  AND risk_score >= 35
  AND dst_host   IS NOT NULL
GROUP BY dst_host
ORDER BY high_risk_events DESC
LIMIT 50;


-- ============================================================
-- QUERY 3: Events Per Minute (Real-Time Throughput)
-- Monitors pipeline throughput. Compare against Kinesis IncomingRecords
-- to verify end-to-end latency and detect drops.
-- SLA tie: if events/min drops to 0 during expected load -> lag alarm.
-- ============================================================
SELECT
    DATE_FORMAT(event_time, '%Y-%m-%d %H:%i')  AS minute_bucket,
    COUNT(*)                                    AS events
FROM authpulse.auth_events_curated
WHERE event_date = DATE_FORMAT(CURRENT_DATE, '%Y-%m-%d')
GROUP BY DATE_FORMAT(event_time, '%Y-%m-%d %H:%i')
ORDER BY minute_bucket DESC
LIMIT 120;   -- last 2 hours at 1-min granularity


-- ============================================================
-- QUERY 4: Unique Users Per Hour
-- Baseline activity metric. Sudden drops indicate producer or
-- Flink job issues; spikes may indicate credential stuffing.
-- ============================================================
SELECT
    DATE_FORMAT(event_time, '%Y-%m-%d %H:00') AS hour_bucket,
    COUNT(DISTINCT user_id)                    AS unique_users,
    COUNT(*)                                   AS total_events
FROM authpulse.auth_events_curated
WHERE event_date >= DATE_FORMAT(DATE_ADD('day', -1, CURRENT_DATE), '%Y-%m-%d')
GROUP BY DATE_FORMAT(event_time, '%Y-%m-%d %H:00')
ORDER BY hour_bucket DESC;


-- ============================================================
-- QUERY 5: Lateral Movement Detection
-- Users who accessed >= 10 distinct hosts within any 1-hour window.
-- Directly maps to the lateral_movement risk rule threshold.
-- SLA tie: risk_score contribution = 35 pts for lateral_movement.
-- ============================================================
SELECT
    user_id,
    window_start,
    window_end,
    unique_hosts,
    event_count
FROM authpulse.user_behavior_hourly
WHERE window_size   = '1h'
  AND unique_hosts  >= 10
  AND window_start  >= DATE_ADD('hour', -24, NOW())
ORDER BY unique_hosts DESC, window_start DESC
LIMIT 100;


-- ============================================================
-- QUERY 6: New Device Alerts (Last 24 Hours)
-- Events where a user authenticated from a host never seen before.
-- Each row is a potential account takeover or new endpoint.
-- ============================================================
SELECT
    event_time,
    user_id,
    dst_host,
    risk_score,
    risk_flags
FROM authpulse.auth_events_curated
WHERE event_date       >= DATE_FORMAT(DATE_ADD('day', -1, CURRENT_DATE), '%Y-%m-%d')
  AND has_new_device   = TRUE
ORDER BY event_time DESC
LIMIT 200;


-- ============================================================
-- QUERY 7: Data Freshness Check (SLA Monitoring)
-- Measures the lag between the latest curated event_time and NOW().
-- Target SLA: lag < 5 minutes (300 seconds).
-- Alert if lag_seconds > 300.
-- ============================================================
SELECT
    MAX(event_time)                                                  AS latest_event_time,
    CURRENT_TIMESTAMP                                                AS query_time,
    DATE_DIFF('second', MAX(event_time), CURRENT_TIMESTAMP)         AS lag_seconds,
    CASE
        WHEN DATE_DIFF('second', MAX(event_time), CURRENT_TIMESTAMP) <= 300
            THEN 'OK'
        ELSE 'SLA_BREACH'
    END                                                              AS freshness_status
FROM authpulse.auth_events_curated
WHERE event_date >= DATE_FORMAT(DATE_ADD('day', -1, CURRENT_DATE), '%Y-%m-%d');
