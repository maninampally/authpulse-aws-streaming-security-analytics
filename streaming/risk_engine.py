"""
AuthPulse - Risk Engine (PySpark entry point)
Delegates to the shared, pure-Python rule library in src/stream/risk_rules.py.

This module is the PySpark/EMR adapter: it wraps the deterministic risk rules
as Spark UDFs so they can be applied to a DataFrame of auth events.

Pipeline use:
    from streaming.risk_engine import apply_risk_engine
    enriched_df = apply_risk_engine(features_df)
"""

from __future__ import annotations

from typing import Any


def _get_compute_risk():
    """Lazy import so pyspark is not required at module import time."""
    import sys
    import os

    # Ensure src/ is on the path when running via spark-submit.
    src_root = os.path.join(os.path.dirname(__file__), "..", "src")
    if src_root not in sys.path:
        sys.path.insert(0, os.path.abspath(src_root))

    from stream.risk_rules import compute_risk  # pure Python, no Flink dependency
    return compute_risk


def detect_new_device(has_new_device: bool | None) -> bool:
    """Return True when the event involves a host never seen before for this user."""
    return bool(has_new_device)


def detect_burst_login(
    window_1h_event_count: int | None,
    threshold: int = 50,
) -> bool:
    """Return True when login volume in the last 1h exceeds *threshold*."""
    return int(window_1h_event_count or 0) >= threshold


def detect_lateral_movement(
    window_1h_unique_hosts: int | None,
    threshold: int = 10,
) -> bool:
    """Return True when distinct hosts in the last 1h exceeds *threshold*."""
    return int(window_1h_unique_hosts or 0) >= threshold


def detect_rare_host(has_new_device: bool | None) -> bool:
    """Return True when destination host is historically unseen for this user."""
    return bool(has_new_device)


def compute_risk_score(
    *,
    user_id: str,
    dst_host: str | None,
    src_host: str | None = None,
    window_1h_event_count: int = 0,
    window_1h_unique_hosts: int = 0,
    window_24h_unique_hosts: int = 0,
    has_new_device: bool = False,
    cfg: dict[str, Any] | None = None,
) -> tuple[int, list[str]]:
    """Compute risk score and fired rule IDs. Returns (score, flags)."""
    compute_risk = _get_compute_risk()
    return compute_risk(
        user_id=user_id,
        dst_host=dst_host,
        src_host=src_host,
        window_1h_event_count=window_1h_event_count,
        window_1h_unique_hosts=window_1h_unique_hosts,
        window_24h_unique_hosts=window_24h_unique_hosts,
        has_new_device=has_new_device,
        cfg=cfg,
    )


def apply_risk_engine(df: Any, cfg: dict[str, Any] | None = None) -> Any:
    """Apply risk scoring UDFs to a PySpark DataFrame of enriched auth events.

    Expected input columns (all nullable except user_id):
        user_id, dst_host, src_host, window_1h_event_count,
        window_1h_unique_hosts, window_24h_unique_hosts, has_new_device

    Returns the input DataFrame with two new columns appended:
        risk_score (IntegerType), risk_flags (ArrayType(StringType))
    """
    from pyspark.sql import functions as F
    from pyspark.sql.types import ArrayType, IntegerType, StringType

    compute_risk = _get_compute_risk()
    _cfg = cfg  # captured in closure

    def _score(user_id, dst_host, src_host, c1, u1, u24, new_dev):
        score, _ = compute_risk(
            user_id=str(user_id or ""),
            dst_host=dst_host,
            src_host=src_host,
            window_1h_event_count=int(c1 or 0),
            window_1h_unique_hosts=int(u1 or 0),
            window_24h_unique_hosts=int(u24 or 0),
            has_new_device=bool(new_dev),
            cfg=_cfg,
        )
        return score

    def _flags(user_id, dst_host, src_host, c1, u1, u24, new_dev):
        _, flags = compute_risk(
            user_id=str(user_id or ""),
            dst_host=dst_host,
            src_host=src_host,
            window_1h_event_count=int(c1 or 0),
            window_1h_unique_hosts=int(u1 or 0),
            window_24h_unique_hosts=int(u24 or 0),
            has_new_device=bool(new_dev),
            cfg=_cfg,
        )
        return flags

    score_udf = F.udf(_score, IntegerType())
    flags_udf = F.udf(_flags, ArrayType(StringType()))

    _cols = (
        F.col("user_id"),
        F.col("dst_host"),
        F.col("src_host"),
        F.col("window_1h_event_count"),
        F.col("window_1h_unique_hosts"),
        F.col("window_24h_unique_hosts"),
        F.col("has_new_device"),
    )

    return df.withColumn("risk_score", score_udf(*_cols)).withColumn(
        "risk_flags", flags_udf(*_cols)
    )


__all__ = [
    "detect_new_device",
    "detect_burst_login",
    "detect_lateral_movement",
    "detect_rare_host",
    "compute_risk_score",
    "apply_risk_engine",
]
