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

# -----------------------------------------------------------------------------
# ENVIRONMENT INITIALIZATION
# -----------------------------------------------------------------------------

# Anti-shadowing and path visibility logic
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not getattr(sys, 'frozen', False):
    SRC_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)


# -----------------------------------------------------------------------------
# GLOBAL SUPERVISOR (EXCEPTION HANDLING)
# -----------------------------------------------------------------------------

def global_exception_handler(exctype: type[BaseException], value: BaseException, tb: Any) -> None:
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

    # Ensure the crash is persisted in logs
    logger = logging.getLogger("transcriptor4ai.supervisor")
    logger.critical(f"FATAL EXCEPTION DETECTED: {error_msg}\n{stack_trace}")

    # CLI Fallback: Detailed trace to stderr
    if len(sys.argv) > 1:
        print("\n" + "=" * 80, file=sys.stderr)
        print("CRITICAL ERROR (TRANSCRIPTOR4AI CLI)", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(stack_trace, file=sys.stderr)
        sys.exit(1)

    # GUI Fallback: UI-driven reporting
    else:
        try:
            from transcriptor4ai.interface.gui.dialogs.crash_modal import show_crash_modal
            show_crash_modal(error_msg, stack_trace)
        except Exception as e:
            logger.error(f"Custom crash modal failed: {e}. Falling back to system alert.")
            try:
                import tkinter.messagebox as mb
                from tkinter import Tk
                root = Tk()
                root.withdraw()
                mb.showerror(
                    "Transcriptor4AI - Fatal Error",
                    f"A critical error occurred in the interface:\n\n{error_msg}\n\n"
                    f"Technical details have been saved to the log file."
                )
                root.destroy()
            except Exception:
                print(f"CRITICAL SYSTEM ERROR: {error_msg}\n{stack_trace}", file=sys.stderr)

        sys.exit(1)


# Hook into the Python interpreter exception flow
sys.excepthook = global_exception_handler


# -----------------------------------------------------------------------------
# EXECUTION ROUTING
# -----------------------------------------------------------------------------

def main() -> int:
    """
    Detect execution context and delegate to the specific interface controller.

    Routes execution based on command line arguments presence.

    Returns:
        int: Standard process exit code (0: Success, 1: Error).
    """
    try:
        # Detect CLI mode by argument presence
        if len(sys.argv) > 1:
            from transcriptor4ai.interface.cli.app import main as cli_main
            return cli_main()

        # Default to GUI mode
        else:
            from transcriptor4ai.interface.gui.app import main as gui_main
            gui_main()
            return 0

    except Exception as e:
        global_exception_handler(type(e), e, sys.exc_info()[2])
        return 1


if __name__ == "__main__":
    sys.exit(main())