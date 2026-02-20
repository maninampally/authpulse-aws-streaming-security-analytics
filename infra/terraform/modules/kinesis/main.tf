resource "aws_kinesis_stream" "this" {
  name             = var.stream_name
  shard_count      = var.shard_count
  retention_period = var.retention_hours
  encryption_type  = var.encryption_type
  kms_key_id       = var.encryption_type == "KMS" ? var.kms_key_id : null

  tags = var.tags
}

