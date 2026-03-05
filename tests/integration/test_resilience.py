from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Dict

import pytest

from transcriptor4ai.application.pipeline.orchestrator import run_pipeline
from transcriptor4ai.domain.entities.pipeline_results import PipelineResult
from transcriptor4ai.infrastructure.persistence.sqlite_cache_repo import SqliteCacheRepository
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter
from transcriptor4ai.infrastructure.system.user_context_adapter import UserContextAdapter


# ==============================================================================
# TEST GROUP: PIPELINE RESILIENCE & CHAOS TESTING
# ==============================================================================

@pytest.fixture
def resilience_env(tmp_path: Path, mock_config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a sandboxed environment with real infrastructure adapters
    to test true system resilience against disk and memory failures.
    """
    fs = FileSystemAdapter()

    # Isolate user data to tmp_path to prevent polluting real cache
    os.environ["LOCALAPPDATA"] = str(tmp_path / "appdata")
    cache = SqliteCacheRepository(fs_adapter=fs)
    user_context = UserContextAdapter()

    source_dir = tmp_path / "source_project"
    source_dir.mkdir()

    out_dir = tmp_path / "output_project"

    config = mock_config_dict.copy()
    config["input_path"] = str(source_dir)
    config["output_base_dir"] = str(out_dir)

    return {
        "fs": fs,
        "cache": cache,
        "user_context": user_context,
        "config": config,
        "source_dir": source_dir,
        "out_dir": out_dir
    }


@pytest.mark.integration
def test_pipeline_survives_partial_file_read_failures(mocker: Any, resilience_env: Dict[str, Any]) -> None:
    # 1. ARRANGE: Set up preconditions and mocks
    env = resilience_env
    source_dir = env["source_dir"]

    # Create 5 valid python files
    for i in range(5):
        (source_dir / f"file_{i}.py").write_text(f"print('Hello {i}')", encoding="utf-8")

    # CRITICAL POINT: Inject a failure specifically on file_2.py
    # We mock the reader to simulate an OS lock or permission denial during stream
    original_stream = __import__(
        "transcriptor4ai.application.pipeline.components.file_reader").application.pipeline.components.file_reader.stream_file_content

    def faulty_stream(file_path: str) -> Any:
        if "file_2.py" in file_path:
            raise OSError("Simulated Permission Denied on locked file")
        return original_stream(file_path)

    mocker.patch(
        "transcriptor4ai.application.pipeline.stages.worker.stream_file_content",
        side_effect=faulty_stream
    )

    # 2. ACT: Execute the specific behavior/method
    result: PipelineResult = run_pipeline(
        fs=env["fs"],
        cache=env["cache"],
        user_context=env["user_context"],
        config=env["config"],
        overwrite=True
    )

    # 3. ASSERT: Verify the outcome and side effects
    # Pipeline should complete successfully despite one file failing
    assert result.ok is True

    # 4 files should be processed, 1 file skipped due to error
    assert result.summary["processed"] == 4
    assert result.summary["errors"] == 1

    # The output master context should exist
    assert "unified" in result.summary["generated_files"]


@pytest.mark.integration
def test_pipeline_handles_critical_directory_creation_failure(mocker: Any, resilience_env: Dict[str, Any]) -> None:
    # 1. ARRANGE: Set up preconditions and mocks
    env = resilience_env

    # CRITICAL POINT: Mock safe_mkdir to simulate a critical infrastructure failure
    # (e.g., trying to write to a completely restricted network drive)
    mocker.patch(
        "transcriptor4ai.infrastructure.system.os_file_system.FileSystemAdapter.safe_mkdir",
        return_value=(False, "Access is completely denied by Admin")
    )

    # 2. ACT: Execute the specific behavior/method
    result: PipelineResult = run_pipeline(
        fs=env["fs"],
        cache=env["cache"],
        user_context=env["user_context"],
        config=env["config"],
        overwrite=True
    )

    # 3. ASSERT: Verify the outcome and side effects
    # Pipeline must abort gracefully at the Setup stage
    assert result.ok is False
    assert result.summary["status"] == "failed"
    assert "Access is completely denied" in result.error
    assert result.token_count == 0


@pytest.mark.integration
def test_pipeline_recovers_from_worker_thread_crashes(mocker: Any, resilience_env: Dict[str, Any]) -> None:
    # 1. ARRANGE: Set up preconditions and mocks
    env = resilience_env
    source_dir = env["source_dir"]

    # Create 3 files
    for i in range(3):
        (source_dir / f"test_{i}.py").write_text("def test(): pass", encoding="utf-8")

    # CRITICAL POINT: Simulate a violent memory or logic crash inside the thread pool
    # It must not raise an unhandled exception that brings down the main thread
    mocker.patch(
        "transcriptor4ai.application.pipeline.stages.transcriber_engine.process_file_task",
        side_effect=RuntimeError("Violent Unhandled Thread Crash")
    )

    # 2. ACT: Execute the specific behavior/method
    result: PipelineResult = run_pipeline(
        fs=env["fs"],
        cache=env["cache"],
        user_context=env["user_context"],
        config=env["config"],
        overwrite=True
    )

    # 3. ASSERT: Verify the outcome and side effects
    # The pipeline finishes, but all worker tasks resulted in logged errors
    assert result.ok is True
    assert result.summary["processed"] == 0
    assert result.summary["errors"] == 3


@pytest.mark.integration
def test_pipeline_cancels_gracefully_during_heavy_load(mocker: Any, resilience_env: Dict[str, Any]) -> None:
    # 1. ARRANGE: Set up preconditions and mocks
    env = resilience_env
    source_dir = env["source_dir"]

    # Generate a decent amount of files to simulate heavy load
    for i in range(20):
        (source_dir / f"script_{i}.py").write_text(f"# Logic {i}", encoding="utf-8")

    cancellation_event = threading.Event()

    # We introduce a tiny delay in the worker to allow the cancellation thread to fire mid-process
    original_task = __import__(
        "transcriptor4ai.application.pipeline.stages.worker").application.pipeline.stages.worker.process_file_task

    def delayed_task(*args: Any, **kwargs: Any) -> Any:
        time.sleep(0.02)
        return original_task(*args, **kwargs)

    mocker.patch(
        "transcriptor4ai.application.pipeline.stages.transcriber_engine.process_file_task",
        side_effect=delayed_task
    )

    def trigger_cancellation() -> None:
        time.sleep(0.1)  # Fire cancellation mid-flight
        cancellation_event.set()

    threading.Thread(target=trigger_cancellation, daemon=True).start()

    # 2. ACT: Execute the specific behavior/method
    result: PipelineResult = run_pipeline(
        fs=env["fs"],
        cache=env["cache"],
        user_context=env["user_context"],
        config=env["config"],
        overwrite=True,
        cancellation_event=cancellation_event
    )

    # 3. ASSERT: Verify the outcome and side effects
    # The pipeline should detect the cancellation and abort cleanly
    assert result.ok is False
    assert "Operation cancelled by user" in result.error
    assert result.summary["status"] == "failed"