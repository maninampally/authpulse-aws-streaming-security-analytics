# AuthPulse: Real-Time Authentication Risk & Behavior Analytics  
### AWS Streaming Lakehouse Project

AuthPulse is a real-time streaming security analytics platform that processes enterprise authentication events to detect abnormal behavior and generate live operational metrics.

It simulates a production-grade security pipeline using real authentication logs and an AWS streaming lakehouse architecture:

**Kinesis → Flink/Spark → S3 Iceberg → Athena → QuickSight**

This project demonstrates how modern data engineering systems handle:

- large-scale event streams
- stateful streaming logic
- anomaly detection
- dataset SLAs
- production monitoring

---

## Business Problem

Security teams need real-time visibility into authentication behavior to detect risky patterns such as:

- sudden lateral movement across machines
- abnormal login bursts
- new device spikes
- rare host access
- unusual user activity trends

Without streaming analytics, these patterns are often detected hours or days later during manual log reviews.

AuthPulse transforms raw authentication events into curated datasets, alerts, and live dashboards that support incident response and operational monitoring.

---

## Dataset

This project uses the **LANL "User-Computer Authentication Associations in Time" dataset**.

Each record is:

```
time,user,computer
```

representing a successful authentication by a user to a computer at a given time.

Key facts:

- 9 months of enterprise activity
- 708M+ authentication events
- 11k+ users
- 22k+ computers
- timestamps at 1-second resolution

Dataset source:

https://csr.lanl.gov/data/auth/

The dataset is replayed as a live event stream into Amazon Kinesis to simulate production traffic.

---

## Architecture

Event Replay  
→ Amazon Kinesis  
→ Streaming Processor (Flink/Spark)  
→ S3 Lakehouse (Iceberg)  
→ Athena / Redshift  
→ QuickSight Dashboards  
→ CloudWatch + SNS Alerts

### Components

**Replay producer**
- reads LANL files
- replays events in timestamp order
- configurable throughput (1k–10k events/sec)

**Streaming processor**
- parse & validate events
- deduplicate by event ID
- maintain per-user rolling state
- detect anomalies
- assign risk scores

**Lakehouse storage**
- raw + curated Iceberg tables in S3
- registered in AWS Glue catalog

**Analytics**
- Athena for investigations
- QuickSight dashboards

**Monitoring**
- CloudWatch lag + error metrics
- SNS alerts for SLA violations

---

## Features

- real-time authentication event streaming
- per-user behavior modeling
- rolling 1h / 24h windows
- new-device detection
- lateral movement detection
- rule-based risk scoring
- Iceberg analytics tables
- live dashboards
- dataset SLAs
- pipeline monitoring

---

## Data Model

### `auth_events_curated`

Fact table with risk context:

- event_time
- user_id
- computer_id
- risk_flags
- risk_score

Partitioned by:

- date
- optional hour

### Aggregations

`user_behavior_hourly`
- hourly auth counts
- unique machines
- anomaly counts

`host_popularity_daily`
- daily unique users per host
- alert counts

Stored as Apache Iceberg tables in S3.

---

## Tech Stack

**Streaming**
- Amazon Kinesis Data Streams
- Apache Flink (Kinesis Data Analytics)
- or Spark Structured Streaming

**Lakehouse**
- Amazon S3
- Apache Iceberg
- AWS Glue Catalog

**Analytics**
- Amazon Athena
- Amazon QuickSight

**Monitoring**
- CloudWatch
- SNS alerts

**Languages**
- Python
- Java/Scala (Flink optional)

**Infrastructure**
- Terraform or AWS CDK
- Docker

---

## Getting Started

### Clone repository

```bash
git clone https://github.com/maninampally/authpulse-aws-streaming-security-analytics.git
cd authpulse-aws-streaming-security-analytics
```

### Download dataset

Request the dataset from:

https://csr.lanl.gov/data/auth/

Place it under:

```
data/raw/auth.txt
```

Dataset is not included in repo.

---

### Deploy infrastructure

```bash
cd infra/terraform
terraform init
terraform apply
```

Creates:

- Kinesis stream
- S3 buckets
- IAM roles
- Kinesis Data Analytics app
- CloudWatch alarms
- SNS alerts

---

### Start replay producer

```bash
cd src/producer
python replay_lanl_to_kinesis.py --stream-name authpulse-stream --rate 2000
```

---

### Deploy streaming job

Upload Flink/Spark job to Kinesis Data Analytics.

Verify in CloudWatch:

- iterator lag
- throughput
- error rate

---

### Create Iceberg tables

```bash
cd src/batch
./create_iceberg_tables.sh
```

Query in Athena:

```sql
SELECT * FROM auth_events_curated LIMIT 100;
```

---

### Setup QuickSight dashboard

See:

```
dashboards/quicksight_setup.md
```

Includes:

- live overview
- risk dashboard
- behavior trends
- SLA monitoring

---

## SLAs

AuthPulse treats streaming as production:

**Freshness SLA**  
Curated data < 5 minutes behind

**Completeness SLA**  
< 0.1% invalid records per hour

CloudWatch alarms trigger SNS alerts on violations.

---

## Repository Structure

```
authpulse-aws-streaming-security-analytics/
  README.md
  pyproject.toml

  architecture/
    architecture-diagram.png
    system-overview.md
    dataflow-sequence.md

  config/
    dev.yaml
    prod.yaml
    logging.yaml

  data/
    raw/                                 # LANL dataset (gitignored)
    sample/                              # tiny samples for tests / docs

  infra/
    terraform/
      envs/
        dev/
          main.tf
          variables.tf
        prod/
          main.tf
          variables.tf
      modules/
        kinesis/
        s3/
        kda_flink/
        glue_iceberg/
        monitoring/
        iam/

  src/
    common/
    producer/
    stream/
      flink/
      spark/
    batch/
      ddl/
      jobs/
    quality/
      expectations/
      dq_reports/

  observability/
    cloudwatch_dashboards.json
    alarms/
    logs/

  dashboards/
    quicksight_setup.md
    kpi_definitions.md

  ci-cd/
    github-actions/
    tests/
      unit/
      integration/

  notebooks/
    exploration.ipynb
    threshold_tuning.ipynb

  scripts/
    setup_env.sh
    run_local_stack.sh
    load_sample_to_kinesis.sh

  docs/
    design_decisions.md
    sla_definition.md
    runbook_operations.md
    faq_interview.md
```

---

## Disclaimer

This project uses anonymized LANL authentication data for research and educational purposes only.

Dataset credit belongs to Los Alamos National Laboratory.

---

## Future Improvements

- ML anomaly detection
- adaptive risk scoring
- Kafka deployment
- multi-region failover
- automated backfill pipeline

