from __future__ import annotations

import os
import time
from pathlib import Path

import boto3

import pytest

from ingest.replay_lanl import replay_lanl


def _read_one_record(
    *,
    client: object,
    stream_name: str,
    timeout_sec: int = 15,
) -> bytes | None:
    kinesis = client  # boto3 client
    stream = kinesis.describe_stream(StreamName=stream_name)["StreamDescription"]
    shard_id = stream["Shards"][0]["ShardId"]

    it = kinesis.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="TRIM_HORIZON",
    )["ShardIterator"]

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        out = kinesis.get_records(ShardIterator=it, Limit=10)
        it = out["NextShardIterator"]
        recs = out.get("Records") or []
        if recs:
            return recs[0]["Data"]
        time.sleep(1)
    return None


def test_kinesis_roundtrip_replay_producer_v1(tmp_path: Path) -> None:
    if os.getenv("AUTHPULSE_INTEGRATION") != "1":
        pytest.skip("Set AUTHPULSE_INTEGRATION=1 to run integration tests")

    # Use an explicit profile if provided, otherwise fall back to the default chain.
    profile = os.getenv("AWS_PROFILE")
    region = os.getenv("AWS_REGION") or "us-east-1"

    # Keep the config self-contained for the test run.
    stream_name = os.getenv("AUTHPULSE_KINESIS_STREAM") or "authpulse-dev-stream"
    sample_path = tmp_path / "auth_sample.csv"
    sample_path.write_text("time,user,computer\n1,U1,C1\n2,U2,C2\n", encoding="utf-8")

    cfg_path = tmp_path / "config.yaml"
    aws_lines = [
        "aws:",
        f"  region: {region}",
    ]
    if profile:
        aws_lines.append(f"  profile: {profile}")

    cfg_path.write_text(
        "\n".join(
            [
                *aws_lines,
                "",
                "kinesis:",
                f"  stream_name: {stream_name}",
                "  partition_key_field: user_id",
                "",
                "replay:",
                f"  input_path: {sample_path.as_posix()}",
                "  batch_size: 500",
                "  sleep_interval_ms: 0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Run the replay into the real dev stream.
    replay_lanl(str(cfg_path))

    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    client = session.client("kinesis", region_name=region)
    data = _read_one_record(client=client, stream_name=stream_name)
    assert data is not None

    payload = data.decode("utf-8")
    assert "event_time" in payload
    assert "user_id" in payload
    assert "computer_id" in payload
    assert "event_id" in payload
