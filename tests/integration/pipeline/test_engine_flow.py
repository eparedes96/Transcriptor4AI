# ==============================================================================
# TEST GROUP: TRANSCRIPTION ENGINE CORE FLOW
# ==============================================================================

import threading

import pytest

from transcriptor4ai.application.pipeline.stages.transcriber_engine import execute_parallel_workers
from transcriptor4ai.domain.entities.transcription_error import TranscriptionError


@pytest.fixture
def engine_context(mocker):
    """
    Provides a synchronized environment for testing engine orchestration.
    Ensures locks support the Context Manager protocol (with lock:).
    """
    # 1. ARRANGE: Create mocks that support 'with' statement
    mock_lock_module = mocker.MagicMock()
    mock_lock_test = mocker.MagicMock()
    mock_lock_resource = mocker.MagicMock()

    return {
        "scanner": mocker.Mock(),
        "cache": mocker.Mock(),
        "user_ctx": mocker.Mock(),
        "locks": {
            "module": mock_lock_module,
            "test": mock_lock_test,
            "resource": mock_lock_resource
        },
        "output_paths": {
            "module": "/out/modules.txt",
            "test": "/out/tests.txt",
            "resource": "/out/resources.txt"
        },
        "results": {
            "processed": 0, "cached": 0, "skipped": 0, "total_tokens": 0,
            "tests_written": 0, "modules_written": 0, "resources_written": 0, "errors": []
        }
    }


# ------------------------------------------------------------------------------
# SCENARIO: CACHE HIT LOGIC (PERFORMANCE OPTIMIZATION)
# ------------------------------------------------------------------------------

def test_engine_should_handle_cache_hits_without_workers(mocker, engine_context):
    """
    FIX FOR DETECTED BUG: Verifies that cache hits bypass worker execution
    and use thread locks correctly.
    """
    # 1. ARRANGE
    ctx = engine_context
    ctx["scanner"].yield_project_files.return_value = [
        {
            "status": "process",
            "file_path": "/src/cached.py",
            "rel_path": "cached.py",
            "ext": ".py",
            "file_name": "cached.py"
        }
    ]

    # Simulate a hit in the SQLite cache
    ctx["cache"].get_entry.return_value = ("ALREADY_PROCESSED_CONTENT", 100)

    # Mock lower-level dependencies
    mocker.patch("os.stat", return_value=mocker.Mock(st_mtime=1.0, st_size=500))
    m_worker = mocker.patch("transcriptor4ai.application.pipeline.stages.transcriber_engine.process_file_task")
    m_writer = mocker.patch("transcriptor4ai.application.pipeline.stages.transcriber_engine.append_entry")

    # 2. ACT
    execute_parallel_workers(
        scanner_service=ctx["scanner"], input_path="/src", extensions=[".py"],
        include_rx=[], exclude_rx=[], processing_depth="full",
        process_tests=True, process_resources=True, enable_sanitizer=False,
        mask_user_paths=False, minify_output=False, locks=ctx["locks"],
        output_paths=ctx["output_paths"], results=ctx["results"],
        cache_repo=ctx["cache"], config_hash="cfg_hash", user_context=ctx["user_ctx"]
    )

    # 3. ASSERT
    # Worker must NOT be spawned for cached files
    m_worker.assert_not_called()

    # Verify content was written using the 'module' lock
    m_writer.assert_called_once_with("/out/modules.txt", "cached.py", "ALREADY_PROCESSED_CONTENT")
    ctx["locks"]["module"].__enter__.assert_called_once()

    # Metrics must reflect the cache hit
    assert ctx["results"]["cached"] == 1
    assert ctx["results"]["total_tokens"] == 100


# ------------------------------------------------------------------------------
# SCENARIO: CACHE MISS AND PARALLEL EXECUTION
# ------------------------------------------------------------------------------

