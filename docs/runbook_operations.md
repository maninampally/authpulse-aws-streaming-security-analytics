# Runbook (Operations)

On-call style runbook for the AuthPulse streaming security analytics pipeline.
Covers deployment, common alerts, diagnosis steps, and rollback procedures.

---

## 1. One-Shot Dev Deployment

### Prerequisites
- AWS CLI configured (`aws configure` or SSO) with the target account.
- Terraform >= 1.5, Python 3.10+, venv activated.
- S3 bucket `authpulse-dev-lakehouse-289591071327` exists (created by Terraform on first run).

### Step 1 — Deploy infrastructure
```powershell
cd infra/terraform/envs/dev
cp terraform.tfvars.example terraform.tfvars   # edit alert_email before applying
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### Step 2 — Create Athena/Glue tables
Run the DDL once in Athena (Query Editor, engine v3):
```sql
-- paste contents of lakehouse/iceberg_ddl.sql
```
Or via AWS CLI:
```bash
aws athena start-query-execution \
  --query-string file://lakehouse/iceberg_ddl.sql \
  --work-group primary \
  --result-configuration OutputLocation=s3://authpulse-dev-lakehouse-289591071327/athena-results/
```

### Step 3 — Start the replay producer
```powershell
.venv\Scripts\Activate.ps1
python -m producer.replay_lanl \
  --config config/dev.yaml \
  --input data/sample/auth_sample.csv \
  --dry-run        # remove --dry-run to actually send to Kinesis
```

### Step 4 — Submit the Flink job (Managed Service for Apache Flink)
Package and upload the job zip to S3, then update the KDA application via console or:
```bash
aws kinesisanalyticsv2 start-application \
  --application-name authpulse-dev-flink-app \
  --run-configuration '{"ApplicationRestoreConfiguration":{"ApplicationRestoreType":"SKIP_RESTORE_FROM_SNAPSHOT"}}'
```
Environment variables required by the job:
```
AUTHPULSE_KINESIS_STREAM=authpulse-dev-stream
AWS_REGION=us-east-1
AUTHPULSE_S3_RAW_PATH=s3a://authpulse-dev-lakehouse-289591071327/raw/auth_events
AUTHPULSE_S3_FEATURES_PATH=s3a://authpulse-dev-lakehouse-289591071327/features/auth_user_features/
AUTHPULSE_S3_CURATED_EVENTS_PATH=s3a://authpulse-dev-lakehouse-289591071327/curated/auth_events_curated/
```

### Step 5 — Run DQ checks
```powershell
python -m quality.run_quality_checks \
  --config config/dev.yaml \
  --suite  src/quality/expectations/auth_events_expectations.yml
```
Exit code 0 = all checks pass. Non-zero = at least one check exceeded `failure_threshold_pct`.

### Step 6 — Verify in Athena
Run the freshness query from `analytics/athena_queries.sql` (Query 7).
`lag_seconds` should be < 300.

---

## 2. Alert Response Playbook

### Alert: `authpulse-dev-kinesis-iterator-age-high`
**Meaning:** Consumer lag > 5 minutes — curated data will be delayed; Freshness SLA at risk.

**Diagnosis:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kinesis \
  --metric-name GetRecords.IteratorAgeMilliseconds \
  --dimensions Name=StreamName,Value=authpulse-dev-stream \
  --start-time $(date -u -d '30 minutes ago' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --period 60 --statistics Maximum
# Check Flink application status:
aws kinesisanalyticsv2 describe-application --application-name authpulse-dev-flink-app
```
**Likely causes:**
1. Flink job crashed or throttled — check `numberOfFailedCheckpoints` alarm.
2. Shard count too low for incoming throughput — scale shards.
3. Transient AWS outage — wait one evaluation period (3 min), check if self-clears.

**Remediation:**
- Restart Flink app: `aws kinesisanalyticsv2 stop-application …` then `start-application`.
- If persistent, increase Kinesis shard count: `aws kinesis update-shard-count …`.

