from __future__ import annotations

"""
Pipeline Metrics and Statistics Helper.

Provides specialized utilities for updating execution counters and 
categorizing file processing events. Centralizes the logic for 
interpreting file types into reporting metrics (Modules, Tests, Resources).
"""

import logging
from typing import Any, Dict

from transcriptor4ai.application.pipeline.components.file_filters import (
    is_resource_file,
    is_test,
)

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC METRICS API
# ==============================================================================

def increment_mode_counters(
        file_data: Dict[str, Any],
        results: Dict[str, Any],
        processing_depth: str,
        process_tests: bool,
        process_resources: bool,
) -> None:
    """
    Update global transcription counters based on file classification.

    This helper interprets the nature of a processed file (or a cache hit)
    and increments the corresponding counter in the results dictionary.

    Args:
        file_data: Metadata dictionary of the processed file.
        results: Global accumulator for metrics (modified in-place).
        processing_depth: Logic depth strategy ('full', 'skeleton', 'tree_only').
        process_tests: Config flag for test inclusion.
        process_resources: Config flag for resource inclusion.
    """
    # 1. VALIDATE: If depth is tree-only, content counters remain unchanged
    if processing_depth == "tree_only":
        return

    # 2. CLASSIFY: Identify the specific metric category
    file_name = file_data.get("file_name", "")

    # Priority A: Test Suites
    if is_test(file_name) and process_tests:
        results["tests_written"] = results.get("tests_written", 0) + 1
        return

    # Priority B: Non-code Resources
    if is_resource_file(file_name) and process_resources:
        results["resources_written"] = results.get("resources_written", 0) + 1
        return

    # Default: Source Modules
    # Note: Resources are treated as modules if resources flag is OFF
    # but the file still passed the scanner filter.
    results["modules_written"] = results.get("modules_written", 0) + 1


def initialize_results_dict() -> Dict[str, Any]:
    """
    Construct a clean results dictionary with standard pipeline keys.

    Returns:
        Dict[str, Any]: Initialized metrics map.
    """
    return {
        "processed": 0,
        "cached": 0,
        "skipped": 0,
        "total_tokens": 0,
        "tests_written": 0,
        "modules_written": 0,
        "resources_written": 0,
        "errors": []
    }