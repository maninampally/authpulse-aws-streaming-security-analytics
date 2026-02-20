from __future__ import annotations

import argparse
import bz2
import hashlib
import json
import time
from pathlib import Path
from typing import IO, Any, Iterable

import boto3

from common.io_utils import iter_lines
from common.logging_utils import get_logger
from common.models import parse_lanl_record
from producer.config_loader import load_yaml


logger = get_logger(__name__)


def make_event_id(time_s: str, user: str, computer: str) -> str:
    h = hashlib.sha256(f"{time_s}|{user}|{computer}".encode("utf-8")).hexdigest()
    return h[:32]


def _open_text(path: Path) -> IO[str]:
    if path.suffix.lower() == ".bz2":
        return bz2.open(path, mode="rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def iter_lanl_rows(
    input_path: str | Path,
    *,
    start_line: int = 0,
    max_events: int | None = None,
) -> Iterable[tuple[str, str, str]]:
    """Yield (time_s, user, computer) rows.

    Supports:
    - Plain text LANL auth files: `time,user,computer` (no header)
    - CSVs with a header row (e.g., the repo sample)
    - `.bz2` compressed input
    """
    p = Path(input_path)
    yielded = 0

    if p.suffix.lower() == ".csv":
        with _open_text(p) as f:
            for idx, line in enumerate(f):
                if idx < start_line:
                    continue
                line = line.strip()
                if not line:
                    continue
                parts = [x.strip() for x in line.split(",")]
                if len(parts) != 3:
                    continue
                time_s, user, computer = parts
                if time_s.lower() == "time":
                    continue
                if not time_s.isdigit():
                    continue
                yield time_s, user, computer
                yielded += 1
                if max_events is not None and yielded >= max_events:
                    return
        return

    # Default: line-based parsing.
    for idx, line in enumerate(iter_lines(p)):
        if idx < start_line:
            continue
        parts = [x.strip() for x in line.split(",")]
        if len(parts) != 3:
            continue
        time_s, user, computer = parts
        if not time_s.isdigit():
            continue
        yield time_s, user, computer
        yielded += 1
        if max_events is not None and yielded >= max_events:
            return


def _sleep_for_rate(*, sent_events: int, start_time: float, rate_events_per_sec: int) -> None:
    if rate_events_per_sec <= 0:
        return
    elapsed = time.time() - start_time
    expected = sent_events / rate_events_per_sec
    if elapsed < expected:
        time.sleep(expected - elapsed)


def _put_records_with_retry(
    *,
    client: Any,
    stream_name: str,
    records: list[dict[str, Any]],
    max_attempts: int = 5,
) -> tuple[int, int]:
    """Send a single PutRecords batch with retries.

    Returns (successful, failed).
    """
    attempt = 1
    pending = records
    successful = 0

    while pending:
        resp = client.put_records(StreamName=stream_name, Records=pending)
        failed_count = int(resp.get("FailedRecordCount") or 0)
        if failed_count == 0:
            successful += len(pending)
            return successful, 0

        # Keep only failed records for retry.
        next_pending: list[dict[str, Any]] = []
        for record, record_resp in zip(pending, resp.get("Records", []), strict=False):
            if record_resp and record_resp.get("ErrorCode"):
                next_pending.append(record)
            else:
                successful += 1

        pending = next_pending
        if not pending:
            return successful, 0

        if attempt >= max_attempts:
            return successful, len(pending)

        # Exponential backoff with a small cap.
        time.sleep(min(0.25 * (2 ** (attempt - 1)), 5.0))
        attempt += 1

    return successful, 0


