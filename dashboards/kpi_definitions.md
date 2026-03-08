# KPI Definitions

KPI formulas used in CloudWatch dashboards, Athena queries, and SLA checks.

---

## Operational KPIs

### 1. Data Freshness
```
freshness_seconds = AVG(processing_time - event_time)  [seconds, P95]
Target: freshness_seconds < 300  (5 minutes)
SLA breach: freshness_seconds >= 300
```
Source: `analytics/athena_queries.sql` — Query 7 (Data Freshness Check)

### 2. Invalid Record Rate
```
invalid_record_rate = (invalid_count / total_count) * 100  [%]
Target: invalid_record_rate < 0.1%
```
Source: CloudWatch custom metric `AuthPulse/InvalidRecordRate`

### 3. Pipeline Throughput
```
throughput_eps = events_processed / window_seconds  [events/sec]
Target: throughput_eps >= producer_rate
```
Source: CloudWatch `Kinesis/IncomingRecords` (1-min sum / 60)

### 4. Kinesis Consumer Lag
```
iterator_age_ms = GetRecords.IteratorAgeMilliseconds  [ms]
Target: iterator_age_ms < 60000  (1 minute)
```
Source: CloudWatch Kinesis namespace, stream `authpulse-dev-stream`

### 5. Flink Checkpoint Duration
```
checkpoint_duration_ms = lastCheckpointDuration  [ms]
Target: checkpoint_duration_ms < 10000  (10 seconds)
```
Source: KDA v2 CloudWatch application metrics

---

## Security KPIs

### 6. High-Risk Alert Rate
```
risk_rate = (high_critical_events / total_events) * 100  [%]
Baseline: < 1% of events (tunable)
```
```sql
SELECT
  COUNT_IF(risk_level IN ('HIGH','CRITICAL')) * 100.0 / COUNT(*) AS risk_rate
FROM authpulse.auth_events_curated
WHERE event_date = CURRENT_DATE;
```

### 7. New Device Rate
```
new_device_rate = (is_new_device_count / total_events) * 100  [%]
```
```sql
SELECT
  SUM(is_new_device) * 100.0 / COUNT(*) AS new_device_rate
FROM authpulse.auth_events_curated
WHERE event_date = CURRENT_DATE;
```

### 8. Lateral Movement Incidents
```
lateral_move_count = COUNT events WHERE is_lateral_movement = 1 per hour
```
```sql
SELECT
  DATE_TRUNC('hour', event_time) AS hour,
  COUNT(DISTINCT user_id) AS users_flagged
FROM authpulse.auth_events_curated
WHERE is_lateral_movement = 1
  AND event_date = CURRENT_DATE
GROUP BY 1
ORDER BY 1;
```

### 9. Average Risk Score (by hour)
```
avg_risk_score = AVG(risk_score) per tumbling 1-hour window
```
```sql
SELECT
  window_start,
  SUM(total_risk_score) * 1.0 / NULLIF(SUM(total_logins), 0) AS avg_risk_score
FROM authpulse.user_behavior_hourly
WHERE window_start >= CURRENT_TIMESTAMP - INTERVAL '24' HOUR
GROUP BY window_start
ORDER BY window_start;
```

### 10. Rare Host Access Count
```
rare_host_events = COUNT events WHERE is_rare_host = 1 per day
```
```sql
SELECT
  event_date,
  SUM(is_rare_host) AS rare_host_events
FROM authpulse.auth_events_curated
GROUP BY event_date
ORDER BY event_date DESC;
```

---

## Risk Score Formula

```
risk_score = (is_new_device       * 30)
           + (is_burst_login      * 25)
           + (is_lateral_movement * 35)
           + (is_rare_host        * 10)

Risk Level:
  LOW      :  0 – 25
  MEDIUM   : 26 – 50
  HIGH     : 51 – 75
  CRITICAL : 76+
```

---

## CloudWatch Dashboard Widgets

| Widget | Metric / Query | Alarm Threshold |
|--------|---------------|------------------|
| Freshness (P95) | Athena Query 7 result | > 300s |
| Invalid Record % | `AuthPulse/InvalidRecordRate` | > 0.1% |
| Kinesis Iterator Age | `GetRecords.IteratorAgeMilliseconds` | > 60000 ms |
| Flink Checkpoint Duration | KDA `lastCheckpointDuration` | > 10000 ms |
| Events / min | Kinesis `IncomingRecords` 1-min sum | — |
| High-Risk Events / hr | Custom `AuthPulse/HighRiskCount` | > 500 |
