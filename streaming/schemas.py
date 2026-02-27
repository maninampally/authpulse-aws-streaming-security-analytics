"""
AuthPulse - PySpark Schema Definitions
Defines structured schemas for raw events, enriched events, and aggregations.
All schemas mirror the Flink sink DDLs so S3 data is interchangeable.

PySpark is an optional runtime dependency; schemas are None when pyspark is
not installed.  The spark job will raise at runtime if they are None.
"""

from __future__ import annotations

try:
    from pyspark.sql.types import (
        ArrayType,
        BooleanType,
        IntegerType,
        LongType,
        StringType,
        StructField,
        StructType,
        TimestampType,
    )

    # ── Raw auth events ──────────────────────────────────────────────────────
    RAW_AUTH_EVENT_SCHEMA = StructType(
        [
            StructField("event_time", TimestampType(), nullable=False),
            StructField("user_id", StringType(), nullable=False),
            StructField("computer_id", StringType(), nullable=False),
            StructField("event_id", StringType(), nullable=False),
            StructField("event_date", StringType(), nullable=False),
        ]
    )

    # ── Curated / enriched events ─────────────────────────────────────────────
    ENRICHED_EVENT_SCHEMA = StructType(
        [
            StructField("event_time", TimestampType(), nullable=False),
            StructField("user_id", StringType(), nullable=False),
            StructField("src_host", StringType(), nullable=True),
            StructField("dst_host", StringType(), nullable=True),
            StructField("success", BooleanType(), nullable=True),
            StructField("window_1h_event_count", LongType(), nullable=True),
            StructField("window_1h_unique_hosts", LongType(), nullable=True),
            StructField("window_24h_unique_hosts", LongType(), nullable=True),
            StructField("has_new_device", BooleanType(), nullable=True),
            StructField("risk_score", IntegerType(), nullable=True),
            StructField("risk_flags", ArrayType(StringType()), nullable=True),
            StructField("event_date", StringType(), nullable=False),
        ]
    )

    # ── Per-user windowed feature aggregations ───────────────────────────────
    USER_BEHAVIOR_HOURLY_SCHEMA = StructType(
        [
            StructField("window_start", TimestampType(), nullable=False),
            StructField("window_end", TimestampType(), nullable=False),
            StructField("user_id", StringType(), nullable=False),
            StructField("window_size", StringType(), nullable=False),
            StructField("unique_hosts", LongType(), nullable=True),
            StructField("event_count", LongType(), nullable=True),
            StructField("has_new_device", BooleanType(), nullable=True),
        ]
    )

    # ── Daily host access statistics ─────────────────────────────────────────
    HOST_POPULARITY_DAILY_SCHEMA = StructType(
        [
            StructField("event_date", StringType(), nullable=False),
            StructField("computer_id", StringType(), nullable=False),
            StructField("access_count", LongType(), nullable=True),
            StructField("unique_users", LongType(), nullable=True),
            StructField("is_rare", BooleanType(), nullable=True),
        ]
    )

except ImportError:  # pyspark not installed (unit-test / local env)
    RAW_AUTH_EVENT_SCHEMA = None       # type: ignore[assignment]
    ENRICHED_EVENT_SCHEMA = None       # type: ignore[assignment]
    USER_BEHAVIOR_HOURLY_SCHEMA = None # type: ignore[assignment]
    HOST_POPULARITY_DAILY_SCHEMA = None  # type: ignore[assignment]


__all__ = [
    "RAW_AUTH_EVENT_SCHEMA",
    "ENRICHED_EVENT_SCHEMA",
    "USER_BEHAVIOR_HOURLY_SCHEMA",
    "HOST_POPULARITY_DAILY_SCHEMA",
]
