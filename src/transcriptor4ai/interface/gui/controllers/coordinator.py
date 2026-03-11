from __future__ import annotations

"""
Main Application Controller (GUI Hub).

Acts as the central Mediator and Dependency Container for the graphical 
interface. It coordinates communication between specialized sub-controllers, 
manages the shared application state, and provides unified access to 
infrastructure ports and application services.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    import customtkinter as ctk

    from transcriptor4ai.domain.ports.cache_port import ICacheRepository
    from transcriptor4ai.domain.ports.config_port import IConfigRepository
    from transcriptor4ai.domain.ports.model_port import IModelRegistry
    from transcriptor4ai.domain.ports.system_port import IFileSystem
    from transcriptor4ai.domain.ports.user_port import IUserContext

# Application Services
from transcriptor4ai.application.services.cost_calculator import CostCalculatorService

# Sub-Controllers (Delegates)
from transcriptor4ai.interface.gui.controllers.config_synchronizer import ConfigSynchronizer
from transcriptor4ai.interface.gui.controllers.execution_controller import ExecutionController
from transcriptor4ai.interface.gui.controllers.feedback_controller import FeedbackController
from transcriptor4ai.interface.gui.controllers.pricing_controller import PricingController
from transcriptor4ai.interface.gui.controllers.profile_controller import ProfileController
from transcriptor4ai.interface.gui.controllers.session_manager import SessionManager
from transcriptor4ai.interface.gui.controllers.view_interactions import ViewInteractionHandler

# Standardized infrastructure logger
logger = logging.getLogger(__name__)


# ==============================================================================
# MAIN COORDINATOR CLASS
# ==============================================================================

class AppController:
    """
    Central Hub responsible for orchestrating the GUI lifecycle.

    This class follows the Mediator pattern, holding the application state
    and delegating specific logic to specialized sub-controllers.
    """

    def __init__(
            self,
            app: ctk.CTk,
            config: Dict[str, Any],
            app_state: Dict[str, Any],
            fs: IFileSystem,
            cache: ICacheRepository,
            config_repo: IConfigRepository,
            registry: IModelRegistry,
            user_context: IUserContext
    ) -> None:
        """
        Initialize the Hub with injected infrastructure and shared state.
        """
        # 1. SHARED STATE: Global configuration and application metadata
        self.app = app
        self.config = config
        self.app_state = app_state

        # 2. INFRASTRUCTURE: Assign injected ports for service access
        self._fs = fs
        self._cache = cache
        self._config_repo = config_repo
        self._registry = registry
        self._user_context = user_context

        # 3. DOMAIN SERVICES: Logic independent of the UI
        self.cost_estimator = CostCalculatorService(self._registry)

        # 4. VIEW REFERENCES: Injected later via register_views()
        self.dashboard_view: Any = None
        self.settings_view: Any = None
        self.logs_view: Any = None
        self.sidebar_view: Any = None

        # 5. DELEGATES: Specialized logic controllers
        # We pass 'self' to allow sub-controllers to talk back to the Hub.
        self.synchronizer = ConfigSynchronizer(self)
        self.session_manager = SessionManager(self)
        self.interactions = ViewInteractionHandler(self)

        self.profile_controller = ProfileController(self)
        self.feedback_controller = FeedbackController(self)
        self.execution_controller = ExecutionController(self)
        self.pricing_controller = PricingController(self)

    def register_views(self, dashboard: Any, settings: Any, logs: Any, sidebar: Any) -> None:
        """
        Bind visual frame instances to the coordinator.
        """
        self.dashboard_view = dashboard
        self.settings_view = settings
        self.logs_view = logs
        self.sidebar_view = sidebar

    # ==========================================================================
    # INFRASTRUCTURE ACCESSORS (FOR DELEGATES)
    # ==========================================================================

    def get_filesystem(self) -> IFileSystem: return self._fs

    def get_cache(self) -> ICacheRepository: return self._cache

    def get_config_repo(self) -> IConfigRepository: return self._config_repo

    def get_model_registry(self) -> IModelRegistry: return self._registry

    def get_user_context(self) -> IUserContext: return self._user_context

    # ==========================================================================
    # DELEGATED UI METHODS (FACADE INTERFACE)
    # ==========================================================================

    # --- Configuration Binding ---
    def sync_view_from_config(self) -> None:
        """Update UI widgets with current configuration values."""
        self.synchronizer.sync_to_view()

    def sync_config_from_view(self) -> None:
        """Update configuration dictionary with current UI values."""
        self.synchronizer.sync_from_view()

    # --- Session & Lifecycle ---
    def reset_config(self) -> None:
        """Trigger a factory reset of the current configuration."""
        self.session_manager.reset_config()

    def purge_cache(self) -> None:
        """Clear the persistent processing cache."""
        self.session_manager.purge_cache()

    # --- Visual Interactions ---
    def on_stack_selected(self, stack_name: str) -> None:
        """Apply a pre-defined extension preset."""
        self.interactions.on_stack_selected(stack_name)

    def on_tree_toggled(self) -> None:
        """Handle visibility logic when tree generation is toggled."""
        self.interactions.on_tree_toggled()

    # --- Execution & Logic Delegation ---
    def start_processing(self, dry_run: bool = False, overwrite: bool = False) -> None:
        """Delegate pipeline execution to the execution engine."""
        self.execution_controller.run_pipeline(dry_run, overwrite)

    def cancel_processing(self) -> None:
        """Abort the active background execution."""
        self.execution_controller.abort_pipeline()

    # --- Pricing & Discovery Delegation ---
    def on_pricing_updated(self, data: Optional[Dict[str, Any]]) -> None:
        """Handle completion of the remote pricing discovery task."""
        self.pricing_controller.sync_remote_data(data)

    def on_provider_selected(self, provider: str) -> None:
        """Handle user selection of an AI provider."""
        self.pricing_controller.handle_provider_change(provider)

    def on_model_selected(self, model_name: str) -> None:
        """Handle user selection of a specific LLM."""
        self.pricing_controller.handle_model_change(model_name)

    # --- Profile Delegation ---
    def load_profile(self) -> None:
        """Delegate configuration profile loading."""
        self.profile_controller.load_profile()

    def save_profile(self) -> None:
        """Delegate configuration profile persistence."""
        self.profile_controller.save_profile()

    def delete_profile(self) -> None:
        """Delegate configuration profile removal."""
        self.profile_controller.delete_profile()