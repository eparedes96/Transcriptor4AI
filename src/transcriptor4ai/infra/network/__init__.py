from __future__ import annotations

"""
Network Communication Infrastructure.

Orchestrates external HTTP interactions via specialized domain clients.
This module acts as a Facade to maintain backward compatibility.
"""

from transcriptor4ai.infra.network.common import calculate_sha256
from transcriptor4ai.infra.network.pricing_client import fetch_external_model_data
from transcriptor4ai.infra.network.telemetry_client import (
    submit_error_report,
    submit_feedback,
)
from transcriptor4ai.infra.network.updates_client import (
    check_for_updates,
    download_binary_stream,
)

# Aliases to prevent breaking changes in updater.py tests
_calculate_sha256 = calculate_sha256

__all__ = [
    "fetch_external_model_data",
    "submit_feedback",
    "submit_error_report",
    "check_for_updates",
    "download_binary_stream",
    "calculate_sha256",
    "_calculate_sha256"
]