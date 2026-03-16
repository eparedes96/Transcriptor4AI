from __future__ import annotations

"""
Configuration Domain Entities.

Defines the core data structures and integrity rules for the application 
state and session configuration. This module implements the "Domain Model" 
pattern, centralizing business logic validation and ensuring consistency 
for polymorphic output strategies.
"""

from typing import Any, Dict

from transcriptor4ai.domain.entities.formatting_options import OutputFormat
from transcriptor4ai.shared import constants as const


# ==============================================================================
# DOMAIN CONSTANTS
# ==============================================================================
DEFAULT_OUTPUT_SUBDIR = "transcript"


# ==============================================================================
# CONFIGURATION FACTORIES (PUBLIC API)
# ==============================================================================

def get_default_config(base_path: str) -> Dict[str, Any]:
    """
    Generate the default execution configuration for a transcription session.

    This dictionary controls the behavior of the application pipeline, including
    I/O paths, filtering rules, and optimization flags.

    Args:
        base_path: The filesystem path to use as root for input and output.

    Returns:
        Dict[str, Any]: Default session configuration values.
    """
    return {
        # 1. IO SETTINGS: Path resolution and naming
        "input_path": base_path,
        "output_base_dir": base_path,
        "output_subdir_name": DEFAULT_OUTPUT_SUBDIR,
        "output_prefix": const.DEFAULT_OUTPUT_PREFIX,

        # 2. SCOPE SETTINGS: Content targeting
        "process_modules": True,
        "processing_depth": "full",  # Strategy: "full", "skeleton", "tree_only"
        "process_tests": True,
        "process_resources": True,

        # 3. OUTPUT STRATEGY (v2.2+): Format and aggregation
        "output_format": OutputFormat.PLAIN_TEXT.value,
        "custom_preamble": "",
        "create_individual_files": True,
        "create_unified_file": True,

        # 4. FILTERS: Inclusion/Exclusion rules
        "extensions": [".py"],
        "include_patterns": [".*"],
        "exclude_patterns": [
            r"^__init__\.py$",
            r".*\.pyc$",
            r"^(__pycache__|\.git|\.idea|\.vscode|node_modules)$",
            r"^\."
        ],
        "respect_gitignore": False,
        "target_model": const.DEFAULT_MODEL_KEY,

        # 5. ANALYSIS & TREE: Static visualization
        "generate_tree": True,
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "print_tree": True,

        # 6. PRIVACY & OPTIMIZATION: Content transformation
        "enable_sanitizer": False,
        "mask_user_paths": False,
        "minify_output": False,

        # 7. DIAGNOSTICS: Failure reporting
        "save_error_log": False
    }


def get_default_app_state(base_path: str) -> Dict[str, Any]:
    """
    Generate the complete root application state structure.

    Encapsulates global application settings, user-defined profiles,
    and the state of the last active session for persistence.

    Args:
        base_path: The filesystem path to use for the initial session.

    Returns:
        Dict[str, Any]: The full application state schema.
    """
    return {
        "version": const.CURRENT_CONFIG_VERSION,
        "app_settings": {
            "theme": "SystemDefault",
            "locale": "en",
            "allow_telemetry": True,
            "auto_check_updates": True,
            "last_update_check": ""
        },
        "last_session": get_default_config(base_path),
        "saved_profiles": {},
        "custom_stacks": {}
    }


# ==============================================================================
# DOMAIN LOGIC: INTEGRITY RULES
# ==============================================================================

def apply_config_integrity(cfg: Dict[str, Any]) -> None:
    """
    Enforce business rules to ensure logical consistency within the config.

    This function modifies the dictionary in-place to prevent invalid
    combinations of processing flags or unsupported formatting options.
    """
    # 1. SCOPE SYNC: Synchronize modules flag with processing depth
    process_modules = cfg.get("process_modules", True)
    depth = cfg.get("processing_depth", "full")

    # Rule A: modules=False forces depth='tree_only'
    if not process_modules and depth != "tree_only":
        cfg["processing_depth"] = "tree_only"

    # Rule B: depth='tree_only' forces modules=False
    if depth == "tree_only":
        cfg["process_modules"] = False

    # 2. FORMATTING VALIDATION: Ensure output_format is a recognized Enum value
    raw_format = str(cfg.get("output_format", OutputFormat.PLAIN_TEXT.value))
    validated_format = OutputFormat.from_str(raw_format)
    cfg["output_format"] = validated_format.value

    # 3. PREAMBLE NORMALIZATION: Clean user-defined instructions
    preamble = cfg.get("custom_preamble", "")
    if isinstance(preamble, str):
        cfg["custom_preamble"] = preamble.strip()
    else:
        cfg["custom_preamble"] = ""

    # 4. XML CONSTRAINTS: Force aggregation for hierarchical formats

    if validated_format == OutputFormat.XML:
        cfg["create_unified_file"] = True