# AuthPulse - System Architecture

## Overview

AuthPulse is a **real-time streaming security analytics platform** built on AWS, designed to process enterprise authentication events for anomaly detection and risk scoring.

---

## Architecture Diagram

```
┌─────────────────┐
│  LANL Dataset   │
│ (708M events)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│   Replay Producer       │
│   (Python boto3)        │
│   - Reads CSV           │
│   - Generates event_id  │
│   - Rate control        │
└────────┬────────────────┘
         │ JSON events
         ▼
┌─────────────────────────┐
│  Amazon Kinesis         │
│  Data Streams           │
│  - 2-5 shards           │
│  - 24h retention        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Amazon EMR (Spark)     │
│  Structured Streaming   │
│  ┌───────────────────┐  │
│  │ Transformation    │  │
│  │ - Parse JSON      │  │
│  │ - Deduplicate     │  │
│  │ - Rolling windows │  │
│  │ - Stateful agg    │  │
│  │ - Risk engine     │  │
│  └───────────────────┘  │
└────────┬────────────────┘
         │
         ├──────────────────┬────────────────┐
         ▼                  ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  S3 Raw Zone │  │ S3 Curated   │  │ S3 Aggregates│
│  (Parquet)   │  │ (Iceberg)    │  │ (Iceberg)    │
└──────────────┘  └──────┬───────┘  └──────┬───────┘
                         │                  │
                         ▼                  ▼
                  ┌──────────────────────────────┐
                  │  AWS Glue Data Catalog       │
                  │  - authpulse.auth_events    │
                  │  - authpulse.user_behavior  │
                  │  - authpulse.host_popularity│
                  └──────┬───────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  Amazon Athena   │          │ Amazon QuickSight│
│  (SQL Queries)   │          │  (Dashboards)    │
└──────────────────┘          └──────────────────┘

         ┌────────────────────────────┐
         │  Amazon CloudWatch         │
         │  - Kinesis lag metrics     │
         │  - Spark metrics           │
         │  - Custom app metrics      │
         └────────┬───────────────────┘
                  │ Alarms
                  ▼
         ┌────────────────┐
         │  Amazon SNS    │
         │  (Alerts)      │
         └────────────────┘
```

---

## Component Details

### 1. Data Source
- **LANL Authentication Dataset**: 708M events, 9 months, time/user/computer format
- **Replay Producer**: Python script using boto3 to simulate live streaming

### 2. Ingestion Layer
- **Amazon Kinesis Data Streams**: Durable, scalable event buffer
  - Shard count: Based on throughput (1MB/s or 1000 records/s per shard)
  - Retention: 24 hours (configurable up to 365 days)
  - Partition key: `user_id` for per-user ordering

### 3. Processing Layer
- **Amazon EMR**: Managed Spark cluster
  - Instance types: r5.xlarge or r5.2xlarge (memory-optimized)
  - Auto-scaling: Based on YARN metrics
- **PySpark Structured Streaming**: Micro-batch processing
  - Trigger interval: 30 seconds
  - Checkpointing: S3-based for fault tolerance
  - Watermarking: 5 minutes for late event handling

### 4. Storage Layer
- **S3 Raw Zone**: Unmodified events (Parquet format)
- **S3 Curated Zone**: Enriched events (Iceberg format)
  - Partitioned by `event_date`
  - Schema evolution support
  - Time travel capabilities
- **AWS Glue Data Catalog**: Metadata repository
  - Centralized schema registry
  - Enables Athena and QuickSight access

### 5. Analytics Layer
- **Amazon Athena**: Serverless SQL queries
  - Presto-based query engine
  - Direct query of Iceberg tables
  - Used for ad-hoc investigations
- **Amazon QuickSight**: BI dashboards
  - Real-time operational metrics
  - Security alert visualization
  - Behavior trend analysis

### 6. Observability Layer
- **Amazon CloudWatch**: Metrics and logs
  - Kinesis iterator age
  - Spark batch duration
  - Custom processing lag metrics
- **Amazon SNS**: Alert notifications
  - SLA violation alerts
  - Pipeline error notifications

---

## Data Flow

1. **Ingestion**: Producer reads LANL CSV → generates JSON → puts to Kinesis
2. **Buffering**: Kinesis stores events with 24h retention
3. **Streaming**: Spark reads from Kinesis, processes micro-batches
4. **Transformation**: Parse → validate → deduplicate → enrich → score
5. **Persistence**: Write to S3 in Parquet/Iceberg formats
6. **Cataloging**: Register tables in Glue for SQL access
7. **Querying**: Athena/QuickSight query Iceberg tables
8. **Monitoring**: CloudWatch tracks metrics, SNS sends alerts

---

## Technology Choices

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Streaming Buffer | Kinesis | Managed, serverless, 24h retention |
| Processing Engine | PySpark on EMR | Rich streaming API, Iceberg support |
| Table Format | Apache Iceberg | ACID, schema evolution, time travel |
| Catalog | AWS Glue | Native integration with Athena/QuickSight |
| Query Engine | Athena | Serverless, cost-effective for ad-hoc queries |
| Dashboards | QuickSight | Native AWS integration, SPICE acceleration |
| Monitoring | CloudWatch | Native metrics, no additional instrumentation |

---

## Scalability Considerations

- **Kinesis**: Add shards to increase throughput (up to MBs per shard)
- **EMR**: Horizontal scaling via auto-scaling groups
- **S3**: Infinite storage, partitioned for query performance
- **Iceberg**: Supports large table evolution and efficient updates
- **Athena**: Auto-scales query concurrency

---

## Fault Tolerance

- **Kinesis**: 24h retention allows replay on failure
- **Spark**: Checkpointing enables exactly-once processing
- **S3**: 99.999999999% durability
- **Iceberg**: ACID transactions prevent partial writes

---

## Security

- **IAM**: Role-based access control for all services
- **Encryption**: At-rest (S3/Kinesis) and in-transit (TLS)
- **VPC**: EMR cluster in private subnet
- **Glue Catalog**: Resource-level permissions

---

## Next Steps

See [data_flow.md](data_flow.md) for detailed pipeline stages and [design_decisions.md](design_decisions.md) for architectural trade-offs.
