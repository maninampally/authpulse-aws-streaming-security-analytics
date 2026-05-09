"""
AuthPulse - Window Metrics Calculator
Computes rolling time-window aggregations for user behavior analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame


def compute_rolling_windows(
    df: "DataFrame",
    *,
    window_1h_duration: str = "1 hour",
    window_1h_slide: str = "5 minutes",
    window_24h_duration: str = "24 hours",
    window_24h_slide: str = "1 hour",
) -> "DataFrame":
    from pyspark.sql import functions as F

    def _agg(duration: str, slide: str, label: str) -> "DataFrame":
        return (
            df.groupBy(
                F.window(F.col("event_time"), duration, slide),
                F.col("user_id"),
            )
            .agg(
                F.countDistinct("computer_id").alias("unique_hosts"),
                F.count("*").alias("event_count"),
                F.max(F.col("is_new_device").cast("boolean")).alias("has_new_device"),
            )
            .select(
                F.col("window.start").alias("window_start"),
                F.col("window.end").alias("window_end"),
                F.col("user_id"),
                F.lit(label).alias("window_size"),
                F.col("unique_hosts"),
                F.col("event_count"),
                F.col("has_new_device"),
            )
        )

    return _agg(window_1h_duration, window_1h_slide, "1h").unionByName(
        _agg(window_24h_duration, window_24h_slide, "24h")
    )


def compute_stateful_aggregates(df: "DataFrame") -> "DataFrame":
    from pyspark.sql import functions as F
    from pyspark.sql.types import BooleanType

    return df.withColumn("is_new_device", F.lit(True).cast(BooleanType()))


def aggregate_user_behavior_hourly(
    features_df: "DataFrame",
    *,
    output_path: str,
    checkpoint_path: str,
    trigger_seconds: int = 30,
) -> None:
    (
        features_df.writeStream.format("parquet")
        .partitionBy("window_size")
        .option("path", output_path)
        .option("checkpointLocation", f"{checkpoint_path}/user_behavior")
        .outputMode("append")
        .trigger(processingTime=f"{trigger_seconds} seconds")
        .start()
    )


def aggregate_host_popularity_daily(
    df: "DataFrame", *, output_path: str
) -> "DataFrame":
    from pyspark.sql import functions as F

    agg = (
        df.groupBy(
            F.date_format(F.col("event_time"), "yyyy-MM-dd").alias("event_date"),
            F.col("computer_id"),
        )
        .agg(
            F.count("*").alias("access_count"),
            F.countDistinct("user_id").alias("unique_users"),
        )
        .withColumn("is_rare", F.col("access_count") < 5)
    )
    return agg


def add_processing_metadata(df: "DataFrame") -> "DataFrame":
    from pyspark.sql import functions as F

    return df.withColumn("processing_time", F.current_timestamp()).withColumn(
        "event_date", F.date_format(F.col("event_time"), "yyyy-MM-dd")
    )


__all__ = [
    "add_processing_metadata",
    "aggregate_host_popularity_daily",
    "aggregate_user_behavior_hourly",
    "compute_rolling_windows",
    "compute_stateful_aggregates",
]
