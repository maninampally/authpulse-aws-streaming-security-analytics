"""
Real data producer for AuthPulse.
Fetches events from enterprise auth sources (Okta, AD, AWS) and streams to Kinesis.

Usage:
  python real_data_producer.py --source okta --config config/okta.yaml
  python real_data_producer.py --source active_directory --config config/ad.yaml
  python real_data_producer.py --source aws --config config/aws.yaml
"""

import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Optional
import yaml
import boto3

from E_extract.connectors import get_connector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RealDataProducer:
    """Produces real authentication events from enterprise sources to Kinesis."""

    def __init__(
        self,
        source_type: str,
        config: Dict,
        environment: str = "prod"
    ):
        self.source_type = source_type
        self.config = config
        self.environment = environment

        # Initialize connector
        self.connector = get_connector(source_type, self._extract_connector_config(config))

        # Initialize Kinesis
        self.kinesis = boto3.client('kinesis', region_name=config.get('aws_region', 'us-east-1'))
        self.stream_name = f"authpulse-{environment}-stream"

        self.events_produced = 0
        self.events_failed = 0

    def _extract_connector_config(self, config: Dict) -> Dict:
        """Extract connector-specific config from config dict."""
        if self.source_type == 'okta':
            return {
                'api_key': config['okta']['api_key'],
                'org_url': config['okta']['org_url'],
                'environment': self.environment
            }
        elif self.source_type == 'active_directory':
            return {
                'server': config['ad']['server'],
                'domain': config['ad']['domain'],
                'username': config['ad']['username'],
                'password': config['ad']['password'],
                'environment': self.environment
            }
        elif self.source_type == 'aws':
            return {
                'region': config.get('aws_region', 'us-east-1'),
                'environment': self.environment
            }
        else:
            raise ValueError(f"Unknown source type: {self.source_type}")

    def run(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        """Fetch events from source and produce to Kinesis.

        Args:
            start_time: Start time for event retrieval (default: 24h ago)
            end_time: End time for event retrieval (default: now)
        """

        logger.info(f"Starting {self.source_type} data producer for {self.environment}")

        # Authenticate with source
        if not self.connector.authenticate():
            logger.error(f"Failed to authenticate with {self.source_type}")
            return

        # Fetch events
        logger.info(f"Fetching events from {self.source_type}...")
        try:
            events = self.connector.fetch_logon_events(
                start_time=start_time,
                end_time=end_time,
                limit=self.config.get('batch_size', 10000)
            )
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return

        logger.info(f"Retrieved {len(events)} events from {self.source_type}")

        # Produce to Kinesis
        for event in events:
            try:
                self._produce_event(event)
                self.events_produced += 1
            except Exception as e:
                logger.error(f"Failed to produce event: {e}")
                self.events_failed += 1

        logger.info(f"Production complete: {self.events_produced} succeeded, {self.events_failed} failed")

    def _produce_event(self, event: Dict):
        """Send a single event to Kinesis."""
        # Add production metadata
        event['_produced_at'] = datetime.utcnow().isoformat() + 'Z'
        event['_source_producer'] = f"{self.source_type}_producer"

        # Use user_id as partition key (distributes across shards)
        partition_key = event.get('user_id', 'unknown')

        response = self.kinesis.put_record(
            StreamName=self.stream_name,
            Data=json.dumps(event),
            PartitionKey=partition_key
        )

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise Exception(f"Failed to put record: {response}")

    def get_stats(self) -> Dict:
        """Return production statistics."""
        return {
            'source': self.source_type,
            'environment': self.environment,
            'events_produced': self.events_produced,
            'events_failed': self.events_failed,
            'success_rate': (self.events_produced / (self.events_produced + self.events_failed)) * 100
                           if (self.events_produced + self.events_failed) > 0 else 0
        }


def load_config(config_file: str) -> Dict:
    """Load configuration from YAML file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream real auth data to AuthPulse")
    parser.add_argument("--source", required=True, choices=["okta", "active_directory", "aws"],
                        help="Data source type")
    parser.add_argument("--config", required=True, help="Config file path")
    parser.add_argument("--environment", default="prod", choices=["dev", "staging", "prod"],
                        help="Target environment")
    parser.add_argument("--start-time", type=str, help="Start time (ISO 8601)")
    parser.add_argument("--end-time", type=str, help="End time (ISO 8601)")
    parser.add_argument("--hours", type=int, help="Hours to look back (default: 24)")

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Parse time range
    end_time = datetime.fromisoformat(args.end_time) if args.end_time else datetime.utcnow()
    if args.start_time:
        start_time = datetime.fromisoformat(args.start_time)
    else:
        hours = args.hours or 24
        start_time = end_time - timedelta(hours=hours)

    logger.info(f"Loading events from {start_time} to {end_time}")

    # Create and run producer
    producer = RealDataProducer(
        source_type=args.source,
        config=config,
        environment=args.environment
    )

    producer.run(start_time=start_time, end_time=end_time)

    # Print stats
    stats = producer.get_stats()
    logger.info(f"Production Stats: {json.dumps(stats, indent=2)}")
