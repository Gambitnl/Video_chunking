"""Tests for UI helper utilities."""

import gradio as gr

from src.ui.helpers import ButtonStates


def test_button_states_busy_disables_and_sets_label():
    """Busy state should disable the button and set the loading label."""

    update = ButtonStates.busy("[WORKING] Starting processing")

    assert isinstance(update, dict)
    assert update["value"] == "[WORKING] Starting processing"
    assert update["interactive"] is False


def test_button_states_ready_enables_and_sets_label():
    """Ready state should enable the button and restore the label."""

    update = ButtonStates.ready("Start Processing")

    assert isinstance(update, dict)
    assert update["value"] == "Start Processing"
    assert update["interactive"] is True


def test_button_states_disabled_disables_and_sets_label():
    """Disabled state should lock the button while keeping the provided label."""

    update = ButtonStates.disabled("Run Preflight Checks")

    assert isinstance(update, dict)
    assert update["value"] == "Run Preflight Checks"
    assert update["interactive"] is False
