from __future__ import annotations

from pathlib import Path

import pytest

from transcriptor4ai.application.pipeline.components.file_writer import (
    _ENTRY_SEPARATOR,
    append_cache_entry,
    append_entry,
    initialize_output_file,
)

# ==============================================================================
# TEST GROUP: FILE INITIALIZATION
# ==============================================================================

@pytest.mark.unit
def test_initialize_output_file_creates_file_with_header(tmp_path: Path):
    # 1. ARRANGE: Set up a safe temporary file path
    target_file = tmp_path / "modules.txt"
    header_text = "SCRIPTS/MODULES:"

    # 2. ACT: Execute initialization
    initialize_output_file(str(target_file), header_text)

    # 3. ASSERT: Verify the file exists and contains exactly the header with a newline
    assert target_file.exists()
    content = target_file.read_text(encoding="utf-8")
    assert content == f"{header_text}\n"


@pytest.mark.unit
def test_initialize_output_file_propagates_os_error_and_logs(mocker, tmp_path: Path):
    # 1. ARRANGE: Mock builtins.open to simulate a system permission error
    # and spy on the logger to ensure the error is recorded.
    mock_open = mocker.patch("builtins.open", side_effect=OSError("Access is denied"))
    mock_logger = mocker.patch("transcriptor4ai.application.pipeline.components.file_writer.logger.error")
    target_file = str(tmp_path / "forbidden.txt")

    # 2. ACT & ASSERT: Expect OSError to be re-raised
    with pytest.raises(OSError, match="Access is denied"):
        initialize_output_file(target_file, "HEADER")

    # 3. ASSERT: Verify the logger captured the exact failure
    mock_open.assert_called_once_with(target_file, "w", encoding="utf-8")
    mock_logger.assert_called_once()
    assert "Failed to initialize" in mock_logger.call_args[0][0]


# ==============================================================================
# TEST GROUP: ENTRY APPENDING & FORMATTING
# ==============================================================================

@pytest.mark.unit
def test_append_entry_formats_block_strictly_according_to_spec(tmp_path: Path):
    # 1. ARRANGE: Setup target and payload
    target_file = tmp_path / "output.txt"
    target_file.touch()  # Simulate an existing initialized file

    rel_path = "src/main.py"
    source_content = "def hello():\n    pass"

    # 2. ACT: Append the new entry
    append_entry(str(target_file), rel_path, source_content)

    # 3. ASSERT: Verify the visual block structure is exact
    written_text = target_file.read_text(encoding="utf-8")
    expected_block = (
        f"{_ENTRY_SEPARATOR}\n"
        f"{rel_path}\n"
        f"{source_content}\n"
    )
    assert written_text == expected_block


@pytest.mark.unit
@pytest.mark.parametrize("payload", [
    "🚀 Transcriptor4AI - Año 2026",  # Emojis and Latin accents
    "こんにちは世界",  # Asian characters
    "",  # Empty string edge case
    "   \n   \n",  # Whitespace only
])
def test_append_entry_supports_complex_unicode_without_corruption(tmp_path: Path, payload: str):
    # 1. ARRANGE
    target_file = tmp_path / "unicode_test.txt"
    rel_path = "i18n/test.txt"

    # 2. ACT
    # Ensures no UnicodeEncodeError is raised by forcing utf-8 locally
    append_entry(str(target_file), rel_path, payload)

    # 3. ASSERT: Read back strictly in UTF-8 and verify integrity
    written_text = target_file.read_text(encoding="utf-8")
    assert payload in written_text


@pytest.mark.unit
def test_append_entry_propagates_os_error_and_logs(mocker, tmp_path: Path):
    # 1. ARRANGE
    mock_open = mocker.patch("builtins.open", side_effect=OSError("Disk full"))
    mock_logger = mocker.patch("transcriptor4ai.application.pipeline.components.file_writer.logger.error")
    target_file = str(tmp_path / "full_disk.txt")

    # 2. ACT & ASSERT
    with pytest.raises(OSError, match="Disk full"):
        append_entry(target_file, "path/file.py", "content")

    # 3. ASSERT
    mock_open.assert_called_once_with(target_file, "a", encoding="utf-8")
    mock_logger.assert_called_once()
    assert "Failed to append entry for path/file.py" in mock_logger.call_args[0][0]


# ==============================================================================
# TEST GROUP: CACHE DELEGATION
# ==============================================================================

@pytest.mark.unit
def test_append_cache_entry_delegates_to_standard_append_logic(mocker):
    # 1. ARRANGE
    # Mocking the core append function to ensure the wrapper calls it properly
    mock_append = mocker.patch("transcriptor4ai.application.pipeline.components.file_writer.append_entry")

    target = "/fake/out.txt"
    rel_path = "cached.py"
    content = "cache hit content"

    # 2. ACT
    append_cache_entry(target, rel_path, content)

    # 3. ASSERT
    mock_append.assert_called_once_with(target, rel_path, content)