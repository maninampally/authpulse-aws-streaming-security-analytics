from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AthenaSettings:
    workgroup: str
    output_s3: str
    region: str
    profile: str | None


def _load_yaml(path: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("PyYAML is required for batch job configuration") from exc

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML config: expected mapping at root: {path}")
    return data


def _get_nested(dct: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = dct
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def load_athena_settings(*, config_path: str) -> AthenaSettings:
    cfg = _load_yaml(config_path)

    region = str(_get_nested(cfg, ["aws", "region"], "us-east-1"))
    profile_val = _get_nested(cfg, ["aws", "profile"], None)
    profile = None if profile_val in (None, "") else str(profile_val)

    workgroup = str(_get_nested(cfg, ["athena", "workgroup"], "primary"))
    output_s3 = str(_get_nested(cfg, ["athena", "output_s3"], "")).strip()
    if not output_s3:
        raise ValueError(
            "Missing athena.output_s3 in config. "
            "Set it to something like s3://authpulse-dev-raw/athena-results/"
        )

    return AthenaSettings(workgroup=workgroup, output_s3=output_s3, region=region, profile=profile)


def _boto3_athena_client(settings: AthenaSettings):
    import boto3  # type: ignore

    session = boto3.Session(profile_name=settings.profile, region_name=settings.region)
    return session.client("athena")


def run_athena_query(*, sql: str, settings: AthenaSettings, poll_seconds: float = 2.0) -> str:
    athena = _boto3_athena_client(settings)

    start = athena.start_query_execution(
        QueryString=sql,
        WorkGroup=settings.workgroup,
        ResultConfiguration={"OutputLocation": settings.output_s3},
    )
    qid = start["QueryExecutionId"]

    while True:
        res = athena.get_query_execution(QueryExecutionId=qid)
        status = res["QueryExecution"]["Status"]["State"]
        if status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            if status != "SUCCEEDED":
                reason = res["QueryExecution"]["Status"].get("StateChangeReason", "")
                raise RuntimeError(f"Athena query {qid} {status}: {reason}")
            return qid
        time.sleep(poll_seconds)


def _date_range_defaults() -> tuple[date, date]:
    today = date.today()
    return today - timedelta(days=1), today


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_sql(*, start_date: date, end_date: date) -> tuple[str, str]:
    start_d = f"DATE '{start_date.isoformat()}'"
    end_d = f"DATE '{end_date.isoformat()}'"

    delete_sql = "\n".join(
        [
            "DELETE FROM lakehouse.host_popularity_daily",
            f"WHERE event_date >= {start_d}",
            f"  AND event_date < {end_d};",
        ]
    )

    start_ts = f"TIMESTAMP '{start_date.isoformat()} 00:00:00'"
    end_ts = f"TIMESTAMP '{end_date.isoformat()} 00:00:00'"

    insert_sql = "\n".join(
        [
            "INSERT INTO lakehouse.host_popularity_daily",
            "SELECT",
            "  CAST(date(event_time) AS date) AS event_date,",
            "  dst_host AS host_id,",
            "  count(distinct user_id) AS distinct_users,",
            "  count(*) AS total_events",
            "FROM lakehouse.auth_events_curated",
            f"WHERE event_time >= {start_ts}",
            f"  AND event_time < {end_ts}",
            "GROUP BY 1, 2;",
        ]
    )

    return delete_sql, insert_sql


def run(*, config_path: str, start_date: date, end_date: date) -> None:
    settings = load_athena_settings(config_path=config_path)
    delete_sql, insert_sql = build_sql(start_date=start_date, end_date=end_date)

    print(
        f"[host_popularity_daily_job] Refreshing {start_date.isoformat()} → {end_date.isoformat()} "
        f"(workgroup={settings.workgroup})"
    )
    run_athena_query(sql=delete_sql, settings=settings)
    run_athena_query(sql=insert_sql, settings=settings)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Populate lakehouse.host_popularity_daily via Athena")
    parser.add_argument(
        "--config",
        default=str(Path("config") / "dev.yaml"),
        help="Path to YAML config (defaults to config/dev.yaml)",
    )
    default_start, default_end = _date_range_defaults()
    parser.add_argument("--start-date", type=_parse_date, default=default_start)
    parser.add_argument("--end-date", type=_parse_date, default=default_end)

    args = parser.parse_args(argv)

    if args.end_date <= args.start_date:
        raise SystemExit("end-date must be after start-date")

    run(config_path=str(args.config), start_date=args.start_date, end_date=args.end_date)


if __name__ == "__main__":
    main()
