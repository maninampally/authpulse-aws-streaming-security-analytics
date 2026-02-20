from __future__ import annotations

import json
from pathlib import Path

import boto3
from moto import mock_aws

from producer.replay_lanl import replay_to_kinesis


@mock_aws
def test_replay_to_kinesis_writes_records_from_sample(tmp_path: Path) -> None:
    region = "us-east-1"
    stream_name = "test-stream"

    client = boto3.client("kinesis", region_name=region)
    client.create_stream(StreamName=stream_name, ShardCount=1)

    sample = Path("data") / "sample" / "auth_sample.csv"
    ckpt = tmp_path / "ckpt.json"

    metrics = replay_to_kinesis(
        input_path=sample,
        stream_name=stream_name,
        region=region,
        rate_events_per_sec=1000000,
        batch_size=50,
        checkpoint_path=ckpt,
        resume=False,
    )

    assert metrics["failed"] == 0
    assert metrics["sent"] == 8

    stream = client.describe_stream(StreamName=stream_name)["StreamDescription"]
    shard_id = stream["Shards"][0]["ShardId"]

    it = client.get_shard_iterator(
        StreamName=stream_name,
        ShardId=shard_id,
        ShardIteratorType="TRIM_HORIZON",
    )["ShardIterator"]

    records: list[dict] = []
    while it:
        out = client.get_records(ShardIterator=it, Limit=100)
        it = out.get("NextShardIterator")
        if not out.get("Records"):
            break
        records.extend(out["Records"])

    assert len(records) == 8
    payload = json.loads(records[0]["Data"].decode("utf-8"))
    assert set(payload.keys()) == {"event_time", "user_id", "computer_id", "event_id"}