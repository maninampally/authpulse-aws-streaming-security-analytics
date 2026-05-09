from __future__ import annotations


def build_streaming_query() -> str:
    """Return a simple SQL-shaped enrichment query for the raw auth feed.

    The repo's production Spark job lives in `streaming/spark_streaming_job.py`,
    but this helper keeps the package API usable for smoke tests and future SQL
    assembly.
    """

    return "\n".join(
        [
            "SELECT",
            "  event_time,",
            "  user_id,",
            "  computer_id,",
            "  event_id,",
            "  event_date,",
            "  CAST(TRUE AS BOOLEAN) AS is_new_device",
            "FROM raw_auth_events",
            "WHERE event_time IS NOT NULL",
            "  AND user_id IS NOT NULL",
            "  AND computer_id IS NOT NULL",
        ]
    )
