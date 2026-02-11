# AuthPulse - Design Decisions

> Architecture Decision Records (ADR) documenting key technical choices

---

## Decision 1: Kinesis vs. Kafka

### Context
Need durable, scalable event streaming buffer between producer and processor.

### Options Considered
1. **Amazon Kinesis Data Streams**
2. Apache Kafka on EC2
3. Amazon MSK (Managed Kafka)

### Decision: Kinesis Data Streams

### Rationale
**Pros:**
- Fully managed (no cluster operations)
- Native AWS integration (IAM, CloudWatch, KMS)
- Pay-per-shard pricing (predictable costs)
- Built-in 24h retention, extendable to 365 days
- Automatic durability and replication across 3 AZs

**Cons:**
- Less flexible than Kafka (no topics, just shards)
- 1MB/sec write limit per shard (requires sharding for high throughput)
- Proprietary (vendor lock-in)

**Why not Kafka:**
- Higher operational overhead (even with MSK)
- Over-engineered for this use case (no need for complex topic hierarchies)
- Additional cost for broker instances

---

## Decision 2: PySpark vs. Flink

### Context
Need stream processing engine for real-time transformations and aggregations.

### Options Considered
1. **Apache Spark Structured Streaming** (PySpark)
2. Apache Flink (Python DataStream API or Java)

### Decision: PySpark on EMR

### Rationale
**Pros:**
- Unified batch + streaming API (same code for both)
- Rich DataFrame API (SQL-like transformations)
- Native Iceberg support (Spark 3.5+)
- EMR provides managed runtime
- Python ecosystem (easier development)
- Mature stateful processing (mapGroupsWithState)

**Cons:**
- Micro-batch model (not true streaming like Flink)
- Higher latency than Flink (30s trigger interval vs. millisecond in Flink)

**Why not Flink:**
- Lower-level API (more code for same logic)
- Less mature Iceberg integration
- Requires Kinesis Data Analytics (KDA) or self-managed deployment
- Python API less mature than PySpark

**Acceptable Trade-off:**
- 30-60 second latency meets our 5-minute SLA
- Micro-batching simplifies state management
- For sub-second latency requirements, would reconsider Flink

---

## Decision 3: Iceberg vs. Delta Lake vs. Hudi

### Context
Need ACID lakehouse format for S3 with schema evolution and time travel.

### Options Considered
1. **Apache Iceberg**
2. Delta Lake
3. Apache Hudi

### Decision: Apache Iceberg

### Rationale
**Pros:**
- Vendor-neutral (not tied to Databricks)
- Best-in-class Glue Catalog integration
- Efficient partition evolution (hidden partitioning)
- True time travel with snapshot isolation
- Athena natively supports Iceberg queries
- Growing ecosystem support

**Cons:**
- Slightly more complex than Delta for beginners
- Requires Spark 3.3+ for full feature set

**Why not Delta Lake:**
- Databricks-centric (though open source)
- Athena support is beta/limited
- Less flexible partition evolution

**Why not Hudi:**
- More complex operational model (copy-on-write vs. merge-on-read)
- Primarily designed for Hive-style batch updates
- Less streaming-focused than Iceberg

---

## Decision 4: EMR vs. Glue Streaming vs. Lambda

### Context
Need compute runtime for Spark streaming job.

### Options Considered
1. **Amazon EMR** (Elastic MapReduce)
2. AWS Glue Streaming Jobs
3. AWS Lambda (for simpler event processing)

### Decision: Amazon EMR

### Rationale
**Pros:**
- Full control over Spark configuration
- Can use latest Spark version (3.5+)
- Supports advanced Iceberg features
- Horizontal scaling with auto-scaling groups
- SSH access for debugging
- Cost-effective for sustained workloads

**Cons:**
- Must manage cluster lifecycle
- Need EMR expertise for tuning

**Why not Glue Streaming:**
- Limited Spark version (often 1-2 versions behind)
- Less control over executor configuration
- Higher per-DPU cost
- Slower cold start

**Why not Lambda:**
- 15-minute timeout (too short for stateful streaming)
- No native PySpark support
- Complex for windowed aggregations
- Better suited for simple event-driven transformations

---

## Decision 5: Athena vs. Redshift

### Context
Need query engine for interactive analytics and dashboards.

### Options Considered
1. **Amazon Athena**
2. Amazon Redshift Serverless
3. Redshift Provisioned

### Decision: Amazon Athena

### Rationale
**Pros:**
- Serverless (no cluster to manage)
- Pay-per-query (cost-effective for ad-hoc analysis)
- Native Iceberg support
- Direct S3 access (no ETL needed)
- Integrates with QuickSight
- Presto-based (supports complex SQL)

**Cons:**
- Slower than Redshift for complex joins
- No query result caching (unless using CTAS)
- Can get expensive for frequent large scans

