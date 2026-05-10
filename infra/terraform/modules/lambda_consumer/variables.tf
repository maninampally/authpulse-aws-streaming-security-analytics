variable "name_prefix" {
  type        = string
  description = "Resource name prefix (e.g. authpulse-dev)"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "kinesis_stream_arn" {
  type        = string
  description = "Source Kinesis stream ARN"
}

variable "lakehouse_bucket_name" {
  type        = string
  description = "S3 lakehouse bucket name"
}

variable "lakehouse_bucket_arn" {
  type        = string
  description = "S3 lakehouse bucket ARN"
}

variable "lambda_zip_path" {
  type        = string
  description = "Local path to lambda deployment ZIP"
}

variable "batch_size" {
  type    = number
  default = 100
}

variable "batch_window_seconds" {
  type    = number
  default = 30
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "tags" {
  type    = map(string)
  default = {}
}
