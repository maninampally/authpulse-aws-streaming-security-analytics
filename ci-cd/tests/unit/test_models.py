from __future__ import annotations

from datetime import datetime

import pytest

from common.models import AuthEvent, parse_lanl_record


def test_parse_lanl_record_produces_utc_timestamp() -> None:
    event = parse_lanl_record("1", "U1", "C1", "abc")
    assert event.event_time.tzinfo is not None
    assert event.event_time.isoformat().endswith("+00:00")


def test_auth_event_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        AuthEvent(event_time=datetime(2020, 1, 1), user_id="U1", computer_id="C1", event_id="e1")


def test_auth_event_strips_and_rejects_blank_ids() -> None:
    event = parse_lanl_record("1", " U1 ", " C1 ", " e1 ")
    assert event.user_id == "U1"
    assert event.computer_id == "C1"
    assert event.event_id == "e1"

    with pytest.raises(ValueError, match="non-empty"):
        parse_lanl_record("1", " ", "C1", "e1")
