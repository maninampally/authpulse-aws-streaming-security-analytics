locals {
  effective_role_name = coalesce(var.role_name, "${var.name_prefix}-role")

  policy_statements = [
    {
      Sid    = "KinesisWrite"
      Effect = "Allow"
      Action = [
        "kinesis:DescribeStream",
        "kinesis:DescribeStreamSummary",
        "kinesis:PutRecord",
        "kinesis:PutRecords"
      ]
      Resource = var.kinesis_stream_arn
    },
    {
      Sid    = "S3LakehouseAccess"
      Effect = "Allow"
      Action = [
        "s3:ListBucket"
      ]
      Resource = var.s3_bucket_arn
    },
    {
      Sid    = "S3LakehouseObjectAccess"
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ]
      Resource = "${var.s3_bucket_arn}/*"
    }
  ]
}

resource "aws_iam_policy" "this" {
  name        = "${var.name_prefix}-policy"
  description = "AuthPulse IAM policy for Kinesis + S3 lakehouse access"

  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.policy_statements
  })

  tags = var.tags
}

resource "aws_iam_role" "this" {
  count = var.create_role ? 1 : 0

  name = local.effective_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = var.trusted_services
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "this" {
  count = var.create_role ? 1 : 0

  role       = aws_iam_role.this[0].name
  policy_arn = aws_iam_policy.this.arn
}
