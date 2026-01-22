from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional, Tuple

import requests

from transcriptor4ai.infra.network.common import CHUNK_SIZE, DEFAULT_TIMEOUT, USER_AGENT

logger = logging.getLogger(__name__)

GITHUB_OWNER = "eparedes96"
GITHUB_REPO = "Transcriptor4AI"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

def check_for_updates(current_version: str) -> Dict[str, Any]:
    """Query the GitHub API to detect newer application releases."""
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
        response = requests.get(GITHUB_API_URL, headers=headers, timeout=DEFAULT_TIMEOUT)
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
            logger.info("Application is currently up to date.")

    except requests.exceptions.RequestException as e:
        msg = f"GitHub API communication failure: {e}"
        logger.error(msg)
        result["error"] = msg

    return result

def download_binary_stream(
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
) -> Tuple[bool, str]:
    """Acquire a remote binary using buffered streaming."""
    headers = {"User-Agent": USER_AGENT}
    try:
        with requests.get(url, headers=headers, stream=True, timeout=DEFAULT_TIMEOUT) as response:
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