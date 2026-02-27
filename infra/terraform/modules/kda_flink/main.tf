# ============================================================
# AuthPulse – Managed Service for Apache Flink (KDA v2)
# ============================================================
# Provisions an aws_kinesisanalyticsv2_application (Flink runtime).
# The application code (ZIP or JAR) must be uploaded to S3 before
# running `terraform apply`.  Set var.app_s3_key to the object key.
# ============================================================

resource "aws_kinesisanalyticsv2_application" "this" {
  name                   = var.application_name
  runtime_environment    = var.runtime_environment   # e.g. FLINK-1_18
  service_execution_role = var.service_execution_role_arn

  application_configuration {

    # ── Application code location (S3) ──────────────────────
    application_code_configuration {
      code_content_type = "ZIPFILE"

      code_content {
        s3_content_location {
          bucket_arn = var.app_s3_bucket_arn
          file_key   = var.app_s3_key
        }
      }
    }

    # ── Flink runtime properties ─────────────────────────────
    flink_application_configuration {

      checkpoint_configuration {
        configuration_type         = "CUSTOM"
        checkpointing_enabled      = true
        checkpoint_interval        = var.checkpoint_interval_ms   # 60000 ms
        min_pause_between_checkpoints = var.checkpoint_min_pause_ms  # 10000 ms
      }

      monitoring_configuration {
        configuration_type = "CUSTOM"
        log_level          = var.log_level     # INFO / DEBUG / WARN / ERROR
        metrics_level      = "APPLICATION"
      }

      parallelism_configuration {
        configuration_type   = "CUSTOM"
        parallelism          = var.parallelism
        parallelism_per_kpu  = var.parallelism_per_kpu
        auto_scaling_enabled = var.auto_scaling_enabled
      }
    }

    # ── Environment properties (passed as job env vars) ──────
    environment_properties {
      property_group {
        property_group_id = "authpulse"
        property_map = merge(
          {
            "AUTHPULSE_KINESIS_STREAM"          = var.kinesis_stream_name
            "AWS_REGION"                         = var.aws_region
            "AUTHPULSE_S3_RAW_PATH"             = "s3a://${var.lakehouse_bucket_name}/raw/auth_events"
            "AUTHPULSE_S3_FEATURES_PATH"        = "s3a://${var.lakehouse_bucket_name}/features/auth_user_features/"
            "AUTHPULSE_S3_CURATED_EVENTS_PATH"  = "s3a://${var.lakehouse_bucket_name}/curated/auth_events_curated/"
            "AUTHPULSE_SOURCE_FORMAT"           = var.source_format
          },
          var.extra_env_properties
        )
      }
    }
  }

  # ── CloudWatch Logs ──────────────────────────────────────
  cloudwatch_logging_options {
    log_stream_arn = aws_cloudwatch_log_stream.flink.arn
  }

  tags = var.tags

  lifecycle {
    # Prevent accidental deletion of a running application.
    prevent_destroy = false
  }
}

# ── CloudWatch log group + stream ────────────────────────────
resource "aws_cloudwatch_log_group" "flink" {
  name              = "/aws/kinesis-analytics/${var.application_name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_stream" "flink" {
  name           = "authpulse-flink-stream"
  log_group_name = aws_cloudwatch_log_group.flink.name
}
