from __future__ import annotations

# ==============================================================================
# TEST GROUP: ATOMIC TRANSCRIPTION WORKER (UNIT)
# ==============================================================================

import pytest
from unittest.mock import MagicMock, ANY
# Importamos el módulo completo para poder espiar sus funciones internas
import transcriptor4ai.application.pipeline.stages.worker as worker_module
from transcriptor4ai.application.pipeline.stages.worker import process_file_task


@pytest.fixture
def mock_locks(mocker):
    """
    Provides a thread-safe lock map where each lock is a mock
    supporting the context manager protocol via MagicMock.
    """
    return {
        "module": mocker.MagicMock(),
        "test": mocker.MagicMock(),
        "resource": mocker.MagicMock(),
        "error": mocker.MagicMock()
    }


@pytest.fixture
def mock_paths():
    """Provides categorized destination paths for the staging area."""
    return {
        "module": "/staging/modules.txt",
        "test": "/staging/tests.txt",
        "resource": "/staging/resources.txt"
    }


@pytest.fixture
def mock_sanitizer(mocker):
    """
    Mock for the PrivacySanitizerService to avoid regex overhead.
    """
    service = mocker.Mock()
    service.sanitize_stream.side_effect = lambda lines: lines
    service.mask_paths_stream.side_effect = lambda lines: lines
    return service


@pytest.mark.unit
def test_worker_should_process_module_from_data_folder(mocker, mock_locks, mock_paths, mock_sanitizer,
                                                       sample_project_source):
    """
    Ensures the worker correctly processes a real source file from the
    sample project, applying locks and writing to the module category.
    """
    # 1. ARRANGE
    file_path = str(sample_project_source / "src" / "calculator.py")
    rel_path = "src/calculator.py"

    m_writer = mocker.patch("transcriptor4ai.application.pipeline.stages.worker.append_entry")

    # 2. ACT
    result = process_file_task(
        file_path=file_path, rel_path=rel_path, ext=".py", file_name="calculator.py",
        processing_depth="full", process_tests=True, process_resources=True,
        enable_sanitizer=True, mask_user_paths=True, minify_output=False,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer,
        composite_hash="hash_calc_123"
    )

    # 3. ASSERT
    assert result["ok"] is True
    assert result["mode"] == "module"
    assert "class Calculator" in result["processed_content"]

    mock_locks["module"].__enter__.assert_called_once()
    m_writer.assert_called_once_with(
        output_path="/staging/modules.txt",
        rel_path=rel_path,
        content=ANY
    )


@pytest.mark.unit
def test_worker_should_skeletonize_python_file_from_data(mocker, mock_locks, mock_paths, mock_sanitizer,
                                                         sample_project_source):
    """
    Validates that the worker correctly routes Python files to the
    AST skeletonizer when depth is set to 'skeleton'.
    """
    # 1. ARRANGE
    file_path = str(sample_project_source / "src" / "calculator.py")
    mocker.patch("transcriptor4ai.application.pipeline.stages.worker.append_entry")

    # FIX: Spying on the actual module object, not a string string
    m_skeleton = mocker.spy(worker_module, "generate_skeleton_code")

    # 2. ACT
    result = process_file_task(
        file_path=file_path, rel_path="src/calculator.py", ext=".py", file_name="calculator.py",
        processing_depth="skeleton", process_tests=False, process_resources=False,
        enable_sanitizer=False, mask_user_paths=False, minify_output=False,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer
    )

    # 3. ASSERT
    assert result["ok"] is True
    # Verificamos que se haya llamado a la lógica de esqueleto
    assert m_skeleton.called
    # El contenido debe estar procesado estructuralmente (sin la lógica de suma)
    assert "pass" in result["processed_content"]
    assert "self.value += number" not in result["processed_content"]


@pytest.mark.unit
def test_worker_should_use_test_lock_for_test_files(mocker, mock_locks, mock_paths, mock_sanitizer,
                                                    sample_project_source):
    """
    Ensures that files inside the 'tests/' folder are identified
    and use the specific 'test' synchronization lock.
    """
    # 1. ARRANGE
    file_path = str(sample_project_source / "tests" / "test_calculator.py")
    m_writer = mocker.patch("transcriptor4ai.application.pipeline.stages.worker.append_entry")

    # 2. ACT
    process_file_task(
        file_path=file_path, rel_path="tests/test_calculator.py", ext=".py", file_name="test_calculator.py",
        processing_depth="full", process_tests=True, process_resources=True,
        enable_sanitizer=False, mask_user_paths=False, minify_output=False,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer
    )

    # 3. ASSERT
    mock_locks["test"].__enter__.assert_called_once()
    mock_locks["module"].__enter__.assert_not_called()
    m_writer.assert_called_once_with(
        output_path="/staging/tests.txt",
        rel_path="tests/test_calculator.py",
        content=ANY
    )


@pytest.mark.unit
def test_worker_should_skip_when_depth_is_tree_only(mocker, mock_locks, mock_paths, mock_sanitizer):
    """
    Verifies that the worker immediately returns a skip status
    without attempting any I/O when processing logic is disabled.
    """
    # 1. ARRANGE
    m_reader = mocker.patch("transcriptor4ai.application.pipeline.stages.worker.stream_file_content")

    # 2. ACT
    result = process_file_task(
        file_path="/any/path.py", rel_path="path.py", ext=".py", file_name="path.py",
        processing_depth="tree_only", process_tests=True, process_resources=True,
        enable_sanitizer=True, mask_user_paths=True, minify_output=True,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer
    )

    # 3. ASSERT
    assert result["ok"] is False
    assert result["mode"] == "skip"
    m_reader.assert_not_called()


@pytest.mark.unit
def test_worker_should_handle_io_error_gracefully(mocker, mock_locks, mock_paths, mock_sanitizer):
    """
    Validates resilience: if the reader encounters a system error,
    the worker captures it without crashing the thread.
    """
    # 1. ARRANGE
    mocker.patch(
        "transcriptor4ai.application.pipeline.stages.worker.stream_file_content",
        side_effect=OSError("Access Denied")
    )

    # 2. ACT
    result = process_file_task(
        file_path="/protected/system.log", rel_path="system.log", ext=".log", file_name="system.log",
        processing_depth="full", process_tests=True, process_resources=True,
        enable_sanitizer=False, mask_user_paths=False, minify_output=False,
        locks=mock_locks, output_paths=mock_paths, sanitizer_service=mock_sanitizer
    )

    # 3. ASSERT
    assert result["ok"] is False
    assert "Access Denied" in result["error"]