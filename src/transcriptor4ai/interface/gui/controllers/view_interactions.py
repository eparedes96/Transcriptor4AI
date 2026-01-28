from __future__ import annotations

"""
View Interaction Handler.

Manages purely visual logic such as toggling visibility of UI sections
(AST controls) and applying preset configurations (Stacks). 
Separates presentation logic from the main application coordinator.
"""

from typing import TYPE_CHECKING

from transcriptor4ai.shared import constants as const

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.coordinator import AppController


class ViewInteractionHandler:
    """
    Delegate controller for UI-specific events that do not affect backend logic.
    """

    def __init__(self, coordinator: AppController) -> None:
        """
        Initialize with a weak reference to the main coordinator.

        Args:
            coordinator: Reference to the AppController for accessing UI widgets.
        """
        self.main = coordinator

    def on_stack_selected(self, stack_name: str) -> None:
        """
        Apply a pre-defined extension stack to the settings view inputs.

        Args:
            stack_name: Key identifier from the constants.DEFAULT_STACKS dictionary.
        """
        if stack_name in const.DEFAULT_STACKS:
            extensions = const.DEFAULT_STACKS[stack_name]

            # Update UI Entry
            self.main.settings_view.entry_ext.delete(0, "end")
            self.main.settings_view.entry_ext.insert(0, ",".join(extensions))

            # Update Config State immediately
            self.main.config["extensions"] = extensions

    def on_tree_toggled(self) -> None:
        """
        Update the visibility of AST controls based on the Tree switch state.

        If the tree generation is disabled, specific AST options (Classes/Functions)
        are irrelevant and should be hidden to reduce cognitive load.
        """
        if self.main.dashboard_view.sw_tree.get():
            self.main.dashboard_view.frame_ast.grid(
                row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10)
            )
        else:
            self.main.dashboard_view.frame_ast.grid_forget()