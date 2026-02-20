variable "stream_name" {
  type = string
}

variable "shard_count" {
  type    = number
  default = 1
}

variable "retention_hours" {
  type    = number
  default = 24
}

variable "encryption_type" {
  type    = string
  default = "KMS"

  validation {
    condition     = contains(["KMS", "NONE"], var.encryption_type)
    error_message = "encryption_type must be one of: KMS, NONE."
  }
}

variable "kms_key_id" {
  type    = string
  description = "KMS key ID/ARN/alias to use when encryption_type=KMS. Defaults to the AWS-managed key alias for Kinesis."
  default = "alias/aws/kinesis"
}

variable "tags" {
  type    = map(string)
  default = {}
}
