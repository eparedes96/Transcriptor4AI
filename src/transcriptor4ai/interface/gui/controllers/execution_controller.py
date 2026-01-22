from __future__ import annotations

import logging
import os
import threading
import tkinter.messagebox as mb
from typing import TYPE_CHECKING, Any

from transcriptor4ai.domain import constants as const
from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.interface.gui import threads
from transcriptor4ai.interface.gui.dialogs import crash_modal, results_modal
from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.main_controller import AppController

logger = logging.getLogger(__name__)


class ExecutionController:
    """
    Manages the transcription pipeline lifecycle (start, stop, results).
    """

    def __init__(self, main_controller: AppController):
        self.main = main_controller
        self._cancellation_event = threading.Event()

    def run_pipeline(self, dry_run: bool = False, overwrite: bool = False) -> None:
        """Initiate the transcription pipeline in a background thread."""
        # Access Main Controller to sync config before running
        self.main.sync_config_from_view()

        input_path: str = self.main.config.get("input_path", "")
        if not os.path.isdir(input_path):
            mb.showerror(i18n.t("gui.dialogs.error_title"), i18n.t("gui.dialogs.invalid_input"))
            return

        self.set_ui_state(disabled=True)

        btn_text: str = i18n.t("gui.dashboard.btn_simulating") if dry_run else "PROCESSING..."
        self.main.dashboard_view.btn_process.configure(text=btn_text, fg_color="gray")

        self._cancellation_event.clear()
        logger.debug(f"Starting pipeline (DryRun={dry_run}). Config: {self.main.config}")

        threading.Thread(
            target=threads.run_pipeline_task,
            args=(
                self.main.config,
                overwrite,
                dry_run,
                self.handle_thread_callback,
                self._cancellation_event
            ),
            daemon=True
        ).start()

    def abort_pipeline(self) -> None:
        """Signal the background pipeline to abort execution."""
        if not self._cancellation_event.is_set():
            logger.info("User requested task cancellation. Signaling workers...")
            self._cancellation_event.set()
            self.main.dashboard_view.btn_process.configure(text="CANCELING...", state="disabled")

    def handle_thread_callback(self, result: Any) -> None:
        """Handle pipeline completion from the background thread."""
        # Use main app root to schedule UI update on main thread
        self.main.app.after(0, lambda: self.process_result_and_modals(result))

    def process_result_and_modals(self, result: Any) -> None:
        """Process pipeline result, managing collisions and context validation."""
        if isinstance(result, PipelineResult) and not result.ok:
            if result.existing_files:
                msg_files = "\n".join(result.existing_files)
                msg = i18n.t("gui.popups.overwrite_msg", files=msg_files)
                if mb.askyesno(i18n.t("gui.popups.overwrite_title"), msg):
                    self.run_pipeline(dry_run=False, overwrite=True)
                    return

        self.set_ui_state(disabled=False)
        self.main.dashboard_view.btn_process.configure(
            text=i18n.t("gui.dashboard.btn_start"),
            fg_color="#1F6AA5"
        )

        if isinstance(result, PipelineResult):
            if result.ok:
                target_model: str = self.main.config.get("target_model", const.DEFAULT_MODEL_KEY)

                # Financial Calculation using Main's Estimator
                cost: float = self.main.cost_estimator.calculate_cost(result.token_count, target_model)
                if self.main.dashboard_view and hasattr(self.main.dashboard_view, "update_cost_display"):
                    self.main.dashboard_view.update_cost_display(cost)

                # Context Window Validation
                limit: int = self.main.cost_estimator.get_context_limit(target_model)
                if result.token_count > limit:
                    warning_msg: str = (
                        f"Warning: Estimated tokens ({result.token_count:,}) exceed "
                        f"the model's context window ({limit:,}).\n\n"
                        "The output will likely be truncated by the AI provider."
                    )
                    mb.showwarning("Context Overflow", warning_msg)

                results_modal.show_results_window(self.main.app, result)
            else:
                err_msg: str = result.error.lower() if result.error else ""
                if self._cancellation_event.is_set() and "cancelled" in err_msg:
                    logger.info("Pipeline stopped by user signal.")
                else:
                    mb.showerror(i18n.t("gui.dialogs.pipeline_failed"), result.error)
        elif isinstance(result, Exception):
            crash_modal.show_crash_modal(str(result), "See logs for details.", self.main.app)

    def set_ui_state(self, disabled: bool) -> None:
        """Helper to enable/disable interaction during processing."""
        state: str = "disabled" if disabled else "normal"
        self.main.dashboard_view.btn_process.configure(state=state)
        self.main.dashboard_view.btn_simulate.configure(state=state)