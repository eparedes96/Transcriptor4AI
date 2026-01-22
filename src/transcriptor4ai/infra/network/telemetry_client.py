from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

import requests

from transcriptor4ai.infra.network.common import DEFAULT_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

FORMSPREE_ENDPOINT = "https://formspree.io/f/xnjjazrl"

def submit_feedback(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Transmit user feedback to the centralized collection endpoint."""
    return _secure_post(FORMSPREE_ENDPOINT, payload)

def submit_error_report(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Transmit critical crash data for diagnostic analysis."""
    return _secure_post(FORMSPREE_ENDPOINT, payload)

def _secure_post(url: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    """Execute a secure JSON POST request with robust exception handling."""
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=DEFAULT_TIMEOUT)
        return response.status_code in (200, 201), "Success"
    except Exception as e:
        return False, str(e)