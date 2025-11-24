"""
Setup Wizard UI for first-time users.
"""
import gradio as gr
from typing import Tuple, Optional, Dict, Any
import logging

from src.ui.helpers import StatusMessages, UIComponents
from src.ui.api_key_manager import save_api_keys
from src.ui.config_manager import ConfigManager
from src.party_config import CampaignManager
from src.config import Config

logger = logging.getLogger(__name__)

# Stepper CSS styles are in theme.py, utilizing .stepper, .step, etc.

class SetupWizard:
    """
    Manages the First-Time Setup Wizard UI (Phase 2).
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
        # Load initial config to pre-populate
        current_config = ConfigManager.load_env_config()

        with gr.Column(visible=False, elem_id="setup-wizard") as wizard_container:
            # Header
            gr.Markdown("# \u2728 Welcome to D&D Session Processor")
            gr.Markdown("Let's get your environment set up in 3 easy steps.")

            # Stepper UI
            step_tracker = gr.State(value=1)

            # We use HTML to render the stepper. The CSS classes used here
            # (.stepper, .step, .step.active, .step.completed) must be present in theme.py
            stepper_html = gr.HTML(self._generate_stepper_html(1))

            # --- STEP 1: AI Backend ---
            with gr.Column(visible=True) as step1_container:
                gr.Markdown("### 1. Choose Your AI Backend")
                gr.Markdown("Select the primary service you want to use. You can change this later.")

                backend_choice = gr.Radio(
                    choices=["OpenAI (Recommended)", "Groq (Fast)", "Ollama (Local)", "Custom / Mixed"],
                    value="OpenAI (Recommended)",
                    label="Primary Backend"
                )

                # API Key Inputs
                with gr.Group():
                    openai_key = gr.Textbox(
                        label="OpenAI API Key",
                        type="password",
                        placeholder="sk-...",
                        value=current_config.get("OPENAI_API_KEY", ""),
                        visible=True
                    )
                    groq_key = gr.Textbox(
                        label="Groq API Key",
                        type="password",
                        placeholder="gsk_...",
                        value=current_config.get("GROQ_API_KEY", ""),
                        visible=False
                    )
                    hf_key = gr.Textbox(
                        label="Hugging Face Token (Optional, for PyAnnote)",
                        type="password",
                        placeholder="hf_...",
                        value=current_config.get("HUGGING_FACE_API_KEY", ""),
                        info="Required only if you use HuggingFace-based diarization."
                    )
                    ollama_url = gr.Textbox(
                        label="Ollama URL",
                        value=current_config.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                        visible=False
                    )

                step1_status = gr.Markdown("")

                with gr.Row():
                    # Empty column to push button to right
                    gr.Column(scale=1)
                    step1_next_btn = gr.Button("Next: Configure Models \u2192", variant="primary", scale=0)

            # --- STEP 2: Model Configuration ---
            with gr.Column(visible=False) as step2_container:
                gr.Markdown("### 2. Configure Models")
                gr.Markdown("We've selected defaults based on your backend choice. Review and adjust if needed.")

                with gr.Group():
                    with gr.Row():
                        whisper_backend = gr.Dropdown(
                            choices=ConfigManager.VALID_WHISPER_BACKENDS,
                            value=current_config.get("WHISPER_BACKEND", "openai"),
                            label="Whisper Backend (Transcription)"
                        )
                        whisper_model = gr.Dropdown(
                            choices=ConfigManager.VALID_WHISPER_MODELS,
                            value=current_config.get("WHISPER_MODEL", "large-v3"),
                            label="Whisper Model"
                        )

                    with gr.Row():
                        llm_backend = gr.Dropdown(
                            choices=ConfigManager.VALID_LLM_BACKENDS,
                            value=current_config.get("LLM_BACKEND", "openai"),
                            label="LLM Backend (Analysis)"
                        )
                        diarization_backend = gr.Dropdown(
                            choices=ConfigManager.VALID_DIARIZATION_BACKENDS,
                            value=current_config.get("DIARIZATION_BACKEND", "local"),
                            label="Diarization Backend"
                        )

                step2_status = gr.Markdown("")

                with gr.Row():
                    step2_back_btn = gr.Button("\u2190 Back", variant="secondary", scale=0)
                    gr.Column(scale=1)
                    step2_next_btn = gr.Button("Next: Finalize \u2192", variant="primary", scale=0)

            # --- STEP 3: Finalize ---
            with gr.Column(visible=False) as step3_container:
                gr.Markdown("### 3. Create Campaign & Finish")

                # Connectivity Test
                with gr.Group():
                    gr.Markdown("**Pre-flight Check**")
                    test_status = gr.Markdown("Click 'Test Connection' to verify your settings.")
                    test_btn = gr.Button("Test Connection", size="sm")

                gr.Markdown("---")

                # Campaign Creation
                gr.Markdown("**First Campaign**")
                campaign_name = gr.Textbox(
                    label="Campaign Name",
                    placeholder="e.g., The Curse of Strahd",
                    info="A campaign organizes your sessions and characters."
                )

                creation_status = gr.Markdown("")

                with gr.Row():
                    step3_back_btn = gr.Button("\u2190 Back", variant="secondary", scale=0)
                    gr.Column(scale=1)
                    # This is the "Finish" button app.py expects
                    create_btn = UIComponents.create_action_button("Create Campaign & Start", variant="primary")

        # --- Event Wiring ---

        # Step 1: Backend Choice Logic
        def _update_visibility(choice):
            return (
                gr.update(visible=(choice == "OpenAI (Recommended)" or choice == "Custom / Mixed")),
                gr.update(visible=(choice == "Groq (Fast)" or choice == "Custom / Mixed")),
                gr.update(visible=(choice == "Ollama (Local)" or choice == "Custom / Mixed"))
            )

        backend_choice.change(
            fn=_update_visibility,
            inputs=[backend_choice],
            outputs=[openai_key, groq_key, ollama_url]
        )

        # Step 1 -> Step 2
        step1_next_btn.click(
            fn=self._save_step1_and_advance,
            inputs=[backend_choice, openai_key, groq_key, hf_key, ollama_url],
            outputs=[step1_status, step_tracker, stepper_html, step1_container, step2_container, whisper_backend, llm_backend, diarization_backend]
        )

        # Step 2 -> Step 3
        step2_next_btn.click(
            fn=self._save_step2_and_advance,
            inputs=[whisper_backend, whisper_model, llm_backend, diarization_backend],
            outputs=[step2_status, step_tracker, stepper_html, step2_container, step3_container]
        )

        # Back Buttons
        step2_back_btn.click(
            fn=lambda: (1, self._generate_stepper_html(1), gr.update(visible=True), gr.update(visible=False)),
            outputs=[step_tracker, stepper_html, step1_container, step2_container]
        )

        step3_back_btn.click(
            fn=lambda: (2, self._generate_stepper_html(2), gr.update(visible=True), gr.update(visible=False)),
            outputs=[step_tracker, stepper_html, step2_container, step3_container]
        )

        # Test Connection
        test_btn.click(
            fn=self._test_connection,
            outputs=[test_status]
        )

        # Finish
        create_btn.click(
            fn=self._complete_setup,
            inputs=[campaign_name],
            outputs=[creation_status, wizard_container]
        )

        return wizard_container, create_btn, campaign_name

    def _generate_stepper_html(self, current_step: int) -> str:
        """Generates HTML for the progress stepper."""
        steps = ["Backend", "Models", "Finalize"]
        html = '<div class="stepper">'

        for i, label in enumerate(steps, 1):
            active_class = "active" if i == current_step else ""
            completed_class = "completed" if i < current_step else ""

            # Connector
            if i > 1:
                # We add a visual connector, maybe CSS handles it or we add a div
                pass

            html += f"""
            <div class="step {active_class} {completed_class}">
                <div class="step-connector"></div>
                <div class="step-number">{i if i >= current_step else "✓"}</div>
                <div class="step-label">{label}</div>
            </div>
            """
        html += '</div>'
        return html

    def _save_step1_and_advance(self, backend_choice, openai, groq, hf, ollama_url):
        # 1. Save API Keys
        try:
            keys_to_save = {}
            if openai: keys_to_save["OPENAI_API_KEY"] = openai
            if groq: keys_to_save["GROQ_API_KEY"] = groq
            if hf: keys_to_save["HUGGING_FACE_API_KEY"] = hf

            if keys_to_save:
                save_api_keys(**{k.lower(): v for k, v in keys_to_save.items()})

            # 2. Save Ollama URL if changed
            if ollama_url:
                ConfigManager.save_config({"OLLAMA_BASE_URL": ollama_url})

            # 3. Determine defaults for next step
            whisper_def = "openai"
            llm_def = "openai"
            diarization_def = "local" # Default unless HF key present?

            if backend_choice == "Groq (Fast)":
                whisper_def = "groq"
                llm_def = "groq"
            elif backend_choice == "Ollama (Local)":
                whisper_def = "local"
                llm_def = "ollama"

            # If HF key is provided, suggest huggingface diarization?
            # Or stick to local as safer default.

            return (
                gr.update(visible=False), # Clear status
                2, # Step 2
                self._generate_stepper_html(2),
                gr.update(visible=False), # Hide Step 1
                gr.update(visible=True),  # Show Step 2
                gr.update(value=whisper_def),
                gr.update(value=llm_def),
                gr.update(value=diarization_def)
            )

        except Exception as e:
            return (
                StatusMessages.error("Error", str(e)),
                1,
                self._generate_stepper_html(1),
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(), gr.update(), gr.update()
            )

    def _save_step2_and_advance(self, whisper, whisper_model, llm, diarization):
        try:
            # Save Config
            ConfigManager.save_config({
                "WHISPER_BACKEND": whisper,
                "WHISPER_MODEL": whisper_model,
                "LLM_BACKEND": llm,
                "DIARIZATION_BACKEND": diarization
            })

            return (
                gr.update(visible=False),
                3,
                self._generate_stepper_html(3),
                gr.update(visible=False),
                gr.update(visible=True)
            )
        except Exception as e:
             return (
                StatusMessages.error("Error", str(e)),
                2,
                self._generate_stepper_html(2),
                gr.update(visible=True),
                gr.update(visible=False)
            )

    def _test_connection(self):
        # Basic check: Do we have keys for the selected backends?
        config = ConfigManager.load_env_config()
        llm = config.get("LLM_BACKEND", "openai")

        missing = []
        if llm == "openai" and not config.get("OPENAI_API_KEY"):
            missing.append("OpenAI API Key")
        if llm == "groq" and not config.get("GROQ_API_KEY"):
            missing.append("Groq API Key")

        if missing:
            return StatusMessages.error("Missing Keys", f"Please provide: {', '.join(missing)}")

        return StatusMessages.success("Ready", "Configuration looks good! Ready to create campaign.")

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
