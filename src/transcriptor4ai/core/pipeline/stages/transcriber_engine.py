from __future__ import annotations

import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from transcriptor4ai.core.pipeline.stages.worker import process_file_task
from transcriptor4ai.core.services.cache import CacheService
from transcriptor4ai.core.services.scanner import yield_project_files
from transcriptor4ai.domain.transcription_models import TranscriptionError


def execute_parallel_workers(
        input_path: str,
        extensions: List[str],
        include_rx: List[re.Pattern],
        exclude_rx: List[re.Pattern],
        processing_depth: str,
        process_tests: bool,
        process_resources: bool,
        enable_sanitizer: bool,
        mask_user_paths: bool,
        minify_output: bool,
        locks: Dict[str, threading.Lock],
        output_paths: Dict[str, str],
        results: Dict[str, Any],
        cache_service: CacheService,
        config_hash: str,
        cancellation_event: Optional[threading.Event] = None
) -> None:
    """Consumes the Scanner's generator, manages Caching, and dispatches workers."""
    tasks = []

    with ThreadPoolExecutor(thread_name_prefix="TranscriptionWorker") as executor:

        # Legacy backward compatibility check for Scanner
        process_modules_flag = processing_depth != "tree_only"

        for file_data in yield_project_files(
                input_path=input_path,
                extensions=extensions,
                include_rx=include_rx,
                exclude_rx=exclude_rx,
                process_modules=process_modules_flag,
                process_tests=process_tests,
                process_resources=process_resources
        ):
            if cancellation_event and cancellation_event.is_set():
                break

            if file_data.get("status") == "skipped":
                results["skipped"] += 1
                continue

            if file_data.get("status") == "process":
                f_path = file_data["file_path"]

                # Cache Hit Check
                try:
                    stat = os.stat(f_path)
                    comp_hash = cache_service.compute_composite_hash(
                        f_path, stat.st_mtime, stat.st_size, config_hash
                    )
                    cached_entry = cache_service.get_entry(comp_hash)

                    if cached_entry is not None:
                        # cached_entry is Tuple[str, int] -> (content, token_count)
                        content, t_count = cached_entry

                        write_cached_content(
                            content,
                            file_data,
                            locks,
                            output_paths,
                            processing_depth,
                            process_tests,
                            process_resources
                        )
                        results["processed"] += 1
                        results["cached"] += 1
                        results["total_tokens"] += t_count

                        # Increment specific counters for reporting
                        increment_mode_counters(
                            file_data,
                            results,
                            processing_depth,
                            process_tests,
                            process_resources
                        )
                        continue

                except OSError:
                    comp_hash = ""

                # Dispatch Worker
                tasks.append(executor.submit(
                    process_file_task,
                    file_path=f_path,
                    rel_path=file_data["rel_path"],
                    ext=file_data["ext"],
                    file_name=file_data["file_name"],
                    processing_depth=processing_depth,
                    process_tests=process_tests,
                    process_resources=process_resources,
                    enable_sanitizer=enable_sanitizer,
                    mask_user_paths=mask_user_paths,
                    minify_output=minify_output,
                    locks=locks,
                    output_paths=output_paths,
                    composite_hash=comp_hash
                ))

        # Synchronize and aggregate worker results
        for future in as_completed(tasks):
            if cancellation_event and cancellation_event.is_set():
                continue

            worker_res = future.result()
            if worker_res["ok"]:
                results["processed"] += 1
                results["total_tokens"] += worker_res.get("token_count", 0)
                mode = worker_res.get("mode")

                # Update Cache if worker returned content + hash
                if worker_res.get("processed_content") and worker_res.get("composite_hash"):
                    cache_service.set_entry(
                        worker_res["composite_hash"],
                        worker_res["file_path"],
                        worker_res["processed_content"],
                        worker_res.get("token_count", 0)
                    )

                if mode == "test":
                    results["tests_written"] += 1
                elif mode == "module":
                    results["modules_written"] += 1
                elif mode == "resource":
                    results["resources_written"] += 1
            else:
                results["errors"].append(TranscriptionError(
                    rel_path=worker_res["rel_path"],
                    error=worker_res["error"]
                ))


def increment_mode_counters(
        file_data: Dict[str, Any],
        results: Dict[str, Any],
        depth: str,
        p_tests: bool,
        p_resources: bool
) -> None:
    """Helper to increment transcription counters for cached hits."""
    from transcriptor4ai.core.pipeline.components.filters import is_resource_file, is_test

    file_name = file_data["file_name"]
    if depth == "tree_only":
        return

    if is_test(file_name) and p_tests:
        results["tests_written"] += 1
    elif is_resource_file(file_name) and p_resources:
        results["resources_written"] += 1
    else:
        results["modules_written"] += 1


def write_cached_content(
        content: str,
        file_data: Dict[str, Any],
        locks: Dict[str, threading.Lock],
        output_paths: Dict[str, str],
        processing_depth: str,
        process_tests: bool,
        process_resources: bool
) -> None:
    """Helper to write retrieved cache content respecting headers and locks."""
    from transcriptor4ai.core.pipeline.components.filters import is_resource_file, is_test

    file_name = file_data["file_name"]
    file_is_test = is_test(file_name)
    file_is_resource = is_resource_file(file_name)
    target_mode = "skip"

    # Routing logic based on new processing_depth
    if processing_depth != "tree_only":
        if file_is_test:
            if process_tests:
                target_mode = "test"
        elif file_is_resource:
            if process_resources:
                target_mode = "resource"
            else:
                target_mode = "module"
        else:
            target_mode = "module"

    if target_mode == "skip":
        return

    separator = "-" * 200
    lock = locks.get(target_mode)
    out_path = output_paths.get(target_mode)

    if lock and out_path:
        with lock:
            with open(out_path, "a", encoding="utf-8") as out:
                out.write(f"{separator}\n")
                out.write(f"{file_data['rel_path']}\n")
                out.write(content)
                out.write("\n")
