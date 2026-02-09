from __future__ import annotations

import os

import pytest


def test_placeholder() -> None:
    if os.getenv("AUTHPULSE_INTEGRATION") != "1":
        pytest.skip("Set AUTHPULSE_INTEGRATION=1 to run integration tests")
    assert True
