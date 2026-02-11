# AuthPulse - Key Performance Indicators (KPIs)

## Operational KPIs

### 1. Pipeline Throughput
- **Metric**: Events processed per second
- **Target**: Match producer rate (1k-10k events/sec)
- **Source**: CloudWatch Spark metrics

### 2. Data Freshness (SLA)
- **Metric**: Time between event_time and processing_time
- **Target**: < 5 minutes (P95)
- **Source**: `SELECT MAX(processing_time - event_time) FROM auth_events_curated`

### 3. Data Completeness (SLA)
- **Metric**: Invalid record rate
- **Target**: < 0.1% per hour
- **Source**: CloudWatch error metrics

### 4. Processing Lag
- **Metric**: Kinesis iterator age
- **Target**: < 1 minute
- **Source**: CloudWatch GetRecords.IteratorAgeMilliseconds

---

## Security KPIs

### 5. High-Risk Alert Rate
- **Metric**: Events with risk_level = HIGH or CRITICAL
- **Target**: < 1% of total events (tunable threshold)
- **Source**: `SELECT COUNT(*) WHERE risk_level IN ('HIGH', 'CRITICAL')`

### 6. New Device Rate
- **Metric**: First-time computer authentications
- **Target**: Monitor trend (no fixed target)
- **Source**: `SELECT COUNT(*) WHERE is_new_device = 1`

### 7. Lateral Movement Incidents
- **Metric**: Users flagged for lateral movement
- **Target**: Zero expected for normal users
- **Source**: `SELECT COUNT(DISTINCT user_id) WHERE is_lateral_movement = 1`

### 8. Burst Login Incidents
- **Metric**: Users with login bursts
- **Target**: Monitor and investigate
- **Source**: `SELECT COUNT(*) WHERE is_burst_login = 1`

---

## Business KPIs

### 9. Active Users per Hour
- **Metric**: Distinct users authenticating
- **Source**: `user_behavior_hourly` table

### 10. Host Coverage
- **Metric**: Percentage of hosts accessed daily
- **Source**: `host_popularity_daily` table

---

## Dashboard Recommendations

### QuickSight Dashboard 1: Real-Time Operations
- Live event throughput (events/sec)
- Processing lag gauge
- Error rate trend
- Freshness SLA status

### QuickSight Dashboard 2: Security Alerts
- High-risk events (last 24h)
- Top risky users
- Top risky hosts
- Risk flag distribution (pie chart)

### QuickSight Dashboard 3: Behavior Trends
- Daily active users
- Login patterns by hour
- Computer access distribution
- New device trend
