from __future__ import annotations

"""
Integration tests for the Transcriber Service.

Validates the multi-threaded scanning process, pattern filtering, 
and the concurrent writing of categorized artifacts to disk.
"""

import os
from pathlib import Path

import pytest

from transcriptor4ai.core.pipeline.stages.transcriber import transcribe_code


@pytest.fixture
def complex_project(tmp_path: Path) -> Path:
    """Creates a realistic project structure for integration testing."""
    root = tmp_path / "app"
    root.mkdir()

    # Modules
    src = root / "src"
    src.mkdir()
    (src / "core.py").write_text("class Core: pass", encoding="utf-8")
    (src / "secret.py").write_text("API_KEY = 'sk-1234567890'", encoding="utf-8")

    # Tests
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_core.py").write_text("def test_core(): pass", encoding="utf-8")

    # Resources
    docs = root / "docs"
    docs.mkdir()
    (docs / "README.md").write_text("# Project Docs", encoding="utf-8")

    # Ignored file
    (root / ".gitignore").write_text("*.log", encoding="utf-8")
    (root / "debug.log").write_text("error traces", encoding="utf-8")

    return root


def test_transcribe_code_full_integration(tmp_path: Path, complex_project: Path) -> None:
    """TC-01: Verify categorization and generation of all artifact types."""
    out_dir = tmp_path / "out"

    res = transcribe_code(
        input_path=str(complex_project),
        modules_output_path=str(out_dir / "mod.txt"),
        tests_output_path=str(out_dir / "test.txt"),
        resources_output_path=str(out_dir / "res.txt"),
        error_output_path=str(out_dir / "err.txt"),
        process_modules=True,
        process_tests=True,
        process_resources=True,
        respect_gitignore=True,
        enable_sanitizer=True
    )

    assert res["ok"] is True
    assert res["counters"]["processed"] >= 3

    # Verify file content
    mod_content = (out_dir / "mod.txt").read_text(encoding="utf-8")
    assert "class Core" in mod_content
    assert "[[REDACTED_SECRET]]" in mod_content

    test_content = (out_dir / "test.txt").read_text(encoding="utf-8")
    assert "def test_core" in test_content

    res_content = (out_dir / "res.txt").read_text(encoding="utf-8")
    assert "# Project Docs" in res_content


def test_transcribe_code_respects_gitignore(tmp_path: Path, complex_project: Path) -> None:
    """TC-02: Ensure .gitignore patterns prevent file transcription."""
    out_dir = tmp_path / "out_git"
    os.makedirs(out_dir, exist_ok=True)

    res = transcribe_code(
        input_path=str(complex_project),
        modules_output_path=str(out_dir / "mod.txt"),
        tests_output_path=str(out_dir / "test.txt"),
        resources_output_path=str(out_dir / "res.txt"),
        error_output_path=str(out_dir / "err.txt"),
        respect_gitignore=True
    )

    # The debug.log should be skipped
    assert "debug.log" not in (out_dir / "mod.txt").read_text(encoding="utf-8")
    assert res["counters"]["skipped"] >= 1