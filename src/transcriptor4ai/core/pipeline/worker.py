from __future__ import annotations

import threading
from typing import Dict, Any

from transcriptor4ai.core.pipeline.filters import is_test, is_resource_file
from transcriptor4ai.core.pipeline.reader import stream_file_content
from transcriptor4ai.core.pipeline.writer import _append_entry


def process_file_task(
        file_path: str,
        rel_path: str,
        ext: str,
        file_name: str,
        process_modules: bool,
        process_tests: bool,
        process_resources: bool,
        enable_sanitizer: bool,
        mask_user_paths: bool,
        minify_output: bool,
        locks: Dict[str, threading.Lock],
        output_paths: Dict[str, str]
) -> Dict[str, Any]:
    """
    Atomic worker task: processes a single file and appends it to output.
    """
    # 1. Classification
    file_is_test = is_test(file_name)
    file_is_resource = is_resource_file(file_name)
    target_mode = "skip"

    if file_is_test:
        if process_tests: target_mode = "test"
    elif file_is_resource:
        if process_resources:
            target_mode = "resource"
        elif process_modules:
            target_mode = "module"
    else:
        if process_modules: target_mode = "module"

    if target_mode == "skip":
        return {"ok": False, "rel_path": rel_path, "error": "Filtered by mode", "mode": "skip"}

    # 2. Transcription Logic
    try:
        line_iterator = stream_file_content(file_path)

        lock = locks[target_mode]
        with lock:
            _append_entry(
                output_path=output_paths[target_mode],
                rel_path=rel_path,
                line_iterator=line_iterator,
                extension=ext,
                enable_sanitizer=enable_sanitizer,
                mask_user_paths=mask_user_paths,
                minify_output=minify_output
            )
        return {"ok": True, "mode": target_mode, "rel_path": rel_path}

    except (OSError, UnicodeDecodeError) as e:
        return {"ok": False, "rel_path": rel_path, "error": str(e), "mode": target_mode}