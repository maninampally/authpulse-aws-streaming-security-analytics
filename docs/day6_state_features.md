# Day 6 — Stateful User Behavior Features (Flink)

Day 6 adds a **stateful feature stream** per user on top of the raw AuthEvent stream.

Inputs:
- LANL auth events replayed into Kinesis as AuthEvent JSON (recommended) or LANL CSV.

Outputs:
- Raw events to S3 (same as Day 5)
- Per-user windowed behavior features to S3 (new): `auth_user_features/`

## What’s computed

For each user, Flink keeps **keyed state** (per `user_id`) of historically seen `computer_id` values.

It then emits features over event-time windows:
- `event_count` in the window
- `unique_hosts` (`COUNT(DISTINCT computer_id)`) in the window
- `has_new_device`: whether any event in that window had a computer the user has never used before

Windows:
- `1h` rolling window (HOP window, 5-minute slide)
- `24h` rolling window (HOP window, 1-hour slide)

## How to run (dev)

1) Produce a small sample into Kinesis

- Use the replay producer with a small subset of LANL data (or the sample CSV).
- Ensure it writes AuthEvent JSON to the same stream the Flink app reads.

2) Start the Flink job (AWS Managed Service for Apache Flink / KDA)

- Configure the app to run `src/stream/flink/main_job.py`.
- Set env vars / args:
  - `AUTHPULSE_KINESIS_STREAM`
  - `AUTHPULSE_AWS_REGION`
  - `AUTHPULSE_SOURCE_FORMAT=json` (recommended)
  - `AUTHPULSE_S3_RAW_PATH=s3a://<raw-bucket>/raw/auth_events`
  - `AUTHPULSE_S3_FEATURES_PATH=s3a://<curated-bucket>/auth_user_features/`

3) Validate output in S3

List files:

```bash
aws s3 ls s3://<curated-bucket>/auth_user_features/ --recursive | head
```

You should see partition directories:
- `window_size=1h/`
- `window_size=24h/`

Inspect a few JSON records:

```bash
aws s3 cp s3://<curated-bucket>/auth_user_features/window_size=1h/<somefile>.json - | head
```

Manual spot-check ideas:
- Pick a `user_id` and verify `event_count` matches the number of raw events for that user in the same window.
- Verify `unique_hosts` matches distinct `computer_id` values.
- Verify `has_new_device` becomes `true` the first time a user authenticates to a new computer (and stays `false` for repeat computers).

## Notes / tuning

- If you want non-overlapping windows, switch to tumbling windows in the helper in `src/stream/state_manager.py`.
- The “historical host set” is unbounded per user. For long-running prod, consider adding state TTL or periodic compaction.
