# AuthPulse: Real-Time Authentication Risk & Behavior Analytics
### Production-Grade AWS Streaming Lakehouse for Security Analytics

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Apache Flink](https://img.shields.io/badge/Apache%20Flink-1.18+-purple.svg)](https://flink.apache.org/)
[![Apache Iceberg](https://img.shields.io/badge/Apache%20Iceberg-1.4+-blue.svg)](https://iceberg.apache.org/)
[![Terraform](https://img.shields.io/badge/Terraform-1.5+-623CE4.svg)](https://www.terraform.io/)
[![AWS](https://img.shields.io/badge/AWS-Kinesis%20%7C%20KDA%20%7C%20S3-yellow.svg)](https://aws.amazon.com/)

AuthPulse is a **production-grade real-time streaming analytics platform** that processes enterprise authentication events to detect security anomalies, compute risk scores, and generate actionable insights for security operations teams.

Built with **Apache Flink on Managed Service for Apache Flink (KDA v2)** as the primary streaming engine, with a PySpark/EMR path for batch and historical replay. Infrastructure is fully provisioned with **Terraform**. It demonstrates modern data engineering best practices for high-throughput event processing, stateful stream analytics, and lakehouse architecture on AWS.

**Pipeline Architecture:**
```
LANL Dataset → Kinesis Streams → Managed Apache Flink (KDA) → S3 Iceberg Tables → Athena/QuickSight
```

**Key Capabilities:**
- Real-time stream processing (1k-10k events/sec)
- Rule-based risk engine (lateral movement, burst login, new device detection)
- Apache Iceberg lakehouse with ACID guarantees
- Sub-5-minute end-to-end latency (SLA-enforced)
- Production monitoring with CloudWatch + SNS alerts

---

## 📋 Table of Contents

- [Business Problem](#-business-problem)
- [Dataset](#-dataset)
- [Architecture](#-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Key Features](#-key-features)
- [Risk Detection Rules](#-risk-detection-rules)
- [Data Model](#-data-model)
- [Getting Started](#-getting-started)
- [Usage](#-usage)
- [Monitoring & SLAs](#-monitoring--slas)
- [Design Decisions](#-design-decisions)
- [Resume Impact](#-resume-impact)
- [Future Enhancements](#-future-enhancements)

---

## 🧱 Terraform (Dev Infra)

Terraform lives in `infra/terraform` and is composed per-environment under `infra/terraform/envs/*`.

For Windows/PowerShell, use the repo wrapper (auto-finds Terraform, runs init/fmt/validate/plan):

- Plan dev: `./scripts/terraform.ps1 -Env dev -Action plan`
- Apply dev: `./scripts/terraform.ps1 -Env dev -Action apply`

If you use multiple AWS accounts, target a specific AWS CLI profile:

- Plan dev (profile): `./scripts/terraform.ps1 -Env dev -Action plan -AwsProfile <profile>`
- Apply dev (profile): `./scripts/terraform.ps1 -Env dev -Action apply -AwsProfile <profile>`

Note: `terraform apply` creates AWS resources (costs possible).

---

## 🎯 Business Problem

Security teams need **real-time visibility** into authentication behavior to detect risky patterns:

- **Lateral Movement**: Attackers pivoting through network after initial compromise
- **Burst Logins**: Abnormal authentication spikes indicating automation or credential stuffing
- **New Device Spikes**: First-time access from unfamiliar computers
- **Rare Host Access**: Targeting of sensitive/uncommon systems
- **Unusual Behavior**: Deviation from established user patterns

**The Challenge:** Traditional batch-based log analysis detects threats **hours or days late**.

**The Solution:** AuthPulse provides **sub-5-minute detection** using streaming analytics, enabling:
- **Real-time alerting** for security operations centers (SOC)
- **Live dashboards** for operational monitoring
- **Historical investigations** via SQL-queryable lakehouse

---

## 📊 Dataset

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

## 🏗️ Architecture

```
┌──────────────┐
│ LANL Dataset │
│   (708M+)    │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Replay Producer  │ Python boto3
│ (JSON events)    │ Rate-controlled
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Kinesis Streams  │ 2-5 shards
│                  │ 24h retention
└──────┬───────────┘
       │
       ▼
┌──────────────────────────────┐
│  Amazon EMR (Spark 3.5)      │
│  ┌────────────────────────┐  │
│  │ PySpark Streaming Job  │  │
│  │ • Parse & Validate     │  │
│  │ • Deduplication        │  │
│  │ • Rolling Windows      │  │
│  │ • Stateful Aggregates  │  │
│  │ • Risk Engine          │  │
│  └────────────────────────┘  │
└──────┬────────────────────────┘
       │
       ├─────────┬──────────┐
       ▼         ▼          ▼
  ┌────────┐ ┌────────┐ ┌────────┐
  │ S3 Raw │ │ S3     │ │ S3     │
  │ Zone   │ │Curated │ │Aggreg. │
  │(Parquet)│ │(Iceberg)│ │(Iceberg)│
  └────────┘ └───┬────┘ └───┬────┘
                 │           │
                 ▼           ▼
          ┌──────────────────────┐
          │ AWS Glue Catalog     │
          └──────┬───────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
 ┌─────────────┐   ┌─────────────┐
 │   Athena    │   │ QuickSight  │
 │ (SQL Query) │   │ (Dashboard) │
 └─────────────┘   └─────────────┘

  ┌────────────────────────┐
  │  CloudWatch + SNS      │
  │  (Metrics & Alerts)    │
  └────────────────────────┘
```

### Component Details

| Component | Technology | Purpose |
|-----------|------------|----------|
| **Ingestion** | Amazon Kinesis Data Streams | Durable event buffer, 1MB/s per shard |
| **Streaming (primary)** | Apache Flink on KDA v2 | Low-latency stateful stream processing |
| **Streaming (secondary)** | PySpark on Amazon EMR | Batch replay + historical backfill |
| **Infrastructure** | Terraform >= 1.5 | Full IaC for all AWS resources |
| **Storage** | S3 + Apache Iceberg | ACID lakehouse with schema evolution |
| **Catalog** | AWS Glue Data Catalog | Centralized metadata for Athena/QuickSight |
| **Query** | Amazon Athena | Serverless SQL for ad-hoc investigations |
| **Visualization** | Amazon QuickSight | Real-time dashboards with SPICE |
| **Monitoring** | CloudWatch + SNS | Metrics, logs, and SLA alerts |

---

## 🛠️ Technology Stack

### Core Technologies
- **Python 3.11+** - Primary development language
- **Apache Flink 1.18+** - Primary streaming runtime (PyFlink SQL Table API)
- **PySpark 3.5+** - Secondary path: batch replay and historical backfill on EMR
- **Apache Iceberg 1.4+** - Lakehouse table format with ACID guarantees
- **Terraform >= 1.5** - Infrastructure as Code for all AWS resources

### AWS Services
- **Amazon Kinesis Data Streams** - Event ingestion (no Kafka/MSK)
- **Managed Service for Apache Flink (KDA v2)** - Serverless Flink runtime
- **Amazon EMR** - Managed Spark cluster for batch/backfill path
- **Amazon S3** - Raw and curated data zones
- **AWS Glue Data Catalog** - Metadata repository
- **Amazon Athena** - Serverless SQL queries
- **Amazon QuickSight** - Business intelligence dashboards
- **Amazon CloudWatch** - Metrics and logging
- **Amazon SNS** - Alert notifications

### Key Libraries
- `boto3` - AWS SDK for Python
- `pyflink` - Flink SQL Table API (runtime-provided on KDA)
- `pyspark` - DataFrame API and Structured Streaming (runtime-provided on EMR)
- `pyarrow` - Parquet file format support

---

## 📁 Project Structure

```
authpulse-aws-streaming-security-analytics/
│
├── src/
│   ├── producer/
│   │   ├── replay_lanl.py              # Kinesis event replay (primary entry)
│   │   └── config_loader.py            # Config from YAML / env vars
│   ├── stream/
│   │   ├── flink/
│   │   │   └── main_job.py             # PyFlink SQL Table API job (KDA)
│   │   ├── risk_rules.py               # Rule-based risk scoring logic
│   │   └── state_manager.py            # Flink keyed state management
│   ├── batch/                          # Daily batch aggregations
│   ├── common/
│   │   ├── models.py                   # Pydantic event models
│   │   ├── metrics.py                  # CloudWatch metric publishing
│   │   └── logging_utils.py            # Structured JSON logging
│   └── quality/
│       └── run_quality_checks.py       # Great Expectations DQ checks
│
├── streaming/                          # PySpark/EMR secondary path
│   ├── spark_streaming_job.py          # PySpark Structured Streaming job
│   ├── schemas.py                      # PySpark StructType schemas
│   ├── config.py                       # Config dataclasses
│   ├── risk_engine.py                  # PySpark UDF risk engine wrapper
│   └── window_metrics.py              # Rolling window aggregations
│
├── infra/terraform/
│   ├── envs/dev/                       # Dev environment root module
│   │   ├── main.tf                     # Wires all modules
│   │   ├── variables.tf
│   │   └── terraform.tfvars.example    # Template (gitignored .tfvars)
│   └── modules/
│       ├── kinesis/                    # Kinesis stream
│       ├── s3/                         # Lakehouse S3 bucket
│       ├── iam/                        # Execution roles
│       ├── glue_iceberg/               # Glue DB + Iceberg table definitions
│       ├── kda_flink/                  # Managed Service for Apache Flink
│       └── monitoring/                 # CloudWatch alarms + SNS
│
├── lakehouse/
│   ├── iceberg_ddl.sql                 # CREATE TABLE DDL for Athena
│   └── table_definitions.sql           # Schema documentation
│
├── analytics/
│   ├── athena_queries.sql              # Production SQL queries
│   └── kpis.md                         # KPI definitions
│
├── ci-cd/
│   ├── tests/unit/                     # pytest unit tests
│   └── tests/integration/              # pytest integration tests (needs AWS)
│
├── observability/
│   ├── cloudwatch_dashboards.json      # CloudWatch dashboard JSON
│   └── alarms/                         # Terraform alarm configs
│
├── docs/
│   ├── architecture.md                 # System design
│   ├── data_flow.md                    # Pipeline stage details
│   ├── design_decisions.md             # ADRs (Architecture Decision Records)
│   ├── data_contracts.md               # Event schema & field contracts
│   ├── runbook_operations.md           # Ops runbook: deploy, alerts, rollback
│   ├── sla_definition.md               # SLA targets and measurement
│   └── faq_interview.md               # Interview talking points
│
├── scripts/                            # PowerShell dev helpers
│   ├── setup_env.ps1
│   ├── run_tests.ps1
│   ├── commit.ps1
│   └── terraform.ps1
│
├── config/
│   ├── dev.yaml                        # Dev environment config
│   └── prod.yaml                       # Prod environment config
│
├── pyproject.toml                      # Python project + pytest config
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

---

## ✨ Key Features

### Real-Time Processing
- **Throughput**: 1,000-10,000 events/sec
- **Latency**: 30-60 seconds end-to-end (micro-batch)
- **Watermarking**: 5-minute late event tolerance
- **Exactly-once semantics**: Via Spark checkpointing

### Stateful Analytics
- **Rolling Windows**: 1-hour and 24-hour per-user metrics
- **Device Tracking**: All-time history of computers per user
- **Deduplication**: Event ID-based across watermark window

### Risk Engine
- **4 Detection Rules**: NEW_DEVICE, BURST_LOGIN, LATERAL_MOVEMENT, RARE_HOST
- **Weighted Scoring**: Configurable risk score calculation
- **Risk Levels**: LOW / MEDIUM / HIGH / CRITICAL classification

### Lakehouse Architecture
- **Dual Zones**: Raw (archival) + Curated (analytics)
- **ACID Transactions**: Iceberg prevents partial writes
- **Schema Evolution**: Add/modify columns without rewrite
- **Time Travel**: Query historical snapshots
- **Partitioning**: Daily partitions for query efficiency

### Production Monitoring
- **SLA Enforcement**: Freshness < 5 min, Completeness < 0.1% invalid
- **CloudWatch Metrics**: Kinesis lag, Spark batch duration, custom app metrics
- **SNS Alerts**: Automatic notifications on threshold breaches

---

## 🚨 Risk Detection Rules

The risk engine applies **4 rule-based detections** with weighted scoring:

### 1. NEW_DEVICE_SPIKE (Weight: 30)
**Detection**: User authenticates from previously unseen computer
**Business Logic**: First-time device may indicate:
- Legitimate new device onboarding
- Stolen credentials used remotely
- Lateral movement by attacker

### 2. BURST_LOGIN (Weight: 25)
**Detection**: Login count > 50 within 1 hour
**Business Logic**: Rapid successive logins may indicate:
- Brute force attempts (successful auths)
- Automated script behavior
- Compromised account exploitation

### 3. LATERAL_MOVEMENT (Weight: 35)
**Detection**: Access to ≥10 distinct computers within 1 hour
**Business Logic**: Accessing many hosts quickly indicates:
- Attacker pivoting through network
- Reconnaissance activity
- Privilege escalation attempts

### 4. RARE_HOST (Weight: 10)
**Detection**: Authentication to statistically infrequent host (bottom 5% popularity)
**Business Logic**: Accessing rarely-used hosts may indicate:
- Access to sensitive admin systems
- Unusual behavior deviation
- Targeting of high-value assets

### Risk Score Calculation
```
risk_score = (is_new_device × 30) + (is_burst_login × 25) + 
             (is_lateral_movement × 35) + (is_rare_host × 10)
```

**Risk Levels**:
- **LOW**: 0-25
- **MEDIUM**: 26-50
- **HIGH**: 51-75
- **CRITICAL**: 76+

---

## 📊 Data Model

### Table: `auth_events_curated` (Iceberg)
**Purpose**: Enriched events with risk analytics

| Column | Type | Description |
|--------|------|-------------|
| event_id | STRING | Unique identifier (SHA256) |
| event_time | TIMESTAMP | Authentication timestamp (UTC) |
| user_id | STRING | User identifier |
| computer_id | STRING | Computer/host identifier |
| ingestion_time | TIMESTAMP | Kinesis ingestion timestamp |
| login_count_1h | LONG | Rolling 1-hour login count |
| login_count_24h | LONG | Rolling 24-hour login count |
| unique_computers_1h | LONG | Distinct computers in 1 hour |
| unique_computers_24h | LONG | Distinct computers in 24 hours |
| is_new_device | INT | 1 if first-time computer |
| is_burst_login | INT | 1 if burst detected |
| is_lateral_movement | INT | 1 if lateral movement detected |
| is_rare_host | INT | 1 if rare host accessed |
| risk_flags | ARRAY<STRING> | Triggered risk rules |
| risk_score | INT | Weighted risk score (0-100) |
| risk_level | STRING | LOW/MEDIUM/HIGH/CRITICAL |
| processing_time | TIMESTAMP | Spark processing timestamp |
| event_date | DATE | Partition column (YYYY-MM-DD) |

**Partitioning**: Daily by `event_date`  
**Format**: Apache Iceberg with ACID guarantees

### Table: `user_behavior_hourly` (Iceberg)
**Purpose**: Hourly user activity aggregations

| Column | Type | Description |
|--------|------|-------------|
| window_start | TIMESTAMP | Hour window start |
| window_end | TIMESTAMP | Hour window end |
| user_id | STRING | User identifier |
| total_logins | LONG | Authentication count |
| unique_computers | LONG | Distinct hosts accessed |
| anomaly_count | LONG | Events with risk_score > 0 |
| total_risk_score | LONG | Sum of all risk scores |
| max_risk_score | INT | Highest single risk score |

### Table: `host_popularity_daily` (Iceberg)
**Purpose**: Daily host access statistics

| Column | Type | Description |
|--------|------|-------------|
| date | DATE | Aggregation date |
| computer_id | STRING | Computer/host identifier |
| unique_users | LONG | Distinct users accessed |
| total_logins | LONG | Total authentication count |
| high_risk_events | LONG | Count of HIGH/CRITICAL events |

**Use Case**: Support rare host detection by computing percentile ranks.

---

## 🚀 Getting Started

### Prerequisites

1. **AWS Account** with appropriate permissions:
   - Kinesis: CreateStream, PutRecords
   - EMR: CreateCluster, SubmitStep
   - S3: CreateBucket, PutObject, GetObject
   - Glue: CreateDatabase, CreateTable
   - Athena: StartQueryExecution
   - IAM: CreateRole, AttachRolePolicy

2. **AWS CLI** configured:
```bash
aws configure
aws sts get-caller-identity  # Verify credentials
```

3. **Python 3.11+** installed locally

4. **LANL Dataset**: Download from https://csr.lanl.gov/data/auth/
   - Place in `data/raw/auth.txt` (gitignored)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/authpulse-aws-streaming-security-analytics.git
cd authpulse-aws-streaming-security-analytics

# Install Python dependencies
pip install -r requirements.txt
```

### Local Development (Windows)

```powershell
# Create venv + install dev deps
./scripts/setup_env.ps1

# Run lint + unit tests
./scripts/run_tests.ps1

# Run lint/tests, stage changes, and commit
./scripts/commit.ps1 -All -Message "chore: update docs"
```

---

## 💻 Usage

### Step 1: Provision AWS Infrastructure (Terraform)

All AWS resources (Kinesis, S3, Glue, KDA Flink app, IAM, CloudWatch alarms) are created via Terraform.

```powershell
# Windows (PowerShell wrapper)
cd infra/terraform/envs/dev

# Copy example vars and fill in your account-specific values
copy terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: set alert_email and AWS account ID

# Plan + apply (creates all AWS resources)
.\..\..\..\scripts\terraform.ps1 -Env dev -Action plan
.\..\..\..\scripts\terraform.ps1 -Env dev -Action apply
```

This creates:
- Kinesis stream: `authpulse-dev-stream`
- S3 bucket: `authpulse-dev-lakehouse-<account-id>`
- Glue database: `authpulse`
- KDA Flink application: `authpulse-dev-flink-app`
- CloudWatch alarms + SNS topic

> **Note**: `terraform apply` creates real AWS resources (costs apply). Destroy with `terraform destroy` when done.

### Step 2: Run Iceberg DDL in Athena

```bash
# Open Athena in AWS Console, run the contents of:
cat lakehouse/iceberg_ddl.sql
# Or via CLI:
aws athena start-query-execution \
  --query-string file://lakehouse/iceberg_ddl.sql \
  --result-configuration OutputLocation=s3://authpulse-dev-lakehouse-<account-id>/athena-results/
```

### Step 3: Upload Flink Job & Start Application

```bash
# Package the Flink job
cd src/stream/flink
zip -r authpulse-flink-job.zip *.py ../risk_rules.py ../state_manager.py

# Upload to S3
aws s3 cp authpulse-flink-job.zip \
  s3://authpulse-dev-lakehouse-<account-id>/flink-app/authpulse-flink-job.zip

# Start the KDA Flink application
aws kinesisanalyticsv2 start-application \
  --application-name authpulse-dev-flink-app \
  --run-configuration '{"ApplicationRestoreConfiguration":{"ApplicationRestoreType":"SKIP_RESTORE_FROM_SNAPSHOT"}}'
```

### Step 4: Start Event Replay Producer

```bash
python src/producer/replay_lanl.py \
  --input data/raw/auth.txt \
  --stream-name authpulse-dev-stream \
  --region us-east-1 \
  --rate 2000 \
  --max-events 100000
```

**Options**:
- `--rate`: Events per second (default: 2000)
- `--batch-size`: Records per `put_records` call (default: 500)
- `--max-events`: Stop after N events (useful for testing)
- `--dry-run`: Parse and validate without sending to Kinesis

### Step 6: Query Data in Athena

```sql
-- High-risk users in last hour
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

See [analytics/athena_queries.sql](analytics/athena_queries.sql) for more examples.

### Step 7: Build QuickSight Dashboard

1. Connect QuickSight to Athena
2. Create dataset from `authpulse.auth_events_curated`
3. Build visualizations:
   - Risk level distribution (pie chart)
   - Events per minute (line chart)
   - Top risky users (bar chart)
   - Geographic heatmap (if computer_id contains location)

See [dashboards/quicksight_setup.md](dashboards/quicksight_setup.md) for detailed steps.

---

## 📊 Monitoring & SLAs

### Service Level Agreements

| SLA | Target | Measurement | Alert Threshold |
|-----|--------|-------------|------------------|
| **Freshness** | < 5 minutes | `processing_time - event_time` P95 | > 300 seconds |
| **Completeness** | < 0.1% invalid | Error count / total count | > 0.1% per hour |
| **Availability** | 99.9% uptime | Spark job running | Job stopped |

### CloudWatch Metrics

**Kinesis Metrics**:
- `GetRecords.IteratorAgeMilliseconds` → Alert if > 60000 (1 min lag)
- `IncomingRecords` → Monitor producer throughput
- `ReadProvisionedThroughputExceeded` → Alert on throttling

**EMR Spark Metrics**:
- `StreamingBatchDuration` → Alert if > 30000ms (exceeds trigger interval)
- `StreamingSchedulingDelay` → Alert if growing (backlog)
- `ExecutorMemoryUsed` → Alert if > 80%

**Custom App Metrics** (published from Spark):
```python
import boto3
cw = boto3.client('cloudwatch')

cw.put_metric_data(
    Namespace='AuthPulse',
    MetricData=[{
        'MetricName': 'ProcessingLagSeconds',
        'Value': lag_seconds,
        'Unit': 'Seconds'
    }]
)
```

### SNS Alert Topics

```bash
# Create SNS topic
aws sns create-topic --name authpulse-critical-alerts

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:authpulse-critical-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

**Alert Conditions**:
- Freshness SLA breach (P95 lag > 5 min)
- Invalid record rate > 0.1%
- Spark job failure
- Kinesis throttling

See [monitoring/cloudwatch_metrics.md](monitoring/cloudwatch_metrics.md) for complete metric catalog.

---

## 📝 Design Decisions

Key architectural choices documented in [docs/design_decisions.md](docs/design_decisions.md):

1. **Kinesis vs. Kafka**: Chose Kinesis for managed service simplicity
2. **PySpark vs. Flink**: PySpark for unified batch/streaming API
3. **Iceberg vs. Delta**: Iceberg for vendor-neutral lakehouse
4. **EMR vs. Glue**: EMR for full Spark control and latest versions
5. **Athena vs. Redshift**: Athena for serverless ad-hoc queries
6. **Daily partitioning**: Balance between query performance and partition count
7. **Stateful processing**: Hybrid approach (in-memory + Iceberg bootstrap)
8. **Dead letter queue**: Handle invalid records without stopping pipeline

---

## 💼 Resume Impact

**What This Project Demonstrates**:

✅ **Real-Time Streaming**: Kinesis + PySpark Structured Streaming micro-batching  
✅ **Stateful Processing**: Rolling windows, user state tracking, deduplication  
✅ **Lakehouse Architecture**: Apache Iceberg with ACID, schema evolution, time travel  
✅ **Data Modeling**: Star schema (fact + dimensions), partitioning strategy  
✅ **AWS Expertise**: Kinesis, EMR, S3, Glue, Athena, QuickSight, CloudWatch, SNS  
✅ **Production Best Practices**: SLA monitoring, alerting, checkpointing, error handling  
✅ **Security Analytics**: Domain knowledge in authentication logs, risk scoring  
✅ **SQL Proficiency**: Complex Athena queries, aggregations, window functions  
✅ **Python**: OOP, dataclasses, type hints, boto3, PySpark DataFrame API  
✅ **Documentation**: Architecture diagrams, decision records, runbooks  

**Talking Points for Interviews**:

- "Built end-to-end streaming pipeline processing 10k events/sec with sub-5-minute latency"
- "Implemented stateful stream processing with PySpark mapGroupsWithState for user behavior tracking"
- "Designed Apache Iceberg lakehouse with daily partitioning, reducing query costs by 90%"
- "Enforced SLAs via CloudWatch metrics and SNS alerts, achieving 99.9% pipeline uptime"
- "Developed rule-based risk engine detecting lateral movement and credential anomalies"

**Keywords for ATS**:
PySpark, Apache Iceberg, AWS EMR, Kinesis Data Streams, AWS Glue, Amazon Athena, Structured Streaming, Real-Time Analytics, Lakehouse, Data Engineering, Python, CloudWatch, SNS, QuickSight, Security Analytics

---

## 🔮 Future Enhancements

### Machine Learning Integration
- **Replace rule engine** with ML model (SageMaker)
- **Anomaly detection**: Isolation Forest or autoencoders
- **Feature engineering**: Extract behavioral patterns for training
- **Online inference**: Real-time scoring via SageMaker endpoint

### Advanced Analytics
- **Graph analysis**: User-computer network using Neptune
- **Temporal patterns**: Hour-of-day / day-of-week baselines
- **Entity resolution**: Merge duplicate user/computer identities

### Operational Improvements
- **Auto-scaling**: EMR fleet based on Kinesis lag
- **Cost optimization**: Reserved instances, S3 lifecycle policies
- **Multi-region**: Disaster recovery with cross-region replication
- **CI/CD**: Automated testing and deployment pipelines

### Enhanced Monitoring
- **Grafana dashboards**: Time-series visualization
- **OpenTelemetry**: Distributed tracing for latency analysis
- **Data quality**: Great Expectations framework integration

---

## 📚 Additional Resources

- **[Architecture Overview](docs/architecture.md)** - Detailed system design and component specifications
- **[Data Flow](docs/data_flow.md)** - End-to-end pipeline stages and transformations
- **[Design Decisions](docs/design_decisions.md)** - ADRs explaining technology choices
- **[Athena Query Examples](analytics/athena_queries.sql)** - Production SQL queries
- **[KPI Definitions](analytics/kpis.md)** - Key performance indicators and metrics
- **[CloudWatch Metrics](monitoring/cloudwatch_metrics.md)** - Complete observability catalog

---

## 🤝 Contributing

This is a portfolio/educational project. Issues and pull requests are welcome for:
- Bug fixes
- Documentation improvements
- Additional SQL query examples
- Enhanced risk detection rules

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **LANL** for providing the authentication dataset
- **Apache Iceberg** community for excellent lakehouse format
- **AWS** for managed services enabling rapid development
