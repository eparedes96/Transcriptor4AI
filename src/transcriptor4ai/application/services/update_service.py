from __future__ import annotations

"""
Update Lifecycle Management Service.

Orchestrates the background process for application updates. Handles state 
transitions from version discovery to binary acquisition and cryptographic 
verification. Delegates technical IO and archive management to infrastructure 
adapters.
"""

import logging
import os
import shutil
from enum import Enum
from typing import Any, Dict

# 1. PORTS & ADAPTERS: Injected via constructor to maintain Hexagonal integrity
from transcriptor4ai.domain.ports.network_port import IUpdateClient
from transcriptor4ai.domain.ports.system_port import IFileSystem

logger = logging.getLogger(__name__)


# ==============================================================================
# UPDATE STATE DEFINITIONS
# ==============================================================================

class UpdateStatus(Enum):
    """Enumeration of the background update process states."""
    IDLE = "IDLE"
    CHECKING = "CHECKING"
    DOWNLOADING = "DOWNLOADING"
    READY = "READY"
    ERROR = "ERROR"


# ==============================================================================
# UPDATE MANAGER SERVICE
# ==============================================================================

class UpdateManager:
    """
    Stateful manager for the Over-The-Air (OTA) update cycle.

    This service is designed for asynchronous execution within a background
    thread to prevent GUI blocking.
    """

    def __init__(
            self,
            network_client: IUpdateClient,
            fs_adapter: IFileSystem
    ) -> None:
        """
        Initialize the manager with injected domain ports.
        """
        self._network = network_client
        self._fs = fs_adapter

        self._status = UpdateStatus.IDLE
        self._update_info: Dict[str, Any] = {}
        self._temp_dir = os.path.join(self._fs.get_user_data_dir(), "updates")
        self._pending_binary_path: str = ""

    # --------------------------------------------------------------------------
    # PUBLIC PROPERTIES (UI OBSERVABLES)
    # --------------------------------------------------------------------------

    @property
    def status(self) -> UpdateStatus:
        """Get current lifecycle status."""
        return self._status

    @property
    def update_info(self) -> Dict[str, Any]:
        """Get metadata of the latest discovered version."""
        return self._update_info

    @property
    def pending_path(self) -> str:
        """Get the absolute path to the verified local binary."""
        return self._pending_binary_path

    # --------------------------------------------------------------------------
    # CORE UPDATE CYCLE
    # --------------------------------------------------------------------------

    def run_silent_cycle(self, current_version: str) -> None:
        """
        Execute a complete non-interactive update check and download.

        Coordinates environment preparation, remote discovery, and verification.
        Delegates technical file handling to the infrastructure layer.

        Args:
            current_version: Semantic version of the running application.
        """
        self._status = UpdateStatus.CHECKING

        try:
            # 1. PREPARE: Clean and recreate staging environment
            if os.path.exists(self._temp_dir):
                try:
                    # shutil.rmtree is used here for directory-level cleanup
                    shutil.rmtree(self._temp_dir)
                except OSError as e:
                    logger.warning(f"UpdateManager: Staging cleanup partial: {e}")

            self._fs.safe_mkdir(self._temp_dir)

            # 2. SYNC: Query remote authority for newer releases
            res = self._network.check_for_updates(current_version)
            if not res.get("has_update") or not res.get("binary_url"):
                self._status = UpdateStatus.IDLE
                return

            # 3. ACQUISITION: Initiate stream-based binary download
            self._status = UpdateStatus.DOWNLOADING
            self._update_info = res
            latest_version = res.get("latest_version", "unknown")

            binary_url = res["binary_url"]
            is_zip = binary_url.lower().endswith(".zip")
            download_ext = ".zip" if is_zip else ".exe"
            filename = f"transcriptor4ai_v{latest_version}{download_ext}"
            download_path = os.path.join(self._temp_dir, filename)

            success, msg = self._network.download_binary_stream(binary_url, download_path)
            if not success:
                logger.error(f"UpdateManager: Download failed: {msg}")
                self._status = UpdateStatus.ERROR
                return

            # 4. INTEGRITY: Verify cryptographic checksum (SHA-256)
            expected_sha = res.get("sha256")
            if expected_sha:
                from transcriptor4ai.shared.hashing import calculate_sha256
                actual_sha = calculate_sha256(download_path)

                if actual_sha.lower() != expected_sha.lower():
                    logger.error("UpdateManager: Integrity breach. Checksum mismatch.")
                    self._status = UpdateStatus.ERROR
                    return
                logger.debug("UpdateManager: Binary integrity verified.")

            # 5. DEPLOYMENT: Extract package or resolve direct binary path
            # Logic delegated to FileSystemAdapter to maintain Separation of Concerns
            if is_zip:
                extracted_path = self._fs.unpack_executable_from_zip(
                    download_path,
                    self._temp_dir
                )
                if not extracted_path:
                    self._status = UpdateStatus.ERROR
                    return
                self._pending_binary_path = extracted_path

                # Cleanup original zip archive via adapter
                self._fs.delete_file(download_path)
            else:
                self._pending_binary_path = download_path

            # 6. FINALIZATION: Mark update as ready for swap
            self._status = UpdateStatus.READY
            logger.info(f"UpdateManager: v{latest_version} verified and staged.")

        except Exception as e:
            logger.error(f"UpdateManager: Critical failure in lifecycle: {e}", exc_info=True)
            self._status = UpdateStatus.ERROR