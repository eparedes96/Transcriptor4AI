from __future__ import annotations

"""
PySimpleGUI layout definitions.

This module acts as the 'View' layer. It contains no business logic,
only the structural definition of the main window and its components.
"""

from typing import List, Dict, Any

import PySimpleGUI as sg

from transcriptor4ai.domain import config as cfg
from transcriptor4ai.utils.i18n import i18n


def _get_menu_def() -> List[List[Any]]:
    """Define the top menu bar structure."""
    return [
        ['&File', ['&Reset Config', '---', 'E&xit']],
        ['&Community', ['&Send Feedback', '&Check for Updates']],
        ['&Help', ['&About']]
    ]


def _get_profiles_frame(profile_names: List[str]) -> List[List[sg.Element]]:
    """Create the profile management section."""
    return [[
        sg.Text(i18n.t("gui.labels.profile"), font=("Any", 8)),
        sg.Combo(
            values=profile_names,
            key="-PROFILE_LIST-",
            size=(20, 1),
            readonly=True
        ),
        sg.Button(i18n.t("gui.profiles.load"), key="btn_load_profile", font=("Any", 8)),
        sg.Button(i18n.t("gui.profiles.save"), key="btn_save_profile", font=("Any", 8)),
        sg.Button(i18n.t("gui.profiles.del"), key="btn_del_profile", font=("Any", 8), button_color="gray"),
        sg.Push(),
        sg.Button(
            "Feedback Hub",
            key="btn_feedback",
            button_color=("white", "#4A90E2"),
            font=("Any", 8, "bold")
        )
    ]]


def _get_content_frame(config: Dict[str, Any]) -> List[List[sg.Element]]:
    """Create the content selection checkboxes."""
    return [
        [
            sg.Checkbox(
                i18n.t("gui.checkboxes.modules"),
                key="process_modules",
                default=config["process_modules"]
            ),
            sg.Checkbox(
                i18n.t("gui.checkboxes.tests"),
                key="process_tests",
                default=config["process_tests"]
            ),
            sg.Checkbox(
                "Resources (.md, .json...)",
                key="process_resources",
                default=config.get("process_resources", False)
            ),
        ],
        [
            sg.Checkbox(
                i18n.t("gui.checkboxes.gen_tree"),
                key="generate_tree",
                default=config["generate_tree"],
                enable_events=True
            ),
        ],
        [
            sg.Text("      └─ AST symbols:", font=("Any", 8)),
            sg.Checkbox(
                i18n.t("gui.checkboxes.func"),
                key="show_functions",
                default=config["show_functions"],
                font=("Any", 8)
            ),
            sg.Checkbox(
                i18n.t("gui.checkboxes.cls"),
                key="show_classes",
                default=config["show_classes"],
                font=("Any", 8)
            ),
            sg.Checkbox(
                i18n.t("gui.checkboxes.meth"),
                key="show_methods",
                default=config["show_methods"],
                font=("Any", 8)
            ),
        ]
    ]


def _get_io_frame(config: Dict[str, Any]) -> List[List[sg.Element]]:
    """Create the input/output path selection section."""
    return [
        [sg.Text(i18n.t("gui.sections.input"))],
        [
            sg.Input(
                default_text=config["input_path"],
                key="input_path",
                expand_x=True
            ),
            sg.Button(i18n.t("gui.buttons.explore"), key="btn_browse_in")
        ],
        [sg.Text(i18n.t("gui.sections.output"))],
        [
            sg.Input(
                default_text=config["output_base_dir"],
                key="output_base_dir",
                expand_x=True
            ),
            sg.Button(i18n.t("gui.buttons.examine"), key="btn_browse_out")
        ],
        [
            sg.Text(i18n.t("gui.sections.sub_output")),
            sg.Input(
                config["output_subdir_name"],
                size=(15, 1),
                key="output_subdir_name"
            ),
            sg.Text(i18n.t("gui.sections.prefix")),
            sg.Input(config["output_prefix"], size=(15, 1), key="output_prefix"),
        ],
    ]