def test_engine_should_dispatch_to_workers_on_cache_miss(mocker, engine_context):
    """Ensures new or modified files are processed via the thread pool."""
    # 1. ARRANGE
    ctx = engine_context
    ctx["scanner"].yield_project_files.return_value = [
        {"status": "process", "file_path": "/src/new.py", "rel_path": "new.py", "ext": ".py", "file_name": "new.py"}
    ]
    ctx["cache"].get_entry.return_value = None  # Force a cache miss
    mocker.patch("os.stat", return_value=mocker.Mock(st_mtime=2.0, st_size=200))

    # Mock Worker success
    m_worker = mocker.patch(
        "transcriptor4ai.application.pipeline.stages.transcriber_engine.process_file_task",
        return_value={
            "ok": True, "mode": "module", "token_count": 42,
            "processed_content": "NEW_CONTENT", "composite_hash": "H1",
            "file_path": "/src/new.py", "rel_path": "new.py"
        }
    )

    # 2. ACT
    execute_parallel_workers(
        scanner_service=ctx["scanner"], input_path="/src", extensions=[".py"],
        include_rx=[], exclude_rx=[], processing_depth="full",
        process_tests=True, process_resources=True, enable_sanitizer=False,
        mask_user_paths=False, minify_output=False, locks=ctx["locks"],
        output_paths=ctx["output_paths"], results=ctx["results"],
        cache_repo=ctx["cache"], config_hash="H", user_context=ctx["user_ctx"]
    )

    # 3. ASSERT
    assert m_worker.call_count == 1
    # Cache must be updated with the new result
    ctx["cache"].set_entry.assert_called_once_with("H1", "/src/new.py", "NEW_CONTENT", 42)
    assert ctx["results"]["processed"] == 1
    assert ctx["results"]["total_tokens"] == 42


# ------------------------------------------------------------------------------
# SCENARIO: ERROR HANDLING & CANCELLATION
# ------------------------------------------------------------------------------

def test_engine_should_capture_worker_exceptions_in_results(mocker, engine_context):
    """Verifies that thread-level crashes are trapped and reported as TranscriptionErrors."""
    # 1. ARRANGE
    ctx = engine_context
    ctx["scanner"].yield_project_files.return_value = [
        {"status": "process", "file_path": "/src/broken.py", "rel_path": "broken.py", "ext": ".py",
         "file_name": "broken.py"}
    ]
    ctx["cache"].get_entry.return_value = None
    mocker.patch("os.stat", return_value=mocker.Mock(st_mtime=1, st_size=1))

    # Simulate worker returning a logical error
    mocker.patch(
        "transcriptor4ai.application.pipeline.stages.transcriber_engine.process_file_task",
        return_value={"ok": False, "rel_path": "broken.py", "error": "IO Error during read"}
    )

    # 2. ACT
    execute_parallel_workers(
        scanner_service=ctx["scanner"], input_path="/src", extensions=[".py"],
        include_rx=[], exclude_rx=[], processing_depth="full",
        process_tests=True, process_resources=True, enable_sanitizer=False,
        mask_user_paths=False, minify_output=False, locks=ctx["locks"],
        output_paths=ctx["output_paths"], results=ctx["results"],
        cache_repo=ctx["cache"], config_hash="H", user_context=ctx["user_ctx"]
    )

    # 3. ASSERT
    assert len(ctx["results"]["errors"]) == 1
    err = ctx["results"]["errors"][0]
    assert isinstance(err, TranscriptionError)
    assert err.rel_path == "broken.py"
    assert "IO Error" in err.error


def test_engine_aborts_on_cancellation_event(mocker, engine_context):
    """Ensures the thread pool stops submitting tasks if cancellation is signaled."""
    # 1. ARRANGE
    ctx = engine_context
    cancel_event = threading.Event()
    cancel_event.set()  # Abort from the start

    ctx["scanner"].yield_project_files.return_value = [
        {"status": "process", "file_path": "/src/never.py", "rel_path": "never.py", "ext": ".py",
         "file_name": "never.py"}
    ]
    m_worker = mocker.patch("transcriptor4ai.application.pipeline.stages.transcriber_engine.process_file_task")

    # 2. ACT
    execute_parallel_workers(
        scanner_service=ctx["scanner"], input_path="/root", extensions=[".py"],
        include_rx=[], exclude_rx=[], processing_depth="full",
        process_tests=True, process_resources=True, enable_sanitizer=False,
        mask_user_paths=False, minify_output=False, locks=ctx["locks"],
        output_paths=ctx["output_paths"], results=ctx["results"],
        cache_repo=ctx["cache"], config_hash="H", user_context=ctx["user_ctx"],
        cancellation_event=cancel_event
    )

    # 3. ASSERT
    # Worker should NEVER be called if cancelled
    m_worker.assert_not_called()