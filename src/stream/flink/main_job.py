from __future__ import annotations

import argparse
import os
from typing import Literal


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _build_kinesis_source_ddl(*, table_name: str, stream_name: str, region: str, fmt: str) -> str:
    common_with = "\n".join(
        [
            "  'connector' = 'kinesis',",
            f"  'stream' = '{stream_name}',",
            f"  'aws.region' = '{region}',",
            "  'scan.stream.initpos' = 'LATEST'",
        ]
    )

    if fmt == "json":
        return "\n".join(
            [
                f"CREATE TABLE {table_name} (",
                "  event_time TIMESTAMP_LTZ(3)",
                "  ,user_id STRING",
                "  ,src_host STRING",
                "  ,computer_id STRING",
                "  ,success BOOLEAN",
                "  ,event_id STRING",
                "  ,WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND",
                ") WITH (",
                common_with + ",",
                "  'format' = 'json',",
                "  'json.ignore-parse-errors' = 'true',",
                "  'json.fail-on-missing-field' = 'false'",
                ")",
            ]
        )

    # CSV input from LANL format: time,user,computer (time is epoch seconds)
    return "\n".join(
        [
            f"CREATE TABLE {table_name} (",
            "  time_s STRING",
            "  ,user STRING",
            "  ,computer STRING",
            "  ,event_time AS TO_TIMESTAMP_LTZ(CAST(time_s AS BIGINT) * 1000, 3)",
            "  ,user_id AS user",
            "  ,src_host AS CAST(NULL AS STRING)",
            "  ,computer_id AS computer",
            "  ,success AS CAST(TRUE AS BOOLEAN)",
            "  ,event_id AS CONCAT(time_s, '-', user, '-', computer)",
            "  ,WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND",
            ") WITH (",
            common_with + ",",
            "  'format' = 'csv',",
            "  'csv.ignore-parse-errors' = 'true',",
            "  'csv.disable-quote-character' = 'true'",
            ")",
        ]
    )


def _build_s3_sink_ddl(*, table_name: str, s3_path: str) -> str:
    # Filesystem sink writes JSON objects to S3. Partitioning uses Hive-style directories.
    # NOTE: On Managed Service for Apache Flink, checkpointing controls file finalization.
    return "\n".join(
        [
            f"CREATE TABLE {table_name} (",
            "  event_time TIMESTAMP_LTZ(3)",
            "  ,user_id STRING",
            "  ,computer_id STRING",
            "  ,event_id STRING",
            "  ,event_date STRING",
            ") PARTITIONED BY (event_date) WITH (",
            "  'connector' = 'filesystem',",
            f"  'path' = '{s3_path}',",
            "  'format' = 'json',",
            "  'sink.partition-commit.trigger' = 'process-time',",
            "  'sink.partition-commit.delay' = '1 min',",
            "  'sink.partition-commit.policy.kind' = 'success-file'",
            ")",
        ]
    )


def _build_user_features_sink_ddl(*, table_name: str, s3_path: str) -> str:
    return "\n".join(
        [
            f"CREATE TABLE {table_name} (",
            "  window_start TIMESTAMP(3)",
            "  ,window_end TIMESTAMP(3)",
            "  ,user_id STRING",
            "  ,window_size STRING",
            "  ,unique_hosts BIGINT",
            "  ,event_count BIGINT",
            "  ,has_new_device BOOLEAN",
            ") PARTITIONED BY (window_size) WITH (",
            "  'connector' = 'filesystem',",
            f"  'path' = '{s3_path}',",
            "  'format' = 'json',",
            "  'sink.partition-commit.policy.kind' = 'success-file',",
            "  'sink.partition-commit.delay' = '1 min'",
            ")",
        ]
    )


