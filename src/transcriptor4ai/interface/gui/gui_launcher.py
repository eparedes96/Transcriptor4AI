from __future__ import annotations

"""
GUI Entrypoint and Application Lifecycle Orchestrator.

Sequences the startup phases by integrating the Dependency Injection container, 
environment bootstrapping, and UI component assembly. It bridges asynchronous 
background tasks with the main thread event loop.
"""

import logging
import threading
from typing import Any

import customtkinter as ctk

# Bootstrap & DI
from transcriptor4ai.interface.gui.bootstrap.di_container import build_application_context
from transcriptor4ai.interface.gui.bootstrap.startup import (
    init_diagnostic_system,
    setup_visual_theme,
    start_log_polling,
)

# Common Helpers
from transcriptor4ai.interface.gui.common.dialog_helpers import browse_directory

# Application Services & Tasks
from transcriptor4ai.application.services.update_service import UpdateManager
from transcriptor4ai.interface.gui.common import async_workers

# View Components
from transcriptor4ai.interface.gui.components.dashboard import DashboardFrame
from transcriptor4ai.interface.gui.components.logs_console import LogsFrame
from transcriptor4ai.interface.gui.components.main_window import create_main_window
from transcriptor4ai.interface.gui.components.settings import SettingsFrame
from transcriptor4ai.interface.gui.components.sidebar import SidebarFrame

# Controllers
from transcriptor4ai.interface.gui.controllers.coordinator import AppController
from transcriptor4ai.interface.gui.controllers.update_controller import UpdateController
from transcriptor4ai.interface.gui.dialogs.feedback_modal import show_feedback_window

# Standardized infrastructure logger
logger = logging.getLogger(__name__)


# ==============================================================================
# MAIN APPLICATION ORCHESTRATOR
# ==============================================================================

def main() -> None:
    """
    Execute the professional UI startup sequence.
    """

    # --- PHASE 1: ENVIRONMENT & INFRASTRUCTURE ---
    # 1. Start logging and get the UI message queue
    log_queue = init_diagnostic_system()
    setup_visual_theme()

    # 2. Build the dependency graph and recover persistent state
    context = build_application_context()

    # --- PHASE 2: VIEW HIERARCHY ASSEMBLY ---
    # 1. Primary Window
    app: ctk.CTk = create_main_window()

    def show_frame(name: str) -> None:
        """Switch current visible view via grid management."""
        dashboard_frame.grid_forget()
        settings_frame.grid_forget()
        logs_frame.grid_forget()

        sidebar_frame.btn_dashboard.configure(fg_color="transparent")
        sidebar_frame.btn_settings.configure(fg_color="transparent")
        sidebar_frame.btn_logs.configure(fg_color="transparent")

        if name == "dashboard":
            dashboard_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_dashboard.configure(fg_color=("gray75", "gray25"))
        elif name == "settings":
            settings_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_settings.configure(fg_color=("gray75", "gray25"))
        elif name == "logs":
            logs_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_logs.configure(fg_color=("gray75", "gray25"))

    # 2. Specialized Frames
    sidebar_frame = SidebarFrame(app, nav_callback=show_frame)
    sidebar_frame.grid(row=0, column=0, sticky="nsew")

    dashboard_frame = DashboardFrame(app, context.config)
    settings_frame = SettingsFrame(app, context.config, context.profile_names)
    logs_frame = LogsFrame(app)

    # 3. Default Entry Point
    show_frame("dashboard")

    # --- PHASE 3: CONTROLLER INTEGRATION ---
    # Inject context into the main coordinator
    controller = AppController(
        app=app,
        config=context.config,
        app_state=context.app_state,
        fs=context.fs,
        cache=context.cache,
        config_repo=context.config_repo,
        registry=context.registry,
        user_context=context.user_context
    )
    controller.register_views(dashboard_frame, settings_frame, logs_frame, sidebar_frame)

    # --- PHASE 4: COMMAND BINDING & EVENT LOOP ---
    # 1. Bind Directory Discovery
    dashboard_frame.btn_browse_in.configure(
        command=lambda: browse_directory(
            app, dashboard_frame.entry_input, dashboard_frame.entry_output
        )
    )
    dashboard_frame.btn_browse_out.configure(
        command=lambda: browse_directory(app, dashboard_frame.entry_output)
    )

    # 2. Bind Execution & UI States
    dashboard_frame.btn_process.configure(command=lambda: controller.start_processing(False))
    dashboard_frame.btn_simulate.configure(command=lambda: controller.start_processing(True))
    dashboard_frame.sw_tree.configure(command=controller.on_tree_toggled)

    # 3. Bind Settings Actions
    settings_frame.btn_load.configure(command=controller.load_profile)
    settings_frame.btn_save.configure(command=controller.save_profile)
    settings_frame.btn_del.configure(command=controller.delete_profile)
    settings_frame.btn_purge.configure(command=controller.purge_cache)
    settings_frame.btn_reset.configure(command=controller.reset_config)

    # 4. Bind Dropdowns
    settings_frame.combo_stack.configure(command=controller.on_stack_selected)
    settings_frame.combo_provider.configure(command=controller.on_provider_selected)
    settings_frame.combo_model.configure(command=controller.on_model_selected)

    # 5. Bind Sidebar Extras
    sidebar_frame.btn_feedback.configure(command=lambda: show_feedback_window(app))

    # --- PHASE 5: BACKGROUND TASKS ---
    # 1. Initialize Log Terminal Polling
    start_log_polling(app, log_queue, logs_view=logs_frame)

    # 2. Sync Initial State
    controller.sync_view_from_config()

    # 3. Start Over-The-Air Update Engine
    update_manager = UpdateManager(context.network, context.fs)
    ota_controller = UpdateController(app, sidebar_frame, update_manager)

    if context.app_state.get("app_settings", {}).get("auto_check_updates"):
        threading.Thread(target=ota_controller.run_silent_cycle, daemon=True).start()

    # 4. Run Pricing & Metadata Synchronization
    threading.Thread(
        target=async_workers.run_pricing_sync_task,
        args=(controller.cost_estimator, lambda _: app.after(
            0, lambda: controller.on_pricing_updated(None)
        )),
        daemon=True
    ).start()

    # --- PHASE 6: LIFECYCLE MANAGEMENT ---
    def on_closing() -> None:
        """Persist state and cleanup resources before exit."""
        try:
            controller.sync_config_from_view()
            context.config_repo.save_app_state(context.app_state)
            logger.info("Shutdown: Application state successfully persisted.")
        except Exception as e:
            logger.error(f"Shutdown: Persistence failure: {e}")
        finally:
            app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()