from __future__ import annotations

"""
Transcription Context Initialization Service.

Responsible for preparing the physical and logical environment for parallel 
transcription. It handles directory creation via injected ports, initializes 
output file headers, and creates thread-safe synchronization locks.
"""

import hashlib
import json
import logging
import threading
from typing import Any, Dict, Tuple

from transcriptor4ai.application.pipeline.components.file_writer import initialize_output_file
from transcriptor4ai.domain.ports.system_port import IFileSystem

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# CONTEXT INITIALIZATION
# ==============================================================================

def initialize_env(
        fs: IFileSystem,
        modules_path: str,
        tests_path: str,
        resources_path: str,
        error_path: str,
        processing_depth: str,
        process_tests: bool,
        process_resources: bool,
) -> Tuple[Dict[str, threading.Lock], Dict[str, str]]:
    """
    Bootstrap the transcription environment.

    Args:
        fs: Injected FileSystem port implementation.
        modules_path: Destination for source code.
        tests_path: Destination for test files.
        resources_path: Destination for project resources.
        error_path: Destination for the error log.
        processing_depth: Logic depth strategy.
        process_tests: Enable test file initialization.
        process_resources: Enable resource file initialization.

    Returns:
        Tuple: (Thread locks map, Initialized paths map).
    """
    # 1. DIRECTORIES: Ensure all parent hierarchies exist using the port
    for p in [modules_path, tests_path, resources_path, error_path]:
        # Logic: We resolve the parent folder without importing 'os'
        # Split logic handled by implementation-agnostic string manipulation or port
        parent_dir = "/".join(p.replace("\\", "/").split("/")[:-1])
        if parent_dir:
            fs.safe_mkdir(parent_dir)

    # 2. SYNCHRONIZATION: Initialize locks for atomic file appending
    # Critical to prevent data corruption during high-concurrency writing
    locks = {
        "module": threading.Lock(),
        "test": threading.Lock(),
        "resource": threading.Lock(),
        "error": threading.Lock()
    }

    output_paths = {
        "module": modules_path,
        "test": tests_path,
        "resource": resources_path,
        "error": error_path
    }

    # 3. HEADERS: Perform clean initialization of output files with metadata
    if processing_depth != "tree_only":
        initialize_output_file(modules_path, "SCRIPTS/MODULES:")

    if process_tests:
        initialize_output_file(tests_path, "TESTS:")

    if process_resources:
        initialize_output_file(resources_path, "RESOURCES (CONFIG/DATA/DOCS):")

    logger.debug("TranscriptionContext: Staging environment initialized successfully.")
    return locks, output_paths


# ==============================================================================
# STATE FINGERPRINTING
# ==============================================================================

def generate_config_hash(*args: Any) -> str:
    """
    Generate a unique SHA-256 fingerprint for the current configuration.

    Used by the caching engine to detect if global settings have changed
    since the last run, forcing a cache invalidation if necessary.

    Args:
        *args: Sequence of serializable configuration values.

    Returns:
        str: MD5 hexadecimal digest of the configuration state.
    """
    # 1. SERIALIZE: Convert current settings to deterministic JSON
    raw = json.dumps(args, sort_keys=True)

    # 2. HASH: Generate fingerprint
    return hashlib.md5(raw.encode("utf-8")).hexdigest()