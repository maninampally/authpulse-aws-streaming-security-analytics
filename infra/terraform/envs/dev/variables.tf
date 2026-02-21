variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "kinesis_stream_name" {
  type    = string
  default = "authpulse-dev-stream"
}

variable "lakehouse_bucket_name" {
  type    = string
  default = "authpulse-dev-lakehouse-289591071327"
}

variable "tags" {
  type = map(string)
  default = {
    project = "authpulse"
    env     = "dev"
  }
}

variable "create_iam_role" {
  type        = bool
  description = "Whether to create an IAM role in this env (policy is always created)."
  default     = true
}

variable "iam_trusted_services" {
  type        = list(string)
  description = "Service principals allowed to assume the IAM role."
  default     = ["ec2.amazonaws.com"]
}

variable "flink_application_name" {
  type        = string
  description = "Managed Flink application name (for CloudWatch metrics)."
  default     = "authpulse-dev-flink-app"
}

variable "flink_metrics_namespace" {
  type        = string
  description = "CloudWatch namespace for Managed Flink metrics."
  default     = "AWS/KinesisAnalytics"
}

variable "flink_application_dimension_name" {
  type        = string
  description = "Dimension key name for the Flink application."
  default     = "Application"
}

variable "alert_email" {
  type        = string
  description = "Email endpoint for SNS subscription (must confirm)."
  default     = "alerts@example.com"
}

variable "enable_incoming_records_low_alarm" {
  type        = bool
  description = "Optional alarm when Kinesis IncomingRecords is too low."
  default     = false
}

variable "incoming_records_low_threshold" {
  type        = number
  description = "Threshold for optional IncomingRecords-low alarm (records/min)."
  default     = 1
}

variable "enable_dq_log_metric_filter" {
  type        = bool
  description = "Whether to create a CloudWatch Logs metric filter for DQ invalid percent logs."
  default     = false
}

variable "dq_log_group_name" {
  type        = string
  description = "Log group to attach the DQ log metric filter to (if enabled)."
  default     = "/aws/authpulse/dq"
}

variable "dq_log_retention_days" {
  type        = number
  description = "Retention in days for the optional DQ log group."
  default     = 30
}
