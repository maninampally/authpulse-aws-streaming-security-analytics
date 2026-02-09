from __future__ import annotations

from pathlib import Path
from typing import Iterable


def iter_lines(path: str | Path) -> Iterable[str]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield line
