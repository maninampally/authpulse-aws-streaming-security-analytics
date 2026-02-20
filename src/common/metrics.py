from __future__ import annotations

from dataclasses import dataclass

from common.logging_utils import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class Metric:
    name: str
    value: float
    unit: str = "Count"


def emit_metric(metric: Metric) -> None:
    logger.info("metric %s=%s %s", metric.name, metric.value, metric.unit)
