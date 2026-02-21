-- Day 8: Sample Athena queries for validating Iceberg tables.

-- -----------------------------------------------------------------------------
-- Curated events
-- -----------------------------------------------------------------------------

-- Peek latest curated events
SELECT *
FROM lakehouse.auth_events_curated
ORDER BY event_time DESC
LIMIT 20;

-- High-risk events in the last 24 hours
SELECT user_id, dst_host, event_time, risk_score, risk_flags
FROM lakehouse.auth_events_curated
WHERE event_time >= current_timestamp - interval '1' day
  AND risk_score >= 50
ORDER BY risk_score DESC
LIMIT 50;

-- Top risky users by average risk
SELECT user_id, avg(risk_score) AS avg_risk, count(*) AS events
FROM lakehouse.auth_events_curated
GROUP BY user_id
ORDER BY avg_risk DESC
LIMIT 10;

-- Count events by risk score bucket
SELECT
  CASE
    WHEN risk_score >= 75 THEN 'CRITICAL'
    WHEN risk_score >= 50 THEN 'HIGH'
    WHEN risk_score >= 25 THEN 'MEDIUM'
    ELSE 'LOW'
  END AS risk_level,
  count(*) AS events
FROM lakehouse.auth_events_curated
GROUP BY 1
ORDER BY events DESC;

-- -----------------------------------------------------------------------------
-- User behavior (hourly / windowed)
-- -----------------------------------------------------------------------------

-- Latest hourly windows (1h)
SELECT window_start, window_end, user_id, unique_hosts, event_count, has_new_device
FROM lakehouse.user_behavior_hourly
WHERE window_size = '1h'
ORDER BY window_start DESC
LIMIT 50;

-- Users with most unique hosts over last 24h window
SELECT window_start, user_id, unique_hosts, event_count, has_new_device
FROM lakehouse.user_behavior_hourly
WHERE window_size = '24h'
ORDER BY unique_hosts DESC
LIMIT 50;

-- -----------------------------------------------------------------------------
-- Host popularity (daily)
-- -----------------------------------------------------------------------------

-- Top hosts by distinct users for a given day
-- (replace DATE '2026-02-21' with a date you have data for)
SELECT host_id, distinct_users, total_events
FROM lakehouse.host_popularity_daily
WHERE event_date = DATE '2026-02-21'
ORDER BY distinct_users DESC
LIMIT 50;

-- -----------------------------------------------------------------------------
-- Example join (behavior -> curated)
-- -----------------------------------------------------------------------------

-- Join high-risk events with the latest 1h features for the same user.
-- (This is a simple example; you can tighten the time logic as needed.)
SELECT
  e.user_id,
  e.event_time,
  e.dst_host,
  e.risk_score,
  e.risk_flags,
  b.unique_hosts AS unique_hosts_1h,
  b.event_count AS event_count_1h,
  b.has_new_device
FROM lakehouse.auth_events_curated e
LEFT JOIN lakehouse.user_behavior_hourly b
  ON e.user_id = b.user_id
 AND b.window_size = '1h'
WHERE e.event_time >= current_timestamp - interval '1' day
  AND e.risk_score >= 50
ORDER BY e.risk_score DESC
LIMIT 50;
