output "kinesis_stream_name" {
  value = module.kinesis.stream_name
}

output "kinesis_stream_arn" {
  value = module.kinesis.stream_arn
}

output "lakehouse_bucket_name" {
  value = module.s3.bucket_name
}

output "lakehouse_bucket_arn" {
  value = module.s3.bucket_arn
}
