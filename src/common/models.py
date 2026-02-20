from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator


class AuthEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_time: datetime = Field(..., description="Event time as a timezone-aware UTC timestamp")
    user_id: str = Field(..., min_length=1, description="User identifier (non-empty)")
    computer_id: str = Field(..., min_length=1, description="Host/computer identifier (non-empty)")
    event_id: str = Field(
        ..., min_length=1, description="Stable unique identifier for deduplication"
    )

    @field_validator("event_time")
    @classmethod
    def _event_time_must_be_tz_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("event_time must be timezone-aware (UTC)")
        return value.astimezone(timezone.utc)

    @field_validator("user_id", "computer_id", "event_id")
    @classmethod
    def _strip_and_require_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must be non-empty")
        return value


def parse_lanl_record(time_s: str, user: str, computer: str, event_id: str) -> AuthEvent:
    ts = datetime.fromtimestamp(int(time_s), tz=timezone.utc)
    return AuthEvent(event_time=ts, user_id=user, computer_id=computer, event_id=event_id)
