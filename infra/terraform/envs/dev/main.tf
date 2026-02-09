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
