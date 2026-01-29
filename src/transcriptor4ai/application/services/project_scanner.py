from __future__ import annotations

"""
Project Scanning and File Discovery Service.

Provides a high-performance traversal engine for project directories. 
Integrates regex-based filtering, .gitignore compliance, and polyglot 
file classification to feed the transcription pipeline.
"""

import logging
import os
import re
from typing import Iterable, List, Optional, Tuple, TypedDict

from transcriptor4ai.application.pipeline.components.file_filters import (
    compile_patterns,
    default_exclude_patterns,
    default_include_patterns,
    is_resource_file,
    is_test,
    load_gitignore_patterns,
    matches_any,
    matches_include,
)
from transcriptor4ai.domain.entities.transcription_error import TranscriptionError
from transcriptor4ai.domain.ports.system_port import IFileSystem

logger = logging.getLogger(__name__)


# ==============================================================================
# DATA MODELS (INTERNAL TYPE SAFETY)
# ==============================================================================

class FileMetadata(TypedDict, total=False):
    """Schema for file discovery events."""
    status: str  # "process" | "skipped"
    file_path: str  # Absolute path
    rel_path: str  # Path relative to project root
    ext: str  # File extension including dot
    file_name: str  # Base name


# ==============================================================================
# PROJECT SCANNER SERVICE
# ==============================================================================

class ProjectScannerService:
    """
    Application service responsible for project structure inventory
    and file categorization.
    """

    def __init__(self, fs_adapter: IFileSystem) -> None:
        """
        Initialize the scanner with a filesystem port.
        """
        self._fs = fs_adapter

    # --------------------------------------------------------------------------
    # CORE DISCOVERY LOGIC
    # --------------------------------------------------------------------------

    def yield_project_files(
            self,
            input_path: str,
            extensions: List[str],
            include_rx: List[re.Pattern],
            exclude_rx: List[re.Pattern],
            process_modules: bool,
            process_tests: bool,
            process_resources: bool,
    ) -> Iterable[FileMetadata]:
        """
        Traverse the filesystem and yield files compliant with current filters.

        Args:
            input_path: Absolute project root path.
            extensions: Allowed extensions whitelist.
            include_rx: Compiled inclusion regexes.
            exclude_rx: Compiled exclusion regexes.
            process_modules: Flag for source logic files.
            process_tests: Flag for test suite files.
            process_resources: Flag for configuration/documentation files.

        Yields:
            FileMetadata: Typed dictionary with file details and processing status.
        """
        input_path_abs = os.path.abspath(input_path)

        for root, dirs, files in os.walk(input_path_abs):
            # 1. OPTIMIZATION: Prune directories in-place to avoid deep walking excluded paths
            dirs[:] = [d for d in dirs if not matches_any(d, exclude_rx)]
            dirs.sort()
            files.sort()

            for file_name in files:
                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, input_path_abs)
                _, ext = os.path.splitext(file_name)

                # 2. VALIDATION: Check against high-priority exclusion blacklist
                if matches_any(file_name, exclude_rx):
                    yield {"status": "skipped", "rel_path": rel_path}
                    continue

                # 3. VALIDATION: Check against inclusion whitelist
                if not matches_include(file_name, include_rx):
                    yield {"status": "skipped", "rel_path": rel_path}
                    continue

                # 4. CLASSIFICATION: Determine processing eligibility based on type
                # --------------------------------------------------------------
                should_process = False
                file_is_test = is_test(file_name)
                file_is_resource = is_resource_file(file_name)

                if file_is_test:
                    if process_tests:
                        should_process = True
                    else:
                        yield {"status": "skipped", "rel_path": rel_path}
                        continue

                elif file_is_resource:
                    if process_resources:
                        should_process = True

                # If not explicitly marked yet, check if it qualifies as a source module
                if not should_process and process_modules:
                    if ext in extensions or file_name in extensions:
                        should_process = True

                # 5. DECISION
                if not should_process:
                    yield {"status": "skipped", "rel_path": rel_path}
                    continue

                # 6. EMIT
                yield {
                    "status": "process",
                    "file_path": file_path,
                    "rel_path": rel_path,
                    "ext": ext,
                    "file_name": file_name,
                }

    # --------------------------------------------------------------------------
    # RULE PREPARATION
    # --------------------------------------------------------------------------

    def prepare_filtering_rules(
            self,
            input_path: str,
            include_patterns: Optional[List[str]],
            exclude_patterns: Optional[List[str]],
            respect_gitignore: bool
    ) -> Tuple[List[re.Pattern], List[re.Pattern]]:
        """
        Aggregate and compile regex rules from defaults, user config and gitignore.

        Returns:
            Tuple[List[re.Pattern], List[re.Pattern]]: (Inclusion, Exclusion) regexes.
        """
        input_path_abs = os.path.abspath(input_path)

        # Resolve inclusions
        final_includes = include_patterns if include_patterns is not None else default_include_patterns()

        # Resolve exclusions (System defaults + User custom)
        final_exclusions = list(exclude_patterns) if exclude_patterns is not None else default_exclude_patterns()

        # 1. GITIGNORE: Ingest local ignore rules if enabled
        if respect_gitignore:
            git_patterns = load_gitignore_patterns(input_path_abs)
            if git_patterns:
                logger.debug(f"ProjectScanner: Loaded {len(git_patterns)} rules from .gitignore")
                final_exclusions.extend(git_patterns)

        # 2. COMPILE: Transform strings to active regex objects
        return compile_patterns(final_includes), compile_patterns(final_exclusions)

    # --------------------------------------------------------------------------
    # REPORTING UTILITIES
    # --------------------------------------------------------------------------

    def finalize_error_reporting(
            self,
            save_error_log: bool,
            error_output_path: str,
            errors: List[TranscriptionError]
    ) -> str:
        """
        Persist execution errors encountered during scanning/transcription.

        Args:
            save_error_log: User permission to write the log file.
            error_output_path: Destination path for the report.
            errors: List of error objects to format.

        Returns:
            str: Path to the generated log, or empty string if aborted.
        """
        actual_error_path = ""
        if not (save_error_log and errors):
            return actual_error_path

        try:
            # Normalize path to ensure consistency across OS (fixes test assertions)
            abs_error_path = os.path.abspath(error_output_path)
            error_dir = os.path.dirname(abs_error_path)
            self._fs.safe_mkdir(error_dir)

            with open(abs_error_path, "w", encoding="utf-8") as f:
                f.write("TRANSCRIPTION ERRORS REPORT:\n")
                f.write("=" * 80 + "\n")

                for err_item in errors:
                    f.write(f"FILE: {err_item.rel_path}\n")
                    f.write(f"ERROR: {err_item.error}\n")
                    f.write("-" * 80 + "\n")

            actual_error_path = error_output_path
            logger.info(f"ProjectScanner: Error report persisted at {error_output_path}")

        except OSError as e:
            logger.error(f"ProjectScanner: Critical IO failure saving error log: {e}")

        return actual_error_path