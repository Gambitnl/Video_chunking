
"""
Setup Wizard UI for first-time users.
"""
import gradio as gr
from typing import Tuple, Optional

from src.ui.helpers import StatusMessages, UIComponents
from src.ui.api_key_manager import save_api_keys
from src.party_config import CampaignManager

class SetupWizard:
    """
    Manages the First-Time Setup Wizard UI.
    """

    def __init__(self, campaign_manager: CampaignManager, on_complete_callback):
        self.campaign_manager = campaign_manager
        self.on_complete = on_complete_callback

    def create_ui(self) -> Tuple[gr.Column, gr.Button, gr.Textbox]:
        """
        Creates the wizard UI components.

        Returns:
            Tuple of (wizard_container, complete_button, campaign_name_input)
        """
        with gr.Column(visible=False, elem_id="setup-wizard") as wizard_container:
            gr.Markdown("# \u2728 Welcome to D&D Session Processor")
            gr.Markdown("It looks like this is your first time here. Let's get you set up in a few steps.")

            with gr.Group():
                gr.Markdown("### 1. API Configuration (Optional)")
                gr.Markdown("Configure API keys for cloud services. You can skip this if you plan to use local models only.")

                with gr.Row():
                    openai_key = gr.Textbox(label="OpenAI API Key", type="password", placeholder="sk-...")
                    groq_key = gr.Textbox(label="Groq API Key", type="password", placeholder="gsk_...")
                    hf_key = gr.Textbox(label="Hugging Face Token", type="password", placeholder="hf_...")

                save_keys_btn = gr.Button("Save API Keys", size="sm")
                keys_status = gr.Markdown("")

                save_keys_btn.click(
                    fn=self._save_keys,
                    inputs=[openai_key, groq_key, hf_key],
                    outputs=keys_status
                )

            gr.Markdown("---")

            with gr.Group():
                gr.Markdown("### 2. Create Your First Campaign (Required)")
                gr.Markdown("A campaign holds all your sessions, characters, and lore.")

                campaign_name = gr.Textbox(
                    label="Campaign Name",
                    placeholder="e.g., The Curse of Strahd",
                    info="You can change this later."
                )

                create_btn = UIComponents.create_action_button("Create Campaign & Finish Setup", variant="primary")
                creation_status = gr.Markdown("")

        # Event wiring
        # We trigger the creation method, then hide the wizard.
        # The external caller will wire the "on complete" logic to show the main dashboard
        create_btn.click(
            fn=self._complete_setup,
            inputs=[campaign_name],
            outputs=[creation_status, wizard_container]
        )

        # Return the components needed for external wiring
        return wizard_container, create_btn, campaign_name

    def _save_keys(self, openai, groq, hf):
        try:
            save_api_keys({
                "OPENAI_API_KEY": openai,
                "GROQ_API_KEY": groq,
                "HUGGING_FACE_API_KEY": hf
            })
            return StatusMessages.success("Saved", "API keys stored successfully.")
        except Exception as e:
            return StatusMessages.error("Error", str(e))

    def _complete_setup(self, name):
        if not name.strip():
            return StatusMessages.error("Required", "Please enter a campaign name."), gr.update(visible=True)

        try:
            # Create campaign
            cid, _ = self.campaign_manager.create_blank_campaign(name.strip())
            return StatusMessages.success("Success", f"Campaign '{name}' created!"), gr.update(visible=False)
        except Exception as e:
            return StatusMessages.error("Error", str(e)), gr.update(visible=True)

def create_setup_wizard(campaign_manager, on_complete):
    """Factory function."""
    wizard = SetupWizard(campaign_manager, on_complete)
    return wizard.create_ui()
