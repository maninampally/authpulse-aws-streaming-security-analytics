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
                "  ,computer_id STRING",
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


def main() -> None:
    parser = argparse.ArgumentParser(description="AuthPulse Flink raw sink job")
    parser.add_argument(
        "--kinesis-stream",
        default=_env("AUTHPULSE_KINESIS_STREAM", "authpulse-dev-auth-stream"),
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
        default=_env("AUTHPULSE_S3_RAW_PATH", "s3a://authpulse-dev-raw/raw/auth_events"),
        help="S3 path for raw sink (e.g., s3a://bucket/prefix)",
    )
    args = parser.parse_args()

    kinesis_stream = str(args.kinesis_stream).strip()
    aws_region = str(args.aws_region).strip()
    source_format: Literal["json", "csv"] = args.source_format
    s3_raw_path = str(args.s3_raw_path).strip()

    if not kinesis_stream:
        raise SystemExit("Missing --kinesis-stream")
    if not aws_region:
        raise SystemExit("Missing --aws-region")
    if not s3_raw_path:
        raise SystemExit("Missing --s3-raw-path")

    try:
        from pyflink.table import EnvironmentSettings, TableEnvironment  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "pyflink is required to run this job. "
            "On AWS Managed Service for Apache Flink, the runtime provides it."
        ) from exc

    env_settings = EnvironmentSettings.in_streaming_mode()
    t_env = TableEnvironment.create(env_settings)

    cfg = t_env.get_config().get_configuration()
    cfg.set_string("pipeline.name", "authpulse-flink-raw-sink")
    cfg.set_string("execution.checkpointing.interval", "60s")
    cfg.set_string("execution.checkpointing.min-pause", "10s")

    source_table = "kinesis_source"
    sink_table = "s3_raw_sink"

    t_env.execute_sql(
        _build_kinesis_source_ddl(
            table_name=source_table,
            stream_name=kinesis_stream,
            region=aws_region,
            fmt=source_format,
        )
    )
    t_env.execute_sql(_build_s3_sink_ddl(table_name=sink_table, s3_path=s3_raw_path))

    if source_format == "json":
        insert_sql = "\n".join(
            [
                f"INSERT INTO {sink_table}",
                "SELECT",
                "  event_time,",
                "  user_id,",
                "  computer_id,",
                "  event_id,",
                "  DATE_FORMAT(event_time, 'yyyy-MM-dd') AS event_date",
                f"FROM {source_table}",
            ]
        )
    else:
        # Convert LANL epoch seconds to TIMESTAMP_LTZ and shape to AuthEvent.
        insert_sql = "\n".join(
            [
                f"INSERT INTO {sink_table}",
                "SELECT",
                "  TO_TIMESTAMP_LTZ(CAST(time_s AS BIGINT) * 1000, 3) AS event_time,",
                "  user AS user_id,",
                "  computer AS computer_id,",
                "  CONCAT(time_s, '-', user, '-', computer) AS event_id,",
                "  DATE_FORMAT(TO_TIMESTAMP_LTZ(CAST(time_s AS BIGINT) * 1000, 3), 'yyyy-MM-dd') AS event_date",
                f"FROM {source_table}",
                "WHERE time_s IS NOT NULL AND time_s <> ''",
            ]
        )

    # Start streaming pipeline
    stmt_set = t_env.create_statement_set()
    stmt_set.add_insert_sql(insert_sql)
    stmt_set.execute().wait()


if __name__ == "__main__":
    main()
