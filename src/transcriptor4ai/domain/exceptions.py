from __future__ import annotations

"""
Domain Exception Hierarchy.

Defines a structured taxonomy of errors to classify failures across the
application layers. Ensures that low-level technical exceptions (OS, Network, DB) 
are translated into meaningful business errors for the orchestrator and interface.
"""

# ==============================================================================
# BASE DOMAIN EXCEPTION
# ==============================================================================
class DomainError(Exception):
    """
    Root exception for all Transcriptor4AI domain-related errors.
    """
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ==============================================================================
# CONFIGURATION ERRORS
# ==============================================================================
class ConfigurationError(DomainError):
    """
    Raised when the application state or user configuration is invalid,
    corrupted, or contains incompatible parameters.
    """


# ==============================================================================
# INFRASTRUCTURE ERRORS
# ==============================================================================
class InfrastructureError(DomainError):
    """
    Raised when an external service or resource (Filesystem, SQLite, Network)
    fails to perform a requested operation.
    """


# ==============================================================================
# TRANSCRIPTION ERRORS
# ==============================================================================
class TranscriptionFailedError(DomainError):
    """
    Raised when the core pipeline fails to process a file or assemble the
    final context due to logic or resource constraints.
    """


class SecuritySanitizationError(TranscriptionFailedError):
    """
    Raised when the privacy engine identifies a risk that blocks the
    transcription process.
    """