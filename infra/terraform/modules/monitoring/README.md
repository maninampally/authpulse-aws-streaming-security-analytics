# Monitoring Module

Creates a basic but realistic observability layer for the AuthPulse pipeline:

- CloudWatch dashboard (rendered from `infra/terraform/monitoring/cloudwatch_dashboard.json`)
- CloudWatch alarms (Kinesis lag, optional Kinesis low traffic, DQ invalid %)
- SNS topic + email subscription for alert delivery

Notes

- Dashboard widgets cover Kinesis lag, Lambda invocations/errors/duration, DynamoDB state latency, and DQ invalid record percent.
- For DQ invalid % you can either:
	- emit the custom metric directly from your DQ job (recommended for reliability), or
	- enable the optional CloudWatch Logs metric filter (`enable_dq_log_metric_filter = true`) and ensure the job writes JSON log lines into `dq_log_group_name`.
