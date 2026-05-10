# AuthPulse - CloudWatch Metrics & Alarms

## Kinesis Data Streams Metrics

### 1. GetRecords.IteratorAgeMilliseconds
- **Description**: Age of last record read by Lambda consumer
- **Threshold**: > 60,000 ms (1 minute) = WARNING
- **Action**: Check Lambda concurrency or increase shard count

### 2. IncomingRecords
- **Description**: Records successfully put to stream by producer
- **Use**: Validate producer is sending data; alert if drops to 0

### 3. PutRecords.Success
- **Description**: Successful PutRecords API calls
- **Use**: Monitor producer reliability

### 4. ReadProvisionedThroughputExceeded
- **Description**: Consumer throttling events
- **Threshold**: > 0
- **Action**: Increase shard count or enable Enhanced Fan-Out

---

## Lambda Consumer Metrics

### 5. Duration
- **Description**: Lambda invocation execution time
- **Threshold**: P95 > 30,000 ms = WARNING (approaching 60s timeout)
- **Action**: Profile DynamoDB latency or batch size

### 6. Errors
- **Description**: Failed Lambda invocations
- **Threshold**: > 0 consecutive failures = CRITICAL
- **Action**: Check CloudWatch Logs at `/aws/lambda/authpulse-dev-auth-processor`

### 7. Throttles
- **Description**: Lambda concurrency limit reached
- **Threshold**: > 0
- **Action**: Request concurrency limit increase or enable provisioned concurrency

### 8. ConcurrentExecutions
- **Description**: Number of Lambda instances running simultaneously
- **Use**: Scaling signal; correlates with Kinesis shard count

---

## DynamoDB Metrics

### 9. SuccessfulRequestLatency (GetItem)
- **Description**: State read latency per Lambda invocation
- **Threshold**: P99 > 10 ms = WARNING
- **Action**: Check capacity mode (should be PAY_PER_REQUEST)

### 10. SuccessfulRequestLatency (PutItem)
- **Description**: State write latency per Lambda invocation
- **Threshold**: P99 > 10 ms = WARNING

### 11. SystemErrors
- **Description**: DynamoDB internal errors
- **Threshold**: > 0
- **Action**: AWS service issue — check Service Health Dashboard

---

## Application Metrics (Custom)

### 12. InvalidRecordCount
- **Namespace**: `AuthPulse`
- **Description**: Events failing decode or schema validation in Lambda
- **Threshold**: > 0.1% per hour = SLA violation
- **Action**: SNS alert → investigate malformed producer output

### 13. ProcessingLagSeconds
- **Namespace**: `AuthPulse`
- **Description**: `processing_time - event_time` per batch
- **Threshold**: P95 > 300 seconds (5 min) = SLA violation
- **Action**: SNS alert → check Lambda errors and Kinesis iterator age

### 14. RiskScoreDistribution
- **Namespace**: `AuthPulse`
- **Description**: Event count broken down by risk level (LOW/MEDIUM/HIGH/CRITICAL)
- **Use**: Security operations dashboard — spike in HIGH/CRITICAL = active incident

---

## SNS Alert Topics

### Critical Alerts
- SLA violations (freshness P95 > 5 min, completeness > 0.1% invalid)
- Lambda consecutive errors
- Kinesis throttling

### Warning Alerts
- Iterator age > 1 minute
- Lambda P95 duration > 30s
- DynamoDB latency spike

---

## Log Groups

| Log Group | Contents |
|---|---|
| `/aws/lambda/authpulse-dev-auth-processor` | Lambda invocation logs, `batch processed=N failed=N` |
| `/authpulse-dev/dq` | Data quality check results |

---

## Useful Log Insights Queries

```sql
-- Lambda error rate last 1 hour
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() as errors by bin(5m)

-- Average batch size processed
fields @timestamp, @message
| filter @message like /batch processed/
| parse @message "batch processed=* failed=*" as processed, failed
| stats avg(processed) as avg_batch, sum(failed) as total_failed by bin(10m)
```
