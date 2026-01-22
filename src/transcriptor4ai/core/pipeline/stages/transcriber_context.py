from __future__ import annotations

import hashlib
import json

import os
import threading
from typing import Tuple, Dict, Any

from transcriptor4ai.core.pipeline.components.writer import initialize_output_file
from transcriptor4ai.infra.fs import safe_mkdir


def initialize_env(
        modules_path: str,
        tests_path: str,
        resources_path: str,
        error_path: str,
        processing_depth: str,
        process_tests: bool,
        process_resources: bool
) -> Tuple[Dict[str, threading.Lock], Dict[str, str]]:
    """Initialize output directory structure, file headers, and thread locks."""
    for p in [modules_path, tests_path, resources_path, error_path]:
        safe_mkdir(os.path.dirname(os.path.abspath(p)))

    # Thread locks ensure that multiple workers don't corrupt the shared output files
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

    # Only initialize module file if depth is not tree_only
    if processing_depth != "tree_only":
        initialize_output_file(modules_path, "SCRIPTS/MODULES:")
    if process_tests:
        initialize_output_file(tests_path, "TESTS:")
    if process_resources:
        initialize_output_file(resources_path, "RESOURCES (CONFIG/DATA/DOCS):")

    return locks, output_paths


def generate_config_hash(*args: Any) -> str:
    """Generate a unique fingerprint for the current processing configuration."""
    raw = json.dumps(args, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
