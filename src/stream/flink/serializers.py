from __future__ import annotations

import json
from common.models import AuthEvent


def serialize_event(event: AuthEvent) -> bytes:
    return json.dumps(event.model_dump(mode="json")).encode("utf-8")
