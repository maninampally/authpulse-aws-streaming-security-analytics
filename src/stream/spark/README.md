# Spark Reference Implementation

> **Status:** Reference only — **not deployed in dev**.

This directory contains a PySpark Structured Streaming job (`main_job.py`) intended for an
Amazon EMR cluster. It is the secondary/batch path described in the architecture and would be
used to:

- Compact raw JSONL.GZ from Lambda into Apache Iceberg Parquet tables
- Populate `authpulse.user_behavior_hourly` and `authpulse.host_popularity_daily` aggregates
- Run historical backfills against the full LANL dataset

## Why it's not deployed

The dev environment uses the Lambda consumer (`src/lambda_consumer/`) for live streaming, which
is sufficient to validate the business logic and architecture end-to-end. EMR cluster
provisioning and Iceberg writes are listed in the README **Future Enhancements** section.

The same `src/stream/risk_rules.py` module is imported and reused unchanged by both Lambda and
this Spark reference code.
