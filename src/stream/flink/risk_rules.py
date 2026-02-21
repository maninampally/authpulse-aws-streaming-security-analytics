from __future__ import annotations

"""Flink-facing risk rules compatibility wrapper.

Day 7's rules engine lives in `stream.risk_rules` and is intentionally pure-Python.
This module remains to avoid breaking existing imports.
"""

from dataclasses import dataclass

from stream.risk_rules import (  # noqa: F401
    DEFAULT_RULE_CONFIG,
    RiskContext,
    RuleResult,
    compute_risk,
    compute_risk_flags,
)


@dataclass(frozen=True)
class RiskResult:
    risk_score: int
    flags: list[str]


def evaluate_risk(*, is_new_device: bool = False, is_login_burst: bool = False) -> RiskResult:
    """Legacy helper kept for unit tests from early project days."""

    score = 0
    flags: list[str] = []

    if is_new_device:
        score += 30
        flags.append("new_device")
    if is_login_burst:
        score += 20
        flags.append("login_burst")

    return RiskResult(risk_score=score, flags=flags)


__all__ = [
    "DEFAULT_RULE_CONFIG",
    "RiskContext",
    "RuleResult",
    "RiskResult",
    "compute_risk",
    "compute_risk_flags",
    "evaluate_risk",
]
