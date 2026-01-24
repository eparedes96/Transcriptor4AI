from __future__ import annotations

"""
Telemetry API Client Adapter.

Handles the transmission of anonymous usage data, user feedback, and
critical crash reports to the centralized collection endpoint (Formspree).
Implements fail-safe network operations that should never interrupt the
main application flow.
"""

import logging
from typing import Any, Dict, Tuple

import requests

from transcriptor4ai.infrastructure.network.common import DEFAULT_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)


# ==============================================================================
# TELEMETRY CLIENT IMPLEMENTATION
# ==============================================================================
class TelemetryApiClient:
    """
    Network adapter for sending diagnostic data and user feedback.
    """

    # Centralized endpoint for data collection
    FORMSPREE_ENDPOINT = "https://formspree.io/f/xnjjazrl"

    def submit_feedback(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Transmit user feedback to the remote endpoint.

        Args:
            payload: Dictionary containing subject, message, and optional logs.

        Returns:
            Tuple[bool, str]: (Success flag, Response message/Error).
        """
        return self._secure_post(self.FORMSPREE_ENDPOINT, payload)

    def submit_error_report(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Transmit critical crash data for diagnostic analysis.

        Args:
            payload: Dictionary containing stack trace, OS info, and user context.

        Returns:
            Tuple[bool, str]: (Success flag, Response message/Error).
        """
        return self._secure_post(self.FORMSPREE_ENDPOINT, payload)

    # ==========================================================================
    # INTERNAL NETWORK LOGIC
    # ==========================================================================
    def _secure_post(self, url: str, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Execute a secure JSON POST request with robust exception handling.

        Designed to fail silently or gracefully, ensuring that telemetry errors
        do not crash the host application.

        Args:
            url: Destination URL.
            data: JSON-serializable payload.

        Returns:
            Tuple[bool, str]: (Success flag, Status description).
        """
        headers = {"User-Agent": USER_AGENT}
        try:
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=DEFAULT_TIMEOUT
            )
            is_success = response.status_code in (200, 201)
            msg = "Success" if is_success else f"HTTP {response.status_code}"

            if not is_success:
                logger.warning(f"Telemetry: Submission failed with status {response.status_code}")

            return is_success, msg

        except Exception as e:
            logger.error(f"Telemetry: Network transmission error: {e}")
            return False, str(e)