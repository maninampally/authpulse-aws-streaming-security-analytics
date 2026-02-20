variable "name_prefix" {
  type        = string
  description = "Prefix used for IAM resource names"
}

variable "kinesis_stream_arn" {
  type        = string
  description = "ARN of the Kinesis stream to allow access to"
}

variable "s3_bucket_arn" {
  type        = string
  description = "ARN of the S3 bucket to allow access to"
}

variable "create_role" {
  type        = bool
  description = "Whether to create an IAM role and attach the policy"
  default     = true
}

variable "role_name" {
  type        = string
  description = "Role name (when create_role=true). Defaults to '<name_prefix>-role'."
  default     = null
}

variable "trusted_services" {
  type        = list(string)
  description = "AWS service principals allowed to assume the role (when create_role=true)"
  default     = ["ec2.amazonaws.com"]
}

variable "tags" {
  type        = map(string)
  description = "Tags to apply to IAM resources"
  default     = {}
}
