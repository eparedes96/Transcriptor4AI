from __future__ import annotations

"""
GitHub Release Client Adapter.

Handles interaction with the GitHub Releases API to perform Over-The-Air (OTA)
update checks. Manages version comparison, binary asset resolution, and
secure stream-based downloading of updates.
"""

import logging
from typing import Any, Callable, Dict, Optional, Tuple

import requests

from transcriptor4ai.domain.ports.network_port import IUpdateClient
from transcriptor4ai.infrastructure.network.common import (
    CHUNK_SIZE,
    DEFAULT_TIMEOUT,
    USER_AGENT,
)
from transcriptor4ai.shared.versioning import is_newer

logger = logging.getLogger(__name__)

# ==============================================================================
# GITHUB RELEASE CLIENT
# ==============================================================================
class GithubReleaseClient(IUpdateClient):
    """
    Network adapter for the GitHub Releases API.
    """

    GITHUB_OWNER = "eparedes96"
    GITHUB_REPO = "Transcriptor4AI"
    API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

    def check_for_updates(self, current_version: str) -> Dict[str, Any]:
        """
        Query the GitHub API to detect newer application releases.

        Compares the semantic version of the running app against the latest tag
        available on the repository.

        Args:
            current_version: The semantic version string of the local app (e.g., "2.1.0").

        Returns:
            Dict[str, Any]: A dictionary containing update status, metadata,
                            and download URLs.
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
        logger.info(f"UpdateClient: Checking remote versions... (Current: v{current_version})")

        try:
            response = requests.get(
                self.API_URL,
                headers=headers,
                timeout=DEFAULT_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()

            latest_tag = data.get("tag_name", "").lstrip("v")

            if is_newer(current_version, latest_tag):
                result.update({
                    "has_update": True,
                    "latest_version": latest_tag,
                    "download_url": data.get("html_url", ""),
                    "changelog": data.get("body", "No changelog provided.")
                })

                # Locate the correct binary asset
                for asset in data.get("assets", []):
                    asset_name = asset.get("name", "").lower()
                    download_url = asset.get("browser_download_url")

                    if asset_name.endswith(".exe") or asset_name.endswith(".zip"):
                        result["binary_url"] = download_url
                    elif asset_name.endswith(".sha256"):
                        # Fetch sidecar checksum file for integrity verification
                        self._fetch_checksum(download_url, headers, result)
            else:
                logger.info("UpdateClient: Application is up to date.")

        except requests.exceptions.RequestException as e:
            msg = f"GitHub API communication failure: {e}"
            logger.error(msg)
            result["error"] = msg

        return result

    def download_binary_stream(
            self,
            url: str,
            dest_path: str,
            progress_callback: Optional[Callable[[float], None]] = None
    ) -> Tuple[bool, str]:
        """
        Acquire a remote binary using buffered streaming.

        Prevents high memory usage by writing chunks directly to disk.

        Args:
            url: Direct URL to the asset.
            dest_path: Local path where the file will be saved.
            progress_callback: Optional function receiving percentage (0.0-100.0).

        Returns:
            Tuple[bool, str]: (Success flag, Status message).
        """
        headers = {"User-Agent": USER_AGENT}
        try:
            with requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=DEFAULT_TIMEOUT
            ) as response:
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0

                with open(dest_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            if progress_callback and total_size > 0:
                                percentage = (downloaded_size / total_size) * 100
                                progress_callback(percentage)

            return True, "Download completed successfully."

        except Exception as e:
            logger.error(f"UpdateClient: Download failed: {e}")
            return False, str(e)

    # ==========================================================================
    # INTERNAL HELPERS
    # ==========================================================================

    @staticmethod
    def _fetch_checksum(
            url: str,
            headers: Dict[str, str],
            result_dict: Dict[str, Any]
    ) -> None:
        """
        Acquire and extract SHA256 string from a remote sidecar file.
        """
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                # Assumes format: "hash  filename" or just "hash"
                result_dict["sha256"] = resp.text.split()[0].strip()
        except Exception as e:
            logger.debug(f"UpdateClient: Failed to fetch checksum: {e}")