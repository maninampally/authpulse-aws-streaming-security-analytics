# Data Quality (Day 10)

This project includes a lightweight, dependency-minimal Data Quality (DQ) layer.

- Expectations are defined in YAML (no Great Expectations dependency).
- Checks are executed using Athena SQL via `boto3`.
- Reports are written to `src/quality/dq_reports/` as JSON + Markdown.

## Expectations YAML format

Each suite YAML has:

- `table`: fully-qualified Athena table name (e.g. `lakehouse.auth_events_curated`)
- `failure_threshold_pct`: percent threshold (default 0.1 means 0.1%)
- `checks`: list of checks

Supported check types:

- `schema`
  - `expected_columns`: list of `{column_name: type}` entries
  - Uses `SHOW COLUMNS IN <table>` to validate presence and types.

- `not_null`
  - `column`: column to validate
  - Fails rows where `column IS NULL`.

- `range`
  - Numeric range: `min` and/or `max`
  - Allowed values: `allowed_values: [..]` (good for booleans/enums)

## Run

```bash
python -m quality.run_quality_checks --config config/dev.yaml --suite src/quality/expectations/auth_events_expectations.yml
```

Exit codes:
- `0` if all checks pass
- non-zero if any check exceeds `failure_threshold_pct`

## Optional S3 upload

If `dq.s3_reports_prefix` is set in your YAML config, the JSON report is uploaded:

```yaml
dq:
  s3_reports_prefix: s3://authpulse-dev-curated/dq_reports/
```

## Validate

After running, inspect:
- `src/quality/dq_reports/*.json`
- `src/quality/dq_reports/*.md`
