# ==============================================================================
# TEST GROUP: CORE PIPELINE ORCHESTRATOR
# ==============================================================================

import pytest
import threading
from transcriptor4ai.application.pipeline.orchestrator import run_pipeline
from transcriptor4ai.domain.entities.pipeline_results import PipelineResult


@pytest.fixture
def mock_stages(mocker):
    """
    Mocks all major pipeline stages to isolate orchestration logic.
    Ensures that return dictionaries contain mandatory keys to avoid KeyErrors.
    """
    # 1. ARRANGE: Define a valid minimal config that validator would return
    valid_cfg = {
        "input_path": "/src",
        "extensions": [".py"],
        "include_patterns": [".*"],
        "exclude_patterns": [],
        "generate_tree": True,
        "process_tests": True,
        "process_resources": False,
        "respect_gitignore": True,
        "save_error_log": True,
        "create_individual_files": True,
        "create_unified_file": True,
        "processing_depth": "full"
    }

    return {
        "validate": mocker.patch("transcriptor4ai.application.pipeline.orchestrator.validate_config",
                                 return_value=(valid_cfg, [])),
        "setup": mocker.patch("transcriptor4ai.application.pipeline.orchestrator.prepare_environment"),
        "tree_gen": mocker.patch("transcriptor4ai.application.pipeline.orchestrator.generate_directory_tree"),
        "transcribe": mocker.patch("transcriptor4ai.application.pipeline.orchestrator.transcribe_code"),
        "assemble": mocker.patch("transcriptor4ai.application.pipeline.orchestrator.assemble_and_finalize"),
        "error_factory": mocker.patch("transcriptor4ai.application.pipeline.orchestrator.create_error_result")
    }


# ------------------------------------------------------------------------------
# SCENARIO: FULL EXECUTION FLOW
# ------------------------------------------------------------------------------

def test_run_pipeline_should_execute_full_sequence_on_success(mocker, mock_fs, memory_cache_repo, mock_user_context,
                                                              mock_stages):
    """Verifies the correct sequencing and data passing between successful stages."""
    # 1. ARRANGE
    stages = mock_stages
    env_context = {
        "paths": {
            "modules": "m.txt", "tests": "t.txt", "resources": "r.txt",
            "errors": "e.txt", "tree": "tr.txt", "unified": "u.txt"
        },
        "base_path": "/src",
        "final_output_path": "/out",
        "temp_dir_obj": mocker.Mock(),
        "prefix": "out"
    }
    stages["setup"].return_value = (None, env_context)
    stages["tree_gen"].return_value = ["tree_lines"]
    stages["transcribe"].return_value = {"ok": True, "generated": {"modules": "m.txt"}}
    stages["assemble"].return_value = mocker.Mock(spec=PipelineResult)

    # 2. ACT
    run_pipeline(
        fs=mock_fs, cache=memory_cache_repo, user_context=mock_user_context,
        config={"some": "raw_input"}, overwrite=True
    )

    # 3. ASSERT: Verify the execution chain
    stages["validate"].assert_called_once()
    stages["setup"].assert_called_once()

    # Verify concurrency tasks were launched
    stages["tree_gen"].assert_called_once()
    stages["transcribe"].assert_called_once()

    # Verify final assembly was reached with results from workers
    stages["assemble"].assert_called_once_with(
        mock_fs, mocker.ANY, {"ok": True, "generated": {"modules": "m.txt"}},
        ["tree_lines"], env_context, False
    )


# ------------------------------------------------------------------------------
# SCENARIO: ABORTION AND CLEANUP
# ------------------------------------------------------------------------------

def test_run_pipeline_should_abort_if_setup_fails(mocker, mock_fs, memory_cache_repo, mock_user_context, mock_stages):
    """Ensures that environment errors (like path collisions) prevent engine execution."""
    # 1. ARRANGE
    stages = mock_stages
    error_result = mocker.Mock(spec=PipelineResult)
    stages["setup"].return_value = (error_result, {})

    # 2. ACT
    result = run_pipeline(
        fs=mock_fs, cache=memory_cache_repo, user_context=mock_user_context, config={}
    )

    # 3. ASSERT
    assert result == error_result
    # Parallel tasks must NEVER be called
    stages["tree_gen"].assert_not_called()
    stages["transcribe"].assert_not_called()


def test_run_pipeline_should_cleanup_on_transcription_failure(mocker, mock_fs, memory_cache_repo, mock_user_context,
                                                              mock_stages):
    """Verifies that temporary directory is cleaned up even if transcription fails."""
    # 1. ARRANGE
    stages = mock_stages
    temp_dir_mock = mocker.Mock()
    env_context = {
        "paths": {"tree": "tr.txt"},  # Tree path needed for thread launch
        "base_path": "/src", "final_output_path": "/out",
        "temp_dir_obj": temp_dir_mock, "prefix": "out"
    }
    stages["setup"].return_value = (None, env_context)

    # Force engine failure
    stages["transcribe"].return_value = {"ok": False, "error": "Access Denied"}
    stages["error_factory"].return_value = mocker.Mock(spec=PipelineResult)

    # 2. ACT
    run_pipeline(fs=mock_fs, cache=memory_cache_repo, user_context=mock_user_context, config={})

    # 3. ASSERT
    # Temporary resources MUST be released
    temp_dir_mock.cleanup.assert_called_once()
    stages["error_factory"].assert_called_with(
        "Pipeline error: Access Denied", mocker.ANY, "/src", "/out"
    )


# ------------------------------------------------------------------------------
# SCENARIO: SIGNAL PROPAGATION
# ------------------------------------------------------------------------------

def test_run_pipeline_passes_cancellation_event_to_workers(mocker, mock_fs, memory_cache_repo, mock_user_context,
                                                           mock_stages):
    """Validates that the user cancellation signal is correctly routed to background tasks."""
    # 1. ARRANGE
    stages = mock_stages
    stages["setup"].return_value = (None, {
        "paths": {}, "base_path": "/src", "final_output_path": "/out",
        "temp_dir_obj": None, "prefix": "out"
    })
    stages["transcribe"].return_value = {"ok": True}

    cancel_event = threading.Event()

    # 2. ACT
    run_pipeline(
        fs=mock_fs, cache=memory_cache_repo, user_context=mock_user_context,
        config={}, cancellation_event=cancel_event
    )

    # 3. ASSERT: Worker pool must receive the event reference
    _, kwargs = stages["transcribe"].call_args
    assert kwargs["cancellation_event"] == cancel_event