# Day 5 — Flink Job Skeleton (LANL → Kinesis → Flink → S3)

This project’s ingest path already writes **AuthEvent JSON** into Kinesis (via `event.model_dump_json()`).
The Flink job skeleton is implemented in:

- `src/stream/flink/main_job.py`

It supports two input formats:

- `json` (recommended): reads AuthEvent JSON from Kinesis
- `csv`: reads LANL `time,user,computer` rows and converts to AuthEvent-shaped fields

## 1) Configure

Defaults are aimed at dev, but you can override via CLI args or environment variables:

- `AUTHPULSE_KINESIS_STREAM` (or `--kinesis-stream`)
- `AWS_REGION` / `AUTHPULSE_AWS_REGION` (or `--aws-region`)
- `AUTHPULSE_SOURCE_FORMAT` (or `--source-format`) — `json` or `csv`
- `AUTHPULSE_S3_RAW_PATH` (or `--s3-raw-path`) — e.g. `s3a://<bucket>/raw/auth_events`

The sink is partitioned by `event_date` (`yyyy-MM-dd`) using Hive-style partition directories.

## 2) Deploy to AWS Managed Service for Apache Flink (Kinesis Data Analytics)

High-level steps (AWS console):

1. Create / choose an MSF application (Apache Flink runtime).
2. Ensure the application IAM role has:
   - read permissions for the Kinesis stream
   - write permissions for the S3 raw bucket/prefix
3. Package the Python app per AWS MSF Python examples (zip your app, include dependencies if required).
4. Point the MSF application code location to your uploaded artifact (S3).
5. Start the application and watch logs.

Notes:
- The Kinesis connector and filesystem connector availability depends on the MSF runtime.
- S3 paths often use `s3a://...` in Flink.

## 3) Verify records in S3

After starting the app, verify objects appear under your raw prefix, partitioned by date.

Using AWS CLI:

```bash
aws s3 ls s3://<bucket>/raw/auth_events/ --recursive | head
```

You should see directories like:

- `.../event_date=2026-02-20/...`

and JSON files containing `event_time`, `user_id`, `computer_id`, `event_id`.
