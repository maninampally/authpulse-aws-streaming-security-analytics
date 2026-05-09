"""
AuthPulse - PySpark Structured Streaming Job
Main streaming application for real-time authentication risk analytics on EMR.
"""

from __future__ import annotations

import argparse
import os
import sys

_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)


def _build_spark_session(*, app_name: str, shuffle_partitions: int):
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.streaming.schemaInference", "false")
        .getOrCreate()
    )


def run(cfg) -> None:
    from pyspark.sql import functions as F

    from stream.risk_engine import apply_risk_engine
    from stream.schemas import RAW_AUTH_EVENT_SCHEMA
    from stream.window_metrics import (
        add_processing_metadata,
        compute_rolling_windows,
        compute_stateful_aggregates,
    )

    spark = _build_spark_session(
        app_name=cfg.spark.app_name,
        shuffle_partitions=cfg.spark.shuffle_partitions,
    )

    raw_stream = (
        spark.readStream.format("kinesis")
        .option("streamName", cfg.kinesis.stream_name)
        .option("endpointUrl", f"https://kinesis.{cfg.kinesis.region}.amazonaws.com")
        .option("startingPosition", cfg.kinesis.starting_position)
        .option("awsRegion", cfg.kinesis.region)
        .load()
    )

    parsed = (
        raw_stream.selectExpr("CAST(data AS STRING) AS json_str")
        .select(F.from_json(F.col("json_str"), RAW_AUTH_EVENT_SCHEMA).alias("e"))
        .select("e.*")
        .filter(
            F.col("user_id").isNotNull()
            & (F.col("user_id") != "")
            & F.col("computer_id").isNotNull()
            & F.col("event_time").isNotNull()
        )
        .withWatermark("event_time", "5 minutes")
    )

    deduped = parsed.dropDuplicates(["event_id"])

    enriched = compute_stateful_aggregates(deduped)
    enriched = add_processing_metadata(enriched)

    features = compute_rolling_windows(
        enriched,
        window_1h_duration=cfg.streaming.window_1h_duration,
        window_1h_slide=cfg.streaming.window_1h_slide,
        window_24h_duration=cfg.streaming.window_24h_duration,
        window_24h_slide=cfg.streaming.window_24h_slide,
    )

    events_with_features = (
        enriched.alias("e")
        .join(
            features.filter(F.col("window_size") == "1h").alias("f1"),
            on=(F.col("e.user_id") == F.col("f1.user_id")),
            how="left",
        )
        .select(
            F.col("e.*"),
            F.coalesce(F.col("f1.event_count"), F.lit(0)).alias("window_1h_event_count"),
            F.coalesce(F.col("f1.unique_hosts"), F.lit(0)).alias("window_1h_unique_hosts"),
            F.coalesce(F.col("f1.has_new_device"), F.lit(False)).alias("has_new_device"),
        )
    )

    curated = apply_risk_engine(
        events_with_features.withColumnRenamed("computer_id", "dst_host")
        .withColumn("src_host", F.lit(None).cast("string"))
        .withColumn("window_24h_unique_hosts", F.lit(0)),
        cfg=cfg.risk.as_dict(),
    )

    (
        enriched.select("event_time", "user_id", "computer_id", "event_id", "event_date")
        .writeStream.format("parquet")
        .partitionBy("event_date")
        .option("path", cfg.s3.raw_path)
        .option("checkpointLocation", f"{cfg.streaming.checkpoint_location}/raw")
        .outputMode("append")
        .trigger(processingTime=f"{cfg.streaming.trigger_seconds} seconds")
        .start()
    )

    (
        features.writeStream.format("parquet")
        .partitionBy("window_size")
        .option("path", cfg.s3.features_path)
        .option("checkpointLocation", f"{cfg.streaming.checkpoint_location}/features")
        .outputMode("append")
        .trigger(processingTime=f"{cfg.streaming.trigger_seconds} seconds")
        .start()
    )

    (
        curated.writeStream.format("parquet")
        .partitionBy("event_date")
        .option("path", cfg.s3.curated_path)
        .option("checkpointLocation", f"{cfg.streaming.checkpoint_location}/curated")
        .outputMode("append")
        .trigger(processingTime=f"{cfg.streaming.trigger_seconds} seconds")
        .start()
    )

    spark.streams.awaitAnyTermination()


def main() -> None:
    from stream.config import AppConfig

    ap = argparse.ArgumentParser(description="AuthPulse PySpark Structured Streaming job")
    ap.add_argument("--kinesis-stream", default=None)
    ap.add_argument("--s3-bucket", default=None)
    ap.add_argument("--region", default=None)
    ap.add_argument("--trigger-seconds", type=int, default=30)
    ap.add_argument(
        "--trigger-once",
        action="store_true",
        help="Process one micro-batch then exit (useful for smoke-tests / backfill).",
    )
    args = ap.parse_args()

    cfg = AppConfig()
    if args.kinesis_stream:
        cfg.kinesis.stream_name = args.kinesis_stream
    if args.region:
        cfg.kinesis.region = args.region
    if args.s3_bucket:
        cfg.s3.bucket = args.s3_bucket
    cfg.streaming.trigger_seconds = args.trigger_seconds

    run(cfg)


if __name__ == "__main__":
    main()
