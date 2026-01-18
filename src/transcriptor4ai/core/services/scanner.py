from __future__ import annotations

"""
File Discovery and Filtering Service.

Provides high-level abstractions for traversing project directories, 
applying complex filtering rules (including .gitignore support), 
and classifying files for the transcription pipeline.
"""

import logging
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

from transcriptor4ai.core.pipeline.components.filters import (
    compile_patterns,
    default_exclude_patterns,
    default_include_patterns,
    is_resource_file,
    is_test,
    load_gitignore_patterns,
    matches_any,
    matches_include,
)
from transcriptor4ai.domain.transcription_models import TranscriptionError

logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API (DISCOVERY SERVICES)
# ==============================================================================

def yield_project_files(
        input_path: str,
        extensions: List[str],
        include_rx: List[re.Pattern],
        exclude_rx: List[re.Pattern],
        process_modules: bool,
        process_tests: bool,
        process_resources: bool,
) -> Iterable[Dict[str, str]]:
    """
    Traverse the filesystem and yield files that satisfy the filtering criteria.

    Performs an optimized walk of the directory tree, pruning excluded
    directories early and classifying each file to determine its eligibility
    for processing.

    Args:
        input_path: Absolute path to the project root.
        extensions: Whitelist of allowed file extensions.
        include_rx: Compiled regex patterns for inclusion.
        exclude_rx: Compiled regex patterns for exclusion.
        process_modules: Flag to allow source logic files.
        process_tests: Flag to allow test suite files.
        process_resources: Flag to allow non-code resource files.

    Yields:
        Dict[str, str]: Metadata for each valid file found, including:
                        - file_path: Absolute path.
                        - rel_path: Relative path from root.
                        - ext: File extension.
                        - file_name: Base filename.
    """
    input_path_abs = os.path.abspath(input_path)

    for root, dirs, files in os.walk(input_path_abs):
        # In-place directory pruning to optimize traversal
        dirs[:] = [d for d in dirs if not matches_any(d, exclude_rx)]
        dirs.sort()
        files.sort()

        for file_name in files:
            if matches_any(file_name, exclude_rx):
                continue

            if not matches_include(file_name, include_rx):
                continue

            _, ext = os.path.splitext(file_name)
            should_process = False

            # Classification logic
            if process_resources and is_resource_file(file_name):
                should_process = True
            elif process_tests and is_test(file_name):
                should_process = True
            elif process_modules:
                if ext in extensions or file_name in extensions:
                    should_process = True

            if not should_process:
                continue

            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, input_path_abs)

            yield {
                "file_path": file_path,
                "rel_path": rel_path,
                "ext": ext,
                "file_name": file_name,
            }


def prepare_filtering_rules(
        input_path: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
        respect_gitignore: bool
) -> Tuple[List[re.Pattern], List[re.Pattern]]:
    """
    Compile and aggregate all patterns into actionable regex objects.

    Integrates user-defined patterns with system defaults and local
    .gitignore rules to build a comprehensive filtering context.

    Args:
        input_path: Path to the project root.
        include_patterns: Optional list of raw inclusion regexes.
        exclude_patterns: Optional list of raw exclusion regexes.
        respect_gitignore: Whether to parse local .gitignore files.

    Returns:
        Tuple[List[re.Pattern], List[re.Pattern]]: (Include Patterns, Exclude Patterns).
    """
    input_path_abs = os.path.abspath(input_path)

    final_includes = include_patterns if include_patterns is not None else default_include_patterns()
    final_exclusions = list(exclude_patterns) if exclude_patterns is not None else default_exclude_patterns()

    if respect_gitignore:
        git_patterns = load_gitignore_patterns(input_path_abs)
        if git_patterns:
            logger.debug(f"Loaded {len(git_patterns)} patterns from .gitignore")
            final_exclusions.extend(git_patterns)

    return compile_patterns(final_includes), compile_patterns(final_exclusions)


def finalize_error_reporting(
        save_error_log: bool,
        error_output_path: str,
        errors: List[TranscriptionError]
) -> str:
    """
    Persist collected execution errors to a dedicated log file.

    Formats and saves the list of failed operations to disk to provide
    transparency during the transcription process.

    Args:
        save_error_log: Permission flag to write the file.
        error_output_path: Target filesystem path for the error report.
        errors: Collection of errors encountered during execution.

    Returns:
        str: The path to the generated error log, or an empty string if not saved.
    """
    actual_error_path = ""
    if save_error_log and errors:
        try:
            # Ensure parent directory exists before writing
            os.makedirs(os.path.dirname(os.path.abspath(error_output_path)), exist_ok=True)

            with open(error_output_path, "w", encoding="utf-8") as f:
                f.write("TRANSCRIPTION ERRORS REPORT:\n")
                f.write("=" * 80 + "\n")
                for err_item in errors:
                    f.write(f"FILE: {err_item.rel_path}\n")
                    f.write(f"ERROR: {err_item.error}\n")
                    f.write("-" * 80 + "\n")
            actual_error_path = error_output_path
        except OSError as e:
            logger.error(f"Failed to persist error report to '{error_output_path}': {e}")

    return actual_error_path