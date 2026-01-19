from __future__ import annotations

"""
Unit tests for the File Discovery and Filtering Service.

Verifies the optimized project walking logic, regex-based filtering,
and correct classification of files into processing categories.
"""

import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from transcriptor4ai.core.services.scanner import (
    finalize_error_reporting,
    prepare_filtering_rules,
    yield_project_files,
)
from transcriptor4ai.domain.transcription_models import TranscriptionError


@pytest.fixture
def mock_fs_structure(tmp_path: Path) -> Path:
    """Create a temporary filesystem structure for scanning tests."""
    root = tmp_path / "project"
    root.mkdir()

    # Create directories
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "node_modules").mkdir()
    (root / ".git").mkdir()

    # Create files
    (root / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
    (root / "src" / "utils.py").write_text("def helper(): pass", encoding="utf-8")
    (root / "src" / "exclude_me.tmp").write_text("trash", encoding="utf-8")
    (root / "tests" / "test_main.py").write_text("def test(): pass", encoding="utf-8")
    (root / "README.md").write_text("# Project", encoding="utf-8")
    (root / "node_modules" / "lib.js").write_text("var x = 1;", encoding="utf-8")
    (root / "config.json").write_text("{}", encoding="utf-8")

    return root


def test_prepare_filtering_rules_integration(mock_fs_structure: Path) -> None:
    """Verify aggregation of default, user, and gitignore patterns."""
    with patch("transcriptor4ai.core.services.scanner.load_gitignore_patterns") as mock_git:
        mock_git.return_value = [r"custom_ignore"]

        inc, exc = prepare_filtering_rules(
            str(mock_fs_structure),
            include_patterns=[r".*"],
            exclude_patterns=[r"tmp_.*"],
            respect_gitignore=True
        )

        assert any(rx.pattern == r"custom_ignore" for rx in exc)
        assert any(rx.pattern == r"tmp_.*" for rx in exc)
        assert isinstance(inc[0], re.Pattern)


def test_yield_project_files_classification(mock_fs_structure: Path) -> None:
    """Verify that files are correctly marked for processing or skipping."""
    inc = [re.compile(r".*")]
    # Include exclude_me.tmp explicitly in exclusions
    exc = [re.compile(r"node_modules"), re.compile(r"\.git"), re.compile(r"exclude_me\.tmp")]
    exts = [".py"]

    files = list(yield_project_files(
        input_path=str(mock_fs_structure),
        extensions=exts,
        include_rx=inc,
        exclude_rx=exc,
        process_modules=True,
        process_tests=True,
        process_resources=True
    ))

    # Identify statuses
    processed = [f for f in files if f["status"] == "process"]
    skipped = [f for f in files if f["status"] == "skipped"]

    # main.py, utils.py, test_main.py, README.md, config.json should be processed
    assert len(processed) == 5

    # 1. node_modules/lib.js should NOT be in processed because of directory pruning
    assert not any("node_modules" in f["rel_path"] for f in processed)

    # 2. exclude_me.tmp should be yielded as SKIPPED because its parent dir was visited
    assert any("exclude_me.tmp" in f["rel_path"] for f in skipped)


def test_finalize_error_reporting_persistence(tmp_path: Path) -> None:
    """Verify that transcription errors are correctly formatted and saved."""
    error_path = tmp_path / "errors.txt"
    errors = [
        TranscriptionError(rel_path="src/fail.py", error="Permission Denied"),
        TranscriptionError(rel_path="src/bad.py", error="Syntax Error")
    ]

    path = finalize_error_reporting(True, str(error_path), errors)

    assert path == str(error_path)
    content = error_path.read_text(encoding="utf-8")
    assert "src/fail.py" in content
    assert "Permission Denied" in content
    assert "TRANSCRIPTION ERRORS REPORT" in content