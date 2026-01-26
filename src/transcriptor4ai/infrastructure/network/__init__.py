from __future__ import annotations

"""
Network Communication Infrastructure.

Orchestrates external HTTP interactions via specialized domain clients.
This module acts as a Facade to maintain backward compatibility.
"""

from .github_release_client import GithubReleaseClient
from .pricing_api_client import PricingApiClient
from .telemetry_api_client import TelemetryApiClient

__all__ = [
    "GithubReleaseClient",
    "PricingApiClient",
    "TelemetryApiClient",
]