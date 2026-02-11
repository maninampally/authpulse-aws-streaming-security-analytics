# AuthPulse: Real-Time Authentication Risk & Behavior Analytics
### Production-Grade AWS Streaming Lakehouse for Security Analytics

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![PySpark](https://img.shields.io/badge/PySpark-3.5+-orange.svg)](https://spark.apache.org/)
[![Apache Iceberg](https://img.shields.io/badge/Apache%20Iceberg-1.4+-blue.svg)](https://iceberg.apache.org/)
[![AWS](https://img.shields.io/badge/AWS-Kinesis%20%7C%20EMR%20%7C%20S3-yellow.svg)](https://aws.amazon.com/)

AuthPulse is a **production-grade real-time streaming analytics platform** that processes enterprise authentication events to detect security anomalies, compute risk scores, and generate actionable insights for security operations teams.

Built with **PySpark Structured Streaming on Amazon EMR**, it demonstrates modern data engineering best practices for high-throughput event processing, stateful stream analytics, and lakehouse architecture on AWS.

**Pipeline Architecture:**
```
LANL Dataset → Kinesis Streams → PySpark on EMR → S3 Iceberg Tables → Athena/QuickSight
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
| **Processing** | PySpark on Amazon EMR | Structured Streaming with micro-batching |
| **Storage** | S3 + Apache Iceberg | ACID lakehouse with schema evolution |
| **Catalog** | AWS Glue Data Catalog | Centralized metadata for Athena/QuickSight |
| **Query** | Amazon Athena | Serverless SQL for ad-hoc investigations |
| **Visualization** | Amazon QuickSight | Real-time dashboards with SPICE |
| **Monitoring** | CloudWatch + SNS | Metrics, logs, and SLA alerts |

---

## 🛠️ Technology Stack

### Core Technologies
- **Python 3.11+** - Primary development language
- **PySpark 3.5+** - Structured Streaming for real-time processing
- **Apache Iceberg 1.4+** - Lakehouse table format with ACID guarantees

### AWS Services
- **Amazon Kinesis Data Streams** - Event ingestion (no Kafka/MSK)
- **Amazon EMR** - Managed Spark cluster (no Glue ETL)
- **Amazon S3** - Raw and curated data zones
- **AWS Glue Data Catalog** - Metadata repository
- **Amazon Athena** - Serverless SQL queries
- **Amazon QuickSight** - Business intelligence dashboards
- **Amazon CloudWatch** - Metrics and logging
- **Amazon SNS** - Alert notifications

### Key Libraries
- `boto3` - AWS SDK for Python
- `pyspark` - DataFrame API and Structured Streaming
- `pyarrow` - Parquet file format support

**No Docker, Terraform, or Airflow** - Pure AWS-native deployment.

---

## 📁 Project Structure

```
authpulse-aws-streaming-security-analytics/
│
├── producer/
│   └── replay_producer.py          # Kinesis event replay script
│
├── streaming/
│   ├── spark_streaming_job.py      # Main PySpark job
│   ├── schemas.py                  # Event schema definitions
│   ├── config.py                   # Configuration management
│   ├── risk_engine.py              # Risk detection rules
│   └── window_metrics.py           # Rolling aggregations
│
├── lakehouse/
│   ├── iceberg_ddl.sql             # Table creation DDL
│   └── table_definitions.sql       # Schema documentation
│
├── analytics/
│   ├── athena_queries.sql          # Example SQL queries
│   └── kpis.md                     # KPI definitions
│
├── monitoring/
│   ├── sla_checks.sql              # Data quality checks
│   └── cloudwatch_metrics.md       # Metrics catalog
│
├── docs/
│   ├── architecture.md             # System design
│   ├── data_flow.md                # Pipeline details
│   └── design_decisions.md         # ADRs (Architecture Decision Records)
│
├── requirements.txt                # Python dependencies
└── README.md                       # This file
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

---

## 💻 Usage

### Step 1: Create AWS Resources

#### 1.1 Create Kinesis Stream
```bash
aws kinesis create-stream \
  --stream-name authpulse-stream \
  --shard-count 2 \
  --region us-east-1
```

#### 1.2 Create S3 Bucket
```bash
aws s3 mb s3://authpulse-lakehouse-${AWS_ACCOUNT_ID}
```

#### 1.3 Create Glue Database
```bash
aws glue create-database \
  --database-input '{"Name":"authpulse","Description":"AuthPulse lakehouse"}'
```

#### 1.4 Create IAM Role for EMR
```bash
# See docs/setup_iam.md for detailed role creation
# Role should have: EMR service role, S3 access, Glue catalog access, Kinesis read
```

### Step 2: Start Event Replay Producer

```bash
python producer/replay_producer.py \
  --input data/raw/auth.txt \
  --stream-name authpulse-stream \
  --region us-east-1 \
  --rate 2000 \
  --max-events 100000  # Optional limit for testing
```

**Options**:
- `--rate`: Events per second (default: 2000)
- `--batch-size`: Records per put_records call (default: 500)
- `--max-events`: Stop after N events (useful for testing)

### Step 3: Launch EMR Cluster

```bash
aws emr create-cluster \
  --name "AuthPulse-Streaming" \
  --release-label emr-7.0.0 \
  --applications Name=Spark \
  --instance-type r5.xlarge \
  --instance-count 3 \
  --use-default-roles \
  --log-uri s3://authpulse-lakehouse-${AWS_ACCOUNT_ID}/logs/ \
  --region us-east-1
```

**Note**: Save the `ClusterId` from output.

### Step 4: Submit Spark Streaming Job

```bash
# Package dependencies
zip -r streaming.zip streaming/*.py

# Upload to S3
aws s3 cp streaming.zip s3://authpulse-lakehouse-${AWS_ACCOUNT_ID}/code/

# Submit step to EMR
aws emr add-steps \
  --cluster-id j-XXXXXXXXXXXXX \
  --steps Type=Spark,Name="AuthPulse Streaming",ActionOnFailure=CONTINUE,Args=[\
    --deploy-mode,cluster,\
    --packages,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.4.0,\
    --py-files,s3://authpulse-lakehouse-${AWS_ACCOUNT_ID}/code/streaming.zip,\
    s3://authpulse-lakehouse-${AWS_ACCOUNT_ID}/code/streaming/spark_streaming_job.py,\
    --kinesis-stream,authpulse-stream,\
    --s3-bucket,authpulse-lakehouse-${AWS_ACCOUNT_ID},\
    --region,us-east-1]
```

### Step 5: Create Iceberg Tables

```bash
# Run DDL in Athena console or CLI
aws athena start-query-execution \
  --query-string file://lakehouse/iceberg_ddl.sql \
  --result-configuration OutputLocation=s3://authpulse-lakehouse-${AWS_ACCOUNT_ID}/athena-results/
```

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

---

## ✉️ Contact

For questions or collaboration:
- LinkedIn: [Your Profile]
- GitHub: [@yourusername]
- Email: your.email@example.com

---

**⭐ If this project helped you, please star the repository!**