def _build_curated_events_sink_ddl(*, table_name: str, s3_path: str) -> str:
    return "\n".join(
        [
            f"CREATE TABLE {table_name} (",
            "  event_time TIMESTAMP(3)",
            "  ,user_id STRING",
            "  ,src_host STRING",
            "  ,dst_host STRING",
            "  ,success BOOLEAN",
            "  ,window_1h_event_count BIGINT",
            "  ,window_1h_unique_hosts BIGINT",
            "  ,window_24h_unique_hosts BIGINT",
            "  ,has_new_device BOOLEAN",
            "  ,risk_score INT",
            "  ,risk_flags ARRAY<STRING>",
            ") PARTITIONED BY (user_id) WITH (",
            "  'connector' = 'filesystem',",
            f"  'path' = '{s3_path}',",
            "  'format' = 'json',",
            "  'sink.partition-commit.policy.kind' = 'success-file',",
            "  'sink.partition-commit.delay' = '1 min'",
            ")",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="AuthPulse Flink raw sink job")
    parser.add_argument(
        "--kinesis-stream",
        default=_env("AUTHPULSE_KINESIS_STREAM", "authpulse-dev-stream"),
        help="Kinesis Data Stream name",
    )
    parser.add_argument(
        "--aws-region",
        default=_env("AWS_REGION", _env("AUTHPULSE_AWS_REGION", "us-east-1")),
        help="AWS region",
    )
    parser.add_argument(
        "--source-format",
        choices=["json", "csv"],
        default=_env("AUTHPULSE_SOURCE_FORMAT", "json"),
        help="Input record format in Kinesis (json=AuthEvent JSON, csv=LANL time,user,computer)",
    )
    parser.add_argument(
        "--s3-raw-path",
        default=_env("AUTHPULSE_S3_RAW_PATH", "s3a://authpulse-dev-lakehouse-289591071327/raw/auth_events"),
        help="S3 path for raw sink (e.g., s3a://bucket/prefix)",
    )
    parser.add_argument(
        "--s3-features-path",
        default=_env(
            "AUTHPULSE_S3_FEATURES_PATH",
            "s3a://authpulse-dev-lakehouse-289591071327/features/auth_user_features/",
        ),
        help="S3 path for user behavior feature sink (e.g., s3a://bucket/prefix)",
    )
    parser.add_argument(
        "--s3-curated-events-path",
        default=_env(
            "AUTHPULSE_S3_CURATED_EVENTS_PATH",
            "s3a://authpulse-dev-lakehouse-289591071327/curated/auth_events_curated/",
        ),
        help="S3 path for curated risk-enriched events sink (e.g., s3a://bucket/prefix)",
    )
    args = parser.parse_args()

    kinesis_stream = str(args.kinesis_stream).strip()
    aws_region = str(args.aws_region).strip()
    source_format: Literal["json", "csv"] = args.source_format
    s3_raw_path = str(args.s3_raw_path).strip()
    s3_features_path = str(args.s3_features_path).strip()
    s3_curated_events_path = str(args.s3_curated_events_path).strip()

    if not kinesis_stream:
        raise SystemExit("Missing --kinesis-stream")
    if not aws_region:
        raise SystemExit("Missing --aws-region")
    if not s3_raw_path:
        raise SystemExit("Missing --s3-raw-path")
    if not s3_features_path:
        raise SystemExit("Missing --s3-features-path")
    if not s3_curated_events_path:
        raise SystemExit("Missing --s3-curated-events-path")

    try:
        from pyflink.datastream import StreamExecutionEnvironment  # type: ignore
        from pyflink.table import EnvironmentSettings, StreamTableEnvironment  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "pyflink is required to run this job. "
            "On AWS Managed Service for Apache Flink, the runtime provides it."
        ) from exc

    env = StreamExecutionEnvironment.get_execution_environment()
    env_settings = EnvironmentSettings.in_streaming_mode()
    t_env = StreamTableEnvironment.create(env, environment_settings=env_settings)

    cfg = t_env.get_config().get_configuration()
    cfg.set_string("pipeline.name", "authpulse-flink-raw-sink")
    cfg.set_string("execution.checkpointing.interval", "60s")
    cfg.set_string("execution.checkpointing.min-pause", "10s")

    source_table = "kinesis_source"
    auth_events_view = "auth_events_src"
    auth_events_risk_view = "auth_events_risk_src"
    sink_table = "s3_raw_sink"
    features_sink_table = "auth_user_features"
    curated_sink_table = "auth_events_curated"

    t_env.execute_sql(
        _build_kinesis_source_ddl(
            table_name=source_table,
            stream_name=kinesis_stream,
            region=aws_region,
            fmt=source_format,
        )
    )

    # Canonical view used by both raw and feature pipelines.
    t_env.execute_sql(
        "\n".join(
            [
                f"CREATE TEMPORARY VIEW {auth_events_view} AS",
                "SELECT",
                "  event_time,",
                "  user_id,",
                "  computer_id,",
                "  event_id",
                f"FROM {source_table}",
                "WHERE user_id IS NOT NULL AND user_id <> ''",
                "  AND computer_id IS NOT NULL AND computer_id <> ''",
                "  AND event_time IS NOT NULL",
            ]
        )
    )

    t_env.execute_sql(_build_s3_sink_ddl(table_name=sink_table, s3_path=s3_raw_path))
    t_env.execute_sql(
        _build_user_features_sink_ddl(table_name=features_sink_table, s3_path=s3_features_path)
    )
    t_env.execute_sql(
        _build_curated_events_sink_ddl(table_name=curated_sink_table, s3_path=s3_curated_events_path)
    )

    # Raw event sink (schema normalized for json/csv via computed columns in the source DDL).
    raw_insert_sql = "\n".join(
        [
            f"INSERT INTO {sink_table}",
            "SELECT",
            "  event_time,",
            "  user_id,",
            "  computer_id,",
            "  event_id,",
            "  DATE_FORMAT(event_time, 'yyyy-MM-dd') AS event_date",
            f"FROM {auth_events_view}",
        ]
    )

    # Day 6: user behavior features (stateful new-device detection + window aggregates).
    from stream.state_manager import (  # local import: keeps pyflink optional for unit tests
        build_insert_user_features_sql,
        ensure_user_behavior_feature_views,
    )

    features_view = ensure_user_behavior_feature_views(t_env, auth_events_table=auth_events_view)
    features_insert_sql = build_insert_user_features_sql(
        features_view=features_view,
        sink_table=features_sink_table,
    )

    # Day 7: join events + window features and attach risk flags/score.
    # NOTE: The feature stream is produced from event-time windows; depending on watermarking,
    # values may not be available until the relevant windows close.

    t_env.execute_sql(
        "\n".join(
            [
                f"CREATE TEMPORARY VIEW {auth_events_risk_view} AS",
                "SELECT",
                "  CAST(event_time AS TIMESTAMP(3)) AS event_time,",
                "  user_id,",
                "  src_host,",
                "  computer_id AS dst_host,",
                "  COALESCE(success, TRUE) AS success,",
                "  event_id",
                f"FROM {source_table}",
                "WHERE user_id IS NOT NULL AND user_id <> ''",
                "  AND computer_id IS NOT NULL AND computer_id <> ''",
                "  AND event_time IS NOT NULL",
            ]
        )
    )

    t_env.execute_sql(
        "CREATE TEMPORARY VIEW user_features_1h AS "
        f"SELECT * FROM {features_view} WHERE window_size = '1h'"
    )
    t_env.execute_sql(
        "CREATE TEMPORARY VIEW user_features_24h AS "
        f"SELECT * FROM {features_view} WHERE window_size = '24h'"
    )

    t_env.execute_sql(
        "\n".join(
            [
                "CREATE TEMPORARY VIEW event_features_1h AS",
                "SELECT * FROM (",
                "  SELECT",
                "    e.event_time,",
                "    e.user_id,",
                "    e.src_host,",
                "    e.dst_host,",
                "    e.success,",
                "    e.event_id,",
                "    COALESCE(f.event_count, CAST(0 AS BIGINT)) AS window_1h_event_count,",
                "    COALESCE(f.unique_hosts, CAST(0 AS BIGINT)) AS window_1h_unique_hosts,",
                "    COALESCE(f.has_new_device, FALSE) AS has_new_device,",
                "    ROW_NUMBER() OVER (PARTITION BY e.event_id ORDER BY f.window_end ASC) AS rn",
                f"  FROM {auth_events_risk_view} e",
                "  LEFT JOIN user_features_1h f",
                "    ON e.user_id = f.user_id",
                "   AND e.event_time >= f.window_start",
                "   AND e.event_time < f.window_end",
                ") WHERE rn = 1",
            ]
        )
    )

    t_env.execute_sql(
        "\n".join(
            [
                "CREATE TEMPORARY VIEW event_features_24h AS",
                "SELECT * FROM (",
                "  SELECT",
                "    e.event_id,",
                "    COALESCE(f.unique_hosts, CAST(0 AS BIGINT)) AS window_24h_unique_hosts,",
                "    ROW_NUMBER() OVER (PARTITION BY e.event_id ORDER BY f.window_end ASC) AS rn",
                f"  FROM {auth_events_risk_view} e",
                "  LEFT JOIN user_features_24h f",
                "    ON e.user_id = f.user_id",
                "   AND e.event_time >= f.window_start",
                "   AND e.event_time < f.window_end",
                ") WHERE rn = 1",
            ]
        )
    )

    t_env.execute_sql(
        "\n".join(
            [
                "CREATE TEMPORARY VIEW auth_events_with_features AS",
                "SELECT",
                "  e.event_time,",
                "  e.user_id,",
                "  e.src_host,",
                "  e.dst_host,",
                "  e.success,",
                "  e.window_1h_event_count,",
                "  e.window_1h_unique_hosts,",
                "  f.window_24h_unique_hosts,",
                "  e.has_new_device",
                "FROM event_features_1h e",
                "LEFT JOIN event_features_24h f ON e.event_id = f.event_id",
            ]
        )
    )

    # Register Python UDFs for risk scoring.
    from pyflink.table import DataTypes  # type: ignore
    from pyflink.table.udf import udf  # type: ignore

    from stream.risk_rules import compute_risk  # pure python

    def _risk(user_id, dst_host, src_host, event_time, c1, u1, u24, new_dev):  # type: ignore[no-untyped-def]
        return compute_risk(
            user_id=str(user_id or ""),
            dst_host=None if dst_host is None else str(dst_host),
            src_host=None if src_host is None else str(src_host),
            event_time=None,  # not used by current deterministic rules
            window_1h_event_count=0 if c1 is None else int(c1),
            window_1h_unique_hosts=0 if u1 is None else int(u1),
            window_24h_unique_hosts=0 if u24 is None else int(u24),
            has_new_device=False if new_dev is None else bool(new_dev),
        )

    @udf(result_type=DataTypes.INT())
    def risk_score(user_id, dst_host, src_host, event_time, c1, u1, u24, new_dev):  # type: ignore[no-untyped-def]
        score, _ = _risk(user_id, dst_host, src_host, event_time, c1, u1, u24, new_dev)
        return int(score)

    @udf(result_type=DataTypes.ARRAY(DataTypes.STRING()))
    def risk_flags(user_id, dst_host, src_host, event_time, c1, u1, u24, new_dev):  # type: ignore[no-untyped-def]
        _, flags = _risk(user_id, dst_host, src_host, event_time, c1, u1, u24, new_dev)
        return flags

    t_env.create_temporary_function("risk_score", risk_score)
    t_env.create_temporary_function("risk_flags", risk_flags)

    curated_insert_sql = "\n".join(
        [
            f"INSERT INTO {curated_sink_table}",
            "SELECT",
            "  event_time,",
            "  user_id,",
            "  src_host,",
            "  dst_host,",
            "  success,",
            "  window_1h_event_count,",
            "  window_1h_unique_hosts,",
            "  window_24h_unique_hosts,",
            "  has_new_device,",
            "  risk_score(user_id, dst_host, src_host, event_time, window_1h_event_count, window_1h_unique_hosts, window_24h_unique_hosts, has_new_device) AS risk_score,",
            "  risk_flags(user_id, dst_host, src_host, event_time, window_1h_event_count, window_1h_unique_hosts, window_24h_unique_hosts, has_new_device) AS risk_flags",
            "FROM auth_events_with_features",
        ]
    )

    # Start streaming pipeline
    stmt_set = t_env.create_statement_set()
    stmt_set.add_insert_sql(raw_insert_sql)
    stmt_set.add_insert_sql(features_insert_sql)
    stmt_set.add_insert_sql(curated_insert_sql)
    stmt_set.execute().wait()


if __name__ == "__main__":
    main()
