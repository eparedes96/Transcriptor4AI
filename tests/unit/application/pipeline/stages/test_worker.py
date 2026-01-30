from __future__ import annotations

# ==============================================================================
# TEST GROUP: ATOMIC TRANSCRIPTION WORKER
# ==============================================================================

import pytest
from unittest.mock import MagicMock
from transcriptor4ai.application.pipeline.stages.worker import process_file_task


@pytest.fixture
def mock_locks(mocker):
    """
    Provides a thread-safe lock map where each lock is a mock
    supporting the context manager protocol via MagicMock.
    Crucial to verify that the worker acquires the *correct* lock.
    """
    return {
        "module": mocker.MagicMock(),
        "test": mocker.MagicMock(),
        "resource": mocker.MagicMock(),
        "error": mocker.MagicMock()
    }


@pytest.fixture
def mock_paths():
    """Provides categorized destination paths."""
    return {
        "module": "/out/modules.txt",
        "test": "/out/tests.txt",
        "resource": "/out/resources.txt"
    }


@pytest.fixture
def mock_sanitizer(mocker):
    """
    Mock for the PrivacySanitizerService.
    Bypasses expensive regex operations for unit testing flow logic.
    """
    service = mocker.Mock()
    # Streaming mock: returns the same lines it receives
    service.sanitize_stream.side_effect = lambda lines: lines
    service.mask_paths_stream.side_effect = lambda lines: lines
    return service


@pytest.mark.unit
def test_worker_full_pipeline_happy_path(mocker, mock_locks, mock_paths, mock_sanitizer):
    """
    TC-01: Verifies the standard workflow for a source module.
    Order: Stream -> Sanitizer -> Lock -> AppendEntry.
    """
    # 1. ARRANGE
    file_path = "/src/logic.py"
    rel_path = "logic.py"
    content = ["def run(): pass\n"]

    m_reader = mocker.patch("transcriptor4ai.application.pipeline.stages.worker.stream_file_content",
                            return_value=iter(content))
    m_writer = mocker.patch("transcriptor4ai.application.pipeline.stages.worker.append_entry")

    # 2. ACT
    result = process_file_task(
        file_path=file_path, rel_path=rel_path, ext=".py", file_name="logic.py",
        processing_depth="full", process_tests=True, process_resources=True,
        enable_sanitizer=True, mask_user_paths=True, minify_output=False,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer,
        composite_hash="hash123"
    )

    # 3. ASSERT
    assert result["ok"] is True
    assert result["mode"] == "module"
    assert result["processed_content"] == "def run(): pass\n"

    # Ensures the module lock was acquired (Context Manager used)
    mock_locks["module"].__enter__.assert_called_once()

    # Verify physical write delegation
    m_writer.assert_called_once_with(
        output_path="/out/modules.txt",
        rel_path=rel_path,
        content="def run(): pass\n"
    )


@pytest.mark.unit
def test_worker_routes_to_skeleton_mode_for_python(mocker, mock_locks, mock_paths, mock_sanitizer):
    """
    TC-02: Verifies that in 'skeleton' depth, Python files are
    diverted to the AST skeletonizer service.
    """
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.pipeline.stages.worker.stream_file_content",
                 return_value=iter(["def heavy():\n    pass"]))
    m_skeleton = mocker.patch("transcriptor4ai.application.pipeline.stages.worker.generate_skeleton_code",
                              return_value="def heavy(): pass")
    mocker.patch("transcriptor4ai.application.pipeline.stages.worker.append_entry")

    # 2. ACT
    result = process_file_task(
        file_path="/src/app.py", rel_path="app.py", ext=".py", file_name="app.py",
        processing_depth="skeleton", process_tests=False, process_resources=False,
        enable_sanitizer=False, mask_user_paths=False, minify_output=False,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer
    )

    # 3. ASSERT
    assert result["ok"] is True
    assert result["processed_content"] == "def heavy(): pass"
    m_skeleton.assert_called_once()


@pytest.mark.unit
def test_worker_identifies_and_locks_tests(mocker, mock_locks, mock_paths, mock_sanitizer):
    """
    TC-03: Ensures that files classified as tests use the 'test' lock
    and write to the 'tests' output path.
    """
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.pipeline.stages.worker.stream_file_content", return_value=iter(["test"]))
    m_writer = mocker.patch("transcriptor4ai.application.pipeline.stages.worker.append_entry")

    # 2. ACT
    process_file_task(
        file_path="/tests/test_api.py", rel_path="tests/test_api.py", ext=".py", file_name="test_api.py",
        processing_depth="full", process_tests=True, process_resources=True,
        enable_sanitizer=False, mask_user_paths=False, minify_output=False,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer
    )

    # 3. ASSERT
    mock_locks["test"].__enter__.assert_called_once()
    mock_locks["module"].__enter__.assert_not_called()
    m_writer.assert_called_once_with(output_path="/out/tests.txt", rel_path="tests/test_api.py", content="test")


@pytest.mark.unit
def test_worker_skips_when_depth_is_tree_only(mocker, mock_locks, mock_paths, mock_sanitizer):
    """
    TC-04: Verifies that 'tree_only' depth results in no I/O operations
    and returns a 'skip' status immediately.
    """
    # 1. ARRANGE
    m_reader = mocker.patch("transcriptor4ai.application.pipeline.stages.worker.stream_file_content")

    # 2. ACT
    result = process_file_task(
        file_path="/src/main.py", rel_path="main.py", ext=".py", file_name="main.py",
        processing_depth="tree_only", process_tests=True, process_resources=True,
        enable_sanitizer=True, mask_user_paths=True, minify_output=True,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer
    )

    # 3. ASSERT
    assert result["ok"] is False
    assert result["mode"] == "skip"
    # Ensure expensive I/O was bypassed
    m_reader.assert_not_called()


@pytest.mark.unit
def test_worker_handles_io_error_gracefully(mocker, mock_locks, mock_paths, mock_sanitizer):
    """
    TC-05: Verifies that if reading fails (e.g. Permission Denied),
    the worker returns 'ok=False' instead of crashing the thread pool.
    """
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.pipeline.stages.worker.stream_file_content",
                 side_effect=OSError("Disk Failure"))

    # 2. ACT
    result = process_file_task(
        file_path="/src/locked.py", rel_path="locked.py", ext=".py", file_name="locked.py",
        processing_depth="full", process_tests=True, process_resources=True,
        enable_sanitizer=False, mask_user_paths=False, minify_output=False,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer
    )

    # 3. ASSERT
    assert result["ok"] is False
    assert "Disk Failure" in result["error"]