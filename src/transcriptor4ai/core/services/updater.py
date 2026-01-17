from __future__ import annotations

"""
Update Management Service.

Orchestrates the background lifecycle for application updates. Handles 
state transitions between version checking, binary acquisition via 
streaming downloads, and cryptographic integrity verification before 
flagging an update as ready for installation.
"""

import logging
import os
import shutil
from enum import Enum
from typing import Any, Dict

from transcriptor4ai.infra.fs import get_user_data_dir
from transcriptor4ai.infra import network

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# UPDATE STATE DEFINITIONS
# -----------------------------------------------------------------------------

class UpdateStatus(Enum):
    """Enumeration of the background update process states."""
    IDLE = "IDLE"
    CHECKING = "CHECKING"
    DOWNLOADING = "DOWNLOADING"
    READY = "READY"
    ERROR = "ERROR"

# -----------------------------------------------------------------------------
# UPDATE MANAGER SERVICE
# -----------------------------------------------------------------------------

class UpdateManager:
    """
    Stateful manager for the Over-The-Air (OTA) update cycle.

    Designed to run asynchronously. It coordinates between the network
    infrastructure layer and the local filesystem to prepare validated
    binaries for the sidecar updater utility.
    """

    def __init__(self) -> None:
        """Initialize the update manager with default idle state and paths."""
        self._status = UpdateStatus.IDLE
        self._update_info: Dict[str, Any] = {}
        self._temp_dir = os.path.join(get_user_data_dir(), "updates")
        self._pending_binary_path: str = ""

    @property
    def status(self) -> UpdateStatus:
        """Get the current operational status of the update cycle."""
        return self._status

    @property
    def update_info(self) -> Dict[str, Any]:
        """Get metadata regarding the latest discovered version."""
        return self._update_info

    @property
    def pending_path(self) -> str:
        """Get the absolute path to the verified downloaded binary."""
        return self._pending_binary_path

    def run_silent_cycle(self, current_version: str) -> None:
        """
        Execute a complete non-interactive update check and download.

        Coordinates filesystem preparation, remote version comparison,
        stream-based downloading, and SHA-256 integrity verification.

        Args:
            current_version: Semantic version of the running application.
        """
        self._status = UpdateStatus.CHECKING
        try:
            # 1. Clean staging environment
            if os.path.exists(self._temp_dir):
                try:
                    shutil.rmtree(self._temp_dir)
                except OSError:
                    pass
            os.makedirs(self._temp_dir, exist_ok=True)

            # 2. Remote synchronization
            res = network.check_for_updates(current_version)
            if not res.get("has_update") or not res.get("binary_url"):
                self._status = UpdateStatus.IDLE
                return

            # 3. Binary acquisition
            self._status = UpdateStatus.DOWNLOADING
            self._update_info = res
            latest_version = res.get("latest_version", "unknown")
            dest_path = os.path.join(self._temp_dir, f"transcriptor4ai_v{latest_version}.exe")

            success, msg = network.download_binary_stream(res["binary_url"], dest_path)
            if not success:
                logger.error(f"Background update download failed: {msg}")
                self._status = UpdateStatus.ERROR
                return

            # 4. Cryptographic integrity check
            expected_sha = res.get("sha256")
            if expected_sha:
                actual_sha = network._calculate_sha256(dest_path)
                if actual_sha.lower() != expected_sha.lower():
                    logger.error("Update integrity breach: Checksum mismatch. Discarding binary.")
                    self._status = UpdateStatus.ERROR
                    return

            # 5. Readiness transition
            self._pending_binary_path = dest_path
            self._status = UpdateStatus.READY
            logger.info(f"Update v{latest_version} is verified and ready for deployment.")

        except Exception as e:
            logger.error(f"Critical failure in update service lifecycle: {e}")
            self._status = UpdateStatus.ERROR