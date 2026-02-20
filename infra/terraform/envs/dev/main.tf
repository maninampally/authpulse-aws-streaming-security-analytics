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
