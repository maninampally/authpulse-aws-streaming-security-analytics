# System Overview

AuthPulse is a streaming security analytics pipeline that replays authentication events into Kinesis, processes them with a streaming engine, and stores curated Iceberg tables for analytics.

## Core Flow

1. Replay producer emits events into Amazon Kinesis.
2. Streaming processor validates, deduplicates, and enriches events.
3. Curated datasets are written to S3 as Apache Iceberg tables.
4. Athena/QuickSight query curated tables for dashboards and investigations.
5. CloudWatch/SNS provide operational monitoring and alerting.
