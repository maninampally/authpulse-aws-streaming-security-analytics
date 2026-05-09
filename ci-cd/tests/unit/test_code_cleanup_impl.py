from __future__ import annotations

from datetime import datetime, timezone

from batch.jobs.backfill_partitions import _build_sql as build_backfill_sql
from stream.spark.processor import build_streaming_query
from E_extract.connectors import AWSIAMConnector, OktaConnector, get_connector


def test_build_streaming_query_mentions_raw_input() -> None:
    sql = build_streaming_query()
    assert "FROM raw_auth_events" in sql
    assert "event_id" in sql


def test_backfill_sql_targets_curated_and_raw_tables() -> None:
    delete_sql, insert_sql = build_backfill_sql(
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc).date(),
        end_date=datetime(2026, 1, 2, tzinfo=timezone.utc).date(),
    )
    assert "DELETE FROM lakehouse.auth_events_curated" in delete_sql
    assert "FROM lakehouse.auth_events_raw" in insert_sql
    assert "risk_score" in insert_sql


def test_okta_normalize_event_maps_fields() -> None:
    connector = OktaConnector(api_key="token", org_url="https://example.okta.com")
    event = connector.normalize_event(
        {
            "eventId": "evt-1",
            "published": "2026-05-03T12:00:00Z",
            "client": {"ipAddress": "10.0.0.1"},
            "actor": {"alternateId": "alice@example.com"},
            "eventType": "user.session.start",
            "outcome": {"result": "SUCCESS"},
        }
    )
    assert event["event_type"] == "login"
    assert event["outcome"] == "success"
    assert event["user_id"] == "alice@example.com"


def test_get_connector_factory() -> None:
    connector = get_connector("aws", {"region": "us-east-1"})
    assert isinstance(connector, AWSIAMConnector)
