from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from features import compute_features, get_state, update_state
from sink import write_batch

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from risk_rules import compute_risk

log = logging.getLogger()
log.setLevel(logging.INFO)


def _decode_kinesis_record(record: dict[str, Any]) -> dict[str, Any] | None:
    try:
        raw_b64 = record["kinesis"]["data"]
        decoded = base64.b64decode(raw_b64).decode("utf-8")
        return json.loads(decoded)
    except Exception as exc:
        log.warning("decode_failed seq=%s err=%s", record.get("kinesis", {}).get("sequenceNumber"), exc)
        return None


def _to_epoch(event_time: str) -> int:
    if isinstance(event_time, (int, float)):
        return int(event_time)
    dt = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    raw_records: list[dict[str, Any]] = []
    curated_records: list[dict[str, Any]] = []
    failed = 0

    for record in event.get("Records", []):
        decoded = _decode_kinesis_record(record)
        if not decoded:
            failed += 1
            continue

        try:
            user_id = str(decoded["user_id"]).strip()
            computer_id = str(decoded.get("computer_id") or decoded.get("dst_host", "")).strip()
            event_id = str(decoded.get("event_id", "")).strip()
            event_time_epoch = _to_epoch(decoded["event_time"])

            state = get_state(user_id)
            features = compute_features(state, event_time_epoch, computer_id)
            risk_score, risk_flags = compute_risk(
                user_id=user_id,
                dst_host=computer_id,
                window_1h_event_count=features["window_1h_event_count"],
                window_1h_unique_hosts=features["window_1h_unique_hosts"],
                window_24h_unique_hosts=features["window_24h_unique_hosts"],
                has_new_device=features["has_new_device"],
            )
            update_state(user_id, event_time_epoch, computer_id, state)

            event_date = datetime.fromtimestamp(event_time_epoch, tz=timezone.utc).strftime("%Y-%m-%d")

            raw_records.append({
                "event_time_epoch": event_time_epoch,
                "event_time": datetime.fromtimestamp(event_time_epoch, tz=timezone.utc).isoformat(),
                "user_id": user_id,
                "computer_id": computer_id,
                "event_id": event_id,
                "event_date": event_date,
            })

            curated_records.append({
                "event_time_epoch": event_time_epoch,
                "event_time": datetime.fromtimestamp(event_time_epoch, tz=timezone.utc).isoformat(),
                "user_id": user_id,
                "src_host": None,
                "dst_host": computer_id,
                "success": True,
                "window_1h_event_count": features["window_1h_event_count"],
                "window_1h_unique_hosts": features["window_1h_unique_hosts"],
                "window_24h_unique_hosts": features["window_24h_unique_hosts"],
                "has_new_device": features["has_new_device"],
                "risk_score": risk_score,
                "risk_flags": risk_flags,
                "event_date": event_date,
            })
        except Exception as exc:
            log.exception("process_failed err=%s", exc)
            failed += 1

    if raw_records:
        write_batch(raw_records, curated_records)

    log.info("batch processed=%d failed=%d", len(raw_records), failed)
    return {"processed": len(raw_records), "failed": failed}
