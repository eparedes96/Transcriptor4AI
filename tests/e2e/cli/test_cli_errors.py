import pytest
from transcriptor4ai.interface.cli.app import main


# ==============================================================================
# TEST GROUP: CLI ERROR HANDLING AND RESILIENCE
# ==============================================================================

@pytest.fixture
def mock_infra(mocker):
    """
    Zeroes out all infrastructure I/O by patching adapters and repos.
    Also mocks the logging configuration to prevent thread leaks.
    """
    # 1. Prevent Logging Thread creation (Fixes I/O operation on closed file)
    mocker.patch("transcriptor4ai.interface.cli.app.configure_logging")

    # 2. Mock Infrastructure Classes
    m_fs = mocker.patch("transcriptor4ai.interface.cli.app.FileSystemAdapter", autospec=True)
    mocker.patch("transcriptor4ai.interface.cli.app.SqliteCacheRepository", autospec=True)
    mocker.patch("transcriptor4ai.interface.cli.app.JsonConfigRepository", autospec=True)
    mocker.patch("transcriptor4ai.interface.cli.app.UserContextAdapter", autospec=True)

    # 3. Global OS path mocking
    m_isdir = mocker.patch("os.path.isdir")

    return m_fs.return_value, m_isdir


@pytest.mark.e2e
def test_cli_should_exit_with_code_2_when_input_path_is_missing(mock_infra, capsys):
    """Checks that the CLI identifies non-existent paths before starting."""
    # 1. ARRANGE
    m_fs, m_isdir = mock_infra
    m_fs.file_exists.return_value = False
    m_isdir.return_value = False

    args = ["-i", "/non/existent/path"]

    # 2. ACT
    exit_code = main(args)

    # 3. ASSERT: Code 2 is for Configuration/Path errors detected early
    assert exit_code == 2

    captured = capsys.readouterr()
    assert "not exist" in captured.err.lower()


@pytest.mark.e2e
def test_cli_should_exit_with_code_1_on_unhandled_pipeline_exception(mocker, mock_infra, capsys):
    """Verifies that the CLI traps and reports generic runtime crashes."""
    # 1. ARRANGE
    m_fs, m_isdir = mock_infra
    m_fs.file_exists.return_value = True
    m_isdir.return_value = True

    # Simulate a crash deep inside the pipeline
    mocker.patch(
        "transcriptor4ai.interface.cli.app.run_pipeline",
        side_effect=RuntimeError("Pipeline crash simulation")
    )

    args = ["-i", "/valid/path", "--dry-run"]

    # 2. ACT
    exit_code = main(args)

    # 3. ASSERT: Code 1 for logic failures
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "Pipeline crash simulation" in captured.err


@pytest.mark.e2e
def test_cli_should_return_130_on_keyboard_interrupt(mocker, mock_infra, capsys):
    """Simulates a user pressing Ctrl+C (SIGINT) during execution."""
    # 1. ARRANGE
    m_fs, m_isdir = mock_infra
    m_fs.file_exists.return_value = True
    m_isdir.return_value = True

    mocker.patch(
        "transcriptor4ai.interface.cli.app.run_pipeline",
        side_effect=KeyboardInterrupt()
    )

    # 2. ACT
    exit_code = main(["-i", "/any/path"])

    # 3. ASSERT: 130 is the POSIX standard for terminated by SIGINT
    assert exit_code == 130

    captured = capsys.readouterr()
    assert "cancelled by user" in captured.err.lower()


@pytest.mark.e2e
def test_cli_should_fail_when_input_is_a_file_not_a_directory(mock_infra, capsys):
    """Ensures input validation strictly enforces directory-only scanning."""
    # 1. ARRANGE: Path exists (file_exists=True) but is NOT a dir (isdir=False)
    m_fs, m_isdir = mock_infra
    m_fs.file_exists.return_value = True
    m_isdir.return_value = False

    args = ["-i", "/path/to/script.py"]

    # 2. ACT
    exit_code = main(args)

    # 3. ASSERT
    # Code 1 is returned because 'main' allows files through validation,
    # but 'run_pipeline' (setup stage) rejects them as invalid input.
    assert exit_code == 1

    # Optional: Verify the specific error message to ensure it's not a random crash
    captured = capsys.readouterr()
    # Logged to stderr by the CLI logic when pipeline fails
    assert "error" in captured.err.lower()