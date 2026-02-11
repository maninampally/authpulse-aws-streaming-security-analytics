# AuthPulse - CloudWatch Metrics & Alarms

## Kinesis Data Streams Metrics

### 1. GetRecords.IteratorAgeMilliseconds
- **Description**: Age of last record read from stream
- **Threshold**: > 60000 ms (1 minute) = WARNING
- **Action**: Check Spark processing capacity

### 2. IncomingRecords
- **Description**: Records successfully put to stream
- **Use**: Validate producer is sending data

### 3. PutRecords.Success
- **Description**: Successful put_records calls
- **Use**: Monitor producer reliability

### 4. ReadProvisionedThroughputExceeded
- **Description**: Consumer throttling
- **Threshold**: > 0
- **Action**: Increase shard count or consumer capacity

---

## EMR Spark Streaming Metrics

### 5. StreamingInputRate
- **Description**: Records/second processed by Spark
- **Use**: Monitor throughput

### 6. StreamingBatchDuration
- **Description**: Time to process each micro-batch
- **Threshold**: > 30 seconds (exceeds trigger interval)
- **Action**: Optimize transformations or increase cluster size

### 7. StreamingSchedulingDelay
- **Description**: Queue time before batch processing starts
- **Threshold**: Growing trend = backlog building
- **Action**: Scale cluster

### 8. ExecutorMemoryUsed
- **Description**: Memory consumption
- **Threshold**: > 80% of available
- **Action**: Tune Spark config or add executors

---

## Application Metrics (Custom)

### 9. InvalidRecordCount
- **Description**: Events failing schema validation
- **Threshold**: > 0.1% per hour = SLA violation
- **Action**: SNS alert to on-call engineer

### 10. ProcessingLagSeconds
- **Description**: processing_time - event_time
- **Threshold**: P95 > 300 seconds (5 min) = SLA violation
- **Action**: SNS alert + investigate bottleneck

### 11. RiskScoreDistribution
- **Description**: Count by risk_level (LOW/MEDIUM/HIGH/CRITICAL)
- **Use**: Security monitoring dashboard

---

## SNS Alert Topics

### Critical Alerts (PagerDuty)
- SLA violations (freshness or completeness)
- Spark job failures
- Kinesis throttling

### Warning Alerts (Email)
- Iterator age > 1 minute
- Batch duration increasing
- High risk event spike

---

## CloudWatch Dashboard Layout

```
+---------------------------+---------------------------+
| Kinesis Throughput        | Spark Processing Rate     |
| (IncomingRecords/sec)     | (StreamingInputRate)      |
+---------------------------+---------------------------+
| Processing Lag            | Error Rate                |
| (P95 lag in seconds)      | (Invalid %)               |
+---------------------------+---------------------------+
| Iterator Age              | Batch Duration            |
| (GetRecords.Iterator...)  | (StreamingBatch...)       |
+---------------------------+---------------------------+
| High-Risk Events (24h)    | SLA Status                |
| (Count by risk_level)     | (GREEN/YELLOW/RED)        |
+---------------------------+---------------------------+
```

---

## Implementation Notes

- Use CloudWatch Logs Insights for custom metric extraction
- Publish application metrics from Spark using CloudWatch SDK
- Set up SNS topics with email/SMS/PagerDuty subscriptions
- Create CloudWatch alarms with composite conditions
