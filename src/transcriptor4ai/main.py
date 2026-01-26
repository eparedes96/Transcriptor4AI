from __future__ import annotations

"""
Main Entry Point and Global Supervisor.

Orchestrates application startup, execution routing (CLI/GUI), 
and implements a robust global exception handling mechanism to 
ensure fatal crashes are captured and reported across all interfaces.
"""

import logging
import os
import sys
import traceback
from typing import Any

# ==============================================================================
# ENVIRONMENT INITIALIZATION
# ==============================================================================

# Anti-shadowing and path visibility logic for development vs frozen state
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not getattr(sys, 'frozen', False):
    SRC_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)


# ==============================================================================
# GLOBAL SUPERVISOR (EXCEPTION HANDLING)
# ==============================================================================

def global_exception_handler(
        exctype: type[BaseException],
        value: BaseException,
        tb: Any
) -> None:
    """
    Trap unhandled exceptions and route them to interface-appropriate reporters.

    Captures the full stack trace and delegates reporting to terminal
    (CLI) or custom crash modals (GUI). Implements an emergency fallback
    using native Tkinter if the application state is corrupted.

    Args:
        exctype: Exception class.
        value: Exception instance.
        tb: Traceback object.
    """
    stack_trace = "".join(traceback.format_exception(exctype, value, tb))
    error_msg = str(value)

    # 1. LOGGING: Ensure the crash is persisted in logs even if UI fails
    # We use a fallback logger name in case root isn't configured
    logger = logging.getLogger("transcriptor4ai.supervisor")
    logger.critical(f"FATAL EXCEPTION DETECTED: {error_msg}\n{stack_trace}")

    # 2. ROUTING: Determine reporting strategy based on context

    # CASE A: CLI Mode (Arguments present) -> Print to Stderr
    if len(sys.argv) > 1:
        print("\n" + "=" * 80, file=sys.stderr)
        print("CRITICAL ERROR (TRANSCRIPTOR4AI CLI)", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(stack_trace, file=sys.stderr)
        sys.exit(1)

    # CASE B: GUI Mode (No arguments) -> Launch Crash Modal
    else:
        try:
            # Lazy import to avoid initializing UI stack unnecessarily
            from transcriptor4ai.interface.gui.dialogs.crash_modal import show_crash_modal
            show_crash_modal(error_msg, stack_trace)
        except Exception as e:
            # Emergency Fallback: If CustomTkinter fails, use native Tkinter
            logger.error(f"Custom crash modal failed: {e}. Falling back to system alert.")
            try:
                import tkinter.messagebox as mb
                from tkinter import Tk

                # Create a hidden root to anchor the message box
                root = Tk()
                root.withdraw()
                mb.showerror(
                    "Transcriptor4AI - Fatal Error",
                    f"A critical error occurred in the interface:\n\n{error_msg}\n\n"
                    f"Technical details have been saved to the log file."
                )
                root.destroy()
            except Exception:
                # Last resort: Print to stderr (visible only if run from console)
                print(f"CRITICAL SYSTEM ERROR: {error_msg}\n{stack_trace}", file=sys.stderr)

        sys.exit(1)


# Hook into the Python interpreter exception flow
sys.excepthook = global_exception_handler


# ==============================================================================
# EXECUTION ROUTING
# ==============================================================================

def main() -> int:
    """
    Detect execution context and delegate to the specific interface controller.

    Routes execution based on command line arguments presence.

    Returns:
        int: Standard process exit code (0: Success, 1: Error).
    """
    try:
        # 1. DETECTION: Check for CLI arguments (len > 1 implies user passed flags)
        if len(sys.argv) > 1:
            # Delegate to Command Line Interface Facade
            from transcriptor4ai.interface.cli import main as cli_main
            return cli_main()

        # 2. DEFAULT: Launch Graphical User Interface
        else:
            # Delegate to GUI Facade
            from transcriptor4ai.interface.gui import main as gui_main
            gui_main()
            return 0

    except Exception as e:
        # Explicit catch to route through our supervisor logic
        global_exception_handler(type(e), e, sys.exc_info()[2])
        return 1


if __name__ == "__main__":
    sys.exit(main())