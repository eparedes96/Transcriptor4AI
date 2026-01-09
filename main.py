from __future__ import annotations

"""
Main Entry Point (Smart Router)

This module acts as a dispatcher and global supervisor.
- Handles global unhandled exceptions (Smart Error Reporter).
- Routes to CLI or GUI based on arguments.
"""

import sys
import traceback
import logging
from transcriptor4ai.cli import main as cli_main

logger = logging.getLogger("transcriptor4ai.entrypoint")

def global_exception_handler(exctype, value, tb):
    """
    Catch any unhandled exception and route it to the appropriate
    reporting mechanism (CLI stderr or GUI Modal).
    """
    stack_trace = "".join(traceback.format_exception(exctype, value, tb))
    error_msg = str(value)

    # 1. Always log the error
    logger.critical(f"Unhandled exception: {error_msg}\n{stack_trace}")

    # 2. Check if we are in CLI or GUI mode
    if len(sys.argv) > 1:
        print("\n" + "="*80, file=sys.stderr)
        print("CRITICAL ERROR (TRANSCRIPTOR4AI)", file=sys.stderr)
        print("="*80, file=sys.stderr)
        print(stack_trace, file=sys.stderr)
        sys.exit(1)
    else:
        try:
            from transcriptor4ai.ui.gui import show_crash_modal
            show_crash_modal(error_msg, stack_trace)
        except Exception:
            import tkinter.messagebox as mb
            mb.showerror("Critical Error", f"A fatal error occurred:\n\n{error_msg}")
        sys.exit(1)

sys.excepthook = global_exception_handler

def main() -> None:
    """
    Dispatcher logic.
    """
    if len(sys.argv) > 1:
        sys.exit(cli_main())
    else:
        from transcriptor4ai.ui.gui import main as gui_main
        sys.exit(gui_main())

if __name__ == "__main__":
    main()