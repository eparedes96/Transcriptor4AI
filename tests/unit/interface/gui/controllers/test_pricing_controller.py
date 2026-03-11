# ==============================================================================
# TEST GROUP: GUI PRICING CONTROLLER
# ==============================================================================


import pytest

from transcriptor4ai.interface.gui.controllers.pricing_controller import PricingController


@pytest.fixture
def mock_coordinator(mocker):
    """
    1. ARRANGE: Creates a full mock of the AppController to isolate PricingController logic.
    Ensures all nested view components and registry ports are available.
    """
    coordinator = mocker.Mock()
    # Initial state for the session
    coordinator.config = {"target_model": "old-model"}

    # Mock Services
    coordinator.cost_estimator = mocker.Mock()
    coordinator.get_model_registry.return_value = mocker.Mock()

    # Mock Views
    coordinator.dashboard_view = mocker.Mock()
    coordinator.settings_view = mocker.Mock()
    coordinator.settings_view.combo_model = mocker.Mock()

    return coordinator


@pytest.fixture
def controller(mock_coordinator):
    """Provides the PricingController instance with injected mocks."""
    return PricingController(mock_coordinator)


# ==============================================================================
# TEST GROUP: REMOTE DATA SYNCHRONIZATION
# ==============================================================================

@pytest.mark.unit
def test_sync_remote_data_should_update_ui_to_live_on_success(mocker, controller, mock_coordinator):
    """
    Checks if a successful pricing sync triggers the green status
    indicator and refreshes views.
    """
    # 1. ARRANGE
    mock_coordinator.cost_estimator.sync_remote_data.return_value = True

    # 2. ACT: Execute sync callback
    controller.sync_remote_data(data=None)

    # 3. ASSERT: Verify visual and state side effects
    mock_coordinator.cost_estimator.sync_remote_data.assert_called_once()
    mock_coordinator.dashboard_view.set_pricing_status.assert_called_once_with(is_live=True)
    mock_coordinator.sync_view_from_config.assert_called_once()


@pytest.mark.unit
def test_sync_remote_data_should_show_cached_status_on_failure(mocker, controller, mock_coordinator):
    """
    Ensures the UI shows the 'Default/Cached' status if the network sync fails.
    """
    # 1. ARRANGE
    mock_coordinator.cost_estimator.sync_remote_data.return_value = False

    # 2. ACT
    controller.sync_remote_data(data=None)

    # 3. ASSERT
    mock_coordinator.dashboard_view.set_pricing_status.assert_called_once_with(is_live=False)


# ==============================================================================
# TEST GROUP: SELECTION AND FILTERING LOGIC
# ==============================================================================

@pytest.mark.unit
def test_handle_provider_change_should_filter_models_and_select_default(mocker, controller, mock_coordinator):
    """
    Validates that changing a provider populates the model list with correct entries
    and automatically selects the first available model in the new list.
    """
    # 1. ARRANGE
    mock_registry = mock_coordinator.get_model_registry.return_value
    mock_registry.get_available_models.return_value = {
        "gpt-4o": {"provider": "OPENAI"},
        "gpt-3.5": {"provider": "OPENAI"},
        "claude-3": {"provider": "ANTHROPIC"}
    }

    # Simulate UI returning the new auto-selected item
    mock_coordinator.settings_view.combo_model.get.return_value = "gpt-3.5"

    # 2. ACT: User selects provider from dropdown
    controller.handle_provider_change("OPENAI")

    # 3. ASSERT: Only OpenAI models should be in the list
    expected_models = ["gpt-3.5", "gpt-4o"]
    mock_coordinator.settings_view.combo_model.configure.assert_called_with(values=expected_models)

    # Verify the config dictionary was updated to the new default
    assert mock_coordinator.config["target_model"] == "gpt-3.5"


@pytest.mark.unit
def test_handle_model_change_should_persist_selection_in_config(controller, mock_coordinator):
    """
    Ensures that when a user selects a model, the internal config dict is updated immediately.
    """
    # 1. ARRANGE
    selected_model = "deepseek-coder"

    # 2. ACT
    controller.handle_model_change(selected_model)

    # 3. ASSERT
    assert mock_coordinator.config["target_model"] == selected_model


@pytest.mark.unit
def test_update_model_list_should_show_placeholder_when_no_models_found(controller, mock_coordinator):
    """
    Edge Case: If a provider is returned with zero models, show a descriptive placeholder.
    """
    # 1. ARRANGE
    mock_registry = mock_coordinator.get_model_registry.return_value
    mock_registry.get_available_models.return_value = {}

    # 2. ACT
    controller.update_model_list("GHOST_PROVIDER")

    # 3. ASSERT
    mock_coordinator.settings_view.combo_model.configure.assert_called_with(
        values=["-- No Models --"]
    )
    assert mock_coordinator.config["target_model"] == "-- No Models --"


@pytest.mark.unit
def test_update_model_list_should_preserve_selection_if_available(controller, mock_coordinator):
    """
    Behavioral Fix: If the provider list is refreshed but the previously
    selected model still exists, it should stay selected and state must be consistent.
    """
    # 1. ARRANGE: Set the state to match the model we want to keep
    mock_coordinator.config["target_model"] = "gpt-4o"

    mock_registry = mock_coordinator.get_model_registry.return_value
    mock_registry.get_available_models.return_value = {
        "gpt-4o": {"provider": "OPENAI"},
        "gpt-4-turbo": {"provider": "OPENAI"}
    }

    # 2. ACT: Refresh list for the same provider
    controller.update_model_list("OPENAI", preserve_selection="gpt-4o")

    # 3. ASSERT: View is updated and config is still correct
    mock_coordinator.settings_view.combo_model.set.assert_called_with("gpt-4o")
    assert mock_coordinator.config["target_model"] == "gpt-4o"