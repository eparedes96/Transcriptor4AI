# tests/test_paths.py
import os
from transcriptor4ai.paths import normalizar_dir, ruta_salida_real, DEFAULT_OUTPUT_SUBDIR


# -----------------------------------------------------------------------------
# Path Normalization Tests
# -----------------------------------------------------------------------------

def test_normalizar_dir_handles_none_and_empty():
    """Fallback should be used when input is None or empty."""
    fallback = os.getcwd()

    # Case 1: None
    res_none = normalizar_dir(None, fallback)
    assert res_none == fallback

    # Case 2: Empty string
    res_empty = normalizar_dir("", fallback)
    assert res_empty == fallback

    # Case 3: Whitespace
    res_space = normalizar_dir("   ", fallback)
    assert res_space == fallback


def test_normalizar_dir_resolves_relative_paths():
    """Relative paths should be converted to absolute paths."""
    cwd = os.getcwd()
    rel_path = "subfolder"

    res = normalizar_dir(rel_path, fallback="/tmp")

    assert os.path.isabs(res)
    assert res == os.path.join(cwd, rel_path)


def test_normalizar_dir_expands_user_home():
    """Tilde (~) should be expanded to user home directory."""
    path_with_tilde = os.path.join("~", "Documents")
    res = normalizar_dir(path_with_tilde, fallback="/tmp")

    assert "~" not in res
    assert os.path.isabs(res)


# -----------------------------------------------------------------------------
# Output Path Logic Tests
# -----------------------------------------------------------------------------

def test_ruta_salida_real_joins_paths():
    """Output path should be correctly joined."""
    base = "/tmp/base"
    sub = "my_transcript"

    res = ruta_salida_real(base, sub)
    expected = os.path.join(base, sub)

    assert res == expected


def test_ruta_salida_real_uses_default_subdir():
    """If subdir is missing, use DEFAULT_OUTPUT_SUBDIR."""
    base = "/tmp/base"

    res = ruta_salida_real(base, "")
    expected = os.path.join(base, DEFAULT_OUTPUT_SUBDIR)

    assert res == expected