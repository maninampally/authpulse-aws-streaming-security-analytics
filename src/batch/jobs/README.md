# Batch jobs (Day 9)

These jobs populate Iceberg aggregate tables using **Athena SQL** (via `boto3`) for a lightweight demo-friendly batch layer.

## Configure

Add an `athena` section to your config file (defaults to `config/dev.yaml`):

```yaml
athena:
  workgroup: primary
  output_s3: s3://authpulse-dev-raw/athena-results/
```

The AWS settings are read from the same config:

```yaml
aws:
  region: us-east-1
  profile: default
```

## Run manually

Populate hourly user behavior aggregates:

```bash
python -m batch.jobs.user_behavior_hourly_job --start-date 2026-02-20 --end-date 2026-02-21
```

Populate daily host popularity aggregates:

```bash
python -m batch.jobs.host_popularity_daily_job --start-date 2026-02-20 --end-date 2026-02-21
```

## Run both (scheduler entrypoint)

```bash
python scripts/run_daily_batch.py --start-date 2026-02-20 --end-date 2026-02-21
```

These jobs are **idempotent** for the provided date range:
- they `DELETE` existing rows in the target table for that range
- then `INSERT` fresh aggregates from `lakehouse.auth_events_curated`

## Validate in Athena

Examples are in:
- [src/batch/ddl/sample_queries.sql](../ddl/sample_queries.sql)
