from __future__ import annotations

"""
Standalone Updater Utility for Transcriptor4AI.

This script handles the file swap mechanism:
1. Waits for the main application process to exit.
2. Replaces the old executable with the new downloaded version.
3. Restarts the application.
"""

import os
import sys
import time
import subprocess
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("updater")


def wait_for_pid(pid: int, timeout: int = 30):
    """Wait for a process ID to terminate."""
    logger.info(f"Waiting for process {pid} to exit...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            os.kill(pid, 0)
        except OSError:
            return True
        time.sleep(0.5)
    return False


def run_update(old_exe: str, new_exe: str, pid: int):
    """Perform the file swap and restart."""

    # 1. Wait for the main app to close
    if not wait_for_pid(pid):
        logger.error("Timeout waiting for main application to close.")
        sys.exit(1)

    # 2. Perform the swap
    try:
        if not os.path.exists(new_exe):
            logger.error(f"New version not found at: {new_exe}")
            sys.exit(1)

        # On Windows, we often need to wait a fraction longer for locks to release
        time.sleep(1)

        logger.info(f"Updating {old_exe}...")

        # We use a rename strategy to allow rollback if possible
        backup_exe = old_exe + ".old"
        if os.path.exists(backup_exe):
            os.remove(backup_exe)

        os.rename(old_exe, backup_exe)
        os.rename(new_exe, old_exe)

        logger.info("Update applied successfully.")

        # Remove backup
        try:
            os.remove(backup_exe)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Failed to apply update: {e}")
        if os.path.exists(old_exe + ".old") and not os.path.exists(old_exe):
            os.rename(old_exe + ".old", old_exe)
        sys.exit(1)

    # 3. Restart the application
    try:
        logger.info(f"Restarting application: {old_exe}")
        if sys.platform == "win32":
            os.startfile(old_exe)
        else:
            subprocess.Popen([old_exe])
    except Exception as e:
        logger.error(f"Failed to restart application: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Transcriptor4AI Sidecar Updater")
    parser.add_argument("--pid", type=int, required=True, help="PID of the process to wait for")
    parser.add_argument("--old", type=str, required=True, help="Path to the current executable")
    parser.add_argument("--new", type=str, required=True, help="Path to the new executable")

    args = parser.parse_args()

    # Give the OS a moment to initialize the updater process
    time.sleep(0.5)

    run_update(args.old, args.new, args.pid)
    logger.info("Updater finished.")


if __name__ == "__main__":
    main()