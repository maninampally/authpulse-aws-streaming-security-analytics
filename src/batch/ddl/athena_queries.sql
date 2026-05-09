-- AuthPulse - Athena Query Examples
-- Production queries for security analytics and investigations.
-- All queries target the authpulse Glue catalog (Iceberg tables).

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

SELECT
    DATE_FORMAT(event_time, '%Y-%m-%d %H:%i')  AS minute_bucket,
    COUNT(*)                                    AS events
FROM authpulse.auth_events_curated
WHERE event_date = DATE_FORMAT(CURRENT_DATE, '%Y-%m-%d')
GROUP BY DATE_FORMAT(event_time, '%Y-%m-%d %H:%i')
ORDER BY minute_bucket DESC
LIMIT 120;

SELECT
    DATE_FORMAT(event_time, '%Y-%m-%d %H:00') AS hour_bucket,
    COUNT(DISTINCT user_id)                    AS unique_users,
    COUNT(*)                                   AS total_events
FROM authpulse.auth_events_curated
WHERE event_date >= DATE_FORMAT(DATE_ADD('day', -1, CURRENT_DATE), '%Y-%m-%d')
GROUP BY DATE_FORMAT(event_time, '%Y-%m-%d %H:00')
ORDER BY hour_bucket DESC;

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