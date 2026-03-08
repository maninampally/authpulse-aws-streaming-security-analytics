# AuthPulse — Data Contracts

> Canonical field definitions, types, and nullability rules for all event schemas in the pipeline.
> Any producer or consumer touching these tables must conform to this contract.

---

## 1. Raw Kinesis Payload

**Producer**: `src/producer/replay_lanl.py`  
**Destination**: Kinesis stream `authpulse-dev-stream`  
**Format**: JSON (UTF-8), one record per `put_records` entry

```json
{
  "event_id":       "a3b2c1d4e5f6...",
  "event_time":     "2024-03-15T10:30:45Z",
  "user_id":        "U1234",
  "computer_id":    "C5678",
  "ingestion_time": "2024-03-15T10:30:47Z"
}
```

| Field | Type | Nullable | Notes |
|-------|------|----------|-------|
| `event_id` | string | NO | SHA-256 of `time\|user_id\|computer_id`, truncated to 32 hex chars. Stable across replays. |
| `event_time` | string (ISO 8601 UTC) | NO | Parsed from LANL integer offset; base epoch is 2024-01-01T00:00:00Z |
| `user_id` | string | NO | LANL `user` field; stripped of whitespace; reject if blank |
| `computer_id` | string | NO | LANL `computer` field; stripped of whitespace; reject if blank |
| `ingestion_time` | string (ISO 8601 UTC) | NO | UTC timestamp when producer called `put_records` |

**Validation rules (enforced by `models.AuthEvent`):**
- `event_time` must be timezone-aware (UTC); naive datetimes rejected
- `user_id` and `computer_id` must be non-empty after strip
- `event_id` must be non-empty

---

## 2. `auth_events_raw` (S3 / Iceberg)

**Written by**: Flink job (`src/stream/flink/main_job.py`) — raw sink  
**Path**: `s3://authpulse-dev-lakehouse-<account>/raw/auth_events/`  
**Format**: Parquet (Snappy compression)  
**Partitioning**: `event_date` (daily)

| Column | Iceberg Type | Nullable | Description |
|--------|-------------|----------|-------------|
| `event_id` | `string` | NO | Stable dedup key |
| `event_time` | `timestamptz` | NO | Auth event time (UTC) |
| `user_id` | `string` | NO | User identifier |
| `computer_id` | `string` | NO | Target computer |
| `ingestion_time` | `timestamptz` | NO | Kinesis ingestion time |
| `processing_time` | `timestamptz` | NO | Flink record processing time |
| `event_date` | `date` | NO | Partition column derived from `event_time` |

---

## 3. `auth_events_curated` (S3 / Iceberg)

**Written by**: Flink job — curated sink  
**Path**: `s3://authpulse-dev-lakehouse-<account>/curated/auth_events_curated/`  
**Format**: Apache Iceberg (Parquet/Snappy)  
**Partitioning**: `event_date` (daily)

| Column | Iceberg Type | Nullable | Description |
|--------|-------------|----------|-------------|
| `event_id` | `string` | NO | Unique event identifier |
| `event_time` | `timestamptz` | NO | Authentication timestamp (UTC) |
| `user_id` | `string` | NO | User identifier |
| `computer_id` | `string` | NO | Computer/host identifier |
| `ingestion_time` | `timestamptz` | NO | Kinesis ingestion time |
| `login_count_1h` | `long` | NO | Rolling 1-hour login count for this user |
| `login_count_24h` | `long` | NO | Rolling 24-hour login count for this user |
| `unique_computers_1h` | `long` | NO | Distinct computer count in last 1 hour |
| `unique_computers_24h` | `long` | NO | Distinct computer count in last 24 hours |
| `is_new_device` | `int` | NO | 1 if first-ever auth from this computer; 0 otherwise |
| `is_burst_login` | `int` | NO | 1 if `login_count_1h > 50`; 0 otherwise |
| `is_lateral_movement` | `int` | NO | 1 if `unique_computers_1h >= 10`; 0 otherwise |
| `is_rare_host` | `int` | NO | 1 if computer is in bottom 5% by access frequency; 0 otherwise |
| `risk_flags` | `array<string>` | NO | List of triggered rule names (empty array if none) |
| `risk_score` | `int` | NO | Weighted sum: NEW_DEVICE×30 + BURST_LOGIN×25 + LATERAL_MOVE×35 + RARE_HOST×10 |
| `risk_level` | `string` | NO | `LOW` (0–25) / `MEDIUM` (26–50) / `HIGH` (51–75) / `CRITICAL` (76+) |
| `processing_time` | `timestamptz` | NO | Flink record processing time |
| `event_date` | `date` | NO | Partition column |

**SLA commitment**: `processing_time - event_time` P95 < 5 minutes.

---

## 4. `user_behavior_hourly` (S3 / Iceberg)

**Written by**: Flink window aggregation sink / PySpark `aggregate_user_behavior_hourly()`  
**Path**: `s3://authpulse-dev-lakehouse-<account>/aggregates/user_behavior_hourly/`  
**Partitioning**: `window_start` (hour-truncated)

| Column | Iceberg Type | Nullable | Description |
|--------|-------------|----------|-------------|
| `window_start` | `timestamptz` | NO | Tumbling window start (top of hour, UTC) |
| `window_end` | `timestamptz` | NO | Tumbling window end (next top of hour, UTC) |
| `user_id` | `string` | NO | User identifier |
| `total_logins` | `long` | NO | Count of auth events in window |
| `unique_computers` | `long` | NO | Distinct hosts accessed in window |
| `anomaly_count` | `long` | NO | Events in window with `risk_score > 0` |
| `total_risk_score` | `long` | NO | Sum of `risk_score` across all events in window |
| `max_risk_score` | `int` | NO | Maximum single `risk_score` in window |

---

## 5. `host_popularity_daily` (S3 / Iceberg)

**Written by**: Flink / PySpark `aggregate_host_popularity_daily()`  
**Path**: `s3://authpulse-dev-lakehouse-<account>/aggregates/host_popularity_daily/`  
**Partitioning**: `date` (daily)

| Column | Iceberg Type | Nullable | Description |
|--------|-------------|----------|-------------|
| `date` | `date` | NO | Aggregation date |
| `computer_id` | `string` | NO | Computer/host identifier |
| `unique_users` | `long` | NO | Distinct users who authenticated to this host |
| `total_logins` | `long` | NO | Total authentication count |
| `high_risk_events` | `long` | NO | Count of events with `risk_level IN ('HIGH','CRITICAL')` |

**Use case**: `rare_host` detection percentile ranking — a host is "rare" if its `unique_users` rank is in the bottom 5th percentile for that day.

---

## 6. Schema Change Policy

| Change Type | Action Required |
|-------------|----------------|
| Add optional column (nullable) | Iceberg schema evolution — no DDL change needed; update this doc |
| Rename column | New column + deprecation period; never rename in-place |
| Remove column | 30-day deprecation window; communicate to all consumers |
| Change type (widening e.g. int→long) | Iceberg supports widening; update DDL + this doc |
| Change type (narrowing) | Breaking change — requires migration job + version bump |
| Add partition column | Full table rewrite required; schedule maintenance window |

---

## 7. Glue Catalog Registration

All four tables are registered in the Glue catalog under database **`authpulse`** via Terraform (`modules/glue_iceberg`).

Athena path: `athpulse.<table_name>`

To verify registration:
```bash
aws glue get-tables --database-name authpulse --query "TableList[].Name"
```
