from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskResult:
    risk_score: int
    flags: list[str]


def evaluate_risk(*, is_new_device: bool = False, is_login_burst: bool = False) -> RiskResult:
    score = 0
    flags: list[str] = []

    if is_new_device:
        score += 30
        flags.append("new_device")
    if is_login_burst:
        score += 20
        flags.append("login_burst")

    return RiskResult(risk_score=score, flags=flags)
