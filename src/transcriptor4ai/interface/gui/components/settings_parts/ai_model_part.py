from __future__ import annotations

"""
UI Section for AI Model Selection.

Manages the provider-to-model mapping interface, allowing users to 
select specific LLM architectures for tokenization and context optimization.
"""

from typing import Any, Dict, TYPE_CHECKING

import customtkinter as ctk

from transcriptor4ai.domain import constants as const
from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.settings import SettingsFrame


class AIModelSection:
    """
    Handles the mapping between AI providers and specific LLM models.
    """

    def __init__(
            self,
            master: SettingsFrame,
            container: ctk.CTkScrollableFrame,
            config: Dict[str, Any]
    ) -> None:
        """
        Initialize the AI selection section and register widgets in the master.

        Args:
            master: The parent SettingsFrame where widgets will be registered.
            container: The scrollable container for layout placement.
            config: Active session configuration for initial values.
        """
        frame_ai = ctk.CTkFrame(container, fg_color="transparent")
        frame_ai.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        frame_ai.grid_columnconfigure((0, 1), weight=1)

        # --- Provider Selection Column ---
        f_prov = ctk.CTkFrame(frame_ai)
        f_prov.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ctk.CTkLabel(
            f_prov,
            text=i18n.t("gui.settings.provider_label"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        master.combo_provider = ctk.CTkComboBox(
            f_prov,
            values=[],
            width=200,
            state="readonly"
        )
        master.combo_provider.pack(padx=10, pady=10, anchor="w", fill="x")

        # --- Model Selection Column ---
        f_mod = ctk.CTkFrame(frame_ai)
        f_mod.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(
            f_mod,
            text=i18n.t("gui.settings.model_label"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        master.combo_model = ctk.CTkComboBox(
            f_mod,
            values=[],
            width=200,
            state="readonly"
        )

        # Set initial value from last session
        target_model = config.get("target_model", const.DEFAULT_MODEL_KEY)
        master.combo_model.set(target_model)
        master.combo_model.pack(padx=10, pady=10, anchor="w", fill="x")