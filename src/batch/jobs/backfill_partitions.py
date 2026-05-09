from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from batch.jobs.user_behavior_hourly_job import load_athena_settings, run_athena_query


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _default_range() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=7), today


def _build_sql(*, start_date: date, end_date: date) -> tuple[str, str]:
    start_d = start_date.isoformat()
    end_d = end_date.isoformat()

    delete_sql = "\n".join(
        [
            "DELETE FROM lakehouse.auth_events_curated",
            f"WHERE event_date >= '{start_d}'",
            f"  AND event_date < '{end_d}';",
        ]
    )

    insert_sql = "\n".join(
        [
            "INSERT INTO lakehouse.auth_events_curated",
            "SELECT",
            "  CAST(event_time AS timestamp) AS event_time,",
            "  user_id,",
            "  CAST(NULL AS varchar) AS src_host,",
            "  computer_id AS dst_host,",
            "  CAST(TRUE AS boolean) AS success,",
            "  CAST(0 AS bigint) AS window_1h_event_count,",
            "  CAST(0 AS bigint) AS window_1h_unique_hosts,",
            "  CAST(0 AS bigint) AS window_24h_unique_hosts,",
            "  CAST(FALSE AS boolean) AS has_new_device,",
            "  CAST(0 AS int) AS risk_score,",
            "  CAST(ARRAY[] AS ARRAY(VARCHAR)) AS risk_flags,",
            "  event_date",
            "FROM lakehouse.auth_events_raw",
            f"WHERE event_date >= '{start_d}'",
            f"  AND event_date < '{end_d}';",
        ]
    )
    return delete_sql, insert_sql


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Backfill lakehouse.auth_events_curated"
    )
    parser.add_argument(
        "--config",
        default=str(Path("config") / "dev.yaml"),
        help="Path to YAML config (defaults to config/dev.yaml)",
    )
    default_start, default_end = _default_range()
    parser.add_argument("--start-date", type=_parse_date, default=default_start)
    parser.add_argument("--end-date", type=_parse_date, default=default_end)

    args = parser.parse_args(argv)

    if args.end_date <= args.start_date:
        raise SystemExit("end-date must be after start-date")

    settings = load_athena_settings(config_path=str(args.config))
    delete_sql, insert_sql = _build_sql(
        start_date=args.start_date, end_date=args.end_date
    )

    print(
        f"[backfill_partitions] Refreshing {args.start_date.isoformat()} → {args.end_date.isoformat()} "
        f"(workgroup={settings.workgroup})"
    )
    run_athena_query(sql=delete_sql, settings=settings)
    run_athena_query(sql=insert_sql, settings=settings)


if __name__ == "__main__":
    main()
