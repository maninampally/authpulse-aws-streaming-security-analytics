variable "name_prefix" {
  type        = string
  description = "Prefix for naming monitoring resources (e.g., authpulse-dev)."
}

variable "aws_region" {
  type        = string
  description = "AWS region for dashboard widgets."
}

variable "kinesis_stream_name" {
  type        = string
  description = "Kinesis stream name used in dashboard widgets and alarms."
}

variable "flink_application_name" {
  type        = string
  description = "Managed Flink application name (used as a CloudWatch metric dimension)."
  default     = ""
}

variable "flink_metrics_namespace" {
  type        = string
  description = "CloudWatch namespace for Managed Flink metrics (varies by deployment)."
  default     = "AWS/KinesisAnalytics"
}

variable "flink_application_dimension_name" {
  type        = string
  description = "Dimension key name that identifies the Flink application (commonly 'Application')."
  default     = "Application"
}

variable "dashboard_json_path" {
  type        = string
  description = "Path to cloudwatch_dashboard.json template file."
}

variable "alert_email" {
  type        = string
  description = "Email endpoint for SNS subscription (must be confirmed by the recipient)."
  default     = "alerts@example.com"
}

variable "dq_metric_namespace" {
  type        = string
  description = "Namespace for DQ custom metrics."
  default     = "Authpulse/DQ"
}

variable "dq_invalid_percent_metric_name" {
  type        = string
  description = "Metric name for invalid record percent."
  default     = "InvalidRecordPercent"
}

variable "enable_incoming_records_low_alarm" {
  type        = bool
  description = "Whether to enable an optional alarm when IncomingRecords is too low."
  default     = false
}

variable "incoming_records_low_threshold" {
  type        = number
  description = "Threshold for the optional IncomingRecords-low alarm (records per minute)."
  default     = 1
}

variable "enable_dq_log_metric_filter" {
  type        = bool
  description = "Whether to create a log metric filter for DQ invalid percent logs."
  default     = false
}

variable "dq_log_group_name" {
  type        = string
  description = "CloudWatch Logs log group name used for the DQ log metric filter."
  default     = "/aws/authpulse/dq"
}

variable "dq_log_retention_days" {
  type        = number
  description = "Retention in days for the optional DQ log group."
  default     = 30
}