def create_main_window(
        profile_names: List[str],
        config: Dict[str, Any]
) -> sg.Window:
    """
    Construct and return the main application window.

    Args:
        profile_names: List of available profile names for the dropdown.
        config: Current configuration dictionary for default values.

    Returns:
        Configured PySimpleGUI Window object.
    """
    sg.theme("SystemDefault")

    frame_profiles = _get_profiles_frame(profile_names)
    frame_content = _get_content_frame(config)
    io_layout = _get_io_frame(config)

    layout = [
        [sg.Menu(_get_menu_def())],
        [sg.Column(frame_profiles, expand_x=True)],
        [sg.HorizontalSeparator()],
        # Input/Output Section
        *io_layout,
        # Content Section
        [sg.Frame(i18n.t("gui.sections.content"), frame_content, expand_x=True)],
        # Format Section
        [sg.Frame(i18n.t("gui.sections.format"), [[
            sg.Checkbox(
                i18n.t("gui.checkboxes.individual"),
                key="create_individual_files",
                default=config["create_individual_files"]
            ),
            sg.Checkbox(
                i18n.t("gui.checkboxes.unified"),
                key="create_unified_file",
                default=config["create_unified_file"]
            ),
        ]], expand_x=True)],
        # Filters & Advanced Section
        [
            sg.Text("Extension Stack:", font=("Any", 8, "bold")),
            sg.Combo(
                ["-- Select --"] + sorted(list(cfg.DEFAULT_STACKS.keys())),
                key="-STACK-",
                enable_events=True,
                readonly=True
            ),
            sg.Text("Target Model:", font=("Any", 8, "bold")),
            sg.Combo(
                ["GPT-4o / GPT-5", "Claude 3.5", "Gemini Pro"],
                key="target_model",
                default_value=config.get("target_model"),
                readonly=True
            )
        ],
        [
            sg.Text("Extensions:"),
            sg.Input(
                ",".join(config["extensions"]),
                key="extensions",
                expand_x=True
            )
        ],
        [
            sg.Text("Include:"),
            sg.Input(
                ",".join(config["include_patterns"]),
                key="include_patterns",
                expand_x=True
            )
        ],
        [
            sg.Text("Exclude:"),
            sg.Input(
                ",".join(config["exclude_patterns"]),
                key="exclude_patterns",
                expand_x=True
            )
        ],
        [
            sg.Checkbox(
                i18n.t("gui.checkboxes.gitignore"),
                key="respect_gitignore",
                default=config.get("respect_gitignore", True)
            ),
            sg.Checkbox(
                "Sanitize Secrets",
                key="enable_sanitizer",
                default=config.get("enable_sanitizer", True)
            ),
            sg.Checkbox(
                "Mask Paths",
                key="mask_user_paths",
                default=config.get("mask_user_paths", True)
            ),
            sg.Checkbox(
                "Minify",
                key="minify_output",
                default=config.get("minify_output", False)
            ),
            sg.Checkbox(
                i18n.t("gui.checkboxes.log_err"),
                key="save_error_log",
                default=config["save_error_log"]
            )
        ],
        # Status & Actions
        [sg.Text("", key="-STATUS-", visible=False, font=("Any", 10, "bold"))],
        [
            sg.Button(
                i18n.t("gui.buttons.simulate"),
                key="btn_simulate",
                button_color=("white", "#007ACC")
            ),
            sg.Button(
                i18n.t("gui.buttons.process"),
                key="btn_process",
                button_color=("white", "green")
            ),
            sg.Push(),
            sg.Button(i18n.t("gui.buttons.reset"), key="btn_reset"),
            sg.Button(
                i18n.t("gui.buttons.exit"),
                key="btn_exit",
                button_color=("white", "red")
            ),
        ],
        # Footer
        [
            sg.Text(
                f"v{cfg.CURRENT_CONFIG_VERSION}",
                font=("Any", 7),
                text_color="gray"
            ),
            sg.Push(),
            sg.Text(
                "",
                key="-UPDATE_BAR-",
                font=("Any", 7),
                text_color="blue",
                enable_events=True
            )
        ]
    ]

    return sg.Window(
        f"Transcriptor4AI - v{cfg.CURRENT_CONFIG_VERSION}",
        layout,
        finalize=True,
        resizable=True
    )