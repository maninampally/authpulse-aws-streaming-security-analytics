output "policy_arn" {
  value       = aws_iam_policy.this.arn
  description = "IAM policy ARN"
}

output "role_name" {
  value       = var.create_role ? aws_iam_role.this[0].name : null
  description = "IAM role name (if created)"
}

output "role_arn" {
  value       = var.create_role ? aws_iam_role.this[0].arn : null
  description = "IAM role ARN (if created)"
}
