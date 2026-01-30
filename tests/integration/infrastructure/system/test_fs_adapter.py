# ==============================================================================
# TEST GROUP: FILESYSTEM ADAPTER (INTEGRATION)
# ==============================================================================

import os
from pathlib import Path

import pytest
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter


@pytest.fixture
def fs():
    """Provides a real instance of the FileSystemAdapter."""
    return FileSystemAdapter()


@pytest.mark.integration
def test_fs_normalization_logic(fs, tmp_path):
    """
    Verifies that the adapter correctly normalizes paths and handles
    fallbacks when inputs are empty or invalid.
    """
    # 1. ARRANGE
    fallback = str(tmp_path)

    # 2. ACT
    # Testing empty input returns absolute fallback
    normalized = fs.normalize_path("", fallback)

    # 3. ASSERT
    assert os.path.isabs(normalized)
    assert normalized == os.path.abspath(fallback)


@pytest.mark.integration
def test_fs_read_write_utf8_integrity(fs, tmp_path):
    """
    Ensures that content with special characters and emojis is
    persisted and recovered without corruption.
    """
    # 1. ARRANGE
    target_file = str(tmp_path / "encoding_test.txt")
    complex_content = "Transcriptor4AI v2.1 🚀 - Línea con tildes y ñ."

    # 2. ACT
    fs.write_text_file(target_file, complex_content)
    recovered = fs.read_file_content(target_file)

    # 3. ASSERT
    assert recovered == complex_content


@pytest.mark.integration
def test_fs_safe_mkdir_recursive(fs, tmp_path):
    """
    Validates that safe_mkdir creates nested directory hierarchies
    and returns a success status.
    """
    # 1. ARRANGE
    nested_path = str(tmp_path / "level1" / "level2" / "level3")

    # 2. ACT
    success, error = fs.safe_mkdir(nested_path)

    # 3. ASSERT
    assert success is True
    assert error is None
    assert os.path.exists(nested_path)
    assert os.path.isdir(nested_path)


@pytest.mark.integration
def test_fs_check_existing_output_files(fs, tmp_path):
    """
    Ensures the adapter correctly identifies naming collisions in a directory.
    """
    # 1. ARRANGE: Create some files
    (tmp_path / "file1.txt").write_text("exists")
    (tmp_path / "file2.txt").write_text("exists")

    names_to_check = ["file1.txt", "file2.txt", "missing.txt"]

    # 2. ACT
    existing = fs.check_existing_output_files(str(tmp_path), names_to_check)

    # 3. ASSERT
    assert len(existing) == 2
    assert any(e.endswith("file1.txt") for e in existing)
    assert not any(e.endswith("missing.txt") for e in existing)


@pytest.mark.integration
def test_fs_generate_unified_file_aggregation(fs, tmp_path):
    """
    CRITICAL: Verifies the core v2.1 functionality of merging multiple
    staging artifacts into a single unified context file.
    """
    # 1. ARRANGE: Prepare staging files
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir()

    mod_file = staging_dir / "modules.txt"
    mod_file.write_text("MODULE_DATA", encoding="utf-8")

    tree_file = staging_dir / "tree.txt"
    tree_file.write_text("TREE_DATA", encoding="utf-8")

    output_unified = str(tmp_path / "master_context.txt")

    category_paths = {
        "modules": str(mod_file)
    }

    # 2. ACT: Merge files
    success = fs.generate_unified_file(
        output_path=output_unified,
        base_path="/fake/project_root",
        tree_path=str(tree_file),
        category_paths=category_paths
    )

    # 3. ASSERT
    assert success is True
    assert os.path.exists(output_unified)

    final_content = Path(output_unified).read_text(encoding="utf-8")
    assert "PROJECT CONTEXT: project_root" in final_content
    assert "TREE_DATA" in final_content
    assert "MODULE_DATA" in final_content


@pytest.mark.integration
def test_fs_delete_and_move_atomic_operations(fs, tmp_path):
    """
    Validates safe file manipulation: moving files with overwrite
    and deleting existing ones.
    """
    # 1. ARRANGE
    src = tmp_path / "source.txt"
    src.write_text("content")
    dst = tmp_path / "destination.txt"

    # 2. ACT: Move
    move_success = fs.move_file(str(src), str(dst))

    # 3. ASSERT
    assert move_success is True
    assert os.path.exists(str(dst))
    assert not os.path.exists(str(src))

    # 4. ACT: Delete
    del_success = fs.delete_file(str(dst))
    assert del_success is True
    assert not os.path.exists(str(dst))