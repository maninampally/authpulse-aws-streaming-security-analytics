# AuthPulse End-to-End Pipeline Runbook

This runbook walks you through running the complete AuthPulse pipeline from code validation through live data processing.

---

## Prerequisites Checklist

- [x] AWS CLI configured: `aws sts get-caller-identity` 
  - Account: **604743481383**
  - Region: us-east-1 (default)
- [ ] **Terraform >= 1.5** — Install from https://www.terraform.io/downloads.html
- [x] Python 3.13 (>= 3.11 required)
- [ ] LANL dataset OR sample data available
  - Sample included at: `data/sample/auth_sample.csv`
  - Full dataset: download from https://csr.lanl.gov/data/auth/ → place in `data/raw/auth.txt`

---

## Phase 1: Code Validation (No AWS Resources)

### Step 1.1 — Lint and type checks

```powershell
# Run Python linting
ruff check src/ --select E,W,F,I

# Check formatting
ruff format src/ --check
```

### Step 1.2 — Unit tests

```powershell
# Run all unit + integration tests
pytest ci-cd/tests/ -v

# Or specific test suite
pytest ci-cd/tests/unit/test_risk_rules.py -v
pytest ci-cd/tests/unit/test_models.py -v
```

### Step 1.3 — Risk engine validation (dry-run)

```powershell
# Test risk scoring logic without AWS
python -c "
from src.stream.risk_rules import compute_risk

# Test case 1: High-risk user (lateral movement + burst login)
score, flags = compute_risk(
    user_id='U1',
    dst_host='C999',
    window_1h_event_count=60,      # burst_login threshold = 50
    window_1h_unique_hosts=12,     # lateral_movement threshold = 10
    window_24h_unique_hosts=30,
    has_new_device=True
)
print(f'Test 1 — Score: {score}, Flags: {flags}')
assert score == 100, f'Expected 100, got {score}'
assert 'lateral_movement' in flags
assert 'burst_login' in flags
print('✓ Risk engine validation passed')
"
```

### Step 1.4 — Validate producer code (dry-run)

```powershell
# Test producer parsing without sending to Kinesis
python src/producer/replay_lanl.py `
  --input data/sample/auth_sample.csv `
  --stream-name authpulse-dev-stream `
  --region us-east-1 `
  --dry-run `
  --max-events 10

# Expected output: "Dry run: parsed 10 events successfully, 0 errors"
```

### Step 1.5 — Validate Lambda handler logic

```powershell
# Test Lambda handler without AWS infrastructure
python -c "
import json
from src.lambda_consumer.handler import process_records

# Mock Kinesis record
mock_record = {
    'eventID': 'test-1',
    'kinesis': {
        'data': 'eyJldmVudF9pZCI6ICJ0ZXN0IiwgInVzZXJfaWQiOiAiVTEiLCAiY29tcHV0ZXJfaWQiOiAiQzEiLCAiZXZlbnRfdGltZSI6IDE2MzAxMjM0NTZ9'  # base64 encoded mock JSON
    }
}

# Note: This requires mocking DynamoDB, skip actual processing
print('✓ Lambda imports validated')
"
```

---

## Phase 2: Infrastructure Setup (Creates AWS Resources)

### Step 2.1 — Install Terraform

Download and install Terraform >= 1.5 from: https://www.terraform.io/downloads.html

Verify installation:
```powershell
terraform -version
# Expected: Terraform v1.5.x
```

### Step 2.2 — Initialize Terraform environment

```powershell
cd infra/terraform/envs/dev

# Copy example variables
Copy-Item terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values:
# - alert_email: your email for SNS alerts
# - aws_account_id: 604743481383
# - aws_region: us-east-1
notepad terraform.tfvars
```

**terraform.tfvars template:**
```hcl
alert_email    = "your-email@example.com"
aws_account_id = "604743481383"
aws_region     = "us-east-1"
```

### Step 2.3 — Terraform init, validate, and plan

```powershell
# Initialize Terraform
terraform init

# Format check
terraform fmt -check -recursive

# Validate configuration
terraform validate

# Preview resources to be created
terraform plan -out=tfplan

# Review the plan output — should show:
# - 1 Kinesis stream (1 shard)
# - 1 S3 bucket (lakehouse)
# - 1 Lambda function (auth processor)
# - 1 DynamoDB table (user state)
# - 1 Glue database
# - CloudWatch dashboard + alarms + SNS topic
```

### Step 2.4 — Apply Terraform (Create Infrastructure)

```powershell
# Review costs before applying — this creates real AWS resources!
# Estimated cost: ~$20-50/month for dev environment

terraform apply tfplan

