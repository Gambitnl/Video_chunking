"""Modern Settings & Tools tab - diagnostics and chat helpers."""
from typing import Dict, Optional, List

import gradio as gr

from src.config import Config
from src.ui.helpers import AccessibilityAttributes, StatusMessages, UIComponents
from src.ui.social_insights_tab import create_social_insights_tab
from src.ui.speaker_manager_tab import create_speaker_manager_tab
from src.ui.config_manager import ConfigManager

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

    def _a11y(component: gr.components.Component, *, label: str, described_by: str | None = None, role: str | None = None, live: str | None = None, elem_id: str | None = None):
        return AccessibilityAttributes.apply(
            component,
            label=label,
            described_by=described_by,
            role=role,
            live=live,
            elem_id=elem_id,
        )

    available_log_levels = log_level_choices or ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    active_console_level = initial_console_level or "INFO"

    # Load current configuration from .env
    current_config = ConfigManager.load_env_config()

    with gr.Tab("Settings & Tools"):
        gr.Markdown(
            """
            # Settings & Tools

            Configure application settings, manage API keys, and control system behavior.
            Changes are saved to your `.env` file and may require an application restart to take effect.
            """
        )

        # Diagnostics Section - Interactive Health Check
        with gr.Accordion("System Diagnostics", open=False):
            gr.Markdown(
                """
                Check system dependencies, model availability, and API connectivity.
                """
            )
            run_health_check_btn = UIComponents.create_action_button(
                "Run Health Check",
                variant="primary",
                size="sm",
                accessible_label="Run health check",
                elem_id="settings-health-check",
            )
            export_diagnostics_btn = UIComponents.create_action_button(
                "Export Diagnostics",
                variant="secondary",
                size="sm",
                accessible_label="Export diagnostics",
                elem_id="settings-export-diagnostics",
            )
            diagnostics_output = _a11y(
                gr.Markdown(
                    value=StatusMessages.info(
                        "Diagnostics",
                        "Click 'Run Health Check' to verify system dependencies and configuration."
                    ),
                    elem_id="settings-diagnostics-output",
                ),
                label="Diagnostics output",
                role="status",
                live="polite",
            )

        # Chat Management Section - Conversation History
        with gr.Accordion("Conversation Management", open=False):
            gr.Markdown(
                """
                Manage campaign chat conversation history. View and delete saved conversations.
                """
            )
            with gr.Row():
                list_conversations_btn = UIComponents.create_action_button(
                    "List Conversations",
                    variant="secondary",
                    size="sm",
                    accessible_label="List conversations",
                    elem_id="settings-list-conversations",
                )
                clear_all_conversations_btn = UIComponents.create_action_button(
                    "Clear All Conversations",
                    variant="stop",
                    size="sm",
                    accessible_label="Clear all conversations",
                    elem_id="settings-clear-conversations",
                )
            chat_output = _a11y(
                gr.Markdown(
                    value=StatusMessages.info(
                        "Conversation History",
                        "Click 'List Conversations' to see saved campaign chat conversations."
                    ),
                    elem_id="settings-chat-output",
                ),
                label="Conversation history output",
                role="status",
                live="polite",
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
                Enter your API keys for cloud services below. These are stored securely in your `.env` file.
                Leave fields empty to keep existing values.
                """
            )

            groq_api_key_input = _a11y(
                gr.Textbox(
                    label="Groq API Key",
                    placeholder="gsk_... (leave empty to keep existing)",
                    type="password",
                    interactive=True,
                    elem_id="settings-groq-key",
                ),
                label="Groq API key",
            )
            openai_api_key_input = _a11y(
                gr.Textbox(
                    label="OpenAI API Key",
                    placeholder="sk-... (leave empty to keep existing)",
                    type="password",
                    interactive=True,
                    elem_id="settings-openai-key",
                ),
                label="OpenAI API key",
            )
            hugging_face_api_key_input = _a11y(
                gr.Textbox(
                    label="Hugging Face API Key",
                    placeholder="hf_... (leave empty to keep existing)",
                    type="password",
                    interactive=True,
                    elem_id="settings-hf-key",
                ),
                label="Hugging Face API key",
            )
            save_api_keys_btn = UIComponents.create_action_button(
                "Save API Keys",
                variant="primary",
                size="sm",
                accessible_label="Save API keys",
                aria_describedby="settings-api-status",
                elem_id="settings-save-api",
            )
            api_keys_status = _a11y(
                gr.Markdown(
                    value=StatusMessages.info(
                        "API Keys",
                        "API keys will be loaded from your `.env` file if it exists."
                    ),
                    elem_id="settings-api-status",
                ),
                label="API key status",
                role="status",
                live="polite",
            )

        with gr.Accordion("Model Configuration", open=False):
            gr.Markdown(
                """
                Configure which models and backends to use for transcription, diarization, and LLM processing.
                """
            )

            with gr.Row():
                whisper_backend_dropdown = _a11y(
                    gr.Dropdown(
                        label="Whisper Backend",
                        choices=ConfigManager.VALID_WHISPER_BACKENDS,
                        value=current_config.get("WHISPER_BACKEND", Config.WHISPER_BACKEND),
                        interactive=True,
                        info="Choose transcription backend: local (Faster Whisper), groq, or openai",
                        elem_id="settings-whisper-backend",
                    ),
                    label="Whisper backend",
                )
                whisper_model_dropdown = _a11y(
                    gr.Dropdown(
                        label="Whisper Model",
                        choices=ConfigManager.VALID_WHISPER_MODELS,
                        value=current_config.get("WHISPER_MODEL", Config.WHISPER_MODEL),
                        interactive=True,
                        info="Model size affects speed and accuracy",
                        elem_id="settings-whisper-model",
                    ),
                    label="Whisper model",
                )
                whisper_language_dropdown = _a11y(
                    gr.Dropdown(
                        label="Whisper Language",
                        choices=ConfigManager.VALID_WHISPER_LANGUAGES,
                        value=current_config.get("WHISPER_LANGUAGE", Config.WHISPER_LANGUAGE),
                        interactive=True,
                        info="Primary language for transcription",
                        elem_id="settings-whisper-language",
                    ),
                    label="Whisper language",
                )

            with gr.Row():
                diarization_backend_dropdown = _a11y(
                    gr.Dropdown(
                        label="Diarization Backend",
                        choices=ConfigManager.VALID_DIARIZATION_BACKENDS,
                        value=current_config.get("DIARIZATION_BACKEND", Config.DIARIZATION_BACKEND),
                        interactive=True,
                        info="Speaker diarization backend",
                        elem_id="settings-diarization-backend",
                    ),
                    label="Diarization backend",
                )
                llm_backend_dropdown = _a11y(
                    gr.Dropdown(
                        label="LLM Backend",
                        choices=ConfigManager.VALID_LLM_BACKENDS,
                        value=current_config.get("LLM_BACKEND", Config.LLM_BACKEND),
                        interactive=True,
                        info="Backend for narrative generation and classification",
                        elem_id="settings-llm-backend",
                    ),
                    label="LLM backend",
                )

            save_model_config_btn = UIComponents.create_action_button(
                "Save Model Configuration",
                variant="primary",
                size="sm",
                accessible_label="Save model configuration",
                aria_describedby="settings-model-status",
                elem_id="settings-save-model",
            )
            model_config_status = _a11y(
                gr.Markdown(
                    value=StatusMessages.info(
                        "Model Configuration",
                        "Current settings loaded from your configuration."
                    ),
                    elem_id="settings-model-status",
                ),
                label="Model configuration status",
                role="status",
                live="polite",
            )

        with gr.Accordion("Processing Settings", open=False):
            gr.Markdown(
                """
                Configure audio processing parameters like chunk size, sample rate, and cleanup behavior.
                """
            )

            with gr.Row():
                chunk_length_input = _a11y(
                    gr.Number(
                        label="Chunk Length (seconds)",
                        value=ConfigManager.safe_int(
                            current_config.get("CHUNK_LENGTH_SECONDS", Config.CHUNK_LENGTH_SECONDS),
                            Config.CHUNK_LENGTH_SECONDS
                        ),
                        minimum=60,
                        maximum=3600,
                        step=60,
                        interactive=True,
                        info="Duration of each audio chunk for processing",
                        elem_id="settings-chunk-length",
                    ),
                    label="Chunk length seconds",
                )
                chunk_overlap_input = _a11y(
                    gr.Number(
                        label="Chunk Overlap (seconds)",
                        value=ConfigManager.safe_int(
                            current_config.get("CHUNK_OVERLAP_SECONDS", Config.CHUNK_OVERLAP_SECONDS),
                            Config.CHUNK_OVERLAP_SECONDS
                        ),
                        minimum=0,
                        maximum=60,
                        step=1,
                        interactive=True,
                        info="Overlap between chunks to avoid cutting words",
                        elem_id="settings-chunk-overlap",
                    ),
                    label="Chunk overlap seconds",
                )
                audio_sample_rate_input = _a11y(
                    gr.Number(
                        label="Audio Sample Rate (Hz)",
                        value=ConfigManager.safe_int(
                            current_config.get("AUDIO_SAMPLE_RATE", Config.AUDIO_SAMPLE_RATE),
                            Config.AUDIO_SAMPLE_RATE
                        ),
                        minimum=8000,
                        maximum=48000,
                        step=1000,
                        interactive=True,
                        info="Sample rate for audio processing",
                        elem_id="settings-audio-sample-rate",
                    ),
                    label="Audio sample rate",
                )

            clean_stale_clips_checkbox = _a11y(
                gr.Checkbox(
                    label="Clean Stale Audio Clips",
                    value=ConfigManager.safe_bool(
                        current_config.get("CLEAN_STALE_CLIPS", str(Config.CLEAN_STALE_CLIPS)),
                        Config.CLEAN_STALE_CLIPS
                    ),
                    interactive=True,
                    info="Automatically remove old temporary audio files",
                    elem_id="settings-clean-stale",
                ),
                label="Clean stale audio clips",
            )

            save_intermediate_outputs_checkbox = _a11y(
                gr.Checkbox(
                    label="Save Intermediate Stage Outputs",
                    value=ConfigManager.safe_bool(
                        current_config.get("SAVE_INTERMEDIATE_OUTPUTS", str(Config.SAVE_INTERMEDIATE_OUTPUTS)),
                        Config.SAVE_INTERMEDIATE_OUTPUTS
                    ),
                    interactive=True,
                    info="Save intermediate outputs (transcript, diarization, classification) to JSON files",
                    elem_id="settings-save-intermediate",
                ),
                label="Save intermediate stage outputs",
            )

            save_processing_config_btn = UIComponents.create_action_button(
                "Save Processing Settings",
                variant="primary",
                size="sm",
                accessible_label="Save processing settings",
                aria_describedby="settings-processing-status",
                elem_id="settings-save-processing",
            )
            processing_config_status = _a11y(
                gr.Markdown(
                    value=StatusMessages.info(
                        "Processing Settings",
                        "Current settings loaded from your configuration."
                    ),
                    elem_id="settings-processing-status",
                ),
                label="Processing settings status",
                role="status",
                live="polite",
            )

        with gr.Accordion("Ollama Settings", open=False):
            gr.Markdown(
                """
                Configure Ollama model and connection settings for local LLM inference.
                """
            )

            with gr.Row():
                ollama_model_input = gr.Textbox(
                    label="Ollama Model",
                    value=current_config.get("OLLAMA_MODEL", Config.OLLAMA_MODEL),
                    interactive=True,
                    info="Model name for Ollama (e.g., qwen2.5:7b, llama3.2:3b)"
                )
                ollama_fallback_model_input = gr.Textbox(
                    label="Ollama Fallback Model (Optional)",
                    value=current_config.get("OLLAMA_FALLBACK_MODEL", Config.OLLAMA_FALLBACK_MODEL or ""),
                    interactive=True,
                    info="Fallback model if primary fails (leave empty for none)"
                )

            ollama_base_url_input = gr.Textbox(
                label="Ollama Base URL",
                value=current_config.get("OLLAMA_BASE_URL", Config.OLLAMA_BASE_URL),
                interactive=True,
                info="Base URL for Ollama API"
            )

            save_ollama_config_btn = UIComponents.create_action_button(
                "Save Ollama Settings",
                variant="primary",
                size="sm",
            )
            ollama_config_status = gr.Markdown(
                value=StatusMessages.info(
                    "Ollama Settings",
                    "Current settings loaded from your configuration."
                )
            )

        with gr.Accordion("Rate Limiting & Colab Settings", open=False):
            gr.Markdown(
                """
                Configure rate limiting for API calls and Colab integration settings.
                """
            )

            gr.Markdown("### Groq Rate Limiting")
            with gr.Row():
                groq_max_calls_input = gr.Number(
                    label="Max Calls Per Second",
                    value=ConfigManager.safe_int(
                        current_config.get("GROQ_MAX_CALLS_PER_SECOND", Config.GROQ_MAX_CALLS_PER_SECOND),
                        Config.GROQ_MAX_CALLS_PER_SECOND
                    ),
                    minimum=1,
                    maximum=100,
                    step=1,
                    interactive=True,
                )
                groq_rate_period_input = gr.Number(
                    label="Rate Limit Period (seconds)",
                    value=ConfigManager.safe_float(
                        current_config.get("GROQ_RATE_LIMIT_PERIOD_SECONDS", Config.GROQ_RATE_LIMIT_PERIOD_SECONDS),
                        Config.GROQ_RATE_LIMIT_PERIOD_SECONDS
                    ),
                    minimum=0.1,
                    maximum=10.0,
                    step=0.1,
                    interactive=True,
                )
                groq_rate_burst_input = gr.Number(
                    label="Rate Limit Burst",
                    value=ConfigManager.safe_int(
                        current_config.get("GROQ_RATE_LIMIT_BURST", Config.GROQ_RATE_LIMIT_BURST),
                        Config.GROQ_RATE_LIMIT_BURST
                    ),
                    minimum=1,
                    maximum=100,
                    step=1,
                    interactive=True,
                )

            gr.Markdown("### Colab Classification Settings")
            with gr.Row():
                colab_poll_interval_input = gr.Number(
                    label="Poll Interval (seconds)",
                    value=ConfigManager.safe_int(
                        current_config.get("COLAB_POLL_INTERVAL", Config.COLAB_POLL_INTERVAL),
                        Config.COLAB_POLL_INTERVAL
                    ),
                    minimum=5,
                    maximum=300,
                    step=5,
                    interactive=True,
                    info="How often to check for classification results"
                )
                colab_timeout_input = gr.Number(
                    label="Timeout (seconds)",
                    value=ConfigManager.safe_int(
                        current_config.get("COLAB_TIMEOUT", Config.COLAB_TIMEOUT),
                        Config.COLAB_TIMEOUT
                    ),
                    minimum=300,
                    maximum=7200,
                    step=300,
                    interactive=True,
                    info="Maximum time to wait for classification"
                )

            save_advanced_config_btn = UIComponents.create_action_button(
                "Save Advanced Settings",
                variant="primary",
                size="sm",
            )
            advanced_config_status = gr.Markdown(
                value=StatusMessages.info(
                    "Advanced Settings",
                    "Current settings loaded from your configuration."
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

        with gr.Accordion("Application Control", open=False):
            gr.Markdown(
                """
                **Restart Application**

                Use this to restart the Gradio app without manually stopping and restarting the server.
                Useful after configuration changes or to clear any stuck processes.

                ⚠️ **Warning:** Any active processing sessions will be terminated.
                """
            )
            restart_app_btn = UIComponents.create_action_button(
                "🔄 Restart Application",
                variant="secondary",
                size="md",
                accessible_label="Restart application",
                elem_id="settings-restart-app",
            )
            restart_status = gr.Markdown(
                value=StatusMessages.info(
                    "Application Status",
                    "Click the button above to restart the application. "
                    "The app will close and reopen automatically in ~2 seconds."
                )
            )

    all_settings_components = [
        run_health_check_btn,
        export_diagnostics_btn,
        diagnostics_output,
        list_conversations_btn,
        clear_all_conversations_btn,
        chat_output,
        groq_api_key_input,
        openai_api_key_input,
        hugging_face_api_key_input,
        save_api_keys_btn,
        api_keys_status,
        whisper_backend_dropdown,
        whisper_model_dropdown,
        whisper_language_dropdown,
        diarization_backend_dropdown,
        llm_backend_dropdown,
        save_model_config_btn,
        model_config_status,
        chunk_length_input,
        chunk_overlap_input,
        audio_sample_rate_input,
        clean_stale_clips_checkbox,
        save_intermediate_outputs_checkbox,
        save_processing_config_btn,
        processing_config_status,
        ollama_model_input,
        ollama_fallback_model_input,
        ollama_base_url_input,
        save_ollama_config_btn,
        ollama_config_status,
        groq_max_calls_input,
        groq_rate_period_input,
        groq_rate_burst_input,
        colab_poll_interval_input,
        colab_timeout_input,
        save_advanced_config_btn,
        advanced_config_status,
        log_level_dropdown,
        apply_log_level_btn,
        log_level_status,
        restart_app_btn,
        restart_status,
    ]

    for component in all_settings_components:
        if isinstance(component, gr.components.Component):
            AccessibilityAttributes.apply(
                component,
                label=getattr(component, "accessible_label", None)
                or getattr(component, "label", None)
                or getattr(component, "elem_id", "settings component"),
            )

    return {
        # Diagnostics controls
        "run_health_check_btn": run_health_check_btn,
        "export_diagnostics_btn": export_diagnostics_btn,
        "diagnostics_output": diagnostics_output,
        # Chat/Conversation controls
        "list_conversations_btn": list_conversations_btn,
        "clear_all_conversations_btn": clear_all_conversations_btn,
        "chat_output": chat_output,
        # Social Insights
        "social_campaign_selector": social_refs["campaign_selector"],
        "social_session_dropdown": social_refs["session_dropdown"],
        "social_keyword_output": social_refs["keyword_output"],
        "social_nebula_output": social_refs["nebula_output"],
        # API Keys
        "groq_api_key_input": groq_api_key_input,
        "openai_api_key_input": openai_api_key_input,
        "hugging_face_api_key_input": hugging_face_api_key_input,
        "save_api_keys_btn": save_api_keys_btn,
        "api_keys_status": api_keys_status,
        # Model Configuration
        "whisper_backend_dropdown": whisper_backend_dropdown,
        "whisper_model_dropdown": whisper_model_dropdown,
        "whisper_language_dropdown": whisper_language_dropdown,
        "diarization_backend_dropdown": diarization_backend_dropdown,
        "llm_backend_dropdown": llm_backend_dropdown,
        "save_model_config_btn": save_model_config_btn,
        "model_config_status": model_config_status,
        # Processing Settings
        "chunk_length_input": chunk_length_input,
        "chunk_overlap_input": chunk_overlap_input,
        "audio_sample_rate_input": audio_sample_rate_input,
        "clean_stale_clips_checkbox": clean_stale_clips_checkbox,
        "save_intermediate_outputs_checkbox": save_intermediate_outputs_checkbox,
        "save_processing_config_btn": save_processing_config_btn,
        "processing_config_status": processing_config_status,
        # Ollama Settings
        "ollama_model_input": ollama_model_input,
        "ollama_fallback_model_input": ollama_fallback_model_input,
        "ollama_base_url_input": ollama_base_url_input,
        "save_ollama_config_btn": save_ollama_config_btn,
        "ollama_config_status": ollama_config_status,
        # Advanced Settings
        "groq_max_calls_input": groq_max_calls_input,
        "groq_rate_period_input": groq_rate_period_input,
        "groq_rate_burst_input": groq_rate_burst_input,
        "colab_poll_interval_input": colab_poll_interval_input,
        "colab_timeout_input": colab_timeout_input,
        "save_advanced_config_btn": save_advanced_config_btn,
        "advanced_config_status": advanced_config_status,
        # Logging and Control
        "log_level_dropdown": log_level_dropdown,
        "apply_log_level_btn": apply_log_level_btn,
        "log_level_status": log_level_status,
        "restart_app_btn": restart_app_btn,
        "restart_status": restart_status,
    }
