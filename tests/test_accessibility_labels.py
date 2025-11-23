import gradio as gr

from src.ui.helpers import AccessibilityAttributes, UIComponents
from src.ui.process_session_components import ProcessSessionTabBuilder


def test_accessibility_attributes_apply_sets_metadata():
    button = gr.Button("Click")
    applied = AccessibilityAttributes.apply(
        button,
        label="Click action",
        described_by="helper",
        role="button",
        live="polite",
        elem_id="click-action",
    )

    assert applied.accessible_label == "Click action"
    assert applied.aria_describedby == "helper"
    assert applied.aria_role == "button"
    assert applied.aria_live == "polite"
    assert applied.elem_id == "click-action"
    assert "aria-live" in applied.elem_classes


def test_action_button_propagates_accessible_label():
    button = UIComponents.create_action_button(
        "Save",
        accessible_label="Save configuration",
        aria_describedby="status-area",
        elem_id="save-config-btn",
    )

    assert button.accessible_label == "Save configuration"
    assert button.aria_describedby == "status-area"
    assert button.elem_id == "save-config-btn"


def test_process_builder_marks_status_live_region():
    builder = ProcessSessionTabBuilder(
        available_parties=["Manual Entry"],
        initial_defaults={},
        campaign_badge_text="",
    )
    with gr.Blocks():
        components = builder.build_ui_components()

    status_output = components["status_output"]
    assert status_output.accessible_label == "Processing status"
    assert status_output.aria_live == "polite"
    assert status_output.aria_role == "status"
