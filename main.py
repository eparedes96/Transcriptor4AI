from __future__ import annotations

"""
Main Entry Point and Global Supervisor.

This module acts as the application's smart router and safety net. It:
1. Configures the Python path to ensure module visibility.
2. Registers a global exception handler to catch crashes.
3. Dispatches execution to either the CLI or GUI based on arguments.
"""

import os
import sys
import traceback
import logging
from typing import Any

# -----------------------------------------------------------------------------
# Path Configuration (Anti-Shadowing Logic)
# -----------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if not getattr(sys, 'frozen', False):
    SRC_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
    if SRC_DIR not in sys.path:
        sys.path.insert(0, SRC_DIR)


# -----------------------------------------------------------------------------
# Global Exception Handling (Smart Error Reporter)
# -----------------------------------------------------------------------------
def global_exception_handler(exctype: type[BaseException], value: BaseException, tb: Any) -> None:
    """
    Catch any unhandled exception and route it to the appropriate
    reporting mechanism (CLI stderr or GUI Modal).

    Includes a robust fallback for GUI crashes where the main event loop
    might be frozen.

    Args:
        exctype: The exception class.
        value: The exception instance.
        tb: The traceback object.
    """
    stack_trace = "".join(traceback.format_exception(exctype, value, tb))
    error_msg = str(value)

    # Internal logger (Ensure critical trace is always recorded)
    logger = logging.getLogger("transcriptor4ai.supervisor")
    logger.critical(f"FATAL EXCEPTION DETECTED: {error_msg}\n{stack_trace}")

    # 1. CLI Mode (Arguments provided)
    if len(sys.argv) > 1:
        print("\n" + "=" * 80, file=sys.stderr)
        print("CRITICAL ERROR (TRANSCRIPTOR4AI CLI)", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(stack_trace, file=sys.stderr)
        sys.exit(1)

    # 2. GUI Mode (No arguments)
    else:
        try:
            from transcriptor4ai.interface.gui.handlers import show_crash_modal
            show_crash_modal(error_msg, stack_trace)
        except Exception as e:
            logger.error(f"Custom crash modal failed: {e}. Falling back to system native alert.")
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
                # Absolute last resort
                print(f"CRITICAL SYSTEM ERROR: {error_msg}\n{stack_trace}", file=sys.stderr)

        sys.exit(1)


# Register the supervisor immediately at start
sys.excepthook = global_exception_handler


# -----------------------------------------------------------------------------
# Entrypoint Router
# -----------------------------------------------------------------------------
def main() -> None:
    """
    Smart router logic to detect execution context.
    Delegates to CLI or GUI application controllers.
    """
    try:
        # CLI Mode
        if len(sys.argv) > 1:
            from transcriptor4ai.interface.cli.app import main as cli_main
            sys.exit(cli_main())

        # GUI Mode
        else:
            from transcriptor4ai.interface.gui.app import main as gui_main
            sys.exit(gui_main())

    except Exception as e:
        global_exception_handler(type(e), e, sys.exc_info()[2])


if __name__ == "__main__":
    main()