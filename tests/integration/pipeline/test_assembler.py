# ==============================================================================
# TEST GROUP: PIPELINE ASSEMBLER & FINALIZATION
# ==============================================================================

import pytest
from transcriptor4ai.application.pipeline.stages.assembler import assemble_and_finalize
from transcriptor4ai.domain.entities.pipeline_results import PipelineResult


@pytest.fixture
def sample_env_context(mocker):
    """Provides a standard environment context for assembly tests."""
    return {
        "final_output_path": "/user/project/transcript",
        "temp_dir_obj": mocker.Mock(),
        "base_path": "/user/project",
        "prefix": "v1",
        "existing_files": [],
        "paths": {
            "modules": "/tmp/stg/v1_modules.txt",
            "tests": "/tmp/stg/v1_tests.txt",
            "unified": "/tmp/stg/v1_full_context.txt"
            # 'tree' is intentionally omitted to test resilience against KeyError
        }
    }


# ------------------------------------------------------------------------------
# SCENARIO: SUCCESSFUL ASSEMBLY FLOW
# ------------------------------------------------------------------------------

def test_assemble_should_orchestrate_full_deployment_successfully(mocker, mock_fs, sample_env_context):
    """Verifies that the assembler coordinates aggregation, tokens, and deployment."""
    # 1. ARRANGE
    cfg = {
        "create_unified_file": True,
        "create_individual_files": True,
        "generate_tree": False,
        "target_model": "gpt-4o"
    }
    trans_res = {
        "ok": True,
        "generated": {"modules": "/tmp/stg/v1_modules.txt"},
        "counters": {"processed": 5, "total_tokens": 100}
    }

    mock_fs.generate_unified_file.return_value = True
    mock_fs.read_file_content.return_value = "dummy content for token count"
    m_tokenizer = mocker.patch("transcriptor4ai.application.pipeline.stages.assembler.count_tokens", return_value=500)

    # 2. ACT
    result = assemble_and_finalize(
        fs=mock_fs, cfg=cfg, trans_res=trans_res,
        tree_lines=[], env_context=sample_env_context, dry_run=False
    )

    # 3. ASSERT
    assert isinstance(result, PipelineResult)
    assert result.ok is True
    assert result.token_count == 500
    mock_fs.deploy_pipeline_artifacts.assert_called_once()
    sample_env_context["temp_dir_obj"].cleanup.assert_called_once()


def test_assemble_should_skip_deployment_during_dry_run(mock_fs, sample_env_context):
    """Ensures that dry_run=True prevents any movement of files to final directory."""
    # 1. ARRANGE
    cfg = {"create_unified_file": False, "create_individual_files": True, "generate_tree": False}
    trans_res = {"ok": True, "generated": {}, "counters": {}}

    # 2. ACT
    result = assemble_and_finalize(
        fs=mock_fs, cfg=cfg, trans_res=trans_res,
        tree_lines=[], env_context=sample_env_context, dry_run=True
    )

    # 3. ASSERT
    assert result.ok is True
    mock_fs.deploy_pipeline_artifacts.assert_not_called()


# ------------------------------------------------------------------------------
# SCENARIO: OUTPUT STRATEGY AND FILTERING (FIXED)
# ------------------------------------------------------------------------------

@pytest.mark.parametrize("create_unified, create_individual", [
    (False, True),
    (True, False)
])
def test_assemble_respects_output_strategy_filters(mocker, mock_fs, sample_env_context, create_unified,
                                                   create_individual):
    """Validates that only the requested file types are present in the final result mapping."""
    # 1. ARRANGE
    cfg = {
        "create_unified_file": create_unified,
        "create_individual_files": create_individual,
        "generate_tree": False
    }
    trans_res = {
        "ok": True,
        "generated": {"modules": "path/m.txt", "tests": "path/t.txt"},
        "counters": {}
    }
    mock_fs.generate_unified_file.return_value = True
    mock_fs.read_file_content.return_value = ""  # Fix precision count warning

    # FIX: Instruct the Mock to simulate the behavior of updating the results_map
    def deploy_side_effect(staging_paths, final_dir, prefix, unified_ok, results_map):
        if unified_ok:
            results_map["unified"] = f"{final_dir}/{prefix}_full_context.txt"

    mock_fs.deploy_pipeline_artifacts.side_effect = deploy_side_effect

    # 2. ACT
    result = assemble_and_finalize(
        fs=mock_fs, cfg=cfg, trans_res=trans_res,
        tree_lines=[], env_context=sample_env_context, dry_run=False
    )

    # 3. ASSERT
    gen_files = result.summary["generated_files"]

    if not create_individual:
        assert "modules" not in gen_files
        assert "tests" not in gen_files

    if create_unified:
        # Now this will pass because the side_effect injected the key
        assert "unified" in gen_files


# ------------------------------------------------------------------------------
# SCENARIO: ERROR HANDLING AND RESILIENCE
# ------------------------------------------------------------------------------

def test_assemble_is_resilient_to_missing_tree_path_key(mock_fs, sample_env_context):
    """Verifies the assembler doesn't crash if the 'tree' key is missing from paths."""
    # 1. ARRANGE
    cfg = {"create_unified_file": False, "create_individual_files": True, "generate_tree": False}
    trans_res = {"ok": True, "generated": {}, "counters": {}}

    # 2. ACT
    result = assemble_and_finalize(
        fs=mock_fs, cfg=cfg, trans_res=trans_res,
        tree_lines=[], env_context=sample_env_context, dry_run=False
    )

    # 3. ASSERT
    assert result.ok is True
    assert result.tree_path == ""


def test_assemble_should_handle_token_counting_errors_gracefully(mocker, mock_fs, sample_env_context):
    """Ensures that a crash in the tokenizer library does not block the pipeline execution."""
    # 1. ARRANGE
    cfg = {"create_unified_file": True, "create_individual_files": True, "generate_tree": False}
    mock_fs.generate_unified_file.return_value = True
    mock_fs.read_file_content.return_value = "dummy"

    mocker.patch("transcriptor4ai.application.pipeline.stages.assembler.count_tokens",
                 side_effect=RuntimeError("Tokenization Engine Crash"))

    # 2. ACT
    result = assemble_and_finalize(
        fs=mock_fs, cfg=cfg, trans_res={"ok": True, "generated": {}},
        tree_lines=[], env_context=sample_env_context, dry_run=False
    )

    # 3. ASSERT
    assert result.ok is True
    assert result.token_count == 0
    mock_fs.deploy_pipeline_artifacts.assert_called_once()