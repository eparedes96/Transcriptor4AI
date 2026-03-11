import textwrap

import pytest

from transcriptor4ai.application.transformation.code_minifier import CodeMinifierService
from transcriptor4ai.application.transformation.privacy_sanitizer import PrivacySanitizerService

# ==============================================================================
# TEST GROUP: FORMAT PRESERVATION & LOGIC INTEGRITY
# ==============================================================================

@pytest.fixture
def minifier():
    return CodeMinifierService()


@pytest.fixture
def sanitizer(mocker):
    mock_user = mocker.Mock()
    mock_user.get_username.return_value = "sdet_user"
    mock_user.get_home_directory.return_value = "/home/sdet_user"
    return PrivacySanitizerService(mock_user)


@pytest.mark.unit
def test_should_preserve_python_indentation_after_minification(minifier):
    """
    Python relies on indentation for logic. Removing empty lines or
    trailing whitespace must not affect the leading spaces.
    """
    # 1. ARRANGE
    source = textwrap.dedent("""
        def outer():
            # Comment to remove
            if True:
                print("Inside")

            return None
    """)

    # 2. ACT
    result = minifier.minify(source, ".py")

    # 3. ASSERT
    # Check that block levels are still there
    assert "    if True:" in result
    assert "        print(" in result
    assert "# Comment" not in result


@pytest.mark.unit
def test_should_not_remove_hash_symbols_inside_strings(minifier):
    """
    CRITICAL: A common bug in minifiers is deleting '#' inside a string literal.
    Example: URLs with anchors or CSS hex colors.
    """
    # 1. ARRANGE
    source = "url = 'https://github.com/repo#anchor' # Trailing comment"

    # 2. ACT
    result = minifier.minify(source, ".py")

    # 3. ASSERT
    assert "https://github.com/repo#anchor" in result
    assert "# Trailing comment" not in result


@pytest.mark.unit
def test_should_maintain_syntax_validity_after_secret_redaction(sanitizer):
    """
    Redacting a secret must replace only the content, not the surrounding
    syntax characters (like quotes or colons) to avoid breaking the script.
    """
    # 1. ARRANGE
    source = 'config = {"api_key": "sk-1234567890abcdef1234567890abcdef"}'

    # 2. ACT
    result = sanitizer.sanitize(source)

    # 3. ASSERT
    # The quotes of the dictionary key and value must remain
    assert '"api_key":' in result
    assert '"[[REDACTED_SENSITIVE]]"' in result or '"[[REDACTED_SECRET]]"' in result


@pytest.mark.unit
@pytest.mark.parametrize("ext, comment_trigger", [
    (".js", "// Logic check"),
    (".ts", "// Logic check"),
    (".cpp", "// Logic check"),
    (".java", "// Logic check"),
])
def test_should_preserve_brackets_and_semicolons_in_c_style_languages(minifier, ext, comment_trigger):
    """
    Ensures that for C-style languages, the stripping of // comments
    doesn't accidentally swallow closing brackets on the same line.
    """
    # 1. ARRANGE
    source = f"if (x) {{ do_thing(); }} {comment_trigger}"

    # 2. ACT
    result = minifier.minify(source, ext)

    # 3. ASSERT
    assert "if (x) { do_thing(); }" in result
    assert comment_trigger not in result


@pytest.mark.unit
def test_integration_combined_transformations_preserve_functional_core(minifier, sanitizer):
    """
    Simulates the full pipeline: Code -> Minify -> Sanitize -> Mask Paths.
    The resulting code must contain only the 'skeleton' of the logic.
    """
    # 1. ARRANGE
    source = textwrap.dedent("""
        def connect():
            # Initializing connection
            user_path = "/home/sdet_user/keys/prod.pem"
            pwd = "password123" 
            return open(user_path)
    """)

    # 2. ACT
    step1 = minifier.minify(source, ".py")
    step2 = sanitizer.sanitize(step1)
    final_result = sanitizer.mask_paths(step2)

    # 3. ASSERT
    assert "def connect():" in final_result
    assert "# Initializing" not in final_result
    assert "<USER_HOME>" in final_result
    assert "[[REDACTED_SECRET]]" in final_result
    assert "return open" in final_result