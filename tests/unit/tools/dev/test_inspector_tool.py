import ast
import pytest
from pathlib import Path
from tools.dev.inspector import ProjectInspector


# ==============================================================================
# TEST GROUP: PROJECT STRUCTURE INSPECTOR
# ==============================================================================

@pytest.fixture
def dummy_project(tmp_path):
    """Creates a temporary project structure for inspection tests."""
    # 1. SETUP STRUCTURE
    # Note: Directories come first in ProjectInspector sorting logic
    src = tmp_path / "src"
    src.mkdir()

    # Valid Python file inside directory
    app_py = src / "app.py"
    app_py.write_text(
        "class Database:\n"
        "    def connect(self): pass\n"
        "def run_server():\n"
        "    pass",
        encoding="utf-8"
    )

    # Excluded directory (should not appear in result)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("hidden", encoding="utf-8")

    # Non-python file at root
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project", encoding="utf-8")

    return tmp_path


@pytest.mark.unit
def test_inspect_should_generate_correct_ascii_tree(dummy_project):
    """
    Verifies the overall ASCII tree structure and symbol extraction.
    Fixed: Matches real sorting logic (Dirs: src first, Files: README last).
    """
    # 1. ARRANGE
    inspector = ProjectInspector(dummy_project)

    # 2. ACT
    result = inspector.inspect()

    # 3. ASSERT
    # Check root name
    assert f"PROJECT_ROOT: {dummy_project.name}" in result

    # Check hierarchy based on (is_file, name) sorting:
    # 'src' is a directory (is_file=False) -> First -> ├──
    # 'README.md' is a file (is_file=True) -> Last -> └──
    assert "├── src" in result
    assert "│   └── app.py" in result
    assert "└── README.md" in result

    # Check AST Symbols inside app.py
    assert "📦 Class: Database" in result
    assert "│   ƒ Method: connect()" in result
    assert "ƒ Function: run_server()" in result


@pytest.mark.unit
def test_inspector_should_ignore_excluded_directories(dummy_project):
    """Ensures that noise directories like .git are strictly filtered out."""
    # 1. ARRANGE
    inspector = ProjectInspector(dummy_project)

    # 2. ACT
    result = inspector.inspect()

    # 3. ASSERT
    assert ".git" not in result
    assert "hidden" not in result


@pytest.mark.unit
def test_extract_symbols_should_handle_syntax_errors(mocker, tmp_path):
    """Ensures the inspector doesn't crash when encountering invalid Python code."""
    # 1. ARRANGE
    broken_file = tmp_path / "broken.py"
    broken_file.write_text("def missing_colon(", encoding="utf-8")

    inspector = ProjectInspector(tmp_path)
    mock_logger = mocker.patch("tools.dev.inspector.logger.debug")

    # 2. ACT
    # Directly testing the private method to verify resilience
    inspector._extract_symbols(broken_file, "    ")

    # 3. ASSERT
    # The output list should remain empty for this file, and log the issue
    assert not any("Function:" in line for line in inspector.output)
    mock_logger.assert_called()


@pytest.mark.unit
def test_tree_sorting_should_be_deterministic(tmp_path):
    """
    Verifies that files are sorted correctly:
    Folders (is_file=False) come BEFORE Files (is_file=True).
    Within the same type, they are sorted alphabetically.
    """
    # 1. ARRANGE
    (tmp_path / "zebra.py").touch()
    (tmp_path / "apple.py").touch()
    (tmp_path / "banana_dir").mkdir()

    inspector = ProjectInspector(tmp_path)

    # 2. ACT
    result = inspector.inspect()

    # 3. ASSERT
    lines = [line for line in result.split("\n") if "── " in line]

    # Logic:
    # 1. banana_dir (Dir -> is_file=0)
    # 2. apple.py   (File -> is_file=1, name='apple')
    # 3. zebra.py   (File -> is_file=1, name='zebra')
    assert "banana_dir" in lines[0]
    assert "apple.py" in lines[1]
    assert "zebra.py" in lines[-1]


@pytest.mark.unit
def test_main_gui_logic_should_be_mocked(mocker):
    """
    Ensures that the main entry point doesn't hang the CI
    waiting for a directory picker.
    """
    # 1. ARRANGE
    mocker.patch("tools.dev.inspector._pick_directory", return_value=None)
    mock_exit = mocker.patch("sys.exit")

    from tools.dev.inspector import main

    # 2. ACT
    main()

    # 3. ASSERT
    # If no directory is picked, it returns normally (0) without calling exit(1)
    assert mock_exit.called is False