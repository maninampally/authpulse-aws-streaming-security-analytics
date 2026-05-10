# DynamoDB table for per-user state
resource "aws_dynamodb_table" "user_state" {
  name         = "${var.name_prefix}-user-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = var.tags
}

# IAM role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.name_prefix}-lambda-consumer-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.name_prefix}-lambda-consumer-policy"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "*"
      },
      {
        Sid    = "KinesisRead"
        Effect = "Allow"
        Action = [
          "kinesis:DescribeStream",
          "kinesis:DescribeStreamSummary",
          "kinesis:GetRecords",
          "kinesis:GetShardIterator",
          "kinesis:ListShards",
          "kinesis:SubscribeToShard",
        ]
        Resource = var.kinesis_stream_arn
      },
      {
        Sid    = "DynamoDBRW"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
        ]
        Resource = aws_dynamodb_table.user_state.arn
      },
      {
        Sid    = "S3Write"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket",
        ]
        Resource = [
          var.lakehouse_bucket_arn,
          "${var.lakehouse_bucket_arn}/*",
        ]
      },
    ]
  })
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.name_prefix}-auth-processor"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# Lambda function
resource "aws_lambda_function" "auth_processor" {
  function_name    = "${var.name_prefix}-auth-processor"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.11"
  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  timeout          = 60
  memory_size      = 512

  environment {
    variables = {
      STATE_TABLE_NAME    = aws_dynamodb_table.user_state.name
      LAKEHOUSE_BUCKET    = var.lakehouse_bucket_name
      S3_RAW_PREFIX       = "raw/auth_events/"
      S3_CURATED_PREFIX   = "curated/auth_events_curated/"
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  tags = var.tags
}

# Kinesis event source mapping
resource "aws_lambda_event_source_mapping" "kinesis" {
  event_source_arn                   = var.kinesis_stream_arn
  function_name                      = aws_lambda_function.auth_processor.arn
  starting_position                  = "LATEST"
  batch_size                         = var.batch_size
  maximum_batching_window_in_seconds = var.batch_window_seconds
  bisect_batch_on_function_error     = true
  maximum_retry_attempts             = 3
}
