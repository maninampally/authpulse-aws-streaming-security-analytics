# Observability Test Plan (Day 11)

This is a lightweight runbook to validate CloudWatch dashboards, alarms, and SNS delivery.

## Preconditions

- Terraform applied for the environment (dev or prod)
- You have access to CloudWatch dashboards/alarms in the target AWS account
- The SNS email subscription is confirmed (AWS sends a confirmation email to the endpoint)

## Test 1: Kinesis lag alarm (iterator age)

**Goal**: trigger the iterator age high alarm and verify SNS notification.

**How (one of the following)**
- Temporarily stop or scale down the Flink application so it stops consuming.
- Temporarily throttle the consumer (reduce parallelism / force backpressure) to build up lag.

**Expected result**
- CloudWatch metric `AWS/Kinesis / GetRecords.IteratorAgeMilliseconds` rises above 300,000 ms.
- Alarm transitions `OK  ALARM` after ~3 minutes.
- SNS sends an email notification.

**Cleanup**
- Restore normal Flink operation and verify alarm returns to `OK`.

## Test 2: DQ invalid-record % alarm

**Goal**: push `InvalidRecordPercent` above 0.1% and verify SNS notification.

**How**
- Inject invalid records (e.g., wrong schema / missing required fields) into the curated table path, OR
- Run the Day 10 DQ suite against a known-bad date partition.

**Expected result**
- The DQ runner emits an `InvalidRecordPercent` value > 0.1.
- CloudWatch alarm transitions to `ALARM` for the custom metric.

**Notes**
- If using log-based metric filters, ensure the emitting process writes logs into the configured log group.
- If using direct `PutMetricData`, ensure the runner has `cloudwatch:PutMetricData` permissions.

## Test 3: Flink failed checkpoints alarm

**Goal**: confirm `numberOfFailedCheckpoints` rate alarm fires.

**How**
- Introduce a controlled failure (e.g., misconfigure a sink permission) to cause checkpoint failures.

**Expected result**
- `numberOfFailedCheckpoints` increases.
- Alarm transitions to `ALARM`.

## Quick sanity checks

- Dashboard widgets render metrics in the correct region.
- Alarms show recent datapoints and do not remain in `INSUFFICIENT_DATA` under normal load.
- SNS subscription is confirmed.
