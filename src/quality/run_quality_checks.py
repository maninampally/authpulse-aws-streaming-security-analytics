from __future__ import annotations

from pathlib import Path


def main() -> None:
    expectations = Path(__file__).parent / "expectations" / "auth_events_expectations.yml"
    if not expectations.exists():
        raise FileNotFoundError(str(expectations))
    raise NotImplementedError("Wire Great Expectations or custom DQ rules")


if __name__ == "__main__":
    main()
