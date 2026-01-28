from __future__ import annotations

"""
Feedback Orchestration Controller.

Provides an abstraction layer for user-initiated feedback and error reporting.
Acts as a bridge between the main application controller and the modal
dialogs, ensuring that UI triggers are decoupled from dialog implementation
details and preventing event loop pollution.
"""

import logging
from typing import TYPE_CHECKING

from transcriptor4ai.interface.gui.dialogs.feedback_modal import show_feedback_window

# Use TYPE_CHECKING to prevent circular imports with the Hub Controller
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.coordinator import AppController

# Standard logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# FEEDBACK CONTROLLER
# ==============================================================================

class FeedbackController:
    """
    Coordinates user feedback workflows and bug reporting sessions.
    """

    def __init__(self, main_controller: AppController) -> None:
        """
        Initialize the controller with a reference to the main app hub.

        Args:
            main_controller: Reference to the parent AppController instance.
        """
        self.main = main_controller

    # ==========================================================================
    # INTERACTION HANDLERS
    # ==========================================================================

    def on_feedback_requested(self) -> None:
        """
        Trigger the display of the Feedback Hub modal.

        Captures requests from the sidebar or settings menu and delegates
        the window creation to the dialogs subsystem, ensuring the main
        window remains the modal parent.
        """
        # 1. LOG: Record the user-initiated event for diagnostics
        logger.debug("FeedbackController: Modal window requested by user.")

        try:
            # 2. DELEGATE: Invoke the specialized view component
            # We pass the root app instance to maintain window hierarchy
            show_feedback_window(self.main.app)

        except Exception as e:
            # 3. CRITICAL: Prevent UI failures from crashing the main process
            # Feedback logic is non-essential for the transcription core
            logger.error(f"FeedbackController: UI initialization failed: {e}", exc_info=True)