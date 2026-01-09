from __future__ import annotations

"""
Network utilities for Transcriptor4AI.

Handles:
- Version checking via GitHub API.
- Feedback and crash report submission.
- Network status validation.
"""

import logging
import requests
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
GITHUB_OWNER = "eparedes96"
GITHUB_REPO = "Transcriptor4AI"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Placeholders for feedback API
FEEDBACK_ENDPOINT = "https://api.example.com/feedback"
REPORT_ENDPOINT = "https://api.example.com/reports"

TIMEOUT = 10


# -----------------------------------------------------------------------------
# Version Checking
# -----------------------------------------------------------------------------
def check_for_updates(current_version: str) -> Dict[str, Any]:
    """
    Query GitHub API to compare the current version with the latest release.

    Returns:
        Dict containing:
        - 'has_update': bool
        - 'latest_version': str
        - 'download_url': str
        - 'changelog': str
        - 'error': Optional[str]
    """
    result = {
        "has_update": False,
        "latest_version": current_version,
        "download_url": "",
        "changelog": "",
        "error": None
    }

    try:
        response = requests.get(GITHUB_API_URL, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        latest_tag = data.get("tag_name", "").replace("v", "")

        if _is_newer(current_version, latest_tag):
            result["has_update"] = True
            result["latest_version"] = latest_tag
            result["download_url"] = data.get("html_url", "")
            result["changelog"] = data.get("body", "No changelog provided.")

    except Exception as e:
        logger.error(f"Failed to check for updates: {e}")
        result["error"] = str(e)

    return result


def _is_newer(current: str, latest: str) -> bool:
    """Simple semantic version comparison."""
    try:
        def parse(v: str) -> Tuple[int, ...]:
            return tuple(map(int, v.split(".")))

        return parse(latest) > parse(current)
    except Exception:
        return False


# -----------------------------------------------------------------------------
# Communication Channels
# -----------------------------------------------------------------------------
def submit_feedback(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Send user feedback/suggestions to the developer.

    Payload should include: 'type', 'subject', 'message', 'email' (optional).
    """
    return _secure_post(FEEDBACK_ENDPOINT, payload, "Feedback")


def submit_error_report(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Send crash reports and stack traces to the developer.

    Payload should include: 'stack_trace', 'version', 'os', 'logs'.
    """
    return _secure_post(REPORT_ENDPOINT, payload, "Error Report")


# -----------------------------------------------------------------------------
# Internal Helpers
# -----------------------------------------------------------------------------
def _secure_post(url: str, data: Dict[str, Any], context: str) -> Tuple[bool, str]:
    """Generic wrapper for POST requests with error handling."""
    if not url or "example.com" in url:
        logger.warning(f"{context} endpoint not configured.")
        return False, "Endpoint not configured."

    try:
        response = requests.post(url, json=data, timeout=TIMEOUT)
        if response.status_code in (200, 201):
            logger.info(f"{context} submitted successfully.")
            return True, "Success"

        err_msg = f"Server returned status {response.status_code}"
        logger.error(f"{context} submission failed: {err_msg}")
        return False, err_msg

    except requests.exceptions.RequestException as e:
        logger.error(f"{context} submission network error: {e}")
        return False, str(e)