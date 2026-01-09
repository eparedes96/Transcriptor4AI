from __future__ import annotations

"""
Standalone Updater Utility for Transcriptor4AI.

This script is independent of the transcriptor4ai package to avoid
import shadowing conflicts. It handles the binary swap lifecycle:
1. Process termination wait.
2. File replacement with rollback safety.
3. Application restart.
"""

import os
import sys
import time
import subprocess
import argparse
import logging

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
        time.sleep(0.5)
    return False


def run_update(old_exe: str, new_exe: str, pid: int) -> None:
    """
    Perform the file swap and restart the application.

    Args:
        old_exe: Path to the current executable to be replaced.
        new_exe: Path to the new version downloaded.
        pid: PID of the running application to wait for.
    """

    # 1. Wait for the main app to close
    if not wait_for_pid(pid):
        logger.error("Timeout waiting for main application to close.")
        sys.exit(1)

    # 2. Perform the swap
    try:
        if not os.path.exists(new_exe):
            logger.error(f"New version not found at: {new_exe}")
            sys.exit(1)

        # Buffer time for OS file locks to release
        time.sleep(1)

        logger.info(f"Updating {old_exe}...")

        # Rename strategy for atomic-like swap and rollback support
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

    # 3. Restart the application
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

    args = parser.parse_args()

    # Safety delay
    time.sleep(0.5)

    run_update(args.old, args.new, args.pid)
    logger.info("Updater lifecycle finished.")


if __name__ == "__main__":
    main()