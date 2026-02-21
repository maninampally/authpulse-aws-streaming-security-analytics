from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence


WindowSize = Literal["1h", "24h"]


@dataclass(frozen=True)
class UserBehaviorFeature:
    window_start: object
    window_end: object
    user_id: str
    window_size: WindowSize
    unique_hosts: int
    event_count: int
    has_new_device: bool


def create_new_device_enriched_view(
    t_env: object,
    *,
    source_table: str,
    view_name: str = "auth_events_enriched",
    watermark_lag_seconds: int = 5,
) -> str:
    """Create a temporary view with an `is_new_device` flag using keyed state.

    This converts the input table -> DataStream, applies a KeyedProcessFunction keyed by
    `user_id` with MapState to remember historically seen `computer_id`s, then converts
    back to a table with an event-time watermark.

    Notes:
    - PyFlink imports are intentionally inside the function so unit tests don't require
      the Flink runtime.
    - State grows with unique hosts per user; if you need bounded state, add TTL.
    """

    try:
        from pyflink.common import Row  # type: ignore
        from pyflink.common.typeinfo import Types  # type: ignore
        from pyflink.datastream.functions import KeyedProcessFunction  # type: ignore
        from pyflink.datastream.state import MapStateDescriptor  # type: ignore
        from pyflink.table import DataTypes, Schema  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "pyflink is required to build stateful feature views; "
            "on AWS Managed Service for Apache Flink, the runtime provides it."
        ) from exc

    class _NewDeviceFlagger(KeyedProcessFunction):
        def open(self, runtime_context):  # type: ignore[no-untyped-def]
            descriptor = MapStateDescriptor(
                "seen_hosts",
                Types.STRING(),
                Types.BOOLEAN(),
            )
            self._seen_hosts = runtime_context.get_map_state(descriptor)

        def process_element(self, value, ctx):  # type: ignore[no-untyped-def]
            # `value` is a Row coming from Table -> DataStream conversion.
            user_id = getattr(value, "user_id", None) or value[1]
            computer_id = getattr(value, "computer_id", None) or value[2]

            is_new_device = True
            try:
                if self._seen_hosts.contains(computer_id):
                    is_new_device = False
                else:
                    self._seen_hosts.put(computer_id, True)
            except AttributeError:
                # Older PyFlink versions may not expose `contains`.
                existing = self._seen_hosts.get(computer_id)
                if existing is not None:
                    is_new_device = False
                else:
                    self._seen_hosts.put(computer_id, True)

            yield Row(
                event_time=getattr(value, "event_time", None) or value[0],
                user_id=user_id,
                computer_id=computer_id,
                event_id=getattr(value, "event_id", None) or value[3],
                is_new_device=is_new_device,
            )

    src_table = t_env.from_path(source_table)
    ds = t_env.to_data_stream(src_table)

    # Key by `user_id` so each user has independent state.
    enriched_ds = ds.key_by(lambda row: getattr(row, "user_id", None) or row[1]).process(
        _NewDeviceFlagger(),
        output_type=Types.ROW_NAMED(
            ["event_time", "user_id", "computer_id", "event_id", "is_new_device"],
            [
                Types.SQL_TIMESTAMP(),
                Types.STRING(),
                Types.STRING(),
                Types.STRING(),
                Types.BOOLEAN(),
            ],
        ),
    )

    watermark_expr = f"event_time - INTERVAL '{int(watermark_lag_seconds)}' SECOND"
    enriched_table = t_env.from_data_stream(
        enriched_ds,
        schema=(
            Schema.new_builder()
            .column("event_time", DataTypes.TIMESTAMP_LTZ(3))
            .column("user_id", DataTypes.STRING())
            .column("computer_id", DataTypes.STRING())
            .column("event_id", DataTypes.STRING())
            .column("is_new_device", DataTypes.BOOLEAN())
            .watermark("event_time", watermark_expr)
            .build()
        ),
    )

    t_env.create_temporary_view(view_name, enriched_table)
    return view_name


def create_user_behavior_features_view(
    t_env: object,
    *,
    enriched_table_or_view: str,
    view_name: str = "user_behavior_features",
    use_hop_windows: bool = True,
    hop_1h_slide_minutes: int = 5,
    hop_24h_slide_hours: int = 1,
) -> str:
    """Create a temporary view that outputs per-user windowed features.

    Produces both 1h and 24h windows and UNION ALLs them into a single view.

    - If `use_hop_windows=True`, uses HOP windows (rolling) with fixed slides.
    - If `False`, uses TUMBLE windows (non-overlapping).
    """

    windowed_1h = _build_window_agg_sql(
        source=enriched_table_or_view,
        window_size="1h",
        use_hop_windows=use_hop_windows,
        hop_slide=f"INTERVAL '{int(hop_1h_slide_minutes)}' MINUTES",
        window_interval="INTERVAL '1' HOUR",
    )
    windowed_24h = _build_window_agg_sql(
        source=enriched_table_or_view,
        window_size="24h",
        use_hop_windows=use_hop_windows,
        hop_slide=f"INTERVAL '{int(hop_24h_slide_hours)}' HOUR",
        window_interval="INTERVAL '24' HOUR",
    )

    sql = "\n".join(
        [
            f"CREATE TEMPORARY VIEW {view_name} AS",
            windowed_1h,
            "UNION ALL",
            windowed_24h,
        ]
    )

    t_env.execute_sql(sql)
    return view_name


def _build_window_agg_sql(
    *,
    source: str,
    window_size: WindowSize,
    use_hop_windows: bool,
    hop_slide: str,
    window_interval: str,
) -> str:
    if use_hop_windows:
        tvf = f"HOP(TABLE {source}, DESCRIPTOR(event_time), {hop_slide}, {window_interval})"
    else:
        tvf = f"TUMBLE(TABLE {source}, DESCRIPTOR(event_time), {window_interval})"

    return "\n".join(
        [
            "SELECT",
            "  window_start,",
            "  window_end,",
            "  user_id,",
            f"  '{window_size}' AS window_size,",
            "  COUNT(DISTINCT computer_id) AS unique_hosts,",
            "  COUNT(*) AS event_count,",
            "  MAX(CAST(is_new_device AS BOOLEAN)) AS has_new_device",
            f"FROM TABLE({tvf})",
            "GROUP BY window_start, window_end, user_id",
        ]
    )


def ensure_user_behavior_feature_views(
    t_env: object,
    *,
    auth_events_table: str,
    enriched_view: str = "auth_events_enriched",
    features_view: str = "user_behavior_features",
) -> str:
    """One-call helper used by the Flink job.

    Expects `auth_events_table` to have at least:
    - event_time (TIMESTAMP_LTZ(3)) with watermark
    - user_id (STRING)
    - computer_id (STRING)
    - event_id (STRING)
    """

    enriched_name = create_new_device_enriched_view(
        t_env, source_table=auth_events_table, view_name=enriched_view
    )
    return create_user_behavior_features_view(
        t_env, enriched_table_or_view=enriched_name, view_name=features_view
    )


def build_insert_user_features_sql(
    *,
    features_view: str,
    sink_table: str,
    columns: Sequence[str] | None = None,
) -> str:
    """Build INSERT SQL from the feature view into the sink table."""

    if columns is None:
        columns = [
            "window_start",
            "window_end",
            "user_id",
            "window_size",
            "unique_hosts",
            "event_count",
            "has_new_device",
        ]

    select_list = ",\n  ".join(columns)
    return "\n".join(
        [
            f"INSERT INTO {sink_table}",
            "SELECT",
            f"  {select_list}",
            f"FROM {features_view}",
        ]
    )
