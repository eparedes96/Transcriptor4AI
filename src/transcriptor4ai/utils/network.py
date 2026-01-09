from __future__ import annotations

"""
Network utilities for Transcriptor4AI.

Handles external communications including:
- Version synchronization via GitHub REST API.
- Secure submission of user feedback and crash reports.
- Semantic version comparison and network failover logic.
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

FEEDBACK_ENDPOINT = "https://api.example.com/feedback"
REPORT_ENDPOINT = "https://api.example.com/reports"

TIMEOUT = 10
USER_AGENT = "Transcriptor4AI-Client/1.3.0"


# -----------------------------------------------------------------------------
# Public API: Version Checking
# -----------------------------------------------------------------------------
def check_for_updates(current_version: str) -> Dict[str, Any]:
    """
    Query GitHub API to compare the local version with the latest remote release.

    Args:
        current_version: The semantic version string of the running application.

    Returns:
        A dictionary containing:
        - 'has_update' (bool): True if a newer version exists.
        - 'latest_version' (str): The version string found on the server.
        - 'download_url' (str): URL to the release page.
        - 'changelog' (str): Release notes from the server.
        - 'error' (Optional[str]): Error message if the request failed.
    """
    result: Dict[str, Any] = {
        "has_update": False,
        "latest_version": current_version,
        "download_url": "",
        "changelog": "",
        "error": None
    }

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # Clean tag
        latest_tag = data.get("tag_name", "").lstrip("v")

        if _is_newer(current_version, latest_tag):
            result["has_update"] = True
            result["latest_version"] = latest_tag
            result["download_url"] = data.get("html_url", "")
            result["changelog"] = data.get("body", "No changelog provided.")

    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API update check failed: {e}")
        result["error"] = str(e)
    except Exception as e:
        logger.error(f"Unexpected error during update check: {e}")
        result["error"] = "Unexpected local error"

    return result


# -----------------------------------------------------------------------------
# Public API: Communication Channels
# -----------------------------------------------------------------------------
def submit_feedback(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Submit user feedback or feature requests to the development team.

    Args:
        payload: Dictionary containing feedback details (type, subject, message).

    Returns:
        Tuple of (Success Status, Server Message/Error).
    """
    return _secure_post(FEEDBACK_ENDPOINT, payload, "Feedback")


def submit_error_report(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Submit technical crash reports and stack traces for analysis.

    Args:
        payload: Dictionary containing crash details, version, and logs.

    Returns:
        Tuple of (Success Status, Server Message/Error).
    """
    return _secure_post(REPORT_ENDPOINT, payload, "Error Report")


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------
def _is_newer(current: str, latest: str) -> bool:
    """
    Perform a semantic version comparison (Major.Minor.Patch).

    Returns:
        True if the latest version is strictly greater than the current version.
    """
    try:
        def parse(v: str) -> Tuple[int, ...]:
            return tuple(map(int, v.split(".")))

        return parse(latest) > parse(current)
    except (ValueError, AttributeError):
        logger.warning(f"Version comparison failed for current='{current}' latest='{latest}'")
        return False


def _secure_post(url: str, data: Dict[str, Any], context: str) -> Tuple[bool, str]:
    """
    Generic wrapper for POST requests with security validation and logging.

    Args:
        url: Destination endpoint.
        data: Payload to be sent as JSON.
        context: Label for logging (e.g., 'Feedback').

    Returns:
        Tuple of (bool, str) representing success status and descriptive message.
    """
    # Prevent execution if placeholders are still present
    if not url or "example.com" in url:
        msg = f"{context} system is not active (endpoint not configured)."
        logger.warning(msg)
        return False, msg

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)

        if response.status_code in (200, 201):
            logger.info(f"{context} submitted successfully.")
            return True, "Success"

        err_msg = f"Server rejected request with status: {response.status_code}"
        logger.error(f"{context} submission failed: {err_msg}")
        return False, err_msg

    except requests.exceptions.RequestException as e:
        err_msg = f"Network communication error: {str(e)}"
        logger.error(f"{context} submission failed: {err_msg}")
        return False, err_msg