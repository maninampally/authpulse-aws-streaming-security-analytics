# Flink Reference Implementation

> **Status:** Reference only — **not the deployed streaming path**.

This directory contains a PyFlink SQL Table API job (`main_job.py`) and Kinesis serializers
(`serializers.py`) that document how this pipeline would be implemented on Amazon Kinesis Data
Analytics (KDA v2 / Managed Service for Apache Flink).

## Why it's not deployed

KDA's PyFlink runtime requires a Maven-built fat JAR with a valid `Main-Class` manifest entry.
After multiple packaging attempts (see `docs/design_decisions.md` Decision 11), this was
abandoned in favor of an AWS Lambda + DynamoDB consumer (`src/lambda_consumer/`) that delivers
equivalent business value without the Java build pipeline.

## What runs in production

The live streaming path is `src/lambda_consumer/handler.py`, deployed via the
`infra/terraform/modules/lambda_consumer/` module. The same `src/stream/risk_rules.py` module is
imported and reused unchanged by both Lambda and this Flink reference code.
