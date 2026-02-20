from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path
from typing import Any

import boto3
import yaml

from common.logging_utils import get_logger
from common.models import parse_lanl_record


logger = get_logger(__name__)


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config at {p} must be a mapping")
    return data


def put_batch(client: Any, stream_name: str, batch: list[dict[str, Any]]) -> tuple[int, int]:
    if not batch:
        return 0, 0

    resp = client.put_records(StreamName=stream_name, Records=batch)
    failed = int(resp.get("FailedRecordCount") or 0)
    if failed:
        logger.warning("kinesis put_records failed=%s of %s", failed, len(batch))
        error_codes: list[str] = []
        error_messages: list[str] = []
        for r in resp.get("Records", []) or []:
            code = r.get("ErrorCode")
            if code:
                error_codes.append(str(code))
                msg = r.get("ErrorMessage")
                if msg:
                    error_messages.append(str(msg))

        if error_codes:
            common = Counter(error_codes).most_common(3)
            summary = ", ".join([f"{c}={n}" for c, n in common])
            logger.warning("kinesis error_codes %s", summary)
        if error_messages:
            logger.warning("kinesis example_error_message %s", error_messages[0])
    return len(batch) - failed, failed


def replay_lanl(config_path: str) -> None:
    cfg = load_yaml_config(config_path)

    aws_cfg = cfg.get("aws") if isinstance(cfg.get("aws"), dict) else {}
    kinesis_cfg = cfg.get("kinesis") if isinstance(cfg.get("kinesis"), dict) else {}
    replay_cfg = cfg.get("replay") if isinstance(cfg.get("replay"), dict) else {}

    region = str(aws_cfg.get("region") or kinesis_cfg.get("region") or "us-east-1")
    profile = aws_cfg.get("profile")
    profile = str(profile).strip() if profile is not None else ""
    if not profile or profile.lower() == "default":
        profile = None

    stream_name = str(kinesis_cfg.get("stream_name") or "").strip()
    if not stream_name:
        raise ValueError("Missing kinesis.stream_name")

    partition_key_field = str(kinesis_cfg.get("partition_key_field") or "user_id").strip()
    input_path = Path(str(replay_cfg.get("input_path") or "").strip())
    if not input_path:
        raise ValueError("Missing replay.input_path")

    batch_size = int(replay_cfg.get("batch_size") or 500)
    if batch_size <= 0 or batch_size > 500:
        raise ValueError("replay.batch_size must be between 1 and 500")

    sleep_interval_ms = int(replay_cfg.get("sleep_interval_ms") or 0)
    sleep_interval_s = max(sleep_interval_ms, 0) / 1000.0

    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    client = session.client("kinesis", region_name=region)

    total_events = 0
    error_events = 0
    batch: list[dict[str, Any]] = []

    start = time.time()

    with input_path.open("r", encoding="utf-8", errors="replace") as f:
        for lineno, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            try:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) != 3:
                    raise ValueError("expected 3 comma-separated fields")
                time_s, user, computer = parts

                # If the input is a CSV with a header, skip it.
                if time_s.lower() == "time":
                    continue

                event_id = f"{time_s}-{user}-{computer}-{lineno}"
                event = parse_lanl_record(time_s, user, computer, event_id, raw_line=line)

                partition_value = getattr(event, partition_key_field)
                partition_key = str(partition_value)
                if not partition_key:
                    raise ValueError(f"empty partition key from field {partition_key_field!r}")

                batch.append(
                    {
                        "Data": event.model_dump_json().encode("utf-8"),
                        "PartitionKey": partition_key,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                error_events += 1
                logger.warning("failed to parse line %s: %s", lineno, exc)
                continue

            if len(batch) >= batch_size:
                ok, failed = put_batch(client, stream_name, batch)
                total_events += ok
                error_events += failed
                batch = []

                if sleep_interval_s:
                    time.sleep(sleep_interval_s)

    if batch:
        ok, failed = put_batch(client, stream_name, batch)
        total_events += ok
        error_events += failed

    duration_sec = max(time.time() - start, 1e-6)
    events_per_sec = total_events / duration_sec

    logger.info(
        "metrics total_events=%s error_events=%s duration_sec=%.3f events_per_sec=%.2f",
        total_events,
        error_events,
        duration_sec,
        events_per_sec,
    )


def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/dev.yaml")
    args = parser.parse_args()
    replay_lanl(args.config)


if __name__ == "__main__":
    _main()
