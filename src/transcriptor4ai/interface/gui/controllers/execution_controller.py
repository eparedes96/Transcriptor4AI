from __future__ import annotations

"""
GUI Execution Controller.

Manages the transcription pipeline lifecycle within the graphical interface. 
Coordinates configuration synchronization, background thread dispatching, 
and result processing (including financial estimation and overflow alerts).
"""

import logging
import threading
import tkinter.messagebox as mb
from typing import TYPE_CHECKING, Any

from transcriptor4ai.domain.entities.pipeline_results import PipelineResult
from transcriptor4ai.interface.gui.common import async_workers
from transcriptor4ai.interface.gui.dialogs import crash_modal, results_modal
from transcriptor4ai.shared import constants as const
from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to prevent circular imports with the Main Controller
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.coordinator import AppController

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# EXECUTION CONTROLLER
# ==============================================================================

class ExecutionController:
    """
    Controller responsible for starting, aborting, and handling pipeline tasks.
    """

    def __init__(self, main_controller: AppController) -> None:
        """
        Initialize the controller with a reference to the application hub.
        """
        self.main = main_controller
        self._cancellation_event = threading.Event()

    # ==========================================================================
    # PIPELINE LIFECYCLE
    # ==========================================================================

    def run_pipeline(self, dry_run: bool = False, overwrite: bool = False) -> None:
        """
        Initiate the transcription process in a dedicated background thread.
        """
        # 1. SYNC: Scrape current UI values into the transient config dictionary
        self.main.sync_config_from_view()

        # 2. VALIDATE: Pre-flight check via infrastructure adapter
        # Force use of IFileSystem port instead of raw 'os' calls
        fs = self.main.get_filesystem()
        input_path: str = self.main.config.get("input_path", "")

        if not fs.directory_exists(input_path):
            mb.showerror(
                i18n.t("gui.dialogs.error_title"),
                i18n.t("gui.dialogs.invalid_input")
            )
            return

        # 3. UI STATE: Lock interaction and update visual feedback
        self.set_ui_state(disabled=True)
        btn_text = i18n.t("gui.dashboard.btn_simulating") if dry_run else "PROCESSING..."
        self.main.dashboard_view.btn_process.configure(text=btn_text, fg_color="gray")

        # 4. DISPATCH: Launch the background worker task
        self._cancellation_event.clear()
        logger.debug(f"Execution: Starting pipeline (DryRun={dry_run}).")

        threading.Thread(
            target=async_workers.run_pipeline_task,
            args=(
                fs,  # Injected Filesystem Port
                self.main.get_cache(),  # Injected Cache Port
                self.main.get_user_context(),
                self.main.config,  # Current configuration
                overwrite,
                dry_run,
                self.handle_thread_callback,
                self._cancellation_event
            ),
            daemon=True
        ).start()

    def abort_pipeline(self) -> None:
        """
        Send a termination signal to the running background pipeline.
        """
        if not self._cancellation_event.is_set():
            logger.info("Execution: User cancellation requested. Signaling workers...")
            self._cancellation_event.set()

            # Visual feedback of the abortion process
            self.main.dashboard_view.btn_process.configure(
                text="CANCELING...",
                state="disabled"
            )

    # ==========================================================================
    # CALLBACK PROCESSING
    # ==========================================================================

    def handle_thread_callback(self, result: Any) -> None:
        """
        Marshal background results back to the UI thread for processing.
        """
        # Force execution on the Main Thread via Tkinter's event loop
        self.main.app.after(0, lambda: self.process_result_and_modals(result))

    def process_result_and_modals(self, result: Any) -> None:
        """
        Interpret the pipeline result and update UI/Modals accordingly.
        """
        # 1. VALIDATION: Check for naming collisions (Overwrite Workflow)
        if isinstance(result, PipelineResult) and not result.ok:
            if result.existing_files:
                msg_files = "\n".join(result.existing_files)
                msg = i18n.t("gui.popups.overwrite_msg", files=msg_files)

                if mb.askyesno(i18n.t("gui.popups.overwrite_title"), msg):
                    # Recursive call with overwrite permission
                    self.run_pipeline(dry_run=False, overwrite=True)
                    return

        # 2. UI RESET: Re-enable interaction
        self.set_ui_state(disabled=False)
        self.main.dashboard_view.btn_process.configure(
            text=i18n.t("gui.dashboard.btn_start"),
            fg_color="#1F6AA5"
        )

        # 3. SUCCESS HANDLING: Calculate costs and show results
        if isinstance(result, PipelineResult):
            if result.ok:
                self._handle_pipeline_success(result)
            else:
                self._handle_pipeline_error(result)

        # 4. FATAL ERROR HANDLING: Unexpected exceptions
        elif isinstance(result, Exception):
            crash_modal.show_crash_modal(str(result), "Detailed logs are available.", self.main.app)

    # ==========================================================================
    # PRIVATE HELPERS
    # ==========================================================================

    def _handle_pipeline_success(self, result: PipelineResult) -> None:
        """Execute logic specific to a successful transcription run."""
        target_model: str = self.main.config.get("target_model", const.DEFAULT_MODEL_KEY)

        # Update financial metrics in the Dashboard
        cost = self.main.cost_estimator.calculate_cost(result.token_count, target_model)
        if self.main.dashboard_view and hasattr(self.main.dashboard_view, "update_cost_display"):
            self.main.dashboard_view.update_cost_display(cost)

        # Verify context window limits against selected model specs
        limit = self.main.cost_estimator.get_context_window(target_model)
        if result.token_count > limit:
            warning_msg = (
                f"Warning: Estimated tokens ({result.token_count:,}) exceed "
                f"the model's context window ({limit:,}).\n\n"
                "The output will likely be truncated by the AI provider."
            )
            mb.showwarning("Context Overflow", warning_msg)

        # Show detailed results dialog
        results_modal.show_results_window(self.main.app, result)

    def _handle_pipeline_error(self, result: PipelineResult) -> None:
        """Handle logical failures reported by the pipeline."""
        err_msg = result.error.lower() if result.error else ""

        if self._cancellation_event.is_set() and "cancelled" in err_msg:
            logger.info("Execution: Task stopped successfully by user signal.")
        else:
            mb.showerror(i18n.t("gui.dialogs.pipeline_failed"), result.error)

    def set_ui_state(self, disabled: bool) -> None:
        """Manage accessibility of execution triggers during processing."""
        state = "disabled" if disabled else "normal"
        self.main.dashboard_view.btn_process.configure(state=state)
        self.main.dashboard_view.btn_simulate.configure(state=state)