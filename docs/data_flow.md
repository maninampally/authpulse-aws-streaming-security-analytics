# AuthPulse - Data Flow Details

## End-to-End Pipeline Stages

---

## Stage 1: Event Generation

### Input
- **Source**: LANL authentication dataset
- **Format**: CSV with 3 columns: `time,user,computer`
- **Volume**: 708M+ records

### Transform
```python
# Replay producer transforms raw CSV into JSON events
{
  "event_id": "a3b2c1d4...",           # SHA256(time|user|computer)[:32]
  "event_time": "2026-01-15T10:30:45Z", # ISO 8601 UTC
  "user_id": "U123",
  "computer_id": "C456",
  "ingestion_time": "2026-01-15T10:30:47Z"
}
```

### Output
- **Destination**: Amazon Kinesis Data Streams
- **Partition Key**: `user_id` (ensures per-user ordering)
- **Rate**: 1k-10k events/sec (configurable)

---

## Stage 2: Stream Ingestion

### Kinesis Processing
- Events buffered in shards (24h retention)
- Consumer (Spark) reads with GetRecords API
- Iterator tracks position in stream
- At-least-once delivery guarantee

---

## Stage 3: Spark Structured Streaming

### 3.1 - Source Read
```python
kinesis_df = spark.readStream \
    .format("kinesis") \
    .option("streamName", "authpulse-stream") \
    .option("region", "us-east-1") \
    .option("startingPosition", "TRIM_HORIZON") \
    .load()
```

### 3.2 - JSON Parsing
```python
parsed_df = kinesis_df.selectExpr("CAST(data AS STRING) as json") \
    .select(from_json("json", RAW_AUTH_EVENT_SCHEMA).alias("event")) \
    .select("event.*")
```

### 3.3 - Deduplication
```python
# Use event_id to drop duplicates within watermark window
deduped_df = parsed_df \
    .withWatermark("event_time", "5 minutes") \
    .dropDuplicates(["event_id"])
```

### 3.4 - Rolling Window Metrics
```python
# Compute per-user 1h and 24h aggregates
windowed_df = deduped_df \
    .withColumn("login_count_1h", count().over(user_1h_window)) \
    .withColumn("unique_computers_1h", countDistinct("computer_id").over(user_1h_window)) \
    .withColumn("login_count_24h", count().over(user_24h_window)) \
    .withColumn("unique_computers_24h", countDistinct("computer_id").over(user_24h_window))
```

### 3.5 - Stateful Device Tracking
```python
# Maintain set of all computers seen per user (ever)
# Uses mapGroupsWithState for stateful processing
stateful_df = windowed_df \
    .groupByKey(lambda x: x.user_id) \
    .mapGroupsWithState(update_seen_computers)
```

### 3.6 - Risk Engine Application
```python
# Apply rule-based risk detection
risk_df = stateful_df \
    .transform(detect_new_device) \
    .transform(detect_burst_login) \
    .transform(detect_lateral_movement) \
    .transform(detect_rare_host) \
    .transform(compute_risk_score)
```

---

## Stage 4: Dual Sink Strategy

### Sink 1: Raw Zone (S3 Parquet)
- **Purpose**: Unmodified archival for replay/audit
- **Format**: Parquet (columnar, compressed)
- **Partitioning**: By ingestion date/hour
- **Retention**: Long-term (can apply lifecycle policy)

```python
raw_query = parsed_df.writeStream \
    .format("parquet") \
    .option("path", "s3://bucket/raw/auth_events") \
    .option("checkpointLocation", "s3://bucket/checkpoints/raw") \
    .partitionBy("ingestion_date") \
    .start()
```

### Sink 2: Curated Zone (S3 Iceberg)
- **Purpose**: Enriched events with risk analytics
- **Format**: Apache Iceberg
- **Partitioning**: By `event_date` (logical date from event_time)
- **Features**: Schema evolution, ACID, time travel

```python
curated_query = risk_df.writeStream \
    .format("iceberg") \
    .option("path", "s3://bucket/curated/auth_events") \
    .option("checkpointLocation", "s3://bucket/checkpoints/curated") \
    .option("catalog", "glue_catalog") \
    .option("database", "authpulse") \
    .option("table", "auth_events_curated") \
    .partitionBy("event_date") \
    .start()
```

