from __future__ import annotations

"""
Main Entry Point and Global Supervisor for Transcriptor4AI.

This module acts as a smart router and safety net. It:
1. Configures the system path to avoid module shadowing.
2. Captures all unhandled exceptions via a global supervisor.
3. Dispatches execution to either the CLI or GUI based on sys.argv.
"""

import os
import sys
import traceback
import logging

# -----------------------------------------------------------------------------
# Path Configuration (Anti-Shadowing Logic)
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


# -----------------------------------------------------------------------------
# Global Exception Handling (Smart Error Reporter)
# -----------------------------------------------------------------------------

def global_exception_handler(exctype: type[BaseException], value: BaseException, tb: Any) -> None:
    """
    Catch any unhandled exception and route it to the appropriate
    reporting mechanism (CLI stderr or GUI Modal).
    """
    stack_trace = "".join(traceback.format_exception(exctype, value, tb))
    error_msg = str(value)

    # Internal logger (might not be configured yet if crash is early)
    logger = logging.getLogger("transcriptor4ai.supervisor")
    logger.critical(f"Unhandled exception: {error_msg}\n{stack_trace}")

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
            from transcriptor4ai.ui.gui import show_crash_modal
            show_crash_modal(error_msg, stack_trace)
        except Exception:
            try:
                import tkinter.messagebox as mb
                mb.showerror("Critical Error", f"A fatal error occurred:\n\n{error_msg}\n\nCheck logs for details.")
            except ImportError:
                print(f"FATAL GUI ERROR: {error_msg}\n{stack_trace}", file=sys.stderr)
        sys.exit(1)


# Register the supervisor
sys.excepthook = global_exception_handler


# -----------------------------------------------------------------------------
# Entrypoint Router
# -----------------------------------------------------------------------------

def main() -> None:
    """
    Smart router logic to detect execution context.
    """
    # CLI Mode
    if len(sys.argv) > 1:
        from transcriptor4ai.cli import main as cli_main
        sys.exit(cli_main())

    # GUI Mode
    else:
        from transcriptor4ai.ui.gui import main as gui_main
        sys.exit(gui_main())


if __name__ == "__main__":
    main()