from __future__ import annotations

"""
Unit tests for GUI Handlers (Controller Logic).

Verifies:
1. Synchronization of GUI form values to Config dict.
2. String parsing utilities specific to GUI inputs.
3. System interaction calls (mocked).
"""

import os
from unittest.mock import patch
import pytest

from transcriptor4ai.interface.gui.handlers import (
    update_config_from_gui,
    parse_list_from_string,
    open_file_explorer
)


def test_parse_list_from_string_gui():
    """Verify helper splits CSV strings from GUI inputs."""
    assert parse_list_from_string(".py, .js") == [".py", ".js"]
    assert parse_list_from_string("  val1  , val2 ") == ["val1", "val2"]
    assert parse_list_from_string("") == []
    assert parse_list_from_string(None) == []


def test_update_config_from_gui_sync(mock_config_dict):
    """
    Verify that the config dictionary is updated with values from the GUI event.
    """
    # Simulate PySimpleGUI values dict
    gui_values = {
        "input_path": "/new/input",
        "output_base_dir": "/new/output",
        "process_modules": False,
        "extensions": ".rs, .toml",
        "target_model": "Claude 3.5"
    }

    update_config_from_gui(mock_config_dict, gui_values)

    assert mock_config_dict["input_path"] == "/new/input"
    assert mock_config_dict["process_modules"] is False
    assert mock_config_dict["extensions"] == [".rs", ".toml"]
    assert mock_config_dict["target_model"] == "Claude 3.5"


def test_open_file_explorer_calls_system(tmp_path):
    """Verify that the correct OS command is called based on platform."""

    target_dir = tmp_path / "target"
    target_dir.mkdir()
    path_str = str(target_dir)

    # Test Windows
    with patch("platform.system", return_value="Windows"):
        with patch("os.startfile", create=True) as mock_start:
            open_file_explorer(path_str)
            mock_start.assert_called_with(path_str)

    # Test Linux
    with patch("platform.system", return_value="Linux"):
        with patch("subprocess.Popen") as mock_popen:
            open_file_explorer(path_str)
            mock_popen.assert_called_with(["xdg-open", path_str])


def test_open_file_explorer_handles_invalid_path():
    """It should verify path existence before calling system."""

    with patch("subprocess.Popen") as mock_popen:
        open_file_explorer("/non/existent/path")
        mock_popen.assert_not_called()