from __future__ import annotations

"""
Feedback Logic Controller.

Provides an abstraction layer for user-initiated feedback and error reporting.
Acts as a bridge between the main application controller and the modal
dialogs, ensuring that UI triggers are decoupled from dialog implementation.
"""

import logging
from typing import TYPE_CHECKING

from transcriptor4ai.interface.gui.dialogs.feedback_modal import show_feedback_window

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.main_controller import AppController

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# FEEDBACK INTERACTION HANDLER
# -----------------------------------------------------------------------------

class FeedbackController:
    """
    Coordinates user feedback workflows and bug reporting sessions.
    """

    def __init__(self, main_controller: AppController):
        """
        Initialize the controller with a reference to the main app orchestrator.

        Args:
            main_controller: Reference to the parent AppController instance.
        """
        self.controller = main_controller

    def on_feedback_requested(self) -> None:
        """
        Trigger the display of the Feedback Hub modal.

        Captures requests from the sidebar or settings menu and delegates
        the window creation to the dialogs subsystem, providing the main
        application as the parent for modal grouping.
        """
        logger.debug("User interaction: Feedback modal requested.")

        try:
            # Delegate UI creation to the specialized dialog module
            show_feedback_window(self.controller.app)
        except Exception as e:
            # Prevent feedback failures from crashing the main event loop
            logger.error(f"UI Exception: Failed to initialize feedback window: {e}")