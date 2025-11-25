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

    def _tooltip_label(label_text: str, tooltip_text: str) -> str:
        """Create an HTML label with a hoverable tooltip."""
        # Sanitize tooltip text for HTML attribute
        safe_tooltip = tooltip_text.replace('"', '&quot;')
        return f"""
        <div class="setting-with-tooltip" style="margin-bottom: 0.25rem;">
            <label style="font-weight: 500; font-size: 0.875rem; color: #374151; display: flex; align-items: center;">
                {label_text}
                <span class="info-icon" data-tooltip="{safe_tooltip}">ⓘ</span>
            </label>
        </div>
        """

    available_log_levels = log_level_choices or ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    active_console_level = initial_console_level or "INFO"

    # Load current configuration from .env
    current_config = ConfigManager.load_env_config()

    with gr.Tab("Settings & Tools"):
        gr.Markdown(
            """
            # Settings & Tools

            Configure application settings, manage API keys, and control system behavior.
            """
        )

        # ---------------------------------------------------------------------
        # Group 1: AI Services Configuration
        # ---------------------------------------------------------------------
        with gr.Accordion("🔑 AI Services Configuration", open=True):

            # API Key Management
            with gr.Accordion("API Key Management", open=True):
                gr.Markdown(
                    """
                    Enter your API keys for cloud services below. These are stored securely in your `.env` file.
                    """
                )

                with gr.Row():
                    with gr.Column():
                        gr.HTML(_tooltip_label("Groq API Key", "Required for Groq transcription and LLM inference. Get one at console.groq.com."))
                        groq_api_key_input = _a11y(
                            gr.Textbox(
                                label=None,
                                show_label=False,
                                placeholder="gsk_... (leave empty to keep existing)",
                                type="password",
                                interactive=True,
                                elem_id="settings-groq-key",
                            ),
                            label="Groq API key",
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("OpenAI API Key", "Required for OpenAI models (GPT-4, Whisper). Get one at platform.openai.com."))
                        openai_api_key_input = _a11y(
                            gr.Textbox(
                                label=None,
                                show_label=False,
                                placeholder="sk-... (leave empty to keep existing)",
                                type="password",
                                interactive=True,
                                elem_id="settings-openai-key",
                            ),
                            label="OpenAI API key",
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Hugging Face API Key", "Required for PyAnnote speaker diarization. Get one at huggingface.co/settings/tokens."))
                        hugging_face_api_key_input = _a11y(
                            gr.Textbox(
                                label=None,
                                show_label=False,
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
                            "Keys loaded from .env"
                        ),
                        elem_id="settings-api-status",
                    ),
                    label="API key status",
                    role="status",
                    live="polite",
                )

            # Model Configuration
            with gr.Accordion("Model Configuration", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.HTML(_tooltip_label("Whisper Backend", "Engine for speech-to-text. 'local' uses your GPU/CPU, 'groq' uses ultra-fast cloud API."))
                        whisper_backend_dropdown = _a11y(
                            gr.Dropdown(
                                label=None,
                                show_label=False,
                                choices=ConfigManager.VALID_WHISPER_BACKENDS,
                                value=current_config.get("WHISPER_BACKEND", Config.WHISPER_BACKEND),
                                interactive=True,
                                elem_id="settings-whisper-backend",
                            ),
                            label="Whisper backend",
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Whisper Model", "Model size affects speed/accuracy. 'medium' is a good balance. 'large-v3' is best accuracy."))
                        whisper_model_dropdown = _a11y(
                            gr.Dropdown(
                                label=None,
                                show_label=False,
                                choices=ConfigManager.VALID_WHISPER_MODELS,
                                value=current_config.get("WHISPER_MODEL", Config.WHISPER_MODEL),
                                interactive=True,
                                elem_id="settings-whisper-model",
                            ),
                            label="Whisper model",
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Whisper Language", "Primary language of the audio. Setting this improves accuracy."))
                        whisper_language_dropdown = _a11y(
                            gr.Dropdown(
                                label=None,
                                show_label=False,
                                choices=ConfigManager.VALID_WHISPER_LANGUAGES,
                                value=current_config.get("WHISPER_LANGUAGE", Config.WHISPER_LANGUAGE),
                                interactive=True,
                                elem_id="settings-whisper-language",
                            ),
                            label="Whisper language",
                        )

                with gr.Row():
                    with gr.Column():
                        gr.HTML(_tooltip_label("Diarization Backend", "Service to identify speakers. 'pyannote' (local GPU) or 'hf_api' (cloud)."))
                        diarization_backend_dropdown = _a11y(
                            gr.Dropdown(
                                label=None,
                                show_label=False,
                                choices=ConfigManager.VALID_DIARIZATION_BACKENDS,
                                value=current_config.get("DIARIZATION_BACKEND", Config.DIARIZATION_BACKEND),
                                interactive=True,
                                elem_id="settings-diarization-backend",
                            ),
                            label="Diarization backend",
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("LLM Backend", "Backend for narrative generation. 'ollama' (local), 'openai', or 'groq'."))
                        llm_backend_dropdown = _a11y(
                            gr.Dropdown(
                                label=None,
                                show_label=False,
                                choices=ConfigManager.VALID_LLM_BACKENDS,
                                value=current_config.get("LLM_BACKEND", Config.LLM_BACKEND),
                                interactive=True,
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
                            "Settings loaded."
                        ),
                        elem_id="settings-model-status",
                    ),
                    label="Model configuration status",
                    role="status",
                    live="polite",
                )

            # Ollama Settings
            with gr.Accordion("Ollama Settings", open=False):
                with gr.Row():
                    with gr.Column():
                        gr.HTML(_tooltip_label("Ollama Model", "Name of the model to use in Ollama (e.g. llama3, mistral). Must be pulled already."))
                        ollama_model_input = gr.Textbox(
                            label=None,
                            show_label=False,
                            value=current_config.get("OLLAMA_MODEL", Config.OLLAMA_MODEL),
                            interactive=True,
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Ollama Fallback Model", "Model to use if primary fails. Optional."))
                        ollama_fallback_model_input = gr.Textbox(
                            label=None,
                            show_label=False,
                            value=current_config.get("OLLAMA_FALLBACK_MODEL", Config.OLLAMA_FALLBACK_MODEL or ""),
                            interactive=True,
                        )

                gr.HTML(_tooltip_label("Ollama Base URL", "URL where Ollama is running. Default: http://localhost:11434"))
                ollama_base_url_input = gr.Textbox(
                    label=None,
                    show_label=False,
                    value=current_config.get("OLLAMA_BASE_URL", Config.OLLAMA_BASE_URL),
                    interactive=True,
                )

                save_ollama_config_btn = UIComponents.create_action_button(
                    "Save Ollama Settings",
                    variant="primary",
                    size="sm",
                )
                ollama_config_status = gr.Markdown(
                    value=StatusMessages.info(
                        "Ollama Settings",
                        "Settings loaded."
                    )
                )

        # ---------------------------------------------------------------------
        # Group 2: Processing & Performance
        # ---------------------------------------------------------------------
        with gr.Accordion("⚙️ Processing & Performance", open=False):

            # Audio Processing Settings
            with gr.Accordion("Audio Processing Settings", open=True):
                with gr.Row():
                    with gr.Column():
                        gr.HTML(_tooltip_label("Chunk Length (s)", "Duration of audio segments. Longer = more context, more memory."))
                        chunk_length_input = _a11y(
                            gr.Number(
                                label=None,
                                show_label=False,
                                value=ConfigManager.safe_int(
                                    current_config.get("CHUNK_LENGTH_SECONDS", Config.CHUNK_LENGTH_SECONDS),
                                    Config.CHUNK_LENGTH_SECONDS
                                ),
                                minimum=60,
                                maximum=3600,
                                step=60,
                                interactive=True,
                                elem_id="settings-chunk-length",
                            ),
                            label="Chunk length seconds",
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Chunk Overlap (s)", "Overlap between chunks to prevent cut-off words. Recommended: 5-10s."))
                        chunk_overlap_input = _a11y(
                            gr.Number(
                                label=None,
                                show_label=False,
                                value=ConfigManager.safe_int(
                                    current_config.get("CHUNK_OVERLAP_SECONDS", Config.CHUNK_OVERLAP_SECONDS),
                                    Config.CHUNK_OVERLAP_SECONDS
                                ),
                                minimum=0,
                                maximum=60,
                                step=1,
                                interactive=True,
                                elem_id="settings-chunk-overlap",
                            ),
                            label="Chunk overlap seconds",
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Sample Rate (Hz)", "Audio sampling rate. 16000Hz is standard for speech processing."))
                        audio_sample_rate_input = _a11y(
                            gr.Number(
                                label=None,
                                show_label=False,
                                value=ConfigManager.safe_int(
                                    current_config.get("AUDIO_SAMPLE_RATE", Config.AUDIO_SAMPLE_RATE),
                                    Config.AUDIO_SAMPLE_RATE
                                ),
                                minimum=8000,
                                maximum=48000,
                                step=1000,
                                interactive=True,
                                elem_id="settings-audio-sample-rate",
                            ),
                            label="Audio sample rate",
                        )

                with gr.Row():
                    clean_stale_clips_checkbox = _a11y(
                        gr.Checkbox(
                            label="Clean Stale Audio Clips",
                            value=ConfigManager.safe_bool(
                                current_config.get("CLEAN_STALE_CLIPS", str(Config.CLEAN_STALE_CLIPS)),
                                Config.CLEAN_STALE_CLIPS
                            ),
                            interactive=True,
                            elem_id="settings-clean-stale",
                        ),
                        label="Clean stale audio clips",
                    )

                    save_intermediate_outputs_checkbox = _a11y(
                        gr.Checkbox(
                            label="Save Intermediate Outputs",
                            value=ConfigManager.safe_bool(
                                current_config.get("SAVE_INTERMEDIATE_OUTPUTS", str(Config.SAVE_INTERMEDIATE_OUTPUTS)),
                                Config.SAVE_INTERMEDIATE_OUTPUTS
                            ),
                            interactive=True,
                            info="Save JSONs for debugging",
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
                            "Settings loaded."
                        ),
                        elem_id="settings-processing-status",
                    ),
                    label="Processing settings status",
                    role="status",
                    live="polite",
                )

            # Rate Limiting
            with gr.Accordion("Rate Limiting & Colab", open=False):
                gr.Markdown("### Groq Rate Limiting")
                with gr.Row():
                    with gr.Column():
                        gr.HTML(_tooltip_label("Max Calls/Sec", "Maximum API calls per second to Groq."))
                        groq_max_calls_input = gr.Number(
                            label=None, show_label=False,
                            value=ConfigManager.safe_int(
                                current_config.get("GROQ_MAX_CALLS_PER_SECOND", Config.GROQ_MAX_CALLS_PER_SECOND),
                                Config.GROQ_MAX_CALLS_PER_SECOND
                            ),
                            minimum=1, maximum=100, step=1, interactive=True,
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Period (s)", "Time window for rate limiting."))
                        groq_rate_period_input = gr.Number(
                            label=None, show_label=False,
                            value=ConfigManager.safe_float(
                                current_config.get("GROQ_RATE_LIMIT_PERIOD_SECONDS", Config.GROQ_RATE_LIMIT_PERIOD_SECONDS),
                                Config.GROQ_RATE_LIMIT_PERIOD_SECONDS
                            ),
                            minimum=0.1, maximum=10.0, step=0.1, interactive=True,
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Burst", "Allowed burst of calls above the limit."))
                        groq_rate_burst_input = gr.Number(
                            label=None, show_label=False,
                            value=ConfigManager.safe_int(
                                current_config.get("GROQ_RATE_LIMIT_BURST", Config.GROQ_RATE_LIMIT_BURST),
                                Config.GROQ_RATE_LIMIT_BURST
                            ),
                            minimum=1, maximum=100, step=1, interactive=True,
                        )

                gr.Markdown("### Colab Classification Settings")
                with gr.Row():
                    with gr.Column():
                        gr.HTML(_tooltip_label("Poll Interval (s)", "How often to check for Colab results."))
                        colab_poll_interval_input = gr.Number(
                            label=None, show_label=False,
                            value=ConfigManager.safe_int(
                                current_config.get("COLAB_POLL_INTERVAL", Config.COLAB_POLL_INTERVAL),
                                Config.COLAB_POLL_INTERVAL
                            ),
                            minimum=5, maximum=300, step=5, interactive=True,
                        )

                    with gr.Column():
                        gr.HTML(_tooltip_label("Timeout (s)", "Max time to wait for Colab processing."))
                        colab_timeout_input = gr.Number(
                            label=None, show_label=False,
                            value=ConfigManager.safe_int(
                                current_config.get("COLAB_TIMEOUT", Config.COLAB_TIMEOUT),
                                Config.COLAB_TIMEOUT
                            ),
                            minimum=300, maximum=7200, step=300, interactive=True,
                        )

                save_advanced_config_btn = UIComponents.create_action_button(
                    "Save Advanced Settings",
                    variant="primary",
                    size="sm",
                )
                advanced_config_status = gr.Markdown(
                    value=StatusMessages.info(
                        "Advanced Settings",
                        "Settings loaded."
                    )
                )

        # ---------------------------------------------------------------------
        # Group 3: Advanced
        # ---------------------------------------------------------------------
        with gr.Accordion("🛠️ Advanced", open=False):

            # Logging Controls
            with gr.Accordion("Logging Controls", open=False):
                gr.HTML(_tooltip_label("Console Log Level", "Detail level of logs printed to the console."))
                log_level_dropdown = gr.Dropdown(
                    label=None, show_label=False,
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
                        f"Current level: {active_console_level}"
                    )
                )

            # Application Control
            with gr.Accordion("Application Control", open=False):
                gr.Markdown(
                    """
                    **Restart Application**
                    Restart the Gradio server. Terminates active processes.
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
                        "Ready."
                    )
                )

            # Diagnostics
            with gr.Accordion("System Diagnostics", open=False):
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
                            "Click 'Run Health Check' to verify system."
                        ),
                        elem_id="settings-diagnostics-output",
                    ),
                    label="Diagnostics output",
                    role="status",
                    live="polite",
                )

            # Chat Management
            with gr.Accordion("Conversation Management", open=False):
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
                            "Manage chat history here."
                        ),
                        elem_id="settings-chat-output",
                    ),
                    label="Conversation history output",
                    role="status",
                    live="polite",
                )

        # Confirmation Modal
        with gr.Modal(visible=False) as confirmation_modal:
            confirmation_message = gr.Markdown()
            confirmation_checkbox = gr.Checkbox(label="I understand this action cannot be undone.", value=False)
            countdown_display = gr.Markdown()
            with gr.Row():
                cancel_button = gr.Button("Cancel")
                confirm_button = gr.Button("Confirm", variant="stop", interactive=False)
            # Hidden state to store which action triggered the modal
            action_to_confirm = gr.State(value=None)


        # Other tabs (Social, Speakers)
        social_refs = create_social_insights_tab(
            story_manager=story_manager,
            refresh_campaign_names=refresh_campaign_names,
            initial_campaign_id=initial_campaign_id,
        )
        create_speaker_manager_tab(speaker_profile_manager=speaker_profile_manager)

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
        # Confirmation Modal
        "confirmation_modal": confirmation_modal,
        "confirmation_message": confirmation_message,
        "confirmation_checkbox": confirmation_checkbox,
        "countdown_display": countdown_display,
        "cancel_button": cancel_button,
        "confirm_button": confirm_button,
        "action_to_confirm": action_to_confirm,
    }
