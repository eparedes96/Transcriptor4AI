from __future__ import annotations

"""
Standalone Updater Utility for Transcriptor4AI.

This script is independent of the transcriptor4ai package to avoid
import shadowing conflicts. It handles the binary swap lifecycle:
1. Process termination wait.
2. Integrity verification (SHA-256 Checksum).
3. File replacement with rollback safety.
4. Application restart.
"""

import os
import sys
import time
import subprocess
import argparse
import logging
import hashlib
from typing import Optional

# Configure basic logging for the standalone script
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("updater")


def wait_for_pid(pid: int, timeout: int = 30) -> bool:
    """
    Wait for a process ID to terminate.

    Args:
        pid: Process ID to monitor.
        timeout: Maximum seconds to wait.

    Returns:
        True if the process terminated, False on timeout.
    """
    logger.info(f"Waiting for process {pid} to exit...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        except Exception:
            return True
        time.sleep(0.5)
    return False


def calculate_sha256(file_path: str) -> str:
    """
    Calculate SHA-256 hash of a file using chunked reading for memory efficiency.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate hash for {file_path}: {e}")
        return ""


def run_update(old_exe: str, new_exe: str, pid: int, expected_sha256: Optional[str] = None) -> None:
    """
    Perform integrity check, file swap, and restart the application.

    Args:
        old_exe: Path to the current executable to be replaced.
        new_exe: Path to the new version downloaded.
        pid: PID of the running application to wait for.
        expected_sha256: Optional checksum to verify binary integrity.
    """

    # 1. Wait for the main app to close
    if not wait_for_pid(pid):
        logger.error("Timeout waiting for main application to close. Aborting update.")
        sys.exit(1)

    # 2. Integrity Verification
    if expected_sha256:
        logger.info("Verifying binary integrity...")
        actual_sha256 = calculate_sha256(new_exe)
        if actual_sha256.lower() != expected_sha256.lower():
            logger.error("INTEGRITY CRITICAL FAILURE: Checksum mismatch!")
            logger.error(f"Expected: {expected_sha256}")
            logger.error(f"Actual:   {actual_sha256}")
            sys.exit(1)
        logger.info("Integrity check passed.")

    # 3. Perform the swap
    try:
        if not os.path.exists(new_exe):
            logger.error(f"New version not found at: {new_exe}")
            sys.exit(1)

        time.sleep(1)

        logger.info(f"Updating {old_exe}...")

        backup_exe = old_exe + ".old"
        if os.path.exists(backup_exe):
            try:
                os.remove(backup_exe)
            except OSError:
                pass

        os.rename(old_exe, backup_exe)

        try:
            os.rename(new_exe, old_exe)
            logger.info("Update applied successfully.")
        except Exception as e:
            logger.error(f"Failed to move new executable: {e}. Rolling back...")
            if os.path.exists(backup_exe):
                os.rename(backup_exe, old_exe)
            raise

        # Cleanup backup
        try:
            if os.path.exists(backup_exe):
                os.remove(backup_exe)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Critical error during swap: {e}")
        sys.exit(1)

    # 4. Restart the application
    try:
        logger.info(f"Restarting application: {old_exe}")
        if sys.platform == "win32":
            os.startfile(old_exe)
        else:
            subprocess.Popen([old_exe], start_new_session=True)
    except Exception as e:
        logger.error(f"Failed to restart application: {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for the updater CLI."""
    parser = argparse.ArgumentParser(description="Transcriptor4AI Sidecar Updater")
    parser.add_argument("--pid", type=int, required=True, help="PID of the process to wait for")
    parser.add_argument("--old", type=str, required=True, help="Path to the current executable")
    parser.add_argument("--new", type=str, required=True, help="Path to the new executable")
    parser.add_argument("--sha256", type=str, help="Expected SHA-256 hash for integrity verification")

    args = parser.parse_args()

    time.sleep(0.5)

    run_update(args.old, args.new, args.pid, args.sha256)
    logger.info("Updater lifecycle finished.")


if __name__ == "__main__":
    main()