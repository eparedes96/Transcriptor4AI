from __future__ import annotations

"""
Main Entry Point Shim.

This module serves as a convenience wrapper. If executed directly,
it launches the Graphical User Interface (GUI).
"""

import sys
from transcriptor4ai.ui.gui import main

if __name__ == "__main__":
    sys.exit(main())