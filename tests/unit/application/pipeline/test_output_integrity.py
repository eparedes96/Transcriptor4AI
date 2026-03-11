from __future__ import annotations

import os
from pathlib import Path

import pytest

from transcriptor4ai.application.pipeline.components.file_writer import (
    _ENTRY_SEPARATOR,
    append_entry,
    initialize_output_file,
)
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter

# ==============================================================================
# TEST GROUP: MASTER CONTEXT INTEGRITY
# ==============================================================================

@pytest.fixture
def fs_adapter() -> FileSystemAdapter:
    """Provides a fresh instance of the FileSystemAdapter."""
    return FileSystemAdapter()


@pytest.mark.integration
def test_unified_file_structure_contains_all_expected_sections(tmp_path: Path, fs_adapter: FileSystemAdapter):
    # 1. ARRANGE: Create standard intermediate pipeline artifacts
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    # Mocking the generated directory tree
    tree_path = staging_dir / "tree.txt"
    tree_path.write_text("├── src/\n│   └── main.py\n└── README.md", encoding="utf-8")

    # Mocking the modules output using the official writer
    modules_path = staging_dir / "modules.txt"
    initialize_output_file(str(modules_path), "SCRIPTS/MODULES:")
    append_entry(str(modules_path), "src/main.py", "def execute():\n    pass")

    # Mocking the tests output
    tests_path = staging_dir / "tests.txt"
    initialize_output_file(str(tests_path), "TESTS:")
    append_entry(str(tests_path), "tests/test_main.py", "def test_execute():\n    assert True")

    output_unified = str(tmp_path / "full_context.txt")
    category_paths = {
        "modules": str(modules_path),
        "tests": str(tests_path)
    }

    # 2. ACT: Trigger the aggregation logic
    success = fs_adapter.generate_unified_file(
        output_path=output_unified,
        base_path="/home/user/super_project",
        tree_path=str(tree_path),
        category_paths=category_paths
    )

    # 3. ASSERT: Validate the exact format expectations for the LLM
    assert success is True
    assert os.path.exists(output_unified)

    final_content = Path(output_unified).read_text(encoding="utf-8")

    # Assert Headers
    assert "PROJECT CONTEXT: super_project" in final_content
    assert "PROJECT STRUCTURE:" in final_content

    # Assert Tree
    assert "├── src/" in final_content

    # Assert File Categories
    assert "SCRIPTS/MODULES:" in final_content
    assert "TESTS:" in final_content

    # Assert File Entries and Separators
    assert _ENTRY_SEPARATOR in final_content
    assert "src/main.py\ndef execute():" in final_content
    assert "tests/test_main.py\ndef test_execute():" in final_content


@pytest.mark.integration
def test_unified_file_preserves_utf8_encoding_and_symbols(tmp_path: Path, fs_adapter: FileSystemAdapter):
    # 1. ARRANGE: Prepare content with complex Unicode (Emojis, Cyrillic, Latin accents)
    resources_path = tmp_path / "resources.txt"
    initialize_output_file(str(resources_path), "RESOURCES:")

    complex_text = "🚀 Iniciando proceso: Año 2026. Data: データ"
    append_entry(str(resources_path), "docs/i18n.md", complex_text)

    output_unified = str(tmp_path / "unicode_context.txt")

    # 2. ACT
    success = fs_adapter.generate_unified_file(
        output_path=output_unified,
        base_path="/project",
        tree_path=None,
        category_paths={"resources": str(resources_path)}
    )

    # 3. ASSERT: Read the file strictly in UTF-8 to ensure no bytes were corrupted
    assert success is True

    final_content = Path(output_unified).read_text(encoding="utf-8")
    assert complex_text in final_content


# ==============================================================================
# TEST GROUP: EDGE CASES & RESILIENCE
# ==============================================================================

@pytest.mark.integration
def test_unified_file_handles_missing_category_files_gracefully(tmp_path: Path, fs_adapter: FileSystemAdapter):
    # 1. ARRANGE: Provide valid paths in the dictionary that do not exist on disk
    # This simulates a pipeline run where 'process_tests' was true, but 0 test files were found.
    modules_path = tmp_path / "modules.txt"
    modules_path.write_text("MODULES_HEADER\nFake content", encoding="utf-8")

    output_unified = str(tmp_path / "partial_context.txt")
    category_paths = {
        "modules": str(modules_path),
        "tests": str(tmp_path / "non_existent_tests.txt"),
        "resources": str(tmp_path / "non_existent_resources.txt")
    }

    # 2. ACT
    success = fs_adapter.generate_unified_file(
        output_path=output_unified,
        base_path="/path/to/app",
        tree_path=None,
        category_paths=category_paths
    )

    # 3. ASSERT: The aggregator should skip missing files without failing
    assert success is True

    final_content = Path(output_unified).read_text(encoding="utf-8")
    assert "MODULES_HEADER" in final_content
    # Ensure it didn't crash or write empty headers for the missing files
    assert "non_existent" not in final_content