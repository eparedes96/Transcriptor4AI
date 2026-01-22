from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from transcriptor4ai.infra.network.common import USER_AGENT

logger = logging.getLogger(__name__)

MODEL_DATA_TIMEOUT = 5

def fetch_external_model_data(url: str) -> Optional[Dict[str, Any]]:
    """Acquire the master model database from a remote authority."""
    headers = {"User-Agent": USER_AGENT}
    logger.debug(f"Initiating dynamic model discovery from: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=MODEL_DATA_TIMEOUT)
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            logger.warning("Network: Received malformed model data (Root is not a dictionary).")
            return None

        size_kb = len(response.content) / 1024
        logger.info(f"Network: Model metadata synchronized ({size_kb:.1f} KB).")
        return data

    except requests.exceptions.Timeout:
        logger.warning(f"Network: Model discovery timed out after {MODEL_DATA_TIMEOUT}s.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network: Communication error during model discovery: {e}")
    except Exception as e:
        logger.error(f"Network: Unexpected failure during model synchronization: {e}")

    return None