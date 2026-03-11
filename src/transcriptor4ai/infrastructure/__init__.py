from __future__ import annotations

"""
Infrastructure Layer Facade.

Centralizes access to concrete implementations of domain ports and technical 
adapters. This layer handles all communication with external systems, 
including:
1. SYSTEM: OS metadata and filesystem operations.
2. PERSISTENCE: SQLite and JSON storage engines.
3. NETWORK: API clients for updates, pricing, and telemetry.
4. LOGGING: Thread-safe diagnostic infrastructure.
"""

# ==============================================================================
# SYSTEM ADAPTERS (OS & FILESYSTEM)
# ==============================================================================
# ==============================================================================
# LOGGING INFRASTRUCTURE
# ==============================================================================
from transcriptor4ai.infrastructure.logging.logger_factory import configure_logging

# ==============================================================================
# NETWORK ADAPTERS (API CLIENTS)
# ==============================================================================
from transcriptor4ai.infrastructure.network.github_release_client import GithubReleaseClient
from transcriptor4ai.infrastructure.network.pricing_api_client import PricingApiClient
from transcriptor4ai.infrastructure.network.telemetry_api_client import TelemetryApiClient

# ==============================================================================
# PERSISTENCE ADAPTERS (REPOSITORIES)
# ==============================================================================
from transcriptor4ai.infrastructure.persistence.json_config_repo import JsonConfigRepository
from transcriptor4ai.infrastructure.persistence.model_registry_repo import ModelRegistryRepository
from transcriptor4ai.infrastructure.persistence.sqlite_cache_repo import SqliteCacheRepository
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter
from transcriptor4ai.infrastructure.system.user_context_adapter import UserContextAdapter

__all__ = [
    # System
    "FileSystemAdapter",
    "UserContextAdapter",
    # Persistence
    "JsonConfigRepository",
    "SqliteCacheRepository",
    "ModelRegistryRepository",
    # Network
    "GithubReleaseClient",
    "PricingApiClient",
    "TelemetryApiClient",
    # Logging
    "configure_logging",
]