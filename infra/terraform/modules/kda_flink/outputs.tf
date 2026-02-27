output "application_name" {
  description = "Managed Flink application name."
  value       = aws_kinesisanalyticsv2_application.this.name
}

output "application_arn" {
  description = "ARN of the Managed Flink application."
  value       = aws_kinesisanalyticsv2_application.this.arn
}

output "application_version_id" {
  description = "Current version ID of the application (increments on each update)."
  value       = aws_kinesisanalyticsv2_application.this.version_id
}

output "log_group_name" {
  description = "CloudWatch log group for Flink application logs."
  value       = aws_cloudwatch_log_group.flink.name
}

output "log_group_arn" {
  description = "CloudWatch log group ARN."
  value       = aws_cloudwatch_log_group.flink.arn
}
