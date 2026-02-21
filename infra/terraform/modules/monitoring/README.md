# Monitoring Module

Creates a basic but realistic observability layer:

- CloudWatch dashboard (rendered from `infra/terraform/monitoring/cloudwatch_dashboard.json`)
- CloudWatch alarms (Kinesis lag, optional Kinesis low traffic, Flink failed checkpoints, DQ invalid %)
- SNS topic + email subscription for alert delivery

Notes

- Managed Flink metric namespaces and dimensions can vary by account/deployment. The module exposes variables to adjust `flink_metrics_namespace` and the application dimension name.
- For DQ invalid % you can either:
	- emit the custom metric directly from your DQ job (recommended for reliability), or
	- enable the optional CloudWatch Logs metric filter (`enable_dq_log_metric_filter = true`) and ensure the job writes JSON log lines into `dq_log_group_name`.