def replay_to_kinesis(
    *,
    input_path: str | Path,
    stream_name: str,
    region: str,
    rate_events_per_sec: int,
    aws_profile: str | None = None,
    batch_size: int = 200,
    max_events: int | None = None,
    checkpoint_path: str | Path | None = None,
    resume: bool = False,
    checkpoint_every: int = 5_000,
    dry_run: bool = False,
) -> dict[str, Any]:
    if batch_size <= 0 or batch_size > 500:
        raise ValueError("batch_size must be between 1 and 500")

    checkpoint_file = Path(checkpoint_path) if checkpoint_path else None
    start_line = 0
    if resume and checkpoint_file and checkpoint_file.exists():
        data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        start_line = int(data.get("line", 0))

    session = boto3.Session(profile_name=aws_profile) if aws_profile else boto3.Session()
    client = session.client("kinesis", region_name=region)

    sent = 0
    failed = 0
    start = time.time()
    line_cursor = start_line

    batch: list[dict[str, Any]] = []
    last_checkpoint_at = 0

    def flush() -> None:
        nonlocal sent, failed, batch
        if not batch:
            return
        if dry_run:
            sent += len(batch)
            batch = []
            return

        ok, bad = _put_records_with_retry(client=client, stream_name=stream_name, records=batch)
        sent += ok
        failed += bad
        batch = []

    for time_s, user, computer in iter_lanl_rows(
        input_path,
        start_line=start_line,
        max_events=max_events,
    ):
        event_id = make_event_id(time_s, user, computer)
        event = parse_lanl_record(time_s, user, computer, event_id)
        payload = json.dumps(event.model_dump(mode="json"), separators=(",", ":")).encode("utf-8")

        batch.append({"Data": payload, "PartitionKey": event.user_id})
        line_cursor += 1

        if len(batch) >= batch_size:
            flush()
            _sleep_for_rate(sent_events=sent, start_time=start, rate_events_per_sec=rate_events_per_sec)

        if checkpoint_file and (sent - last_checkpoint_at) >= checkpoint_every:
            checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_file.write_text(
                json.dumps({"line": line_cursor, "sent": sent, "failed": failed}),
                encoding="utf-8",
            )
            last_checkpoint_at = sent

    flush()
    if checkpoint_file:
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_file.write_text(
            json.dumps({"line": line_cursor, "sent": sent, "failed": failed}),
            encoding="utf-8",
        )

    elapsed = max(time.time() - start, 1e-6)
    return {
        "input": str(input_path),
        "stream": stream_name,
        "region": region,
        "sent": sent,
        "failed": failed,
        "elapsed_sec": elapsed,
        "throughput_events_per_sec": sent / elapsed,
        "dry_run": dry_run,
        "start_line": start_line,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay LANL auth events into Kinesis")
    ap.add_argument(
        "--config",
        default=str(Path("config") / "dev.yaml"),
        help="Path to YAML config (defaults to config/dev.yaml)",
    )
    ap.add_argument(
        "--input",
        default=str(Path("data") / "sample" / "auth_sample.csv"),
        help="Path to LANL auth file (.txt/.csv/.bz2). Defaults to sample CSV.",
    )
    ap.add_argument("--stream-name", help="Kinesis stream name (overrides config)")
    ap.add_argument("--region", help="AWS region (overrides config)")
    ap.add_argument("--profile", help="AWS CLI profile name")
    ap.add_argument("--rate", type=int, help="Events per second (overrides config)")
    ap.add_argument("--max-events", type=int, default=None)
    ap.add_argument("--batch-size", type=int, default=200, help="Kinesis PutRecords batch size (1-500)")
    ap.add_argument(
        "--checkpoint",
        default=str(Path(".checkpoints") / "replay_dev.json"),
        help="Path to checkpoint file",
    )
    ap.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    ap.add_argument("--checkpoint-every", type=int, default=5_000)
    ap.add_argument("--dry-run", action="store_true", help="Parse/validate but do not send")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    cfg_kinesis = cfg.get("kinesis", {}) if isinstance(cfg.get("kinesis"), dict) else {}
    cfg_producer = cfg.get("producer", {}) if isinstance(cfg.get("producer"), dict) else {}

    stream_name = args.stream_name or str(cfg_kinesis.get("stream_name") or "")
    if not stream_name:
        raise SystemExit("Missing stream name. Provide --stream-name or set kinesis.stream_name in config.")

    region = args.region or str(cfg_kinesis.get("region") or "us-east-1")
    rate = args.rate if args.rate is not None else int(cfg_producer.get("rate_events_per_sec") or 2000)

    metrics = replay_to_kinesis(
        input_path=args.input,
        stream_name=stream_name,
        region=region,
        aws_profile=args.profile,
        rate_events_per_sec=rate,
        batch_size=args.batch_size,
        max_events=args.max_events,
        checkpoint_path=args.checkpoint,
        resume=args.resume,
        checkpoint_every=args.checkpoint_every,
        dry_run=args.dry_run,
    )
    logger.info("metrics %s", json.dumps(metrics, separators=(",", ":"), sort_keys=True))


if __name__ == "__main__":
    main()
