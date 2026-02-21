# Day 7 — Risk Rules Engine (Flink)

Day 7 adds a **simple, explainable rules engine** that tags events with `risk_flags` and a combined `risk_score`.

Inputs:
- Kinesis AuthEvent stream (same as Day 5/6)
- Day 6 window features (computed in the same job)

Outputs:
- Raw events to S3 (unchanged)
- User behavior window features to S3 (unchanged)
- Curated, risk-enriched events to S3 (new): `auth_events_curated/`

## Rules (deterministic)

Rules live in `src/stream/risk_rules.py` and are deliberately "boring": fixed thresholds and fixed weights.

- `lateral_movement` — user touches many unique hosts in 1h
- `burst_login` — user generates many logins in 1h
- `rare_host` — approximated as `has_new_device` (host never seen before for that user)
- `new_device_spike` — new device plus high 24h unique hosts

The output is:
- `risk_flags`: list of rule IDs that fired
- `risk_score`: sum of fired rule weights

## Configure

The Flink job adds a new sink path:
- `AUTHPULSE_S3_CURATED_EVENTS_PATH` (or `--s3-curated-events-path`) — e.g. `s3a://<curated-bucket>/auth_events_curated/`

Rule thresholds/weights are in `DEFAULT_RULE_CONFIG` at the top of `src/stream/risk_rules.py`.

## Verify in S3

List partitions:

```bash
aws s3 ls s3://<curated-bucket>/auth_events_curated/ | head
```

Inspect a few events:

```bash
aws s3 ls s3://<curated-bucket>/auth_events_curated/ --recursive | head
aws s3 cp s3://<curated-bucket>/auth_events_curated/user_id=<some-user>/<file>.json - | head
```

What to look for:
- A user with many hosts quickly should show `risk_flags` including `lateral_movement`.
- A user with very high activity volume should show `burst_login`.

## Note on window timing

The Day 6 window features are event-time window aggregations. Depending on runtime/watermarks,
windowed feature values can appear once windows have enough data/watermarks to close.
For a low-latency, per-event risk score, you’d typically compute rolling stats with keyed state
or OVER windows (future enhancement).