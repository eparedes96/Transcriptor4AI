from __future__ import annotations

"""
Main Entry Point (Smart Router).

This module acts as a dispatcher. It detects if command-line arguments
were provided:
- If args are present -> Launches CLI (Command Line Interface).
- If no args -> Launches GUI (Graphical User Interface).

This allows a single executable to serve both use cases.
"""

import sys
from transcriptor4ai.cli import main as cli_main
from transcriptor4ai.ui.gui import main as gui_main

def main() -> None:
    if len(sys.argv) > 1:
        sys.exit(cli_main())
    else:
        sys.exit(gui_main())

if __name__ == "__main__":
    main()