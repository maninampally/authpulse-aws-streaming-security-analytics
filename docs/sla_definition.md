# AuthPulse SLAs (Day 11)

This project is a reference architecture for streaming security analytics:

LANL auth logs → replay producer → Kinesis Data Streams → Managed Service for Apache Flink → S3 (raw/features/curated) → Iceberg/Athena.

The SLAs below are written as measurable targets and mapped to CloudWatch signals so they can be monitored continuously.

## Freshness SLA (curated availability)

Target
- 99% of `lakehouse.auth_events_curated` records are available in S3 within 5 minutes of `event_time`.

How to measure
- Best-effort proxy signals (recommended for demo/PoC environments):
	- Kinesis consumer lag (iterator age): if the consumer lags, curated data will be delayed.
	- Flink health: failed checkpoints and throughput drops correlate strongly with delayed writes.

CloudWatch signals
- `AWS/Kinesis` `GetRecords.IteratorAgeMilliseconds` (Maximum, 60s)
- Flink application metrics (namespace/dimensions vary by deployment; see notes below)

## Lag SLA (Kinesis consumer lag)

Target
- `GetRecords.IteratorAgeMilliseconds` stays below 300,000 ms (5 minutes) under normal load.

CloudWatch signals
- `AWS/Kinesis` `GetRecords.IteratorAgeMilliseconds` (Maximum)

Alarm
- Triggers when iterator age ≥ 300,000 ms for 3 consecutive 1-minute periods.

## Completeness SLA (data loss / drops)

Target
- < 0.1% dropped/invalid events per day.

Notes
- In this repo, completeness is approximated by DQ failures and/or explicit invalid-record counters.
- If you implement a strict “invalid record” routing path (DLQ) in Flink, you can monitor dropped counts directly.

CloudWatch signals
- Custom metric `Authpulse/DQ` `InvalidRecordPercent` (see DQ SLA)
- Optional: Flink error counters or log-based metrics

## Error rate SLA (stream processing)

Target
- Flink job error rate < 0.1% of records.
- Checkpoints must not fail continuously.

CloudWatch signals
- Flink `numberOfFailedCheckpoints` (alarmed on non-zero rate)
- Flink `numRecordsIn` / `numRecordsOut` (throughput proxy)

## DQ SLA (ties to Day 10)

Target
- Invalid records < 0.1% per run/window.

What counts as “invalid” in this repo
- The Day 10 DQ runner evaluates checks (schema, not-null, range, allowed values) and reports `failure_pct` per check.
- For observability, we emit `InvalidRecordPercent` as the maximum `failure_pct` across checks for the suite.

CloudWatch signals
- Custom metric: Namespace `Authpulse/DQ`, Metric `InvalidRecordPercent`
	- Value is a percentage in the range [0, 100]
	- Alarm threshold: 0.1 (meaning 0.1%)

## Interpreting the dashboard

- Iterator age high → likely violates Freshness SLA.
- IncomingRecords low → producer stopped, upstream outage, or permissions (optional alarm).
- Failed checkpoints → unstable processing; often leads to delayed or missing curated outputs.
- InvalidRecordPercent high → violates Completeness and DQ SLAs.

## Managed Flink metric namespace notes

Managed Service for Apache Flink exposes application metrics to CloudWatch, but the exact namespace/dimensions can vary.

Terraform defaults are intentionally configurable (stream name, Flink application name, and Flink metric namespace) so the same monitoring module can be used for both dev and prod.
