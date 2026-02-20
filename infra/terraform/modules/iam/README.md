# IAM Module

Creates an IAM policy granting:

- Write access to a specific Kinesis stream (PutRecord/PutRecords)
- Read/write access to a specific S3 bucket (ListBucket + Get/Put/DeleteObject)

Optionally creates an IAM role and attaches the policy.

## Inputs

- `name_prefix` (string): prefix for resource names
- `kinesis_stream_arn` (string): target Kinesis stream ARN
- `s3_bucket_arn` (string): target S3 bucket ARN
- `create_role` (bool, default: true): create role + attachment
- `trusted_services` (list(string), default: ["ec2.amazonaws.com"]): role trust principals

## Outputs

- `policy_arn`
- `role_arn` (nullable)
- `role_name` (nullable)