# Output should show:
# - Kinesis stream name: authpulse-dev-stream
# - S3 bucket: authpulse-dev-lakehouse-604743481383
# - Lambda function: authpulse-dev-auth-processor
# - DynamoDB table: authpulse-dev-user-state
```

**Cleanup when done:**
```powershell
terraform destroy
```

---

## Phase 3: Data Setup (Athena Tables)

### Step 3.1 — Open Athena Query Editor

1. Go to AWS Console → Athena
2. Select region: **us-east-1**
3. Select database: **authpulse** (created by Terraform)

### Step 3.2 — Create JSON-backed external tables

Copy the contents of `src/batch/ddl/json_tables.sql` and run **each CREATE TABLE statement separately** in Athena:

```sql
-- External table for raw events (immediate queryability)
CREATE EXTERNAL TABLE IF NOT EXISTS authpulse.auth_events_raw_json (
    event_time_epoch BIGINT,
    event_time STRING,
    user_id STRING,
    computer_id STRING,
    event_id STRING
)
PARTITIONED BY (event_date STRING)
STORED AS JSON
LOCATION 's3://authpulse-dev-lakehouse-604743481383/raw/auth_events/'
WITH SERDEPROPERTIES (
    'serialization.format' = '1'
)
TBLPROPERTIES (
    'projection.enabled' = 'true',
    'projection.event_date.type' = 'date',
    'projection.event_date.range' = '1970-01-01,2099-12-31',
    'projection.event_date.format' = 'yyyy-MM-dd'
);

-- External table for curated events (risk-enriched)
CREATE EXTERNAL TABLE IF NOT EXISTS authpulse.auth_events_curated_json (
    event_time_epoch BIGINT,
    event_time STRING,
    user_id STRING,
    dst_host STRING,
    success BOOLEAN,
    window_1h_event_count BIGINT,
    window_1h_unique_hosts BIGINT,
    window_24h_unique_hosts BIGINT,
    has_new_device BOOLEAN,
    risk_score INT,
    risk_flags ARRAY<STRING>
)
PARTITIONED BY (event_date STRING)
STORED AS JSON
LOCATION 's3://authpulse-dev-lakehouse-604743481383/curated/auth_events_curated/'
WITH SERDEPROPERTIES (
    'serialization.format' = '1'
)
TBLPROPERTIES (
    'projection.enabled' = 'true',
    'projection.event_date.type' = 'date',
    'projection.event_date.range' = '1970-01-01,2099-12-31',
    'projection.event_date.format' = 'yyyy-MM-dd'
);
```

**Verify tables created:**
```sql
SHOW TABLES IN authpulse;
-- Should list: auth_events_raw_json, auth_events_curated_json
```

---

## Phase 4: Live Pipeline Execution

### Step 4.1 — Verify Lambda deployment

```powershell
# Check Lambda is deployed and logs are flowing
aws logs tail /aws/lambda/authpulse-dev-auth-processor --follow --region us-east-1

# In another terminal, continue to Step 4.2
```

### Step 4.2 — Start the event replay producer

Open **new PowerShell terminal** (keep logs streaming in previous terminal):

```powershell
# Start replaying sample data into Kinesis
# (use sample for testing, full dataset can take hours)

python src/producer/replay_lanl.py `
  --input data/sample/auth_sample.csv `
  --stream-name authpulse-dev-stream `
  --region us-east-1 `
  --rate 100 `
  --batch-size 50 `
  --max-events 5000

# Expected output:
# Sending batch 1: 50 events
# Batch 1 sent successfully
# ...
# Producer completed: 5000 events sent in 50 seconds
```

**Producer options for tuning:**
- `--rate 100` — Events per second (default 2000; use 100-200 for testing)
- `--batch-size 50` — Records per Kinesis PutRecords call (max 500)
- `--max-events 5000` — Stop after N events (for quick testing)

### Step 4.3 — Monitor Lambda processing

Watch the logs from Step 4.1 for output like:

```
[INFO] Batch received: 100 records from Kinesis
[INFO] Processing user U1: state_lookup=5ms, risk_calc=2ms, s3_write=150ms
[INFO] Batch completed: processed=100, failed=0, duration=157ms
[INFO] Wrote 100 raw records + 100 curated records to S3
```

### Step 4.4 — Verify S3 output

```powershell
# List raw events written by Lambda
aws s3 ls `
  s3://authpulse-dev-lakehouse-604743481383/raw/auth_events/ `
  --recursive `
  --region us-east-1

# List curated (risk-enriched) events
aws s3 ls `
  s3://authpulse-dev-lakehouse-604743481383/curated/auth_events_curated/ `
  --recursive `
  --region us-east-1

# Download sample curated event to inspect
aws s3 cp `
  "s3://authpulse-dev-lakehouse-604743481383/curated/auth_events_curated/event_date=1970-01-15/" `
  ./sample-events.jsonl.gz `
  --recursive

# Decompress and view
gunzip -c sample-events.jsonl.gz | head -5
```

---

## Phase 5: Query Results in Athena

### Step 5.1 — Validate data landed

```sql
SELECT COUNT(*) AS total_raw_events
FROM authpulse.auth_events_raw_json;

SELECT COUNT(*) AS total_curated_events
FROM authpulse.auth_events_curated_json;

