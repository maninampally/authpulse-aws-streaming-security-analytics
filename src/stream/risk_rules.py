from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


DEFAULT_RULE_CONFIG: dict[str, Any] = {
    # Thresholds
    "lateral_movement_unique_hosts_1h": 10,
    "burst_login_event_count_1h": 50,
    "new_device_spike_unique_hosts_24h": 25,
    # Weights
    "weight_lateral_movement": 35,
    "weight_burst_login": 25,
    "weight_rare_host": 10,
    "weight_new_device_spike": 30,
}


@dataclass(frozen=True)
class RiskContext:
    """Inputs used by deterministic risk rules.

    This is intentionally simple and JSON-serializable (except event_time).

    Fields map to what Flink produces in the Day 6 feature stream.
    """

    user_id: str
    dst_host: str | None = None
    src_host: str | None = None
    event_time: datetime | None = None

    window_1h_event_count: int = 0
    window_1h_unique_hosts: int = 0
    window_24h_unique_hosts: int = 0

    has_new_device: bool = False


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    triggered: bool
    weight: int


def rule_lateral_movement(ctx: RiskContext, cfg: dict[str, Any]) -> RuleResult:
    """Lateral movement: user authenticates to N+ distinct hosts in 1 hour."""

    threshold = int(cfg["lateral_movement_unique_hosts_1h"])
    triggered = int(ctx.window_1h_unique_hosts) >= threshold
    return RuleResult("lateral_movement", triggered, int(cfg["weight_lateral_movement"]))


def rule_burst_login(ctx: RiskContext, cfg: dict[str, Any]) -> RuleResult:
    """Burst login: user has unusually high auth volume in 1 hour (fixed threshold)."""

    threshold = int(cfg["burst_login_event_count_1h"])
    triggered = int(ctx.window_1h_event_count) >= threshold
    return RuleResult("burst_login", triggered, int(cfg["weight_burst_login"]))


def rule_rare_host(ctx: RiskContext, cfg: dict[str, Any]) -> RuleResult:
    """Rare host: destination host is historically unseen for this user.

    In Day 6 we approximate "rare for user" as "new device" (host never seen before).
    """

    triggered = bool(ctx.has_new_device)
    return RuleResult("rare_host", triggered, int(cfg["weight_rare_host"]))


def rule_new_device_spike(ctx: RiskContext, cfg: dict[str, Any]) -> RuleResult:
    """New device spike: new device + high 24h host diversity.

    Approximates scenarios where a user touches many new hosts in a day.
    """

    threshold = int(cfg["new_device_spike_unique_hosts_24h"])
    triggered = bool(ctx.has_new_device) and int(ctx.window_24h_unique_hosts) >= threshold
    return RuleResult("new_device_spike", triggered, int(cfg["weight_new_device_spike"]))


def compute_risk_flags(
    ctx: RiskContext,
    *,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate all risk rules and return JSON-serializable outputs.

    Returns:
      {"risk_flags": [..], "risk_score": int}
    """

    cfg = DEFAULT_RULE_CONFIG if cfg is None else cfg

    rules = [
        rule_lateral_movement,
        rule_burst_login,
        rule_rare_host,
        rule_new_device_spike,
    ]

    fired: list[str] = []
    score = 0
    for rule_fn in rules:
        result = rule_fn(ctx, cfg)
        if result.triggered:
            fired.append(result.rule_id)
            score += int(result.weight)

    return {"risk_flags": fired, "risk_score": int(score)}


def compute_risk(
    *,
    user_id: str,
    dst_host: str | None,
    src_host: str | None = None,
    event_time: datetime | None = None,
    window_1h_event_count: int | None = None,
    window_1h_unique_hosts: int | None = None,
    window_24h_unique_hosts: int | None = None,
    has_new_device: bool | None = None,
    cfg: dict[str, Any] | None = None,
) -> tuple[int, list[str]]:
    """Convenience wrapper used by Flink UDFs."""

    ctx = RiskContext(
        user_id=user_id,
        dst_host=dst_host,
        src_host=src_host,
        event_time=event_time,
        window_1h_event_count=int(window_1h_event_count or 0),
        window_1h_unique_hosts=int(window_1h_unique_hosts or 0),
        window_24h_unique_hosts=int(window_24h_unique_hosts or 0),
        has_new_device=bool(has_new_device or False),
    )
    out = compute_risk_flags(ctx, cfg=cfg)
    return int(out["risk_score"]), list(out["risk_flags"])  # JSON friendly
