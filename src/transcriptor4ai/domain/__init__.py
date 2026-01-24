from __future__ import annotations

"""
Domain Layer Facade.

Centralizes access to the core business logic components:
1. ENTITIES: Immutable data structures (Value Objects/DTOs).
2. PORTS: Abstract interfaces defining infrastructure contracts.
3. EXCEPTIONS: Domain-specific error hierarchy.
"""

# ==============================================================================
# ENTITIES (DATA MODELS)
# ==============================================================================
from transcriptor4ai.domain.entities.app_config import (
    get_default_app_state,
    get_default_config,
)
from transcriptor4ai.domain.entities.file_node import FileNode, Tree
from transcriptor4ai.domain.entities.pipeline_results import PipelineResult
from transcriptor4ai.domain.entities.transcription_error import TranscriptionError

# ==============================================================================
# PORTS (INFRASTRUCTURE CONTRACTS)
# ==============================================================================
from transcriptor4ai.domain.ports.cache_port import ICacheRepository
from transcriptor4ai.domain.ports.config_port import IConfigRepository
from transcriptor4ai.domain.ports.model_port import IModelRegistry
from transcriptor4ai.domain.ports.network_port import IUpdateClient
from transcriptor4ai.domain.ports.system_port import IFileSystem
from transcriptor4ai.domain.ports.user_port import IUserContext

# ==============================================================================
# EXCEPTIONS (BUSINESS ERRORS)
# ==============================================================================
from transcriptor4ai.domain.exceptions import (
    ConfigurationError,
    DomainError,
    InfrastructureError,
    TranscriptionFailedError,
)

__all__ = [
    # Entities
    "get_default_app_state",
    "get_default_config",
    "FileNode",
    "Tree",
    "PipelineResult",
    "TranscriptionError",
    # Ports
    "ICacheRepository",
    "IConfigRepository",
    "IModelRegistry",
    "IFileSystem",
    "IUpdateClient",
    "IUserContext",
    # Exceptions
    "DomainError",
    "ConfigurationError",
    "InfrastructureError",
    "TranscriptionFailedError",
]