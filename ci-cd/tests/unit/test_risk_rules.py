from __future__ import annotations

from stream.flink.risk_rules import evaluate_risk


def test_evaluate_risk_flags_and_score() -> None:
    r = evaluate_risk(is_new_device=True, is_login_burst=True)
    assert r.risk_score == 50
    assert "new_device" in r.flags
    assert "login_burst" in r.flags
