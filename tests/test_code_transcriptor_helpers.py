# tests/test_code_transcriptor_helpers.py
# -----------------------------------------------------------------------------
# Unit tests for code_transcriptor.py helpers.
# Focus:
# - defaults
# - regex compilation behavior (valid/invalid)
# - matching semantics (re.match)
# - test-file detection
# - safe mkdir behavior
# -----------------------------------------------------------------------------

import os
import re
import code_transcriptor as ct


def test_default_extensiones_is_py():
    assert ct._default_extensiones() == [".py"]


def test_default_patrones_incluir_is_match_all():
    pats = ct._default_patrones_incluir()
    assert pats == [".*"]
    compiled = ct._compile_patterns(pats)
    assert ct._matches_include("anything.py", compiled) is True


def test_default_patrones_excluir_includes_pycache_and_hidden():
    pats = ct._default_patrones_excluir()
    assert any("__pycache__" in p for p in pats)
    assert any(r"^\." in p for p in pats)

    compiled = ct._compile_patterns(pats)
    assert ct._matches_any("__pycache__", compiled) is True
    assert ct._matches_any(".venv", compiled) is True
    assert ct._matches_any("normal_dir", compiled) is False


def test_compile_patterns_keeps_valid_drops_invalid():
    patterns = [r"^ok$", r"([unclosed", r".*\.py$"]
    compiled = ct._compile_patterns(patterns)

    # Invalid pattern should be ignored; the valid ones remain.
    assert all(isinstance(x, re.Pattern) for x in compiled)
    assert any(rx.pattern == r"^ok$" for rx in compiled)
    assert any(rx.pattern == r".*\.py$" for rx in compiled)
    assert not any(rx.pattern == r"([unclosed" for rx in compiled)


def test_matches_any_true_false_and_empty_list():
    compiled = ct._compile_patterns([r"^a.*", r".*\.py$"])

    assert ct._matches_any("abc", compiled) is True
    assert ct._matches_any("file.py", compiled) is True
    assert ct._matches_any("zzz", compiled) is False
    assert ct._matches_any("anything", []) is False


def test_matches_include_false_when_include_empty():
    assert ct._matches_include("file.py", []) is False


def test_es_test_matches_test_prefix_and_suffix_only():
    assert ct._es_test("test_algo.py") is True
    assert ct._es_test("algo_test.py") is True

    assert ct._es_test("algo.py") is False
    assert ct._es_test("test_algo.txt") is False
    assert ct._es_test("algo_test.txt") is False


def test_es_test_edge_cases():
    assert ct._es_test("test_.py") is True
    assert ct._es_test("_test.py") is True  # matches .*_test.py
    assert ct._es_test("test.py") is False  # no underscore after test
    assert ct._es_test("mytest_file.py") is False


def test_safe_mkdir_creates_and_ok_if_exists(tmp_path):
    target = tmp_path / "out"
    ok, err = ct._safe_mkdir(str(target))
    assert ok is True
    assert err is None
    assert target.exists() and target.is_dir()

    # Calling again should still be ok
    ok2, err2 = ct._safe_mkdir(str(target))
    assert ok2 is True
    assert err2 is None


def test_safe_mkdir_returns_error_on_failure(monkeypatch, tmp_path):
    target = tmp_path / "out"

    def boom(*args, **kwargs):
        raise OSError("nope")

    monkeypatch.setattr(os, "makedirs", boom)

    ok, err = ct._safe_mkdir(str(target))
    assert ok is False
    assert err is not None
    assert "nope" in err