---

### Alert: `authpulse-dev-flink-failed-checkpoints-rate`
**Meaning:** Flink checkpoints are failing — state may be inconsistent; job could auto-restart.

**Diagnosis:**
```bash
# CloudWatch Logs for the Flink application
aws logs filter-log-events \
  --log-group-name /aws/kinesis-analytics/authpulse-dev-flink-app \
  --filter-pattern "ERROR" \
  --start-time $(date -d '30 minutes ago' +%s000)
```
**Likely causes:**
1. S3 write permission denied (check IAM role includes `s3:PutObject` on the lakehouse bucket).
2. Checkpoint S3 path unreachable / bucket deleted.
3. Memory pressure — increase KPU allocation.

**Remediation:**
- Fix IAM: `terraform apply` after correcting `modules/iam/main.tf`.
- Increase KPUs via the KDA application configuration.
- Force snapshot restore after fix:
  ```bash
  aws kinesisanalyticsv2 stop-application --application-name authpulse-dev-flink-app
  aws kinesisanalyticsv2 start-application --application-name authpulse-dev-flink-app \
    --run-configuration '{"ApplicationRestoreConfiguration":{"ApplicationRestoreType":"RESTORE_FROM_LATEST_SNAPSHOT"}}'
  ```

---

### Alert: `authpulse-dev-dq-invalid-record-percent-high`
**Meaning:** `InvalidRecordPercent > 0.1%` — DQ SLA breach; data quality degraded.

**Diagnosis:**
```powershell
# Re-run DQ checks to get the latest report
python -m quality.run_quality_checks \
  --config config/dev.yaml \
  --suite  src/quality/expectations/auth_events_expectations.yml
# Check the JSON report in src/quality/dq_reports/
Get-ChildItem src/quality/dq_reports/ | Sort-Object LastWriteTime -Descending | Select -First 1
```
**Likely causes:**
1. Schema change in upstream producer — check `auth_events_expectations.yml` schema check.
2. Corrupt batch replayed — inspect the failing `event_id` values.
3. Null user_id / computer_id — Flink filter allows nulls through on CSV parse errors.

**Remediation:**
- If schema changed: update `auth_events_expectations.yml` and the Flink source DDL.
- If corrupt data: identify the bad partition in S3 and delete/re-replay.

---

## 3. Rollback Procedures

### Roll back infrastructure
```bash
cd infra/terraform/envs/dev
terraform plan -destroy -out=destroy.tfplan
terraform apply destroy.tfplan
```
> **Note:** This destroys the Kinesis stream and all CloudWatch alarms. S3 data is retained.

### Roll back Flink job to prior version
1. In the AWS Console → Kinesis Analytics → `authpulse-dev-flink-app` → Snapshots.
2. Select the last known-good snapshot.
3. `start-application` with `ApplicationRestoreType: RESTORE_FROM_CUSTOM_SNAPSHOT`.

### Revert producer config
```bash
git log --oneline config/dev.yaml         # find last good commit
git checkout <commit-hash> -- config/dev.yaml
```

---

## 4. Useful Commands Reference

| Task | Command |
|---|---|
| Check git status | `git status` |
| Run unit tests | `python -m pytest ci-cd/tests/unit/ -v` |
| Run integration tests | `python -m pytest ci-cd/tests/integration/ -v` |
| Dry-run producer | `python -m producer.replay_lanl --config config/dev.yaml --dry-run` |
| Run DQ checks | `python -m quality.run_quality_checks --config config/dev.yaml --suite src/quality/expectations/auth_events_expectations.yml` |
| Athena freshness query | See `analytics/athena_queries.sql` Query 7 |
| Terraform plan | `cd infra/terraform/envs/dev && terraform plan` |
| List SNS subscriptions | `aws sns list-subscriptions-by-topic --topic-arn <arn>` |
| Confirm SNS email | Click link in AWS confirmation email after `terraform apply` |
