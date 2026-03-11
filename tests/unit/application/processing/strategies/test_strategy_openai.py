import pytest

from transcriptor4ai.application.processing.strategies.openai import TiktokenStrategy

# ==============================================================================
# TEST GROUP: OPENAI TIKTOKEN STRATEGY
# ==============================================================================

@pytest.fixture
def mock_encoding(mocker):
    """Mocks a tiktoken encoding object and the get_encoding factory."""
    # Create a mock encoding object
    mock_enc = mocker.Mock()
    # By default, encoding returns 5 tokens
    mock_enc.encode.return_value = [1, 2, 3, 4, 5]

    # Patch the get_encoding function
    return mocker.patch("tiktoken.get_encoding", return_value=mock_enc)


@pytest.fixture
def strategy():
    """Provides a fresh instance of TiktokenStrategy."""
    return TiktokenStrategy()


@pytest.mark.unit
def test_should_raise_import_error_when_tiktoken_is_missing(mocker, strategy):
    """Ensures a clean failure if the tiktoken library is not installed."""
    # 1. ARRANGE: Force the availability flag to False
    mocker.patch("transcriptor4ai.application.processing.strategies.openai.TIKTOKEN_AVAILABLE", False)

    # 2. ACT & 3. ASSERT
    with pytest.raises(ImportError, match="tiktoken' is not installed"):
        strategy.count("some text", "gpt-4")


@pytest.mark.unit
@pytest.mark.parametrize("model_id, expected_encoding", [
    ("gpt-4o", "o200k_base"),
    ("gpt-4o-mini", "o200k_base"),
    ("o1-preview", "o200k_base"),
    ("gpt-4-turbo", "cl100k_base"),
    ("gpt-3.5-turbo", "cl100k_base"),
    ("legacy-text-davinci", "cl100k_base"),
])
def test_should_select_correct_encoding_for_specific_models(
        mocker, mock_encoding, strategy, model_id, expected_encoding
):
    """Verifies the mapping logic between model names and BPE encodings."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.openai.TIKTOKEN_AVAILABLE", True)

    # 2. ACT
    strategy.count("Hello AI", model_id)

    # 3. ASSERT
    # Verify the strategy requested the correct encoding name
    mock_encoding.assert_called_with(expected_encoding)


@pytest.mark.unit
def test_should_fallback_to_cl100k_when_encoding_name_is_invalid(mocker, mock_encoding, strategy):
    """Ensures resilience when tiktoken fails to find a specific encoding name."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.openai.TIKTOKEN_AVAILABLE", True)

    # First call fails with ValueError (common in tiktoken for unknown names), second succeeds
    mock_encoding.side_effect = [
        ValueError("Unknown encoding"),
        mock_encoding.return_value
    ]

    # 2. ACT
    count = strategy.count("Resilience test", "unknown-model")

    # 3. ASSERT
    assert count == 5
    assert mock_encoding.call_count == 2
    # Verify the last call was the safety fallback
    mock_encoding.assert_called_with("cl100k_base")


@pytest.mark.unit
def test_should_return_length_of_encoded_list_as_token_count(mocker, mock_encoding, strategy):
    """Validates that the final count is strictly the number of items in the token list."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.openai.TIKTOKEN_AVAILABLE", True)
    mock_encoding.return_value.encode.return_value = [101, 102, 103]  # 3 tokens

    # 2. ACT
    count = strategy.count("Small text", "gpt-4o")

    # 3. ASSERT
    assert count == 3
    # Ensure disallowed_special=() is used to prevent crashes on raw text input
    mock_encoding.return_value.encode.assert_called_once_with("Small text", disallowed_special=())


@pytest.mark.unit
def test_should_handle_unusual_characters_without_crashing(mocker, mock_encoding, strategy):
    """Verifies that unicode or unusual strings are passed correctly to the encoder."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.openai.TIKTOKEN_AVAILABLE", True)
    complex_text = "🚀 Unicode test with symbols: { } [ ]"

    # 2. ACT
    strategy.count(complex_text, "gpt-4o")

    # 3. ASSERT
    mock_encoding.return_value.encode.assert_called_with(complex_text, disallowed_special=())