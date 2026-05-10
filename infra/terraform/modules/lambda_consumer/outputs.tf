output "lambda_function_name" {
  value = aws_lambda_function.auth_processor.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.auth_processor.arn
}

output "state_table_name" {
  value = aws_dynamodb_table.user_state.name
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda.arn
}
