from __future__ import annotations

"""
Transcription Execution Engine.

Consumes the Project Scanner generator to orchestrate parallel workers and 
manage the caching lifecycle. It handles synchronization of results and 
coordinates cache-hit workflows without being coupled to the physical 
writing or metrics categorization logic.
"""

import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

# Components and Services
from transcriptor4ai.application.pipeline.components.file_filters import determine_target_mode
from transcriptor4ai.application.pipeline.components.file_writer import append_entry
from transcriptor4ai.application.pipeline.components.metrics_helper import increment_mode_counters
from transcriptor4ai.application.transformation.privacy_sanitizer import PrivacySanitizerService
from transcriptor4ai.application.pipeline.stages.worker import process_file_task
from transcriptor4ai.application.services.project_scanner import ProjectScannerService
from transcriptor4ai.domain.entities.transcription_error import TranscriptionError
from transcriptor4ai.domain import ICacheRepository, IUserContext

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# ENGINE: PARALLEL WORKER ORCHESTRATION
# ==============================================================================

def execute_parallel_workers(
        scanner_service: ProjectScannerService,
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
        cache_repo: ICacheRepository,
        config_hash: str,
        user_context: IUserContext,
        cancellation_event: Optional[threading.Event] = None,
) -> None:
    """
    Orchestrate the transcription process by coordinating scanner data,
    caching checks, and parallel task execution.
    """
    # 1. SETUP: Initialize the parallel execution pool
    sanitizer = PrivacySanitizerService(user_context)

    tasks = []
    with ThreadPoolExecutor(thread_name_prefix="TranscriptionWorker") as executor:

        # Modules processing flag based on current depth strategy
        process_modules_flag = processing_depth != "tree_only"

        # 2. DISCOVERY: Iterate through files provided by the scanner service
        for file_data in scanner_service.yield_project_files(
                input_path=input_path,
                extensions=extensions,
                include_rx=include_rx,
                exclude_rx=exclude_rx,
                process_modules=process_modules_flag,
                process_tests=process_tests,
                process_resources=process_resources
        ):
            # Check for external abort signal
            if cancellation_event and cancellation_event.is_set():
                break

            if file_data.get("status") == "skipped":
                results["skipped"] += 1
                continue

            if file_data.get("status") == "process":
                f_path = file_data["file_path"]

                # 3. CACHE HIT: Verify if the file is already processed in current state
                try:
                    stat = os.stat(f_path)
                    # We use the persistence implementation's utility for hash consistency
                    from transcriptor4ai.shared.hashing import compute_composite_hash
                    comp_hash = compute_composite_hash(
                        f_path, stat.st_mtime, stat.st_size, config_hash
                    )

                    cached_entry = cache_repo.get_entry(comp_hash)

                    if cached_entry is not None:
                        content, t_count = cached_entry

                        # 1. ROUTING: Determine target destination based on domain policy
                        target_mode = determine_target_mode(
                            file_data["file_name"],
                            processing_depth,
                            process_tests,
                            process_resources
                        )

                        if target_mode != "skip":
                            lock = locks.get(target_mode)
                            out_path = output_paths.get(target_mode)

                            if lock and out_path:
                                with lock:
                                    append_entry(out_path, file_data["rel_path"], content)

                        # 2. METRICS: Update global counters
                        results["processed"] += 1
                        results["cached"] += 1
                        results["total_tokens"] += t_count

                        increment_mode_counters(
                            file_data, results, processing_depth,
                            process_tests, process_resources
                        )
                        continue

                except (OSError, AttributeError):
                    comp_hash = ""

                # 4. DISPATCH: Submit the processing task for a cache-miss
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
                    sanitizer_service=sanitizer,
                    composite_hash=comp_hash
                ))

        # 5. CONSOLIDATION: Aggregate results from the worker pool
        for future in as_completed(tasks):
            if cancellation_event and cancellation_event.is_set():
                continue

            try:
                worker_res = future.result()
                if worker_res["ok"]:
                    results["processed"] += 1
                    results["total_tokens"] += worker_res.get("token_count", 0)

                    # Update Persistence: Store processed result in cache
                    if worker_res.get("processed_content") and worker_res.get("composite_hash"):
                        cache_repo.set_entry(
                            worker_res["composite_hash"],
                            worker_res["file_path"],
                            worker_res["processed_content"],
                            worker_res.get("token_count", 0)
                        )

                    # Triage results by mode for the final summary
                    mode = worker_res.get("mode")
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
            except Exception as e:
                logger.error(f"Engine: Synchronization failure in worker pool: {e}")