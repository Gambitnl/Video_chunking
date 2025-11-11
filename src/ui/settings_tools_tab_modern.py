"""Modern Settings & Tools tab - diagnostics and chat helpers."""
from typing import Dict, Optional, List

import gradio as gr

from src.ui.helpers import StatusMessages, UIComponents
from src.ui.social_insights_tab import create_social_insights_tab
from src.ui.speaker_manager_tab import create_speaker_manager_tab

def create_settings_tools_tab_modern(
    blocks: gr.Blocks,
    story_manager,
    refresh_campaign_names,
    speaker_profile_manager,
    *,
    initial_campaign_id: Optional[str] = None,
    log_level_choices: Optional[List[str]] = None,
    initial_console_level: str = "INFO",
) -> Dict[str, gr.components.Component]:
    """Create the Settings & Tools tab and return components requiring campaign updates."""

    available_log_levels = log_level_choices or ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    active_console_level = initial_console_level or "INFO"

    with gr.Tab("Settings & Tools"):
        gr.Markdown(
            """
            # Settings & Tools

            Inspect diagnostics, review recent logs, and test LLM connectivity.
            """
        )

        diagnostics_md = gr.Markdown(
            value=StatusMessages.info(
                "Diagnostics",
                "Run a session for the active campaign to see status tracker updates here."
            )
        )

        chat_md = gr.Markdown(
            value=StatusMessages.info(
                "LLM Chat",
                "Load a campaign to initialise chat context for that campaign."
            )
        )

        social_refs = create_social_insights_tab(
            story_manager=story_manager,
            refresh_campaign_names=refresh_campaign_names,
            initial_campaign_id=initial_campaign_id,
        )
        create_speaker_manager_tab(speaker_profile_manager=speaker_profile_manager)

        with gr.Accordion("API Key Management", open=False):
            gr.Markdown(
                """
                Enter your API keys for cloud services below. These are stored locally in your `.env` file.
                """
            )

            groq_api_key_input = gr.Textbox(
                label="Groq API Key",
                placeholder="gsk_...",
                type="password",
                interactive=True,
            )
            hugging_face_api_key_input = gr.Textbox(
                label="Hugging Face API Key",
                placeholder="hf_...",
                type="password",
                interactive=True,
            )
            save_api_keys_btn = UIComponents.create_action_button(
                "Save API Keys",
                variant="primary",
                size="sm",
            )
            api_keys_status = gr.Markdown(
                value=StatusMessages.info(
                    "API Keys",
                    "API keys will be loaded from your `.env` file if it exists."
                )
            )

        with gr.Accordion("Logging Controls", open=False):
            log_level_dropdown = gr.Dropdown(
                label="Console Log Level",
                choices=available_log_levels,
                value=active_console_level,
                interactive=True,
            )
            apply_log_level_btn = UIComponents.create_action_button(
                "Apply Log Level",
                variant="secondary",
                size="sm",
            )
            log_level_status = gr.Markdown(
                value=StatusMessages.info(
                    "Logging",
                    f"Console output currently uses {active_console_level} level."
                )
            )

    return {
        "diagnostics": diagnostics_md,
        "chat": chat_md,
        "social_campaign_selector": social_refs["campaign_selector"],
        "social_session_dropdown": social_refs["session_dropdown"],
        "social_keyword_output": social_refs["keyword_output"],
        "social_nebula_output": social_refs["nebula_output"],
        "groq_api_key_input": groq_api_key_input,
        "hugging_face_api_key_input": hugging_face_api_key_input,
        "save_api_keys_btn": save_api_keys_btn,
        "api_keys_status": api_keys_status,
        "log_level_dropdown": log_level_dropdown,
        "apply_log_level_btn": apply_log_level_btn,
        "log_level_status": log_level_status,
    }
