variable "application_name" {
  type        = string
  description = "Name of the Managed Flink (KDA v2) application."
}

variable "runtime_environment" {
  type        = string
  description = "Flink runtime version. See AWS docs for valid values."
  default     = "FLINK-1_18"
}

variable "service_execution_role_arn" {
  type        = string
  description = "ARN of the IAM role that the Flink application assumes."
}

variable "app_s3_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket that holds the application code artifact."
}

variable "app_s3_key" {
  type        = string
  description = "S3 object key for the application code (ZIP or JAR). Upload this before applying."
  default     = "flink-app/authpulse-flink-job.zip"
}

variable "kinesis_stream_name" {
  type        = string
  description = "Kinesis Data Stream name the Flink job reads from."
}

variable "aws_region" {
  type        = string
  description = "AWS region (passed as env var to the Flink job)."
  default     = "us-east-1"
}

variable "lakehouse_bucket_name" {
  type        = string
  description = "S3 bucket name for raw/features/curated data (passed as env vars)."
}

variable "source_format" {
  type        = string
  description = "Input record format in Kinesis: json or csv."
  default     = "json"
}

variable "extra_env_properties" {
  type        = map(string)
  description = "Additional environment properties merged into the authpulse property group."
  default     = {}
}

variable "parallelism" {
  type        = number
  description = "Default parallelism for the Flink job."
  default     = 1
}

variable "parallelism_per_kpu" {
  type        = number
  description = "Parallelism per KPU (Kinesis Processing Unit)."
  default     = 1
}

variable "auto_scaling_enabled" {
  type        = bool
  description = "Whether to enable Flink auto-scaling."
  default     = false
}

variable "checkpoint_interval_ms" {
  type        = number
  description = "Checkpoint interval in milliseconds."
  default     = 60000
}

variable "checkpoint_min_pause_ms" {
  type        = number
  description = "Minimum pause between checkpoints in milliseconds."
  default     = 10000
}

variable "log_level" {
  type        = string
  description = "Flink application log level: INFO, DEBUG, WARN, or ERROR."
  default     = "INFO"
}

variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention in days for the Flink log group."
  default     = 30
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to all resources."
  default     = {}
}
