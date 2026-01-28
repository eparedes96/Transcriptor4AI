from __future__ import annotations

"""
FileSystem Shell Integration Service.

Provides cross-platform utilities for interacting with the host OS shell.
Specifically handles the invocation of native file managers (Explorer/Finder)
using non-blocking process calls.
"""

import logging
import os
import platform
import subprocess

# Local module logger
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC SHELL API
# ==============================================================================

def open_file_explorer_cmd(path: str) -> None:
    """
    Invoke the native OS file explorer at the specified directory path.

    Supports:
    - Windows: explorer.exe (via os.startfile)
    - macOS: Finder (via open)
    - Linux: System Default (via xdg-open)

    Args:
        path: Absolute path to the directory to be displayed.

    Raises:
        FileNotFoundError: If the provided path does not exist on disk.
        OSError: If the shell command fails to execute.
    """
    # 1. VALIDATION: Prevent system calls on non-existent targets
    if not os.path.exists(path):
        msg = f"ShellUtils: Target path not found: {path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    system_name = platform.system()

    try:
        # 2. EXECUTION: Platform-specific dispatch
        if system_name == "Windows":
            # Uses high-level API for file association
            os.startfile(path)

        elif system_name == "Darwin":
            # Native macOS open command (Non-blocking)
            subprocess.Popen(["open", path])

        else:
            # Freedesktop.org standard for Linux/BSD
            subprocess.Popen(["xdg-open", path])

        logger.debug(f"ShellUtils: Explorer opened successfully at '{path}'")

    except Exception as e:
        # Catch sub-process failures or permission issues
        error_msg = f"ShellUtils: Native command failed for {system_name}: {e}"
        logger.error(error_msg)
        raise OSError(error_msg) from e