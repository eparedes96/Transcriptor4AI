from __future__ import annotations

"""
Feedback Logic Controller.

Handles the user request to open the Feedback/Bug Report interface.
Acts as a bridge between the Main Controller and the Feedback Dialog.
"""

import logging
from typing import TYPE_CHECKING

from transcriptor4ai.interface.gui.dialogs.feedback_modal import show_feedback_window

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.main_controller import AppController

logger = logging.getLogger(__name__)


class FeedbackController:
    """
    Manages user interaction for sending feedback or bug reports.
    """

    def __init__(self, main_controller: AppController):
        self.controller = main_controller

    def on_feedback_requested(self) -> None:
        """
        Trigger the feedback modal workflow.
        """
        logger.debug("User requested feedback window.")

        try:
            show_feedback_window(self.controller.app)
        except Exception as e:
            logger.error(f"Failed to open feedback window: {e}")