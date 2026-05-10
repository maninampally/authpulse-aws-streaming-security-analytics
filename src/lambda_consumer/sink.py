from __future__ import annotations

import gzip
import io
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3

S3_BUCKET = os.environ["LAKEHOUSE_BUCKET"]
S3_RAW_PREFIX = os.environ.get("S3_RAW_PREFIX", "raw/auth_events/")
S3_CURATED_PREFIX = os.environ.get(
    "S3_CURATED_PREFIX", "curated/auth_events_curated/"
)

_s3 = boto3.client("s3")


def _date_partition(event_time_epoch: int) -> str:
    return datetime.fromtimestamp(event_time_epoch, tz=timezone.utc).strftime(
        "%Y-%m-%d"
    )


def _put_jsonl_gz(key: str, records: list[dict[str, Any]]) -> None:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        for r in records:
            gz.write((json.dumps(r, default=str) + "\n").encode("utf-8"))
    _s3.put_object(Bucket=S3_BUCKET, Key=key, Body=buf.getvalue())


def write_batch(raw: list[dict[str, Any]], curated: list[dict[str, Any]]) -> None:
    if not raw:
        return
    event_date = _date_partition(int(raw[0]["event_time_epoch"]))
    suffix = f"{datetime.now(timezone.utc).strftime('%H%M%S')}-{uuid.uuid4().hex[:8]}.jsonl.gz"

    raw_key = f"{S3_RAW_PREFIX}event_date={event_date}/{suffix}"
    curated_key = f"{S3_CURATED_PREFIX}event_date={event_date}/{suffix}"

    _put_jsonl_gz(raw_key, raw)
    _put_jsonl_gz(curated_key, curated)
