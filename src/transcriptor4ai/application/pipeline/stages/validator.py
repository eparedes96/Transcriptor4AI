from __future__ import annotations

"""
Configuration Validation Stage.

Acts as the primary gatekeeper for the pipeline. It transforms untrusted 
inputs into strictly typed domain configurations by coordinating shared 
converters and enforcing domain integrity rules.
"""

import logging
import os
from typing import Any, Dict, List, Tuple

from transcriptor4ai.application.common.file_filters import (
    default_exclude_patterns,
    default_extensions,
    default_include_patterns,
)
from transcriptor4ai.domain.entities.app_config import (
    apply_config_integrity,
    get_default_config,
)
from transcriptor4ai.shared import converters as conv

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# STAGE: CONFIGURATION VALIDATION
# ==============================================================================

def validate_config(
    config: Any,
    base_path: str | None = None,
    *,
    strict: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate and normalize the provided configuration dictionary.

    Args:
        config: Raw configuration data (usually from CLI or GUI).
        base_path: Initial path used for domain default generation.
        strict: If True, raises TypeError on type mismatch instead of coercing.

    Returns:
        Tuple[Dict[str, Any], List[str]]: Normalized configuration and warnings.
    """
    warnings: List[str] = []

    # 1. SETUP: Resolve domain defaults with injected context
    target_base = base_path or os.getcwd()
    defaults = get_default_config(target_base)

    # 2. VALIDATION: Ensure input root integrity
    if not isinstance(config, dict):
        msg = f"Invalid config type: expected dict, received {type(config).__name__}."
        if strict:
            raise TypeError(msg)
        warnings.append(f"{msg} Using defaults.")
        logger.warning(msg)
        return defaults, warnings

    # Initialize working dictionary
    merged: Dict[str, Any] = dict(defaults)
    merged.update(config)

    # 3. SCHEMA: Define field clusters for batch scrubbing
    string_fields = [
        "input_path", "output_base_dir", "output_subdir_name",
        "output_prefix", "target_model", "processing_depth"
    ]

    bool_fields = [
        "process_modules", "process_tests", "process_resources",
        "create_individual_files", "create_unified_file",
        "show_functions", "show_classes", "show_methods",
        "generate_tree", "print_tree", "save_error_log", "respect_gitignore",
        "enable_sanitizer", "mask_user_paths", "minify_output"
    ]

    list_fields_map = {
        "extensions": default_extensions(),
        "include_patterns": default_include_patterns(),
        "exclude_patterns": default_exclude_patterns(),
    }

    # 4. SCRUBBING: Apply type coercion via shared converters
    for field in string_fields:
        merged[field] = conv.to_str(merged.get(field), defaults.get(field, ""))

    for field in bool_fields:
        merged[field] = conv.scrub_bool(merged.get(field), defaults.get(field, False), strict=strict)

    for field, fallback in list_fields_map.items():
        merged[field] = conv.to_list_str(merged.get(field), fallback)

    # 5. NORMALIZATION: Sanitize file extensions
    normalized_exts = [conv.normalize_extension(e) for e in merged["extensions"]]
    merged["extensions"] = [e for e in normalized_exts if e]

    # 6. DOMAIN INTEGRITY: Enforce business rules defined in the entity layer
    # This prevents invalid states (e.g., modules=OFF with depth='full')
    apply_config_integrity(merged)

    return merged, warnings