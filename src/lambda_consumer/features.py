from __future__ import annotations

import os
import time
from typing import Any

import boto3

DDB_TABLE = os.environ.get("STATE_TABLE_NAME", "authpulse-dev-user-state")
HOUR = 3600
DAY = 86400
MAX_EVENTS_PER_USER = 1500

_ddb = boto3.resource("dynamodb")
_table = _ddb.Table(DDB_TABLE)


def _now_epoch() -> int:
    return int(time.time())


def get_state(user_id: str) -> dict[str, Any]:
    resp = _table.get_item(Key={"user_id": user_id})
    item = resp.get("Item")
    if not item:
        return {"events": [], "known_hosts": set()}
    return {
        "events": item.get("events", []),
        "known_hosts": set(item.get("known_hosts", [])),
    }


def compute_features(
    state: dict[str, Any], event_time_epoch: int, computer_id: str
) -> dict[str, Any]:
    one_hour_ago = event_time_epoch - HOUR
    day_ago = event_time_epoch - DAY

    events_1h = [e for e in state["events"] if int(e["ts"]) >= one_hour_ago]
    events_24h = [e for e in state["events"] if int(e["ts"]) >= day_ago]

    has_new_device = computer_id not in state["known_hosts"]

    return {
        "window_1h_event_count": len(events_1h),
        "window_1h_unique_hosts": len({e["host"] for e in events_1h}),
        "window_24h_unique_hosts": len({e["host"] for e in events_24h}),
        "has_new_device": has_new_device,
    }


def update_state(
    user_id: str,
    event_time_epoch: int,
    computer_id: str,
    state: dict[str, Any],
) -> None:
    cutoff = event_time_epoch - DAY
    new_events = [e for e in state["events"] if int(e["ts"]) >= cutoff]
    new_events.append({"ts": event_time_epoch, "host": computer_id})
    if len(new_events) > MAX_EVENTS_PER_USER:
        new_events = new_events[-MAX_EVENTS_PER_USER:]

    new_hosts = state["known_hosts"] | {computer_id}

    _table.put_item(
        Item={
            "user_id": user_id,
            "events": new_events,
            "known_hosts": list(new_hosts),
            "ttl": event_time_epoch + (DAY * 7),
        }
    )
