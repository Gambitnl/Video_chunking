"""
UI component for the first-run setup wizard.

This wizard guides the user through creating their first campaign if no campaigns
are detected on startup. It is designed to be a simple, one-step process
to get them into the main application quickly.
"""
import gradio as gr
from typing import Callable

from src.party_config import CampaignManager
from src.ui.helpers import StatusMessages, UIComponents


def create_setup_wizard(
    campaign_manager: CampaignManager,
    on_finish_callback: Callable[[str], None]
):
    """
    Creates the Gradio UI for the setup wizard.

    The wizard is a single container that is shown only when no campaigns exist.
    It prompts for a new campaign name and, upon completion, triggers a callback
    to reload the main UI.

    Args:
        campaign_manager: An instance of CampaignManager to handle campaign creation.
        on_finish_callback: A function to call when the wizard is completed.
                            It receives the new campaign name as an argument.

    Returns:
        A tuple containing:
        - The main Gradio container for the wizard.
        - The finish button component (to wire up external events).
        - The campaign name input component.
    """
    with gr.Column(
        visible=False,  # Initially hidden, shown from app.py if no campaigns
        elem_id="setup-wizard-container"
    ) as wizard_container:
        gr.Markdown("# Welcome to the D&D Session Processor!")
        gr.Markdown(
            "It looks like this is your first time here. Let's create your first campaign to get started."
        )

        status_message = gr.Markdown(
            value=StatusMessages.info(
                "Campaign Setup",
                "A campaign is a container for your sessions, characters, and lore."
            ),
            elem_id="wizard-status-message"
        )

        with gr.Row():
            new_campaign_name_input = gr.Textbox(
                label="Campaign Name",
                placeholder="e.g., The Dragon's Demise",
                scale=3
            )
            finish_setup_button = UIComponents.create_action_button(
                "Create Campaign & Start",
                variant="primary",
                scale=1
            )

        def _handle_finish_setup(campaign_name: str):
            """Internal handler for the finish button click."""
            if not campaign_name or not campaign_name.strip():
                return gr.update(
                    value=StatusMessages.error(
                        "Invalid Name",
                        "Campaign name cannot be empty."
                    )
                )

            try:
                # Use the campaign manager to create the new campaign
                campaign_id, _ = campaign_manager.create_blank_campaign(name=campaign_name)

                # Hide the wizard UI and show a success message
                # The main app will handle showing the dashboard
                return (
                    gr.update(visible=False),
                    gr.update(
                        value=StatusMessages.success(
                            "Campaign Created!",
                            f"Successfully created '{campaign_name}'. Loading dashboard..."
                        )
                    )
                )

            except Exception as e:
                return gr.update(
                    value=StatusMessages.error(
                        "Creation Failed",
                        "Could not create the campaign. Please check the logs.",
                        str(e)
                    )
                )

        finish_setup_button.click(
            fn=_handle_finish_setup,
            inputs=[new_campaign_name_input],
            outputs=[wizard_container, status_message]
        )

    return wizard_container, finish_setup_button, new_campaign_name_input
