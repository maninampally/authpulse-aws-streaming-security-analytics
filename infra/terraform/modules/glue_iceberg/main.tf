# ============================================================
# AuthPulse – Glue Catalog + Iceberg table definitions
# ============================================================
# Creates the Glue database and all four Iceberg table entries.
# The tables point to S3 locations under the lakehouse bucket.
# Athena query engine v3 (Iceberg) reads these table definitions.
# ============================================================

locals {
  base_location = "s3://${var.lakehouse_bucket_name}"
}

# ── Glue database ────────────────────────────────────────────
resource "aws_glue_catalog_database" "authpulse" {
  name        = var.database_name
  description = "AuthPulse streaming lakehouse database (Iceberg)"

  tags = var.tags
}

# ── auth_events_raw ──────────────────────────────────────────
resource "aws_glue_catalog_table" "auth_events_raw" {
  name          = "auth_events_raw"
  database_name = aws_glue_catalog_database.authpulse.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "table_type"       = "ICEBERG"
    "metadata_location" = "${local.base_location}/raw/auth_events/metadata/"
  }

  storage_descriptor {
    location      = "${local.base_location}/raw/auth_events/"
    input_format  = "org.apache.iceberg.mr.mapred.IcebergInputFormat"
    output_format = "org.apache.iceberg.mr.mapred.IcebergOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.iceberg.mr.hive.IcebergSerDe"
    }

    columns {
      name = "event_time"
      type = "timestamp"
    }
    columns {
      name = "user_id"
      type = "string"
    }
    columns {
      name = "computer_id"
      type = "string"
    }
    columns {
      name = "event_id"
      type = "string"
    }
  }

  partition_keys {
    name = "event_date"
    type = "string"
  }
}

# ── auth_events_curated ──────────────────────────────────────
resource "aws_glue_catalog_table" "auth_events_curated" {
  name          = "auth_events_curated"
  database_name = aws_glue_catalog_database.authpulse.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "table_type"        = "ICEBERG"
    "metadata_location" = "${local.base_location}/curated/auth_events_curated/metadata/"
  }

  storage_descriptor {
    location      = "${local.base_location}/curated/auth_events_curated/"
    input_format  = "org.apache.iceberg.mr.mapred.IcebergInputFormat"
    output_format = "org.apache.iceberg.mr.mapred.IcebergOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.iceberg.mr.hive.IcebergSerDe"
    }

    columns {
      name = "event_time"
      type = "timestamp"
    }
    columns {
      name = "user_id"
      type = "string"
    }
    columns {
      name = "src_host"
      type = "string"
    }
    columns {
      name = "dst_host"
      type = "string"
    }
    columns {
      name = "success"
      type = "boolean"
    }
    columns {
      name = "window_1h_event_count"
      type = "bigint"
    }
    columns {
      name = "window_1h_unique_hosts"
      type = "bigint"
    }
    columns {
      name = "window_24h_unique_hosts"
      type = "bigint"
    }
    columns {
      name = "has_new_device"
      type = "boolean"
    }
    columns {
      name = "risk_score"
      type = "int"
    }
    columns {
      name    = "risk_flags"
      type    = "array<string>"
      comment = "Triggered rule IDs"
    }
  }

  partition_keys {
    name = "event_date"
    type = "string"
  }
}

# ── user_behavior_hourly ─────────────────────────────────────
resource "aws_glue_catalog_table" "user_behavior_hourly" {
  name          = "user_behavior_hourly"
  database_name = aws_glue_catalog_database.authpulse.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "table_type"        = "ICEBERG"
    "metadata_location" = "${local.base_location}/features/auth_user_features/metadata/"
  }

  storage_descriptor {
    location      = "${local.base_location}/features/auth_user_features/"
    input_format  = "org.apache.iceberg.mr.mapred.IcebergInputFormat"
    output_format = "org.apache.iceberg.mr.mapred.IcebergOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.iceberg.mr.hive.IcebergSerDe"
    }

    columns {
      name = "window_start"
      type = "timestamp"
    }
    columns {
      name = "window_end"
      type = "timestamp"
    }
    columns {
      name = "user_id"
      type = "string"
    }
    columns {
      name    = "window_size"
      type    = "string"
      comment = "1h or 24h"
    }
    columns {
      name = "unique_hosts"
      type = "bigint"
    }
    columns {
      name = "event_count"
      type = "bigint"
    }
    columns {
      name = "has_new_device"
      type = "boolean"
    }
  }

  partition_keys {
    name    = "window_size"
    type    = "string"
    comment = "1h or 24h"
  }
}

# ── host_popularity_daily ────────────────────────────────────
resource "aws_glue_catalog_table" "host_popularity_daily" {
  name          = "host_popularity_daily"
  database_name = aws_glue_catalog_database.authpulse.name

  table_type = "EXTERNAL_TABLE"

  parameters = {
    "table_type"        = "ICEBERG"
    "metadata_location" = "${local.base_location}/curated/host_popularity_daily/metadata/"
  }

  storage_descriptor {
    location      = "${local.base_location}/curated/host_popularity_daily/"
    input_format  = "org.apache.iceberg.mr.mapred.IcebergInputFormat"
    output_format = "org.apache.iceberg.mr.mapred.IcebergOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.iceberg.mr.hive.IcebergSerDe"
    }

    columns {
      name = "computer_id"
      type = "string"
    }
    columns {
      name = "access_count"
      type = "bigint"
    }
    columns {
      name = "unique_users"
      type = "bigint"
    }
    columns {
      name = "is_rare"
      type = "boolean"
    }
  }

  partition_keys {
    name    = "event_date"
    type    = "string"
    comment = "yyyy-MM-dd"
  }
}
