from __future__ import annotations

from stream.risk_rules import RiskContext, compute_risk_flags


def test_compute_risk_flags_and_score() -> None:
    ctx = RiskContext(
        user_id="U1",
        dst_host="C123",
        window_1h_event_count=100,
        window_1h_unique_hosts=12,
        window_24h_unique_hosts=30,
        has_new_device=True,
    )
    out = compute_risk_flags(ctx)
    assert out["risk_score"] > 0
    assert "lateral_movement" in out["risk_flags"]
    assert "burst_login" in out["risk_flags"]
    assert "rare_host" in out["risk_flags"]
    assert "new_device_spike" in out["risk_flags"]
