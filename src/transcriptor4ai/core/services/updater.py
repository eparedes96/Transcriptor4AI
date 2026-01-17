from __future__ import annotations

"""
Update Management Service.

Orchestrates the high-level update lifecycle (checking, downloading, and 
verifying) by coordinating between network infrastructure and local 
filesystem state.
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
# DOMAIN ENUMS & CLASSES
# -----------------------------------------------------------------------------

class UpdateStatus(Enum):
    """Represents the possible states of the update background process."""
    IDLE = "IDLE"
    CHECKING = "CHECKING"
    DOWNLOADING = "DOWNLOADING"
    READY = "READY"
    ERROR = "ERROR"


class UpdateManager:
    """
    Manages the background update lifecycle: Check -> Download -> Verify -> Ready.
    Designed to run in a daemon thread without blocking the UI.
    """

    def __init__(self) -> None:
        self._status = UpdateStatus.IDLE
        self._update_info: Dict[str, Any] = {}
        self._temp_dir = os.path.join(get_user_data_dir(), "updates")
        self._pending_binary_path: str = ""

    @property
    def status(self) -> UpdateStatus:
        """Returns the current status of the manager."""
        return self._status

    @property
    def update_info(self) -> Dict[str, Any]:
        """Returns metadata about the latest update found."""
        return self._update_info

    @property
    def pending_path(self) -> str:
        """Returns the local path to the downloaded binary."""
        return self._pending_binary_path

    def run_silent_cycle(self, current_version: str) -> None:
        """
        Execute the full update check and download cycle silently.

        This high-level method coordinates low-level network calls and
        handles filesystem preparation and integrity verification.
        """
        self._status = UpdateStatus.CHECKING
        try:
            # Prepare clean update directory
            if os.path.exists(self._temp_dir):
                try:
                    shutil.rmtree(self._temp_dir)
                except OSError:
                    pass
            os.makedirs(self._temp_dir, exist_ok=True)

            # 1. Check for updates
            res = network.check_for_updates(current_version)
            if not res.get("has_update") or not res.get("binary_url"):
                self._status = UpdateStatus.IDLE
                return

            # 2. Download binary
            self._status = UpdateStatus.DOWNLOADING
            self._update_info = res
            latest_version = res.get("latest_version", "unknown")
            dest_path = os.path.join(self._temp_dir, f"transcriptor4ai_v{latest_version}.exe")

            success, msg = network.download_binary_stream(res["binary_url"], dest_path)
            if not success:
                logger.error(f"Silent download failed: {msg}")
                self._status = UpdateStatus.ERROR
                return

            # 3. Verify Integrity
            expected_sha = res.get("sha256")
            if expected_sha:
                # We reuse the helper from network as it's a utility function
                actual_sha = network._calculate_sha256(dest_path)
                if actual_sha.lower() != expected_sha.lower():
                    logger.error("Silent update checksum mismatch. Discarding.")
                    self._status = UpdateStatus.ERROR
                    return

            self._pending_binary_path = dest_path
            self._status = UpdateStatus.READY
            logger.info("Silent update ready for install.")

        except Exception as e:
            logger.error(f"Update cycle crashed: {e}")
            self._status = UpdateStatus.ERROR