from __future__ import annotations

"""
Standalone Binary Swapper (Sidecar Utility).

Provides a fail-safe update mechanism decoupled from the main application 
package. Executes the binary replacement lifecycle: process synchronization, 
checksum verification, and atomic file rotation with rollback capabilities.
"""

import argparse
import hashlib
import logging
import os
import subprocess
import sys
import time
from typing import Optional

# Standalone logging configuration (Entrypoint owned)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("updater")


# ==============================================================================
# PROCESS AND INTEGRITY HELPERS
# ==============================================================================

def wait_for_pid(pid: int, timeout: int = 30) -> bool:
    """
    Monitor a specific Process ID until termination or timeout.

    Args:
        pid: Target process identifier.
        timeout: Maximum duration in seconds to wait for exit.

    Returns:
        bool: True if process terminated, False if timeout exceeded.
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
    Compute SHA-256 digest using buffered reading for memory efficiency.

    Args:
        file_path: Target file path for hash calculation.

    Returns:
        str: Hexadecimal representation of the SHA-256 checksum.
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


# ==============================================================================
# CORE UPDATE LIFECYCLE
# ==============================================================================

def run_update(
        old_exe: str,
        new_exe: str,
        pid: int,
        expected_sha256: Optional[str] = None
) -> None:
    """
    Perform an atomic binary swap and application restart.

    Implements a backup-rename-deploy strategy to allow manual recovery
    if the operating system file lock prevents direct replacement.

    Args:
        old_exe: Current executable path to be replaced.
        new_exe: New binary path to be deployed.
        pid: Process identifier of the caller to synchronize termination.
        expected_sha256: Integrity verification string.
    """
    # Phase 1: Termination Synchronization
    if not wait_for_pid(pid):
        logger.error("Timeout waiting for main application to close. Aborting update.")
        sys.exit(1)

    # Phase 2: Cryptographic Verification
    if expected_sha256:
        logger.info("Verifying binary integrity...")
        actual_sha256 = calculate_sha256(new_exe)
        if actual_sha256.lower() != expected_sha256.lower():
            logger.error("INTEGRITY CRITICAL FAILURE: Checksum mismatch!")
            logger.error(f"Expected: {expected_sha256}")
            logger.error(f"Actual:   {actual_sha256}")
            sys.exit(1)
        logger.info("Integrity check passed.")

    # Phase 3: Filesystem Swap
    try:
        if not os.path.exists(new_exe):
            logger.error(f"New version not found at: {new_exe}")
            sys.exit(1)

        time.sleep(1)
        logger.info(f"Updating {old_exe}...")

        # Rotate backup file
        backup_exe = old_exe + ".old"
        if os.path.exists(backup_exe):
            try:
                os.remove(backup_exe)
            except OSError:
                pass

        # Robust rename to handle OS file locks (Antivirus/Indexing)
        _retry_rename(old_exe, backup_exe)

        try:
            _retry_rename(new_exe, old_exe)
            logger.info("Update applied successfully.")
        except Exception as e:
            logger.error(f"Failed to move new executable: {e}. Rolling back...")
            if os.path.exists(backup_exe):
                _retry_rename(backup_exe, old_exe)
            raise

        # Clean rotation artifact
        try:
            if os.path.exists(backup_exe):
                os.remove(backup_exe)
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Critical error during swap: {e}")
        sys.exit(1)

    # Phase 4: Application Revival
    try:
        logger.info(f"Restarting application: {old_exe}")
        if sys.platform == "win32":
            os.startfile(old_exe)
        else:
            subprocess.Popen([old_exe], start_new_session=True)
    except Exception as e:
        logger.error(f"Failed to restart application: {e}")
        sys.exit(1)


# ==============================================================================
# PRIVATE HELPERS
# ==============================================================================

def _retry_rename(src: str, dst: str, max_retries: int = 5) -> None:
    """
    Attempt to rename a file with exponential backoff on failure.

    Specifically targets Windows Access Denied (EACCES) errors that occur
    during the short window after a process terminates.

    Args:
        src: Source path.
        dst: Destination path.
        max_retries: Maximum number of attempts before raising exception.
    """
    for i in range(max_retries):
        try:
            if os.path.exists(dst):
                try:
                    os.remove(dst)
                except OSError:
                    pass
            os.rename(src, dst)
            return
        except OSError as e:
            if i == max_retries - 1:
                logger.error(f"Final rename attempt failed: {src} -> {dst}")
                raise e

            wait_time = 1.5 ** i
            logger.warning(
                f"FS lock detected (attempt {i + 1}/{max_retries}). "
                f"Retrying in {wait_time:.2f}s... Error: {e}"
            )
            time.sleep(wait_time)


# ==============================================================================
# SCRIPT INTERFACE
# ==============================================================================

def main() -> None:
    """Parse CLI arguments and initiate the update lifecycle."""
    parser = argparse.ArgumentParser(description="Transcriptor4AI Sidecar Updater")

    parser.add_argument(
        "--pid", type=int, required=True,
        help="PID of the process to wait for"
    )
    parser.add_argument(
        "--old", type=str, required=True,
        help="Path to the current executable"
    )
    parser.add_argument(
        "--new", type=str, required=True,
        help="Path to the new executable"
    )
    parser.add_argument(
        "--sha256", type=str,
        help="Expected SHA-256 hash for integrity verification"
    )

    args = parser.parse_args()

    # Small delay to ensure the parent process starts closing
    time.sleep(0.5)

    run_update(args.old, args.new, args.pid, args.sha256)
    logger.info("Updater lifecycle finished.")


if __name__ == "__main__":
    main()