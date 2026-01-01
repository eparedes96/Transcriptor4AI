# tests/test_tree_generator_helpers.py
# -----------------------------------------------------------------------------
# Unit tests for tree_generator.py helper functions.
# Focus:
# - defaults
# - regex compilation behavior (valid/invalid)
# - matching semantics (re.match, not search)
# - test-file detection
# -----------------------------------------------------------------------------

import re

import transcriptor4ai.filtering
import tree_generator as tg


def test_default_extensiones_is_py():
    assert transcriptor4ai.filtering.default_extensiones() == [".py"]


def test_default_patrones_incluir_is_match_all():
    pats = transcriptor4ai.filtering.default_patrones_incluir()
    assert pats == [".*"]
    compiled = transcriptor4ai.filtering.compile_patterns(pats)
    # match-all should match from beginning
    assert any(rx.match("anything.py") for rx in compiled)


def test_default_patrones_excluir_includes_pycache_and_hidden():
    pats = transcriptor4ai.filtering.default_patrones_excluir()
    assert any("__pycache__" in p for p in pats)
    assert any(r"^\." in p for p in pats)

    compiled = transcriptor4ai.filtering.compile_patterns(pats)
    assert transcriptor4ai.filtering.matches_any("__pycache__", compiled) is True
    assert transcriptor4ai.filtering.matches_any(".venv", compiled) is True
    assert transcriptor4ai.filtering.matches_any("normal_dir", compiled) is False


def test_compile_patterns_keeps_valid_drops_invalid():
    patterns = [r"^ok$", r"([unclosed", r".*\.py$"]
    compiled = transcriptor4ai.filtering.compile_patterns(patterns)

    assert all(isinstance(x, re.Pattern) for x in compiled)
    assert any(rx.pattern == r"^ok$" for rx in compiled)
    assert any(rx.pattern == r".*\.py$" for rx in compiled)
    assert not any(rx.pattern == r"([unclosed" for rx in compiled)


def test_matches_any_semantics_match_not_search():
    compiled = transcriptor4ai.filtering.compile_patterns([r"abc"])
    # re.match requires match at the start; "xabc" should NOT match
    assert transcriptor4ai.filtering.matches_any("abc", compiled) is True
    assert transcriptor4ai.filtering.matches_any("xabc", compiled) is False


def test_matches_any_empty_list_is_false():
    assert transcriptor4ai.filtering.matches_any("anything", []) is False


def test_es_test_same_behavior_as_transcriptor():
    assert transcriptor4ai.filtering.es_test("test_algo.py") is True
    assert transcriptor4ai.filtering.es_test("algo_test.py") is True

    assert transcriptor4ai.filtering.es_test("algo.py") is False
    assert transcriptor4ai.filtering.es_test("test_algo.txt") is False
    assert transcriptor4ai.filtering.es_test("algo_test.txt") is False


def test_es_test_edge_cases():
    assert transcriptor4ai.filtering.es_test("test_.py") is True
    assert transcriptor4ai.filtering.es_test("_test.py") is True
    assert transcriptor4ai.filtering.es_test("test.py") is False
    assert transcriptor4ai.filtering.es_test("mytest_file.py") is False
