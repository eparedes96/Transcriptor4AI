from __future__ import annotations

"""
AI Model Selection UI Section.

Manages the provider-to-model mapping interface. Replaces standard ComboBoxes
with scrollable dropdowns to handle large datasets efficiently using a 
slider-enabled interface while maintaining controller compatibility 
via shimmed methods.
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, cast

import customtkinter as ctk

from transcriptor4ai.shared import constants as const
from transcriptor4ai.interface.gui.common.ui_widgets import CTkScrollableDropdown
from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to resolve circular dependencies in static analysis
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.settings import SettingsFrame

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# VIEW COMPONENT: AI MODEL SECTION
# ==============================================================================

class AIModelSection:
    """
    Handles the UI logic for AI providers and LLM models selection.

    Uses CTkScrollableDropdown to provide a scrollable interface for
    large lists, preventing UI overflow and handling controller callbacks.
    """

    def __init__(
            self,
            master: SettingsFrame,
            container: ctk.CTkScrollableFrame,
            config: Dict[str, Any]
    ) -> None:
        """
        Initialize the AI selection section and register widgets.

        Args:
            master: The parent SettingsFrame where widgets will be registered.
            container: The scrollable container for layout placement.
            config: Active session configuration for initial values.
        """
        self._master = master

        # 1. LAYOUT: Create the main horizontal container for AI settings
        frame_ai = ctk.CTkFrame(container, fg_color="transparent")
        frame_ai.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        frame_ai.grid_columnconfigure((0, 1), weight=1)

        # 2. PROVIDER: Build the infrastructure provider selection column
        f_prov = ctk.CTkFrame(frame_ai)
        f_prov.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(
            f_prov,
            text=i18n.t("gui.settings.provider_label"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        master.combo_provider = self._create_scrollable_trigger(
            f_prov,
            click_callback=self._on_provider_click
        )
        master.combo_provider.pack(padx=10, pady=10, anchor="w", fill="x")

        # 3. MODEL: Build the specific LLM selection column
        f_mod = ctk.CTkFrame(frame_ai)
        f_mod.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            f_mod,
            text=i18n.t("gui.settings.model_label"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        master.combo_model = self._create_scrollable_trigger(
            f_mod,
            click_callback=self._on_model_click
        )

        # 4. INITIALIZE: Set the starting value from the persistent config
        target_model: str = config.get("target_model", const.DEFAULT_MODEL_KEY)
        master.combo_model.set(target_model)
        master.combo_model.pack(padx=10, pady=10, anchor="w", fill="x")

    # ==========================================================================
    # INTERNAL COMPONENT FACTORY
    # ==========================================================================

    def _create_scrollable_trigger(
            self,
            parent: ctk.CTkFrame,
            click_callback: Callable[[], None]
    ) -> ctk.CTkButton:
        """
        Create a button styled as a dropdown with ComboBox compatibility methods.

        Separates the physical click (to open the list) from the logical
        selection callback (to notify the controller).
        """
        # 1. WIDGET: Create base button with ComboBox aesthetics
        btn_widget = ctk.CTkButton(
            parent,
            text="Select...",
            anchor="w",
            fg_color=("white", "#343638"),
            border_width=1,
            border_color=("gray70", "#565b5e"),
            text_color=("gray10", "gray90"),
            hover_color=("gray95", "#3e3f40"),
            command=click_callback
        )

        # Force garbage collection to prevent memory leak in loop (Context: Casting)
        # CRITICAL POINT: We cast to Any to allow dynamic attachment of shim methods
        # that the AppController expects from a standard CTkComboBox.
        btn: Any = cast(Any, btn_widget)

        btn._values_list = []
        btn._selection_callback = None

        # 2. SHIMMING: Attach standard ComboBox methods for controller transparency
        def _set(value: str) -> None:
            btn.configure(text=str(value))

        def _get() -> str:
            return str(btn.cget("text"))

        original_configure = btn.configure

        def _smart_configure(**kwargs: Any) -> None:
            """Interpose configuration to trap 'values' and 'command' keys."""
            if "values" in kwargs:
                btn._values_list = kwargs["values"]
                del kwargs["values"]

            if "command" in kwargs:
                # Store the controller callback without overwriting the click command
                btn._selection_callback = kwargs["command"]
                del kwargs["command"]

            if kwargs:
                original_configure(**kwargs)

        btn.set = _set
        btn.get = _get
        btn.configure = _smart_configure

        return cast(ctk.CTkButton, btn)

    # ==========================================================================
    # EVENT HANDLERS
    # ==========================================================================

    def _on_provider_click(self) -> None:
        """Trigger the scrollable dropdown for providers."""
        widget: Any = self._master.combo_provider

        def _on_select(val: str) -> None:
            widget.set(val)
            if hasattr(widget, "_selection_callback") and widget._selection_callback:
                widget._selection_callback(val)

        CTkScrollableDropdown(
            attach=widget,
            values=getattr(widget, "_values_list", []),
            command=_on_select
        )

    def _on_model_click(self) -> None:
        """Trigger the scrollable dropdown for models."""
        widget: Any = self._master.combo_model

        def _on_select(val: str) -> None:
            widget.set(val)
            if hasattr(widget, "_selection_callback") and widget._selection_callback:
                widget._selection_callback(val)

        CTkScrollableDropdown(
            attach=widget,
            values=getattr(widget, "_values_list", []),
            command=_on_select
        )