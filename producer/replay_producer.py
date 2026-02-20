"""AuthPulse replay producer entrypoint.

This file is a thin wrapper around the package implementation in
`src/producer/replay_lanl.py` so it can be run as:

    python producer/replay_producer.py --config config/dev.yaml --profile authpulse-dev
"""

from __future__ import annotations

import sys
from pathlib import Path


# Allow running this wrapper directly without requiring an editable install.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from producer.replay_lanl import main  # noqa: E402


if __name__ == "__main__":
    main()
