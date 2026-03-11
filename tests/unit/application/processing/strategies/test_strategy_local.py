import pytest

from transcriptor4ai.application.processing.strategies.local import (
    _TOKENIZER_CACHE,
    MistralStrategy,
    TransformersStrategy,
)

# ==============================================================================
# TEST GROUP: LOCAL TOKENIZATION STRATEGIES (TRANSFORMERS & MISTRAL)
# ==============================================================================

@pytest.fixture(autouse=True)
def clear_tokenizer_cache():
    """Ensures a clean state for each test by wiping the module-level cache."""
    _TOKENIZER_CACHE.clear()
    yield
    _TOKENIZER_CACHE.clear()


@pytest.fixture
def mock_transformers_sdk(mocker):
    """Mocks the HuggingFace AutoTokenizer class and its encoding logic."""
    mock_tokenizer = mocker.Mock()
    # Simulate the tokenizer returning a list of token IDs
    mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]

    return mocker.patch("transformers.AutoTokenizer.from_pretrained", return_value=mock_tokenizer)


@pytest.fixture
def mock_mistral_sdk(mocker):
    """Mocks the Mistral reference tokenizer and response structures."""
    mock_tokenizer = mocker.Mock()

    # Simulate response structure: response.tokens -> list
    mock_encoded = mocker.Mock()
    mock_encoded.tokens = [10, 20, 30]
    mock_tokenizer.encode_chat_completion.return_value = mock_encoded

    return mocker.patch("mistral_common.tokens.tokenizers.mistral.MistralTokenizer.v3", return_value=mock_tokenizer)


# ------------------------------------------------------------------------------
# SUBGROUP: TRANSFORMERS STRATEGY
# ------------------------------------------------------------------------------

@pytest.mark.unit
def test_transformers_should_raise_import_error_when_pkg_missing(mocker):
    """Ensures strategy fails gracefully if 'transformers' is not in the environment."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.local.TRANSFORMERS_AVAILABLE", False)
    strategy = TransformersStrategy()

    # 2. ACT & 3. ASSERT
    with pytest.raises(ImportError, match="transformers' is not installed"):
        strategy.count("text", "llama")


@pytest.mark.unit
@pytest.mark.parametrize("model_id, expected_hf_path", [
    ("llama-3-8b", "meta-llama/Meta-Llama-3-8B"),
    ("Qwen-2.5", "Qwen/Qwen2.5-7B-Instruct"),
    ("deepseek-v3", "deepseek-ai/deepseek-coder-33b-instruct"),
])
def test_transformers_should_map_and_count_tokens_correctly(
        mock_transformers_sdk, model_id, expected_hf_path
):
    """Validates mapping of logical names to HuggingFace IDs and token count extraction."""
    # 1. ARRANGE
    strategy = TransformersStrategy()
    text = "Hello local world"

    # 2. ACT
    count = strategy.count(text, model_id)

    # 3. ASSERT
    assert count == 5  # Length of the list in mock_transformers_sdk
    mock_transformers_sdk.assert_called_with(expected_hf_path)
    _TOKENIZER_CACHE[expected_hf_path].encode.assert_called_once_with(text)


@pytest.mark.unit
def test_transformers_should_use_cache_to_avoid_reloading_models(mock_transformers_sdk):
    """Ensures expensive model loading happens only once per model ID."""
    # 1. ARRANGE
    strategy = TransformersStrategy()
    model_id = "llama-3"

    # 2. ACT
    strategy.count("first call", model_id)
    strategy.count("second call", model_id)

    # 3. ASSERT
    # AutoTokenizer.from_pretrained should only be called once
    assert mock_transformers_sdk.call_count == 1


# ------------------------------------------------------------------------------
# SUBGROUP: MISTRAL STRATEGY
# ------------------------------------------------------------------------------

@pytest.mark.unit
def test_mistral_should_raise_import_error_when_pkg_missing(mocker):
    """Ensures strategy fails gracefully if 'mistral_common' is missing."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.local.MISTRAL_AVAILABLE", False)
    strategy = MistralStrategy()

    # 2. ACT & 3. ASSERT
    with pytest.raises(ImportError, match="mistral_common' is not installed"):
        strategy.count("text", "mistral-large")


@pytest.mark.unit
def test_mistral_should_call_sdk_with_correct_request_format(mock_mistral_sdk):
    """Verifies that Mistral strategy wraps text in a ChatCompletionRequest."""
    # 1. ARRANGE
    strategy = MistralStrategy()
    text = "Mistral logic test"

    # 2. ACT
    count = strategy.count(text, "mistral-tiny")

    # 3. ASSERT
    assert count == 3
    mock_mistral_sdk.assert_called_once_with(is_tekken=True)

    # Verify the complex call structure for Mistral SDK
    tokenizer_instance = mock_mistral_sdk.return_value
    args, _ = tokenizer_instance.encode_chat_completion.call_args
    request = args[0]

    assert request.messages[0].content == text


@pytest.mark.unit
def test_local_strategies_should_log_and_propagate_unexpected_errors(mocker, mock_transformers_sdk):
    """Ensures technical failures during local tokenization are recorded."""
    # 1. ARRANGE
    mock_transformers_sdk.side_effect = Exception("GPU/Memory Error")
    mock_logger = mocker.patch("transcriptor4ai.application.processing.strategies.local.logger.error")
    strategy = TransformersStrategy()

    # 2. ACT & 3. ASSERT
    with pytest.raises(Exception, match="GPU/Memory Error"):
        strategy.count("text", "llama")

    mock_logger.assert_called_once()