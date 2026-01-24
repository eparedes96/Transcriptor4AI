from __future__ import annotations

"""
Pricing API Client Adapter.

Handles network interactions required to synchronize the dynamic model database
from external authorities (e.g., LiteLLM GitHub Repository).
Ensures fail-safe data fetching with strict timeouts to prevent application hang.
"""

import logging
from typing import Any, Dict, Optional

import requests

from transcriptor4ai.infrastructure.network.common import USER_AGENT

logger = logging.getLogger(__name__)

# ==============================================================================
# NETWORK CONSTANTS
# ==============================================================================
MODEL_DATA_TIMEOUT = 5  # Strict timeout for pricing sync (seconds)


# ==============================================================================
# PRICING CLIENT IMPLEMENTATION
# ==============================================================================
class PricingApiClient:
    """
    Network adapter for retrieving AI model metadata and pricing.
    """

    def fetch_external_model_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Acquire the master model database from a remote authority.

        Performs a GET request to the specified URL (usually a raw JSON file)
        and validates that the response is a dictionary structure.

        Args:
            url: The endpoint URL for the pricing JSON (defined in shared constants).

        Returns:
            Optional[Dict[str, Any]]: The parsed model dictionary if successful,
                                      None if network error or malformed data.
        """
        headers = {"User-Agent": USER_AGENT}
        logger.debug(f"PricingClient: Initiating dynamic discovery from: {url}")

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=MODEL_DATA_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()

            # Schema Validation: Root must be a dictionary (Key-Value map)
            if not isinstance(data, dict):
                logger.warning("PricingClient: Received malformed data (Root is not a dict).")
                return None

            size_kb = len(response.content) / 1024
            logger.info(f"PricingClient: Metadata synchronized ({size_kb:.1f} KB).")
            return data

        except requests.exceptions.Timeout:
            logger.warning(
                f"PricingClient: Discovery timed out after {MODEL_DATA_TIMEOUT}s. "
                "Using cached/default data."
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"PricingClient: Communication error: {e}")
        except Exception as e:
            logger.error(f"PricingClient: Unexpected failure during sync: {e}")

        return None