**Why not Redshift:**
- Requires data loading (COPY from S3)
- Provisioned clusters = fixed cost even when idle
- Over-engineered for this use case (we don't need sub-second query latency)
- Iceberg support via Spectrum (indirect)

**Use Case Fit:**
- Dashboards refresh every 5 minutes (Athena sufficient)
- Ad-hoc investigations (pay-per-query better than 24/7 cluster)
- Direct Iceberg query (no duplication)

---

## Decision 6: QuickSight vs. Grafana

### Context
Need dashboard visualization for operations and security teams.

### Options Considered
1. **Amazon QuickSight**
2. Grafana (self-hosted or managed)
3. Tableau
4. Apache Superset

### Decision: Amazon QuickSight

### Rationale
**Pros:**
- Native Athena connector
- SPICE in-memory engine (fast dashboards)
- Embedded analytics capability (future: share dashboards)
- Pay-per-session pricing (cost-effective)
- ML-powered insights (anomaly detection)

**Cons:**
- Less flexible than Grafana for time-series
- UI customization limited

**Why not Grafana:**
- Better for time-series metrics (CloudWatch)
- Not ideal for tabular business data
- Need separate hosting (ECS/EKS)

**Hybrid Approach:**
- QuickSight for security dashboards (users, hosts, risk trends)
- CloudWatch dashboards for operational metrics (Kinesis lag, Spark health)

---

## Decision 7: Schema Validation Strategy

### Context
Need to handle malformed events without crashing pipeline.

### Options Considered
1. Fail fast (reject invalid records, stop job)
2. Dead letter queue (send invalid to DLQ, continue processing)
3. Schema enforcement with Glue Schema Registry
4. Relaxed parsing with error flagging

### Decision: Dead Letter Queue + Schema Enforcement

### Rationale
**Implementation:**
- Parse JSON with try/except in Spark
- Valid records → curated pipeline
- Invalid records → S3 DLQ (separate bucket/prefix)
- CloudWatch metric tracks invalid rate
- Alert if invalid rate > 0.1% per hour

**Why this approach:**
- Prevents invalid data from corrupting analytics
- Enables investigation of bad records (stored in DLQ)
- Doesn't halt entire pipeline for single bad event
- SLA metric enforces data quality

---

## Decision 8: Partitioning Strategy

### Context
Need efficient query performance on large Iceberg tables.

### Options Considered
1. No partitioning (small table scan)
2. Partition by `user_id`
3. Partition by `event_date`
4. Partition by `event_date` + `hour`

### Decision: Partition by `event_date`

### Rationale
**Pros:**
- Most queries filter by time range (last 24h, last 7 days)
- Daily partitions balance granularity vs. partition count
- ~365 partitions per year (manageable)
- Athena query cost reduced (scans only relevant dates)

**Cons:**
- User-specific queries scan full daily partition

**Why not hourly:**
- Too many small partitions (365 × 24 = 8760/year)
- Iceberg small file problem (increases metadata size)
- Marginal query performance gain

**Why not user_id:**
- No natural upper bound (could be 10k+ partitions)
- Uneven partition sizes (power users vs. rare users)
- Doesn't match typical query patterns (time-based investigations)

---

## Decision 9: Stateful Processing Approach

### Context
Need to track "seen computers" per user across all time.

### Options Considered
1. Window-based state (last 30 days)
2. Global state (all historical data)
3. Hybrid (recent in-memory, historical in Iceberg)

### Decision: Hybrid Approach

### Rationale
**Implementation:**
- Spark maintains recent state (30 days) in memory via mapGroupsWithState
- Checkpoint state to S3 for fault tolerance
- Periodically (nightly) merge with historical Iceberg table
- On cold start, bootstrap state from Iceberg

**Why hybrid:**
- Pure in-memory would blow up for millions of users × thousands of computers
- Pure external lookups would be too slow (latency)
- Hybrid leverages Spark distributed memory for hot data

**State Size Estimate:**
- 10k users × 100 computers avg = 1M entries
- ~50 bytes per entry = 50MB (easily fits in memory)

---

## Decision 10: Monitoring & Alerting

### Context
Need operational visibility and SLA enforcement.

### Options Considered
1. CloudWatch only
2. Prometheus + Grafana
3. Datadog / New Relic (3rd party APM)

### Decision: CloudWatch + SNS

### Rationale
**Pros:**
- Native integration (no agent installation)
- Kinesis and EMR publish metrics automatically
- Custom metrics from Spark via boto3
- SNS for email/SMS/PagerDuty integration
- Composite alarms (e.g., high lag AND low throughput)

**Cons:**
- Less flexible querying than Prometheus
- Limited retention (15 months)

**Why not 3rd party:**
- Additional cost
- Network egress for metric export
- Not needed for this project scale

**Metrics Published:**
- Kinesis: iterator age, incoming records
- Spark: batch duration, scheduling delay
- Custom: processing lag, risk distribution, invalid rate

---

## Future Considerations

### Machine Learning Integration
- Replace rule-based risk engine with ML model (SageMaker)
- Requires:
  - Feature engineering pipeline
  - Model training on historical data
  - Real-time inference endpoint
  - A/B testing framework

### Multi-Region Deployment
- For disaster recovery
- Requires:
  - Cross-region Kinesis replication
  - Multi-region S3 buckets (or S3 replication)
  - Glue Catalog replication

### Cost Optimization
- Current architecture optimized for simplicity
- For production at scale:
  - Reserved EMR capacity for long-running clusters
  - S3 Intelligent-Tiering for archival data
  - Athena query result caching
  - QuickSight SPICE usage limits

---

## References
- [Architecture Overview](architecture.md)
- [Data Flow Details](data_flow.md)
