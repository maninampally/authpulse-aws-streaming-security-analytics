locals {
  dashboard_template_raw = file(var.dashboard_json_path)

  dashboard_body = replace(
    replace(
      replace(
        replace(local.dashboard_template_raw, "__REGION__", var.aws_region),
        "__STREAM_NAME__",
        var.kinesis_stream_name
      ),
      "__FLINK_APP_NAME__",
      var.flink_application_name
    ),
    "__FLINK_NAMESPACE__",
    var.flink_metrics_namespace
  )
}

resource "aws_sns_topic" "alerts" {
  name = "${var.name_prefix}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-dashboard"
  dashboard_body = local.dashboard_body
}

# --- Alarms ---

resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age_high" {
  alarm_name          = "${var.name_prefix}-kinesis-iterator-age-high"
  alarm_description   = "Kinesis iterator age > 5 minutes (Maximum over 60s)"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 300000

  namespace   = "AWS/Kinesis"
  metric_name = "GetRecords.IteratorAgeMilliseconds"
  statistic   = "Maximum"
  period      = 60

  evaluation_periods = 3
  datapoints_to_alarm = 3

  treat_missing_data = "notBreaching"

  dimensions = {
    StreamName = var.kinesis_stream_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "dq_invalid_record_percent_high" {
  alarm_name        = "${var.name_prefix}-dq-invalid-record-percent-high"
  alarm_description = "Invalid record percent > 0.1% (Authpulse/DQ custom metric)"

  namespace   = var.dq_metric_namespace
  metric_name = var.dq_invalid_percent_metric_name
  statistic   = "Maximum"
  period      = 300

  comparison_operator = "GreaterThanThreshold"
  threshold           = 0.1

  evaluation_periods = 1
  datapoints_to_alarm = 1

  treat_missing_data = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "kinesis_incoming_records_too_low" {
  count = var.enable_incoming_records_low_alarm ? 1 : 0

  alarm_name        = "${var.name_prefix}-kinesis-incoming-records-too-low"
  alarm_description = "IncomingRecords below expected minimum (optional)"

  namespace   = "AWS/Kinesis"
  metric_name = "IncomingRecords"
  statistic   = "Sum"
  period      = 60

  comparison_operator = "LessThanThreshold"
  threshold           = var.incoming_records_low_threshold

  evaluation_periods = 5
  datapoints_to_alarm = 5

  treat_missing_data = "breaching"

  dimensions = {
    StreamName = var.kinesis_stream_name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "flink_failed_checkpoints_rate" {
  count = var.flink_application_name != "" ? 1 : 0

  alarm_name        = "${var.name_prefix}-flink-failed-checkpoints-rate"
  alarm_description = "Flink failed checkpoints increasing (RATE(numberOfFailedCheckpoints) > 0)"

  comparison_operator = "GreaterThanThreshold"
  threshold           = 0

  evaluation_periods = 3
  datapoints_to_alarm = 1

  treat_missing_data = "notBreaching"

  metric_query {
    id          = "m1"
    return_data = false

    metric {
      namespace   = var.flink_metrics_namespace
      metric_name = "numberOfFailedCheckpoints"
      period      = 60
      stat        = "Sum"
      dimensions = {
        "${var.flink_application_dimension_name}" = var.flink_application_name
      }
    }
  }

  metric_query {
    id          = "e1"
    expression  = "RATE(m1)"
    label       = "FailedCheckpointRate"
    return_data = true
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}

# --- Optional log-based metric filter (DQ) ---

resource "aws_cloudwatch_log_group" "dq" {
  count             = var.enable_dq_log_metric_filter ? 1 : 0
  name              = var.dq_log_group_name
  retention_in_days = var.dq_log_retention_days
}

resource "aws_cloudwatch_log_metric_filter" "dq_invalid_percent" {
  count          = var.enable_dq_log_metric_filter ? 1 : 0
  name           = "${var.name_prefix}-dq-invalid-percent"
  log_group_name = aws_cloudwatch_log_group.dq[0].name

  # Expects JSON logs like: {"metric":"dq_invalid_record_percent","value":0.05,...}
  pattern = "{ $.metric = \"dq_invalid_record_percent\" }"

  metric_transformation {
    name      = var.dq_invalid_percent_metric_name
    namespace = var.dq_metric_namespace
    value     = "$.value"
    unit      = "Percent"
  }
}
