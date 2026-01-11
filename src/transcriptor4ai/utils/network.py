from __future__ import annotations

"""
Network utilities for Transcriptor4AI.

Handles external communications including:
- Version synchronization via GitHub REST API.
- Background binary streaming for Seamless OTA updates.
- SHA-256 Checksum retrieval for binary integrity.
- Secure submission of user feedback and crash reports.
"""

import logging
import requests
from typing import Any, Dict, Optional, Tuple, Callable

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
GITHUB_OWNER = "eparedes96"
GITHUB_REPO = "Transcriptor4AI"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

FORMSPREE_ENDPOINT = "https://formspree.io/f/xnjjazrl"

TIMEOUT = 10
USER_AGENT = "Transcriptor4AI-Client/1.5.0"
CHUNK_SIZE = 8192


# -----------------------------------------------------------------------------
# Public API: Version Checking & Updates
# -----------------------------------------------------------------------------
def check_for_updates(current_version: str) -> Dict[str, Any]:
    """
    Query GitHub API to compare the local version with the latest remote release.
    Retrieves metadata for Seamless OTA, including binary URLs and SHA-256.

    Args:
        current_version: The semantic version string of the running application.

    Returns:
        A dictionary containing update status, latest version, changelog,
        binary URL, and expected checksum.
    """
    result: Dict[str, Any] = {
        "has_update": False,
        "latest_version": current_version,
        "download_url": "",
        "binary_url": "",
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

            # Identify Assets: Binary (.exe) and Checksum (.sha256)
            assets = data.get("assets", [])
            for asset in assets:
                asset_name = asset.get("name", "")

                # Direct Binary Asset
                if asset_name.lower().endswith(".exe"):
                    result["binary_url"] = asset.get("browser_download_url")
                    logger.info(f"Direct binary asset detected: {asset_name}")

                # Integrity Checksum
                elif asset_name.lower().endswith(".sha256"):
                    try:
                        checksum_url = asset.get("browser_download_url")
                        c_res = requests.get(checksum_url, headers=headers, timeout=5)
                        if c_res.status_code == 200:
                            raw_hash = c_res.text.split()[0].strip()
                            result["sha256"] = raw_hash
                            logger.info(f"Integrity metadata retrieved: {raw_hash}")
                    except Exception as e:
                        logger.warning(f"Failed to retrieve checksum asset: {e}")
                if result["has_update"] and not result["binary_url"]:
                    logger.warning("No direct .exe asset found in the latest release. Background OTA will be disabled.")
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


def download_binary_stream(
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
) -> Tuple[bool, str]:
    """
    Download a remote binary file using streaming to minimize memory footprint.
    Reports progress via callback for GUI integration.

    Args:
        url: Direct URL to the binary asset.
        dest_path: Local filesystem path to save the binary.
        progress_callback: Optional function receiving a float (0.0 to 100.0).

    Returns:
        Tuple of (Success Status, Message).
    """
    headers = {"User-Agent": USER_AGENT}
    logger.info(f"Starting background download: {url}")

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=TIMEOUT)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)

                    if progress_callback and total_size > 0:
                        percent = (downloaded_size / total_size) * 100
                        progress_callback(percent)

        logger.info(f"Binary downloaded successfully to: {dest_path}")
        return True, "Download complete"

    except requests.exceptions.RequestException as e:
        err_msg = f"Download failed: {str(e)}"
        logger.error(err_msg)
        return False, err_msg
    except OSError as e:
        err_msg = f"Filesystem error during download: {str(e)}"
        logger.error(err_msg)
        return False, err_msg


# -----------------------------------------------------------------------------
# Public API: Communication Channels
# -----------------------------------------------------------------------------
def submit_feedback(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Submit user feedback or feature requests via Formspree."""
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Feedback")


def submit_error_report(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Submit technical crash reports and stack traces."""
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Error Report")


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------
def _is_newer(current: str, latest: str) -> bool:
    """Perform a semantic version comparison (Major.Minor.Patch)."""
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

    except (ValueError, AttributeError):
        return False


def _secure_post(url: str, data: Dict[str, Any], context: str) -> Tuple[bool, str]:
    """Generic wrapper for POST requests with security validation."""
    if not url:
        return False, "Endpoint not configured"

    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
        if response.status_code in (200, 201):
            logger.info(f"{context} submitted successfully.")
            return True, "Success"

        return False, f"Server rejected request ({response.status_code})"
    except requests.exceptions.RequestException as e:
        return False, str(e)