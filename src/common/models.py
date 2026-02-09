from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class AuthEvent(BaseModel):
    event_time: datetime
    user_id: str
    computer_id: str
    event_id: str = Field(..., description="Stable unique identifier for deduplication")


def parse_lanl_record(time_s: str, user: str, computer: str, event_id: str) -> AuthEvent:
    ts = datetime.fromtimestamp(int(time_s), tz=timezone.utc)
    return AuthEvent(event_time=ts, user_id=user, computer_id=computer, event_id=event_id)
