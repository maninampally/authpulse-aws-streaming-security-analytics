from __future__ import annotations

from producer.replay_lanl import make_event_id


def test_make_event_id_is_stable() -> None:
    a = make_event_id("1", "U1", "C1")
    b = make_event_id("1", "U1", "C1")
    assert a == b
    assert len(a) == 32
