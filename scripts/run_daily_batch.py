from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from batch.jobs.host_popularity_daily_job import run as run_host_popularity_daily
from batch.jobs.user_behavior_hourly_job import run as run_user_behavior_hourly


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _default_range() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=1), today


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run daily AuthPulse batch aggregations (Athena)")
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

    # Order matters if you later base user aggregates on other outputs.
    run_user_behavior_hourly(config_path=str(args.config), start_date=args.start_date, end_date=args.end_date)
    run_host_popularity_daily(config_path=str(args.config), start_date=args.start_date, end_date=args.end_date)


if __name__ == "__main__":
    main()