-- Expected: both should show the number of events you sent (e.g., 5000)
```

### Step 5.2 — High-risk events

```sql
SELECT 
    user_id,
    dst_host,
    risk_score,
    risk_flags,
    event_time
FROM authpulse.auth_events_curated_json
WHERE risk_score > 0
ORDER BY risk_score DESC, event_time DESC
LIMIT 20;

-- Expected: Events with risk_score > 0 have lateral_movement, burst_login, etc.
```

### Step 5.3 — Risk distribution

```sql
SELECT
    CASE
        WHEN risk_score = 0        THEN 'NONE'
        WHEN risk_score <= 25      THEN 'LOW'
        WHEN risk_score <= 50      THEN 'MEDIUM'
        WHEN risk_score <= 75      THEN 'HIGH'
        ELSE                            'CRITICAL'
    END AS risk_level,
    COUNT(*) AS event_count,
    MIN(risk_score) AS min_score,
    MAX(risk_score) AS max_score
FROM authpulse.auth_events_curated_json
GROUP BY 1
ORDER BY event_count DESC;

-- Expected: Most events are LOW/NONE, few are HIGH/CRITICAL
```

### Step 5.4 — Users triggering lateral movement

```sql
SELECT 
    user_id,
    COUNT(*) AS event_count,
    MAX(window_1h_unique_hosts) AS max_hosts_1h,
    MAX(risk_score) AS max_risk_score
FROM authpulse.auth_events_curated_json
WHERE array_contains(risk_flags, 'lateral_movement')
GROUP BY user_id
ORDER BY max_risk_score DESC;

-- Expected: Show users accessing 10+ unique hosts in 1 hour windows
```

---

## Phase 6: End-to-End Validation

### Checklist

- [ ] **Code validation** — Linting, tests, risk engine validation passed
- [ ] **Infrastructure** — Terraform apply completed, resources visible in AWS Console
- [ ] **Athena tables** — JSON external tables created and queryable
- [ ] **Producer** — Successfully sent events to Kinesis
- [ ] **Lambda** — Processed events, wrote to S3 (raw + curated)
- [ ] **S3 output** — JSONL.GZ files present in both prefixes
- [ ] **Athena queries** — Data lands in Athena within 30-60 seconds
- [ ] **Risk scoring** — Risk flags computed correctly (lateral_movement, burst_login, etc.)
- [ ] **End-to-end latency** — Producer → Kinesis → Lambda → S3 → Athena ≤ 60 seconds

### Expected Metrics

| Stage | Duration | Notes |
|---|---|---|
| Producer batch (50 events) | ~0.5s | Kinesis PutRecords + backoff |
| Kinesis ingestion | <1s | Immediately available to Lambda |
| Lambda invocation | 100-200ms | Kinesis ESM batch processing |
| DynamoDB read/write | 5-10ms | Per-user state lookup + update |
| S3 write (1000 events) | 100-200ms | Batch JSONL.GZ write |
| Athena query execution | 2-5s | Cold first query; <1s if cached |
| **End-to-End** | **~42 seconds** | Event creation → query result |

---

## Troubleshooting

### Lambda logs empty

```powershell
# Check if Lambda was triggered
aws lambda invoke `
  --function-name authpulse-dev-auth-processor `
  --payload '{"test": true}' `
  --region us-east-1 `
  response.json

cat response.json

# Check Kinesis shard iterator age
aws kinesis describe-stream `
  --stream-name authpulse-dev-stream `
  --region us-east-1 | jq '.StreamDescription.Shards[0]'
```

### No data in S3

```powershell
# Verify Lambda execution role has S3 permissions
aws iam get-role-policy `
  --role-name authpulse-dev-lambda-role `
  --policy-name authpulse-dev-lambda-policy `
  --region us-east-1

# Check S3 bucket exists and is accessible
aws s3 ls authpulse-dev-lakehouse-604743481383/ --region us-east-1
```

### Athena returns 0 rows

```sql
-- Check if event_date partition exists
SELECT DISTINCT event_date
FROM authpulse.auth_events_curated_json
LIMIT 10;

-- If empty, run partition projection refresh (Athena v3 auto-discovers)
-- Just re-run the SELECT query
```

---

## Cleanup

When done testing, destroy infrastructure to avoid costs:

```powershell
cd infra/terraform/envs/dev

# Destroy all resources
terraform destroy

# Confirm by typing: yes
```

---

## Next Steps for Production

1. **Scale Kinesis** — Add shards based on event throughput (1MB/s per shard)
2. **Lambda Provisioned Concurrency** — Eliminate cold starts
3. **Iceberg tables** — Switch from JSON to Parquet for cost optimization
4. **CI/CD** — Automate Lambda ZIP build + Terraform apply on git push
5. **Monitoring** — Set up CloudWatch alarms for SLA breaches
6. **ML integration** — Replace rule engine with SageMaker anomaly detector

---

## Questions?

Refer to:
- [Architecture Overview](docs/architecture.md)
- [Design Decisions](docs/design_decisions.md)
- [Operations Runbook](docs/runbook_operations.md)
