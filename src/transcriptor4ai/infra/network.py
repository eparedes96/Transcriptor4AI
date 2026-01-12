from __future__ import annotations

"""
Network Communication Infrastructure.

Handles external HTTP interactions including:
- Version checking via GitHub API.
- Seamless OTA binary downloading.
- Secure transmission of telemetry and error reports.
"""

import logging
from typing import Any, Dict, Optional, Tuple, Callable

import requests

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
GITHUB_OWNER = "eparedes96"
GITHUB_REPO = "Transcriptor4AI"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

FORMSPREE_ENDPOINT = "https://formspree.io/f/xnjjazrl"

TIMEOUT = 10
USER_AGENT = "Transcriptor4AI-Client/1.6.0"
CHUNK_SIZE = 8192


# -----------------------------------------------------------------------------
# Public API: Version Checking & Updates
# -----------------------------------------------------------------------------
def check_for_updates(current_version: str) -> Dict[str, Any]:
    """
    Check GitHub for a newer release compared to the current version.

    Args:
        current_version: The semantic version string of the running app.

    Returns:
        Dict containing update metadata (has_update, binary_url, etc.).
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
            result.update({
                "has_update": True,
                "latest_version": latest_tag,
                "download_url": data.get("html_url", ""),
                "changelog": data.get("body", "No changelog provided.")
            })

            # Identify Assets
            assets = data.get("assets", [])
            for asset in assets:
                asset_name = asset.get("name", "").lower()
                download_url = asset.get("browser_download_url")

                if asset_name.endswith(".exe"):
                    result["binary_url"] = download_url
                    logger.info(f"Direct binary asset detected: {asset_name}")

                elif asset_name.endswith(".sha256"):
                    _fetch_checksum(download_url, headers, result)

            # Safety Check
            if result["has_update"] and not result["binary_url"]:
                logger.warning("No direct .exe asset found. Background OTA disabled.")
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
    Stream a file download to disk with progress reporting.

    Args:
        url: The URL to download.
        dest_path: Local path to save the file.
        progress_callback: Function accepting a float (0-100) for progress.

    Returns:
        Tuple (Success, Message).
    """
    headers = {"User-Agent": USER_AGENT}
    logger.info(f"Starting background download: {url}")

    try:
        with requests.get(url, headers=headers, stream=True, timeout=TIMEOUT) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback((downloaded_size / total_size) * 100)

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
# Public API: Telemetry
# -----------------------------------------------------------------------------
def submit_feedback(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Submit user feedback via secure POST."""
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Feedback")


def submit_error_report(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Submit crash report via secure POST."""
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Error Report")


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------
def _is_newer(current: str, latest: str) -> bool:
    """Compare two semantic version strings."""
    try:
        def parse(v: str) -> Tuple[int, ...]:
            return tuple(int("".join(filter(str.isdigit, p)) or 0) for p in v.split("."))

        return parse(latest) > parse(current)
    except (ValueError, AttributeError):
        return False


def _fetch_checksum(url: str, headers: Dict[str, str], result_dict: Dict[str, Any]) -> None:
    """Helper to fetch and store SHA256 checksum."""
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            result_dict["sha256"] = resp.text.split()[0].strip()
            logger.info(f"Integrity metadata retrieved: {result_dict['sha256']}")
    except Exception as e:
        logger.warning(f"Failed to retrieve checksum asset: {e}")


def _secure_post(url: str, data: Dict[str, Any], context: str) -> Tuple[bool, str]:
    """Execute a POST request with error handling."""
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