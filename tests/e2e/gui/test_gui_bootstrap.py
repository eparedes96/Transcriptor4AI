import pytest
import customtkinter as ctk
from transcriptor4ai.interface.gui.bootstrap.di_container import build_application_context, ApplicationContext
from transcriptor4ai.interface.gui.components.main_window import create_main_window


# ==============================================================================
# TEST GROUP: GUI BOOTSTRAP AND DI LIFESTYLE
# ==============================================================================

@pytest.mark.gui
def test_application_context_builds_successfully_with_all_dependencies(mocker, mock_fs):
    """Verifies that the DI container wires all infrastructure ports correctly."""
    # 1. ARRANGE: Mock repositories to prevent real disk access during DI build
    mocker.patch("transcriptor4ai.interface.gui.bootstrap.di_container.JsonConfigRepository")
    mocker.patch("transcriptor4ai.interface.gui.bootstrap.di_container.SqliteCacheRepository")
    mocker.patch("transcriptor4ai.interface.gui.bootstrap.di_container.ModelRegistryRepository")

    # 2. ACT: Build the context
    context = build_application_context()

    # 3. ASSERT: Ensure it's the correct type and all adapters are present
    # Critical point: If any port is missing, the GUI controllers will fail later
    assert isinstance(context, ApplicationContext)
    assert context.fs is not None
    assert context.cache is not None
    assert context.config_repo is not None
    assert isinstance(context.profile_names, list)


@pytest.mark.gui
def test_bootstrap_should_fallback_to_defaults_when_config_is_corrupted(mocker):
    """Ensures the app doesn't crash at startup if config files are unreadable."""
    # 1. ARRANGE: Force a critical failure during state recovery
    mocker.patch(
        "transcriptor4ai.infrastructure.persistence.json_config_repo.JsonConfigRepository.load_app_state",
        side_effect=RuntimeError("Hard disk failure simulation")
    )
    # Mocking os.getcwd to provide a stable test path
    mocker.patch("os.getcwd", return_value="/tmp/test_run")

    # 2. ACT: Attempt to build context
    context = build_application_context()

    # 3. ASSERT: Verify it returned a safe fallback state instead of raising exception
    assert context.config["processing_depth"] == "full"
    assert context.app_state["app_settings"]["theme"] == "SystemDefault"
    assert context.profile_names == []


@pytest.mark.gui
def test_main_window_initialization_parameters(mocker):
    """Validates that the main window is configured with the professional standards."""
    # 1. ARRANGE: Mock CTk to prevent the window from actually appearing
    mock_ctk = mocker.patch("customtkinter.CTk")
    mocker.patch("customtkinter.set_appearance_mode")
    mocker.patch("customtkinter.set_default_color_theme")

    # 2. ACT: Call the window factory
    app = create_main_window()

    # 3. ASSERT: Check window metadata and layout configuration
    # Ensures the UI scales correctly on high-DPI displays
    mock_ctk.return_value.title.assert_called()
    mock_ctk.return_value.minsize.assert_called_with(800, 600)

    # Verify grid layout has at least the two main columns (Sidebar + Content)
    mock_ctk.return_value.grid_columnconfigure.assert_any_call(1, weight=1)
    assert app is not None