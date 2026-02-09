from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    unit: str = "Count"


def emit_metric(metric: Metric) -> None:
    logger.info("metric %s=%s %s", metric.name, metric.value, metric.unit)
