provider "aws" {
  region = var.aws_region
  default_tags {
    tags = var.tags
  }
}

module "kinesis" {
  source      = "../../modules/kinesis"
  stream_name = var.kinesis_stream_name
  tags        = var.tags
}

module "s3" {
  source      = "../../modules/s3"
  bucket_name = var.lakehouse_bucket_name
  tags        = var.tags
}

module "iam" {
  source = "../../modules/iam"

  name_prefix        = "authpulse-dev"
  kinesis_stream_arn = module.kinesis.stream_arn
  s3_bucket_arn      = module.s3.bucket_arn

  create_role      = var.create_iam_role
  trusted_services = var.iam_trusted_services

  tags = var.tags
}

module "glue_iceberg" {
  source = "../../modules/glue_iceberg"

  database_name         = var.glue_database_name
  lakehouse_bucket_name = var.lakehouse_bucket_name
  tags                  = var.tags
}

module "lambda_consumer" {
  source = "../../modules/lambda_consumer"

  name_prefix           = "authpulse-dev"
  aws_region            = var.aws_region
  kinesis_stream_arn    = module.kinesis.stream_arn
  lakehouse_bucket_name = var.lakehouse_bucket_name
  lakehouse_bucket_arn  = module.s3.bucket_arn
  lambda_zip_path       = "${path.module}/../../../../src/lambda_consumer/lambda_consumer.zip"

  tags = var.tags
}

module "monitoring" {
  source = "../../modules/monitoring"

  name_prefix         = "authpulse-dev"
  aws_region          = var.aws_region
  kinesis_stream_name = var.kinesis_stream_name

  dashboard_json_path = "${path.module}/../../monitoring/cloudwatch_dashboard.json"

  alert_email = var.alert_email

  enable_incoming_records_low_alarm = var.enable_incoming_records_low_alarm
  incoming_records_low_threshold    = var.incoming_records_low_threshold

  enable_dq_log_metric_filter = var.enable_dq_log_metric_filter
  dq_log_group_name           = var.dq_log_group_name
  dq_log_retention_days       = var.dq_log_retention_days
}
