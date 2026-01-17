from __future__ import annotations

"""
Unit tests for the File Writer module.

Verifies:
1. Physical file creation and appending.
2. Correct formatting (Separator + Relative Path + Content).
3. Integration of the transformation pipeline (Minify/Sanitize).
"""

from transcriptor4ai.core.pipeline.components.writer import append_entry, initialize_output_file


def test_initialize_output_file_creates_header(tmp_path):
    """Verify that initialization writes the header line."""
    f = tmp_path / "output.txt"
    header = "TEST HEADER"

    initialize_output_file(str(f), header)

    assert f.exists()
    assert f.read_text(encoding="utf-8") == f"{header}\n"


def test_append_entry_format(tmp_path):
    """
    Verify the standard block format:
    --------------------
    path
    content
    """
    f = tmp_path / "output.txt"
    # Pre-create file (simulate initialized state)
    f.write_text("HEADER\n", encoding="utf-8")

    rel_path = "src/main.py"
    content_lines = ["print('hello')\n"]

    append_entry(
        output_path=str(f),
        rel_path=rel_path,
        line_iterator=iter(content_lines),
        extension=".py",
        enable_sanitizer=False,
        mask_user_paths=False,
        minify_output=False
    )

    output = f.read_text(encoding="utf-8")

    expected_separator = "-" * 200
    assert "HEADER" in output
    assert expected_separator in output
    assert f"{rel_path}\n" in output
    assert "print('hello')" in output


def test_append_entry_applies_minification(tmp_path):
    """Verify that the minify flag triggers the processing stream."""
    f = tmp_path / "minified.txt"

    # Input with comments and whitespace
    raw_lines = [
        "def foo():  \n",
        "    # comment\n",
        "    pass\n"
    ]

    append_entry(
        output_path=str(f),
        rel_path="script.py",
        line_iterator=iter(raw_lines),
        extension=".py",
        minify_output=True,
        enable_sanitizer=False,
        mask_user_paths=False
    )

    content = f.read_text(encoding="utf-8")

    assert "# comment" not in content
    assert "def foo():" in content
    assert "    pass" in content


def test_append_entry_applies_sanitization(tmp_path):
    """Verify that sanitizer is chained correctly."""
    f = tmp_path / "secure.txt"

    # Using a generic assignment pattern which triggers [[REDACTED_SECRET]]
    secret = "super_secret_password_123"
    raw_lines = [f"password = '{secret}'\n"]

    append_entry(
        output_path=str(f),
        rel_path="config.py",
        line_iterator=iter(raw_lines),
        extension=".py",
        enable_sanitizer=True,
        minify_output=False,
        mask_user_paths=False
    )

    content = f.read_text(encoding="utf-8")

    assert secret not in content
    assert "[[REDACTED_SECRET]]" in content