from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import boto3

from common.io_utils import iter_lines
from common.models import parse_lanl_record


def make_event_id(time_s: str, user: str, computer: str) -> str:
    h = hashlib.sha256(f"{time_s}|{user}|{computer}".encode("utf-8")).hexdigest()
    return h[:32]


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay LANL auth events into Kinesis")
    ap.add_argument("--input", required=True, help="Path to LANL auth.txt")
    ap.add_argument("--stream-name", required=True)
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--rate", type=int, default=2000, help="Events per second")
    args = ap.parse_args()

    client = boto3.client("kinesis", region_name=args.region)
    input_path = Path(args.input)

    sent = 0
    start = time.time()

    for line in iter_lines(input_path):
        parts = line.split(",")
        if len(parts) != 3:
            continue
        time_s, user, computer = parts
        event_id = make_event_id(time_s, user, computer)
        event = parse_lanl_record(time_s, user, computer, event_id)

        payload = event.model_dump(mode="json")
        client.put_record(
            StreamName=args.stream_name,
            Data=json.dumps(payload).encode("utf-8"),
            PartitionKey=event.user_id,
        )
        sent += 1

        elapsed = time.time() - start
        expected = sent / max(args.rate, 1)
        if elapsed < expected:
            time.sleep(expected - elapsed)


if __name__ == "__main__":
    main()
