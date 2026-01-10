from __future__ import annotations

"""
Network utilities for Transcriptor4AI.

Handles external communications including:
- Version synchronization via GitHub REST API.
- SHA-256 Checksum retrieval for binary integrity.
- Secure submission of user feedback and crash reports via Formspree.
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

FORMSPREE_ENDPOINT = "https://formspree.io/f/xnjjazrl"

TIMEOUT = 10
USER_AGENT = "Transcriptor4AI-Client/1.4.0"


# -----------------------------------------------------------------------------
# Public API: Version Checking
# -----------------------------------------------------------------------------
def check_for_updates(current_version: str) -> Dict[str, Any]:
    """
    Query GitHub API to compare the local version with the latest remote release.
    Also attempts to retrieve SHA-256 checksums for integrity verification.

    Args:
        current_version: The semantic version string of the running application.

    Returns:
        A dictionary containing update status, latest version, changelog,
        and expected checksum if available.
    """
    result: Dict[str, Any] = {
        "has_update": False,
        "latest_version": current_version,
        "download_url": "",
        "changelog": "",
        "sha256": None,
        "error": None
    }

    headers = {"User-Agent": USER_AGENT}
    logger.info(f"Checking for updates... (Local version: v{current_version})")

    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        latest_tag = data.get("tag_name", "").lstrip("v")
        logger.info(f"Update check: Remote version found is v{latest_tag}")

        if _is_newer(current_version, latest_tag):
            logger.info(f"Status: New version available! (v{current_version} -> v{latest_tag})")
            result["has_update"] = True
            result["latest_version"] = latest_tag
            result["download_url"] = data.get("html_url", "")
            result["changelog"] = data.get("body", "No changelog provided.")

            # Integrity Check
            assets = data.get("assets", [])
            for asset in assets:
                name = asset.get("name", "")
                if name.endswith(".sha256"):
                    try:
                        checksum_url = asset.get("browser_download_url")
                        c_res = requests.get(checksum_url, headers=headers, timeout=5)
                        if c_res.status_code == 200:
                            raw_hash = c_res.text.split()[0].strip()
                            result["sha256"] = raw_hash
                            logger.info(f"Integrity metadata retrieved: {raw_hash}")
                    except Exception as e:
                        logger.warning(f"Failed to retrieve checksum asset: {e}")
                    break
        else:
            logger.info("Status: Application is up to date.")

    except requests.exceptions.RequestException as e:
        msg = f"GitHub API update check failed: {e}"
        logger.error(msg)
        result["error"] = msg
    except Exception as e:
        msg = f"Unexpected error during update check: {e}"
        logger.error(msg)
        result["error"] = "Unexpected local error"

    return result


# -----------------------------------------------------------------------------
# Public API: Communication Channels
# -----------------------------------------------------------------------------
def submit_feedback(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Submit user feedback or feature requests to the development team.

    Args:
        payload: Dictionary containing feedback details.

    Returns:
        Tuple of (Success Status, Server Message/Error).
    """
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Feedback")


def submit_error_report(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Submit technical crash reports and stack traces for analysis.

    Args:
        payload: Dictionary containing crash details, version, and logs.

    Returns:
        Tuple of (Success Status, Server Message/Error).
    """
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Error Report")


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
            parts = []
            for p in v.split("."):
                clean_p = "".join(filter(str.isdigit, p))
                parts.append(int(clean_p) if clean_p else 0)
            return tuple(parts)

        v_current = parse(current)
        v_latest = parse(latest)

        logger.debug(f"Comparing semantic versions: Local{v_current} vs Remote{v_latest}")
        return v_latest > v_current

    except (ValueError, AttributeError) as e:
        logger.warning(f"Version comparison failed for current='{current}' latest='{latest}'. Error: {e}")
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
    if not url:
        msg = f"{context} system is not active (endpoint not configured)."
        logger.warning(msg)
        return False, msg

    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)

        if response.status_code in (200, 201):
            logger.info(f"{context} submitted successfully to developer.")
            return True, "Success"

        err_msg = f"Server rejected request with status: {response.status_code}"
        logger.error(f"{context} submission failed: {err_msg}")
        return False, err_msg

    except requests.exceptions.RequestException as e:
        err_msg = f"Network communication error: {str(e)}"
        logger.error(f"{context} submission failed: {err_msg}")
        return False, err_msg