### Sink 3: Aggregation Tables (Iceberg)
- **User Behavior Hourly**: Aggregated by 1-hour tumbling windows
- **Host Popularity Daily**: Aggregated by date

---

## Stage 5: Catalog Registration

### AWS Glue Data Catalog
- Iceberg tables automatically register metadata
- Schema stored centrally
- Enables cross-service access (Athena, QuickSight, Redshift Spectrum)

```sql
-- Visible in Glue Catalog as:
-- Database: authpulse
-- Tables:
--   - auth_events_raw
--   - auth_events_curated
--   - user_behavior_hourly
--   - host_popularity_daily
```

---

## Stage 6: Query & Analytics

### Athena Queries
```sql
-- Example: High-risk users in last hour
SELECT 
    user_id,
    COUNT(*) as event_count,
    SUM(risk_score) as total_risk,
    ARRAY_AGG(DISTINCT risk_flags) as flags
FROM authpulse.auth_events_curated
WHERE event_time >= NOW() - INTERVAL '1' HOUR
  AND risk_level IN ('HIGH', 'CRITICAL')
GROUP BY user_id
ORDER BY total_risk DESC
LIMIT 20;
```

### QuickSight Dashboards
- Connect to Athena datasets
- Use SPICE for fast in-memory queries
- Auto-refresh on schedule (e.g., every 5 minutes)

---

## Stage 7: Monitoring

### CloudWatch Metrics Publication
```python
# Custom metric from Spark job
import boto3
cloudwatch = boto3.client('cloudwatch')

cloudwatch.put_metric_data(
    Namespace='AuthPulse',
    MetricData=[{
        'MetricName': 'ProcessingLagSeconds',
        'Value': (processing_time - event_time).total_seconds(),
        'Unit': 'Seconds'
    }]
)
```

### SLA Checks
- **Freshness**: Query max(processing_time - event_time) < 5 min
- **Completeness**: Error count / total count < 0.1%
- **Availability**: Recent partition exists in Iceberg table

### Alerting Logic
```python
if freshness_p95 > 300:  # 5 minutes in seconds
    send_sns_alert(
        topic='authpulse-sla-violations',
        subject='ALERT: Freshness SLA Breach',
        message=f'Processing lag at {freshness_p95}s exceeds 300s threshold'
    )
```

---

## Data Lineage

```
LANL CSV
  → Replay Producer (Python)
    → Kinesis Stream (JSON events)
      → Spark Streaming (micro-batch processing)
        ├→ S3 Raw Zone (Parquet, archival)
        └→ S3 Curated Zone (Iceberg, analytics)
            → Glue Catalog (metadata)
              → Athena (ad-hoc SQL)
              → QuickSight (dashboards)
              → CloudWatch (monitoring)
                → SNS (alerts)
```

---

## Critical Paths

### Latency Path (Event to Query)
1. Producer → Kinesis: ~10ms
2. Kinesis buffering: ~0-30s (trigger interval)
3. Spark processing: ~5-15s per micro-batch
4. S3 write: ~2-5s
5. Glue catalog sync: ~1s
6. **Total E2E latency: ~30-60 seconds** (well under 5-minute SLA)

### Throughput Path
- Producer: 2000 events/sec
- Kinesis: 2000 events/sec (2 shards @ 1000/shard)
- Spark: 5000+ events/sec (EMR cluster with 5 executors)
- S3: No limit (distributed writes)

---

## Failure Recovery

### Scenario: Spark Job Crashes
1. Checkpoints stored in S3 preserve state
2. Job restarts from last checkpoint
3. Kinesis retention allows replay of missed events
4. Result: Exactly-once semantics maintained

### Scenario: Kinesis Throttling
1. Spark automatically retries reads
2. Backpressure slows down processing
3. Alert triggered if iterator age > 1 min
4. Resolution: Add shards or optimize Spark

---

## Performance Optimizations

1. **Predicate Pushdown**: Iceberg uses partition pruning (query only relevant event_date)
2. **Columnar Storage**: Parquet/Iceberg store by column for efficient analytics
3. **Partitioning**: Reduces scan volume (daily partitions = 1/365 of data)
4. **Caching**: Spark caches stateful aggregates in memory
5. **Compaction**: Iceberg periodically compacts small files

---

See [architecture.md](architecture.md) for system design and [design_decisions.md](design_decisions.md) for rationale behind choices.
