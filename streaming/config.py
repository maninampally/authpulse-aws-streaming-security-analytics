"""
AuthPulse - Spark Streaming Configuration
Centralized configuration for PySpark Structured Streaming job on EMR.

Values read from environment variables with sensible defaults matching
the dev Terraform layout (single lakehouse bucket).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip() or default


@dataclass
class KinesisConfig:
    stream_name: str = field(
        default_factory=lambda: _env("AUTHPULSE_KINESIS_STREAM", "authpulse-dev-stream")
    )
    region: str = field(
        default_factory=lambda: _env("AWS_REGION", "us-east-1")
    )
    starting_position: str = "LATEST"  # TRIM_HORIZON for reprocessing


@dataclass
class S3Config:
    bucket: str = field(
        default_factory=lambda: _env(
            "AUTHPULSE_S3_BUCKET", "authpulse-dev-lakehouse-289591071327"
        )
    )
    raw_prefix: str = "raw/auth_events"
    features_prefix: str = "features/auth_user_features"
    curated_prefix: str = "curated/auth_events_curated"
    host_popularity_prefix: str = "curated/host_popularity_daily"

    @property
    def raw_path(self) -> str:
        return f"s3a://{self.bucket}/{self.raw_prefix}"

    @property
    def features_path(self) -> str:
        return f"s3a://{self.bucket}/{self.features_prefix}"

    @property
    def curated_path(self) -> str:
        return f"s3a://{self.bucket}/{self.curated_prefix}"

    @property
    def host_popularity_path(self) -> str:
        return f"s3a://{self.bucket}/{self.host_popularity_prefix}"


@dataclass
class IcebergConfig:
    catalog_name: str = "glue_catalog"
    database: str = "authpulse"
    warehouse: str = field(
        default_factory=lambda: (
            f"s3a://{_env('AUTHPULSE_S3_BUCKET', 'authpulse-dev-lakehouse-289591071327')}/iceberg/"
        )
    )


@dataclass
class RiskConfig:
    """Overrides for risk rule thresholds (all optional; DEFAULT_RULE_CONFIG used if absent)."""
    lateral_movement_unique_hosts_1h: int = 10
    burst_login_event_count_1h: int = 50
    new_device_spike_unique_hosts_24h: int = 25
    weight_lateral_movement: int = 35
    weight_burst_login: int = 25
    weight_rare_host: int = 10
    weight_new_device_spike: int = 30

    def as_dict(self) -> dict:
        return {
            "lateral_movement_unique_hosts_1h": self.lateral_movement_unique_hosts_1h,
            "burst_login_event_count_1h": self.burst_login_event_count_1h,
            "new_device_spike_unique_hosts_24h": self.new_device_spike_unique_hosts_24h,
            "weight_lateral_movement": self.weight_lateral_movement,
            "weight_burst_login": self.weight_burst_login,
            "weight_rare_host": self.weight_rare_host,
            "weight_new_device_spike": self.weight_new_device_spike,
        }


@dataclass
class StreamingConfig:
    checkpoint_location: str = field(
        default_factory=lambda: _env(
            "AUTHPULSE_CHECKPOINT_LOCATION",
            "s3a://authpulse-dev-lakehouse-289591071327/checkpoints/spark-streaming",
        )
    )
    trigger_seconds: int = 30
    window_1h_duration: str = "1 hour"
    window_1h_slide: str = "5 minutes"
    window_24h_duration: str = "24 hours"
    window_24h_slide: str = "1 hour"


@dataclass
class SparkConfig:
    app_name: str = "authpulse-spark-streaming"
    shuffle_partitions: int = 10  # keep low for dev; tune up for prod


@dataclass
class AppConfig:
    """Top-level config aggregator — pass one instance throughout the job."""
    kinesis: KinesisConfig = field(default_factory=KinesisConfig)
    s3: S3Config = field(default_factory=S3Config)
    iceberg: IcebergConfig = field(default_factory=IcebergConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    streaming: StreamingConfig = field(default_factory=StreamingConfig)
    spark: SparkConfig = field(default_factory=SparkConfig)


__all__ = [
    "AppConfig",
    "IcebergConfig",
    "KinesisConfig",
    "RiskConfig",
    "S3Config",
    "SparkConfig",
    "StreamingConfig",
]
