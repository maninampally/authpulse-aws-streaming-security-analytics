output "sns_topic_arn" {
  value       = aws_sns_topic.alerts.arn
  description = "SNS topic ARN used for alarm notifications."
}

output "dashboard_name" {
  value       = aws_cloudwatch_dashboard.main.dashboard_name
  description = "CloudWatch dashboard name."
}
