from __future__ import annotations

"""
Network Communication Infrastructure.

Handles external HTTP interactions including:
- Version checking via GitHub API.
- Seamless OTA binary downloading.
- Secure transmission of telemetry and error reports.
"""

import hashlib
import logging
import os
from typing import Any, Dict, Optional, Tuple, Callable

import requests

logger = logging.getLogger(__name__)

# Constants
GITHUB_OWNER = "eparedes96"
GITHUB_REPO = "Transcriptor4AI"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
FORMSPREE_ENDPOINT = "https://formspree.io/f/xnjjazrl"
TIMEOUT = 10
USER_AGENT = "Transcriptor4AI-Client/2.0.0"
CHUNK_SIZE = 8192


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

def check_for_updates(current_version: str) -> Dict[str, Any]:
    """
    Check GitHub for a newer release compared to the current version.
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

        if _is_newer(current_version, latest_tag):
            result.update({
                "has_update": True,
                "latest_version": latest_tag,
                "download_url": data.get("html_url", ""),
                "changelog": data.get("body", "No changelog provided.")
            })

            for asset in data.get("assets", []):
                asset_name = asset.get("name", "").lower()
                download_url = asset.get("browser_download_url")

                if asset_name.endswith(".exe") or asset_name.endswith(".zip"):
                    result["binary_url"] = download_url
                elif asset_name.endswith(".sha256"):
                    _fetch_checksum(download_url, headers, result)
        else:
            logger.info("Status: Application is up to date.")

    except requests.exceptions.RequestException as e:
        msg = f"GitHub API update check failed: {e}"
        logger.error(msg)
        result["error"] = msg

    return result


def download_binary_stream(
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
) -> Tuple[bool, str]:
    """Stream a file download to disk with progress reporting."""
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
        return True, "Download complete"
    except Exception as e:
        return False, str(e)


def submit_feedback(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Submit user feedback via secure POST."""
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Feedback")


def submit_error_report(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Submit crash report via secure POST."""
    return _secure_post(FORMSPREE_ENDPOINT, payload, "Error Report")


# -----------------------------------------------------------------------------
# PRIVATE HELPERS
# -----------------------------------------------------------------------------

# ------ INICIO DE MODIFICACIÓN: EXTRACCIÓN DE LOGICA DE MANAGER ------
# Se han eliminado las clases UpdateStatus y UpdateManager de este archivo.
# Se mantienen los helpers de bajo nivel para uso interno.
# ------ FIN DE MODIFICACIÓN: EXTRACCIÓN DE LOGICA DE MANAGER ------

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
    except Exception:
        pass


def _secure_post(url: str, data: Dict[str, Any], context: str) -> Tuple[bool, str]:
    """Execute a POST request with error handling."""
    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=TIMEOUT)
        return response.status_code in (200, 201), "Success"
    except Exception as e:
        return False, str(e)


def _calculate_sha256(file_path: str) -> str:
    """Calculate SHA-256 hash of a file for integrity check."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return ""