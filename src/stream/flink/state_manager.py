from __future__ import annotations

"""Compatibility wrapper for Flink stateful helpers.

Day 6 implementation lives in `stream.state_manager`.
"""

from stream.state_manager import (  # noqa: F401
    build_insert_user_features_sql,
    create_new_device_enriched_view,
    create_user_behavior_features_view,
    ensure_user_behavior_feature_views,
)

__all__ = [
    "build_insert_user_features_sql",
    "create_new_device_enriched_view",
    "create_user_behavior_features_view",
    "ensure_user_behavior_feature_views",
]
