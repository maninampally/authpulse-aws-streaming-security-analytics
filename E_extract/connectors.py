"""
Real data integration connectors for AuthPulse.
Provides adapters for connecting to enterprise authentication sources.

Supported sources:
  - Okta (SAML/OAuth provider)
  - Microsoft Active Directory (LDAP)
  - AWS IAM (AWS-native identity provider)
  - Generic SAML 2.0 (Ping Identity, OneLogin, etc.)

Usage:
  from E_extract.connectors import OktaConnector, ADConnector

  # Okta
  okta = OktaConnector(api_key="...", org_url="https://myorg.okta.com")
  events = okta.fetch_logon_events(start_time=..., end_time=...)

  # Active Directory
  ad = ADConnector(server="dc.example.com", username="...", password="...")
  events = ad.fetch_logon_events()
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AuthConnectorBase(ABC):
    """Abstract base class for authentication source connectors"""

    def __init__(self, environment: str = "prod"):
        self.environment = environment
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{environment}")

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the source. Returns True if successful."""
        raise NotImplementedError

    @abstractmethod
    def fetch_logon_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10000
    ) -> List[Dict]:
        """Fetch logon events from the source.

        Args:
            start_time: Start time for event retrieval (default: 24h ago)
            end_time: End time for event retrieval (default: now)
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        raise NotImplementedError

    def normalize_event(self, raw_event: Dict) -> Dict:
        """Normalize event to AuthPulse schema.

        Expected output schema:
        {
            'event_id': str,
            'event_time': str (ISO 8601),
            'event_date': str (YYYY-MM-DD),
            'src_ip': str,
            'dst_host': str,
            'user_id': str,
            'event_type': str (login, logout, sudo, ssh, rdp, etc.),
            'outcome': str (success, failure),
            'source_system': str (okta, ad, aws, etc.),
            'metadata': Dict (system-specific fields)
        }
        """
        raise NotImplementedError


class OktaConnector(AuthConnectorBase):
    """Connector for Okta authentication events"""

    def __init__(
        self,
        api_key: str,
        org_url: str,
        environment: str = "prod"
    ):
        super().__init__(environment)
        self.api_key = api_key
        self.org_url = org_url.rstrip('/')
        self.session = None

    def authenticate(self) -> bool:
        """Verify Okta API credentials"""
        try:
            import requests  # type: ignore

            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.org_url}/api/v1/users/me", headers=headers, timeout=15)
            ok = response.status_code == 200
            self.logger.info("Okta authentication %s", "succeeded" if ok else "failed")
            return ok
        except Exception as e:
            self.logger.error(f"Okta authentication failed: {e}")
            return False

    def fetch_logon_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10000
    ) -> List[Dict]:
        """Fetch Okta System Log events (logon.success, logon.failed, user.session.start, etc.)"""

        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.utcnow()

        self.logger.info(f"Fetching Okta events from {start_time} to {end_time}")

        events: list[dict[str, Any]] = []
        try:
            import requests  # type: ignore

            headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
            after = None
            while len(events) < limit:
                params: dict[str, Any] = {
                    "limit": min(100, limit - len(events)),
                    "filter": (
                        'eventType eq "user.session.start" or '
                        'eventType eq "user.session.end" or '
                        'eventType eq "user.authentication.authenticate_success" or '
                        'eventType eq "user.authentication.authenticate_failure"'
                    ),
                }
                if after:
                    params["after"] = after

                response = requests.get(
                    f"{self.org_url}/api/v1/logs",
                    headers=headers,
                    params=params,
                    timeout=30,
                )
                if response.status_code != 200:
                    self.logger.warning("Okta logs request returned %s", response.status_code)
                    break

                batch = response.json()
                if not isinstance(batch, list) or not batch:
                    break
                events.extend(batch)
                after = batch[-1].get("published")
                if len(batch) < params["limit"]:
                    break
        except Exception as exc:
            self.logger.warning("Okta event fetch unavailable; returning empty set: %s", exc)

        self.logger.info(f"Retrieved {len(events)} Okta events")
        return [self.normalize_event(e) for e in events]

    def normalize_event(self, raw_event: Dict) -> Dict:
        """Convert Okta System Log event to AuthPulse schema"""
        # TODO: Implement Okta event normalization
        # Typical Okta fields: eventType, published, actor, client, outcome, etc.
        return {
            'event_id': raw_event.get('eventId', ''),
            'event_time': raw_event.get('published', ''),
            'event_date': raw_event.get('published', '')[:10],
            'src_ip': raw_event.get('client', {}).get('ipAddress', ''),
            'dst_host': '',
            'user_id': raw_event.get('actor', {}).get('alternateId', ''),
            'event_type': self._map_okta_event_type(raw_event.get('eventType', '')),
            'outcome': self._map_okta_outcome(raw_event.get('outcome', {})),
            'source_system': 'okta',
            'metadata': raw_event
        }

    def _map_okta_event_type(self, event_type: str) -> str:
        """Map Okta event types to AuthPulse event types"""
        mapping = {
            'user.session.start': 'login',
            'user.session.end': 'logout',
            'user.authentication.authenticate_success': 'login',
            'user.authentication.authenticate_failure': 'login',
        }
        return mapping.get(event_type, 'login')

    def _map_okta_outcome(self, outcome: Dict) -> str:
        """Map Okta outcome to AuthPulse outcome"""
        result = outcome.get('result', '').lower()
        return 'success' if 'success' in result else 'failure'


class ADConnector(AuthConnectorBase):
    """Connector for Microsoft Active Directory authentication events"""

    def __init__(
        self,
        server: str,
        domain: str,
        username: str,
        password: str,
        environment: str = "prod"
    ):
        super().__init__(environment)
        self.server = server
        self.domain = domain
        self.username = username
        self.password = password
        self.connection = None

    def authenticate(self) -> bool:
        """Connect to Active Directory"""
        try:
            import ldap  # type: ignore

            self.connection = ldap.initialize(f"ldap://{self.server}")
            self.connection.simple_bind_s(f"{self.username}@{self.domain}", self.password)
            self.logger.info("Active Directory connection established")
            return True
        except Exception as e:
            self.logger.error(f"AD connection failed: {e}")
            return False

    def fetch_logon_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10000
    ) -> List[Dict]:
        """Fetch Active Directory logon events from Windows Event Log via WinRM or direct query"""

        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.utcnow()

        self.logger.info(f"Fetching AD logon events from {start_time} to {end_time}")

        events: list[dict[str, Any]] = []
        self.logger.info(
            "AD event collection requires an environment-specific WinRM/LDAP query; returning empty set"
        )

        self.logger.info(f"Retrieved {len(events)} AD logon events")
        return [self.normalize_event(e) for e in events]

    def normalize_event(self, raw_event: Dict) -> Dict:
        """Convert AD event to AuthPulse schema"""
        # TODO: Implement AD event normalization
        # Typical AD fields: Event ID, TimeCreated, Computer, TargetUserName, SourceIPAddress
        return {
            'event_id': raw_event.get('EventRecordID', ''),
            'event_time': raw_event.get('TimeCreated', ''),
            'event_date': raw_event.get('TimeCreated', '')[:10],
            'src_ip': raw_event.get('SourceIPAddress', ''),
            'dst_host': raw_event.get('Computer', ''),
            'user_id': raw_event.get('TargetUserName', ''),
            'event_type': self._map_ad_event_type(int(raw_event.get('EventID', 0))),
            'outcome': self._map_ad_outcome(int(raw_event.get('EventID', 0))),
            'source_system': 'active_directory',
            'metadata': raw_event
        }

    def _map_ad_event_type(self, event_id: int) -> str:
        """Map AD event IDs to AuthPulse event types"""
        if event_id in [4624, 4625]:  # Logon success/fail
            return 'login'
        elif event_id in [4634, 4647]:  # Logoff
            return 'logout'
        elif event_id == 4672:  # Special privileges
            return 'sudo'
        else:
            return 'login'

    def _map_ad_outcome(self, event_id: int) -> str:
        """Map AD event IDs to success/failure"""
        return 'success' if event_id in [4624, 4634, 4647] else 'failure'


class AWSIAMConnector(AuthConnectorBase):
    """Connector for AWS IAM authentication events via CloudTrail"""

    def __init__(self, region: str = "us-east-1", environment: str = "prod"):
        super().__init__(environment)
        self.region = region
        self.client = None

    def authenticate(self) -> bool:
        """Verify AWS CloudTrail access"""
        try:
            import boto3  # type: ignore

            self.client = boto3.client("cloudtrail", region_name=self.region)
            self.client.describe_trails()
            self.logger.info("AWS CloudTrail access configured")
            return True
        except Exception as e:
            self.logger.error(f"AWS CloudTrail access failed: {e}")
            return False

    def fetch_logon_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 10000
    ) -> List[Dict]:
        """Fetch AWS IAM authentication events from CloudTrail"""

        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if end_time is None:
            end_time = datetime.utcnow()

        self.logger.info(f"Fetching CloudTrail events from {start_time} to {end_time}")

        events: list[dict[str, Any]] = []
        try:
            if self.client is None:
                self.authenticate()
            if self.client is None:
                return []

            next_token: str | None = None
            while len(events) < limit:
                params: dict[str, Any] = {
                    "StartTime": start_time,
                    "EndTime": end_time,
                    "MaxResults": min(50, limit - len(events)),
                    "LookupAttributes": [
                        {"AttributeKey": "EventName", "AttributeValue": "ConsoleLogin"},
                    ],
                }
                if next_token:
                    params["NextToken"] = next_token

                response = self.client.lookup_events(**params)
                batch = response.get("Events", [])
                if not isinstance(batch, list) or not batch:
                    break
                for item in batch:
                    if isinstance(item, dict):
                        events.append(item)
                        if len(events) >= limit:
                            break
                next_token = response.get("NextToken")
                if not next_token:
                    break
        except Exception as exc:
            self.logger.warning("CloudTrail lookup unavailable; returning empty set: %s", exc)

        self.logger.info(f"Retrieved {len(events)} CloudTrail events")
        return [self.normalize_event(e) for e in events]

    def normalize_event(self, raw_event: Dict) -> Dict:
        """Convert CloudTrail event to AuthPulse schema"""
        # TODO: Implement CloudTrail event normalization
        return {
            'event_id': raw_event.get('eventID', ''),
            'event_time': raw_event.get('eventTime', ''),
            'event_date': raw_event.get('eventTime', '')[:10],
            'src_ip': raw_event.get('sourceIPAddress', ''),
            'dst_host': 'aws',
            'user_id': raw_event.get('userIdentity', {}).get('principalId', ''),
            'event_type': 'login',
            'outcome': 'success' if raw_event.get('errorCode') is None else 'failure',
            'source_system': 'aws_iam',
            'metadata': raw_event
        }


def get_connector(source_type: str, config: Dict) -> AuthConnectorBase:
    """Factory function to get the appropriate connector for a data source.

    Args:
        source_type: Type of source (okta, ad, aws)
        config: Configuration dict with source-specific parameters

    Returns:
        Initialized connector instance
    """
    connectors = {
        'okta': OktaConnector,
        'active_directory': ADConnector,
        'aws': AWSIAMConnector,
    }

    connector_class = connectors.get(source_type)
    if not connector_class:
        raise ValueError(f"Unknown source type: {source_type}")

    return connector_class(**config)
