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
