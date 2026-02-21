from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
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
        raise RuntimeError("PyYAML is required for quality checks") from exc

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YAML: expected mapping at root: {path}")
    return data


def _get_nested(dct: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = dct
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _parse_s3_uri(uri: str) -> tuple[str, str]:
    uri = uri.strip()
    if not uri.startswith("s3://"):
        raise ValueError(f"Expected s3://... URI, got: {uri}")
    rest = uri[len("s3://") :]
    bucket, _, key = rest.partition("/")
    return bucket, key


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


def _boto3_session(*, region: str, profile: str | None):
    import boto3  # type: ignore

    return boto3.Session(profile_name=profile, region_name=region)


def run_athena_query(*, sql: str, settings: AthenaSettings, poll_seconds: float = 2.0) -> str:
    """Run an Athena query and block until it finishes. Returns QueryExecutionId."""

    session = _boto3_session(region=settings.region, profile=settings.profile)
    athena = session.client("athena")

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


def fetch_first_value(*, qid: str, settings: AthenaSettings) -> str:
    session = _boto3_session(region=settings.region, profile=settings.profile)
    athena = session.client("athena")
    res = athena.get_query_results(QueryExecutionId=qid, MaxResults=2)

    rows = res.get("ResultSet", {}).get("Rows", [])
    if len(rows) < 2:
        raise RuntimeError(f"No rows returned for query {qid}")
    data = rows[1].get("Data", [])
    if not data:
        raise RuntimeError(f"No columns returned for query {qid}")
    return data[0].get("VarCharValue", "")


def fetch_columns(*, table: str, settings: AthenaSettings) -> list[tuple[str, str]]:
    qid = run_athena_query(sql=f"SHOW COLUMNS IN {table}", settings=settings)

    session = _boto3_session(region=settings.region, profile=settings.profile)
    athena = session.client("athena")
    res = athena.get_query_results(QueryExecutionId=qid, MaxResults=1000)

    out: list[tuple[str, str]] = []
    rows = res.get("ResultSet", {}).get("Rows", [])
    for idx, row in enumerate(rows):
        # Row 0 is header
        if idx == 0:
            continue
        data = row.get("Data", [])
        if len(data) < 2:
            continue
        name = data[0].get("VarCharValue", "")
        dtype = data[1].get("VarCharValue", "")
        if name:
            out.append((name, (dtype or "").lower()))
    return out


def _sql_count(*, table: str, where: str | None, settings: AthenaSettings) -> int:
    sql = f"SELECT count(*) FROM {table}"
    if where:
        sql += f" WHERE {where}"
    qid = run_athena_query(sql=sql, settings=settings)
    value = fetch_first_value(qid=qid, settings=settings)
    return int(value)


def _format_allowed_values(values: list[Any]) -> str:
    parts: list[str] = []
    for v in values:
        if isinstance(v, bool):
            parts.append("TRUE" if v else "FALSE")
        elif isinstance(v, (int, float)):
            parts.append(str(v))
        else:
            parts.append("'" + str(v).replace("'", "''") + "'")
    return ", ".join(parts)


def _normalize_expected_columns(expected: list[Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for item in expected:
        if not isinstance(item, dict) or len(item) != 1:
            raise ValueError("expected_columns must be a list of single-entry mappings")
        (name, dtype), = item.items()
        out.append((str(name), str(dtype).lower()))
    return out


def _write_report_files(*, report_dir: Path, stem: str, payload: dict[str, Any]) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / f"{stem}.json"
    md_path = report_dir / f"{stem}.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")

    lines: list[str] = []
    lines.append(f"# Data Quality Report: {payload['table']}")
    lines.append("")
    lines.append(f"- Run at: {payload.get('run_ts_utc')}")
    lines.append(f"- Total rows: {payload.get('total_rows')}")
    lines.append(f"- Failure threshold (%): {payload.get('failure_threshold_pct')}")
    lines.append(f"- Overall status: {payload.get('overall_status')}")
    lines.append("")
    lines.append("## Checks")
    for chk in payload.get("checks", []):
        lines.append(
            f"- {chk['name']}: {chk['status']} "
            f"(failed_rows={chk.get('failed_rows')}, failure_pct={chk.get('failure_pct')})"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return json_path, md_path


def _maybe_upload_report(*, config: dict[str, Any], settings: AthenaSettings, report_path: Path) -> str | None:
    prefix = _get_nested(config, ["dq", "s3_reports_prefix"], None)
    if not prefix:
        return None
    bucket, key_prefix = _parse_s3_uri(str(prefix))
    key_prefix = key_prefix.rstrip("/")
    key = f"{key_prefix}/{report_path.name}" if key_prefix else report_path.name

    session = _boto3_session(region=settings.region, profile=settings.profile)
    s3 = session.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=report_path.read_bytes(),
        ContentType="application/json",
    )
    return f"s3://{bucket}/{key}"


def run_suite(*, config_path: str, suite_path: str) -> dict[str, Any]:
    config = _load_yaml(config_path)
    settings = load_athena_settings(config_path=config_path)

    suite = _load_yaml(suite_path)
    table = str(suite.get("table", "")).strip()
    if not table:
        raise ValueError("Suite YAML missing required 'table' field")

    checks = suite.get("checks", [])
    if not isinstance(checks, list) or not checks:
        raise ValueError("Suite YAML missing or invalid 'checks' list")

    failure_threshold_pct = float(suite.get("failure_threshold_pct", 0.1))

    total_rows = _sql_count(table=table, where=None, settings=settings)

    results: list[dict[str, Any]] = []
    for chk in checks:
        if not isinstance(chk, dict):
            raise ValueError("Each check must be a mapping")

        name = str(chk.get("name", "")).strip() or "unnamed_check"
        typ = str(chk.get("type", "")).strip()

        failed_rows = 0
        details: dict[str, Any] = {}

        if typ == "not_null":
            col = str(chk.get("column", "")).strip()
            if not col:
                raise ValueError(f"not_null check '{name}' missing column")
            failed_rows = _sql_count(table=table, where=f"{col} IS NULL", settings=settings)
            details = {"column": col}

        elif typ == "range":
            col = str(chk.get("column", "")).strip()
            if not col:
                raise ValueError(f"range check '{name}' missing column")

            if "allowed_values" in chk:
                allowed = chk.get("allowed_values")
                if not isinstance(allowed, list) or not allowed:
                    raise ValueError(f"allowed_values must be a non-empty list for '{name}'")
                allowed_sql = _format_allowed_values(allowed)
                where = f"{col} NOT IN ({allowed_sql})"
                failed_rows = _sql_count(table=table, where=where, settings=settings)
                details = {"column": col, "allowed_values": allowed}
            else:
                min_v = chk.get("min", None)
                max_v = chk.get("max", None)
                if min_v is None and max_v is None:
                    raise ValueError(f"range check '{name}' must define min and/or max")
                predicates: list[str] = []
                if min_v is not None:
                    predicates.append(f"{col} < {min_v}")
                if max_v is not None:
                    predicates.append(f"{col} > {max_v}")
                where = " OR ".join(predicates)
                failed_rows = _sql_count(table=table, where=where, settings=settings)
                details = {"column": col, "min": min_v, "max": max_v}

        elif typ == "schema":
            expected = chk.get("expected_columns", [])
            expected_cols = _normalize_expected_columns(expected)
            actual_cols = fetch_columns(table=table, settings=settings)

            actual_map = {n: t for n, t in actual_cols}
            missing: list[str] = []
            mismatched: list[dict[str, str]] = []
            for col_name, exp_type in expected_cols:
                act_type = actual_map.get(col_name)
                if act_type is None:
                    missing.append(col_name)
                else:
                    # Athena types can vary (e.g. varchar vs string); keep it simple.
                    if act_type != exp_type:
                        mismatched.append(
                            {"column": col_name, "expected": exp_type, "actual": act_type}
                        )

            # Represent schema failures as row failures (1) to fit the reporting format.
            failed_rows = 1 if (missing or mismatched) else 0
            details = {"missing": missing, "mismatched": mismatched}

        else:
            raise ValueError(f"Unknown check type '{typ}' for check '{name}'")

        if total_rows <= 0:
            failure_pct = 0.0 if failed_rows == 0 else 100.0
        else:
            failure_pct = (failed_rows / total_rows) * 100.0

        status = "FAIL" if failure_pct > failure_threshold_pct else "PASS"
        results.append(
            {
                "name": name,
                "type": typ,
                "failed_rows": int(failed_rows),
                "failure_pct": float(round(failure_pct, 6)),
                "status": status,
                **details,
            }
        )

    overall_status = "PASS" if all(r["status"] == "PASS" for r in results) else "FAIL"

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "table": table,
        "run_ts_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_rows": int(total_rows),
        "failure_threshold_pct": float(failure_threshold_pct),
        "checks": results,
        "overall_status": overall_status,
    }

    report_dir = Path(__file__).parent / "dq_reports"
    stem = f"dq_{table.replace('.', '_')}_{now.strftime('%Y%m%d_%H%M%S')}"
    json_path, _ = _write_report_files(report_dir=report_dir, stem=stem, payload=payload)
    uploaded = _maybe_upload_report(config=config, settings=settings, report_path=json_path)
    if uploaded:
        payload["s3_report"] = uploaded

    return payload


def _compute_invalid_record_stats(report: dict[str, Any]) -> tuple[float, int, int]:
    checks = report.get("checks", [])
    if not isinstance(checks, list):
        return 0.0, 0, int(report.get("total_rows", 0) or 0)

    total_rows = int(report.get("total_rows", 0) or 0)

    pcts: list[float] = []
    failed_rows: list[int] = []
    for chk in checks:
        if not isinstance(chk, dict):
            continue
        # Schema checks are not row-level; exclude them from "invalid record %".
        if str(chk.get("type", "")) == "schema":
            continue
        try:
            pcts.append(float(chk.get("failure_pct", 0.0)))
            failed_rows.append(int(chk.get("failed_rows", 0) or 0))
        except Exception:  # noqa: BLE001
            continue
    invalid_percent = float(max(pcts) if pcts else 0.0)
    invalid_rows_est = int(max(failed_rows) if failed_rows else 0)
    return invalid_percent, invalid_rows_est, total_rows


def _emit_dq_invalid_percent_log_line(
    *,
    report: dict[str, Any],
    invalid_record_percent: float,
    invalid_rows_estimate: int,
    total_rows: int,
) -> None:
    # Designed for CloudWatch Logs metric filters.
    print(
        json.dumps(
            {
                "metric": "dq_invalid_record_percent",
                "value": float(round(invalid_record_percent, 6)),
                "count": int(invalid_rows_estimate),
                "total": int(total_rows),
                "table": report.get("table"),
                "run_ts_utc": report.get("run_ts_utc"),
            }
        )
    )


def _maybe_put_cloudwatch_metric(
    *,
    config: dict[str, Any],
    settings: AthenaSettings,
    invalid_record_percent: float,
) -> None:
    emit = bool(_get_nested(config, ["dq", "emit_cloudwatch_metrics"], False))
    if not emit:
        return

    namespace = str(_get_nested(config, ["dq", "cloudwatch_namespace"], "Authpulse/DQ"))
    metric_name = str(
        _get_nested(config, ["dq", "invalid_percent_metric_name"], "InvalidRecordPercent")
    )

    session = _boto3_session(region=settings.region, profile=settings.profile)
    cw = session.client("cloudwatch")
    cw.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                "MetricName": metric_name,
                "Unit": "Percent",
                "Value": float(invalid_record_percent),
            }
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run YAML-driven DQ checks via Athena")
    parser.add_argument(
        "--config",
        default=str(Path("config") / "dev.yaml"),
        help="Path to YAML config (defaults to config/dev.yaml)",
    )
    parser.add_argument(
        "--suite",
        default=str(Path(__file__).parent / "expectations" / "auth_events_expectations.yml"),
        help="Path to expectations suite YAML",
    )
    args = parser.parse_args()

    suite_path = Path(str(args.suite))
    if not suite_path.exists():
        raise FileNotFoundError(str(suite_path))

    report = run_suite(config_path=str(args.config), suite_path=str(suite_path))

    # Emit a single, consistent metric line so infra can attach log metric filters.
    invalid_record_percent, invalid_rows_estimate, total_rows = _compute_invalid_record_stats(report)
    _emit_dq_invalid_percent_log_line(
        report=report,
        invalid_record_percent=invalid_record_percent,
        invalid_rows_estimate=invalid_rows_estimate,
        total_rows=total_rows,
    )

    # Optional: publish custom metric directly (requires cloudwatch:PutMetricData permissions).
    cfg = _load_yaml(str(args.config))
    settings = load_athena_settings(config_path=str(args.config))
    _maybe_put_cloudwatch_metric(
        config=cfg,
        settings=settings,
        invalid_record_percent=invalid_record_percent,
    )

    failures = [c for c in report["checks"] if c["status"] == "FAIL"]
    if failures:
        print(f"DQ FAIL for {report['table']}: {len(failures)} check(s) failed")
        for f in failures:
            print(
                f"- {f['name']} ({f['type']}): failure_pct={f['failure_pct']} failed_rows={f['failed_rows']}"
            )
        raise SystemExit(2)

    print(f"DQ PASS for {report['table']}: {len(report['checks'])} check(s)")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
