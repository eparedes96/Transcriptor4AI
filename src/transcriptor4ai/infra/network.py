from __future__ import annotations

"""
Network Communication Infrastructure.

Orchestrates external HTTP interactions, including remote version
synchronization via GitHub API, binary stream acquisition for OTA
updates, real-time pricing synchronization, and secure transmission 
of telemetry and crash reports.
"""

import hashlib
import logging
from typing import Any, Callable, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# NETWORK CONSTANTS
# -----------------------------------------------------------------------------

GITHUB_OWNER = "eparedes96"
GITHUB_REPO = "Transcriptor4AI"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
FORMSPREE_ENDPOINT = "https://formspree.io/f/xnjjazrl"
TIMEOUT = 10
PRICING_TIMEOUT = 2
USER_AGENT = "Transcriptor4AI-Client/2.1.0"
CHUNK_SIZE = 8192

# -----------------------------------------------------------------------------
# PUBLIC API: REMOTE SYNCHRONIZATION
# -----------------------------------------------------------------------------

def check_for_updates(current_version: str) -> Dict[str, Any]:
    """
    Query the GitHub API to detect newer application releases.

    Args:
        current_version: Local application version string.

    Returns:
        Dict[str, Any]: Metadata containing update status, binary URLs,
                        and cryptographic checksums.
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
    logger.info(f"Checking for remote updates... (Current: v{current_version})")

    try:
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        latest_tag = data.get("tag_name", "").lstrip("v")

        if _is_newer(current_version, latest_tag):
            result.update({
                "has_update": True,
                "latest_version": latest_tag,
                "download_url": data.get("html_url", ""),
                "changelog": data.get("body", "No changelog provided.")
            })

            # Resolve binary asset and checksum
            for asset in data.get("assets", []):
                asset_name = asset.get("name", "").lower()
                download_url = asset.get("browser_download_url")

                if asset_name.endswith(".exe") or asset_name.endswith(".zip"):
                    result["binary_url"] = download_url
                elif asset_name.endswith(".sha256"):
                    _fetch_checksum(download_url, headers, result)
        else:
            logger.info("Application is currently up to date.")

    except requests.exceptions.RequestException as e:
        msg = f"GitHub API communication failure: {e}"
        logger.error(msg)
        result["error"] = msg

    return result


def fetch_pricing_data(url: str) -> Optional[Dict[str, Any]]:
    """
    Synchronize model pricing data from a remote repository.

    Implements a strict timeout to ensure that network latency does not
    degrade the application startup experience.

    Args:
        url: Remote URL pointing to the pricing JSON resource.

    Returns:
        Optional[Dict[str, Any]]: Fresh pricing data or None if the request fails.
    """
    headers = {"User-Agent": USER_AGENT}
    logger.debug(f"Syncing live pricing from: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=PRICING_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            logger.warning("Network: Received malformed pricing data (not a dictionary).")
            return None

        logger.info("Network: Live pricing data synchronized successfully.")
        return data

    except requests.exceptions.Timeout:
        logger.warning(f"Network: Pricing sync timed out after {PRICING_TIMEOUT}s.")
    except Exception as e:
        logger.error(f"Network: Unexpected error during pricing sync: {e}")

    return None


def download_binary_stream(
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
) -> Tuple[bool, str]:
    """
    Acquire a remote binary using buffered streaming.

    Args:
        url: Direct download URL.
        dest_path: Local path to persist the binary.
        progress_callback: Optional hook for percentage reporting.

    Returns:
        Tuple[bool, str]: (Success flag, Status message).
    """
    headers = {"User-Agent": USER_AGENT}
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
        return True, "Download completed successfully."
    except Exception as e:
        return False, str(e)

# -----------------------------------------------------------------------------
# PUBLIC API: TELEMETRY & FEEDBACK
# -----------------------------------------------------------------------------

def submit_feedback(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmit user feedback to the centralized collection endpoint.

    Args:
        payload: Metadata and feedback content.

    Returns:
        Tuple[bool, str]: Operation result status.
    """
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Feedback")


def submit_error_report(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Transmit critical crash data for diagnostic analysis.

    Args:
        payload: Stack trace and environment metadata.

    Returns:
        Tuple[bool, str]: Operation result status.
    """
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Error Report")

# -----------------------------------------------------------------------------
# PRIVATE HELPERS
# -----------------------------------------------------------------------------

def _is_newer(current: str, latest: str) -> bool:
    """Perform semantic version comparison."""
    try:
        def parse(v: str) -> Tuple[int, ...]:
            return tuple(int("".join(filter(str.isdigit, p)) or 0) for p in v.split("."))

        return parse(latest) > parse(current)
    except (ValueError, AttributeError):
        return False


def _fetch_checksum(url: str, headers: Dict[str, str], result_dict: Dict[str, Any]) -> None:
    """Acquire and extract SHA256 string from a remote sidecar file."""
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            result_dict["sha256"] = resp.text.split()[0].strip()
    except Exception:
        pass


def _secure_post(url: str, data: Dict[str, Any], context: str) -> Tuple[bool, str]:
    """Execute a secure JSON POST request with robust exception handling."""
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
        return response.status_code in (200, 201), "Success"
    except Exception as e:
        return False, str(e)


def _calculate_sha256(file_path: str) -> str:
    """Compute SHA-256 digest for local file integrity verification."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return ""