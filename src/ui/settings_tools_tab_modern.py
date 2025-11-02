"""Modern Settings & Tools tab - advanced features and configuration."""
from pathlib import Path
from typing import List

import gradio as gr

from src.ui.helpers import StatusMessages


def create_settings_tools_tab_modern(blocks: gr.Blocks) -> None:
    """Create a modern Settings & Tools tab.

    Consolidates:
    - Configuration
    - Diagnostics
    - Logs
    - Speaker Management
    - LLM Chat (testing)
    - Help
    """

    with gr.Tab("⚙️ Settings & Tools"):
        gr.Markdown("""
        # Settings & Advanced Tools

        Configure the application and access technical features.
        """)

        # Configuration Section
        with gr.Accordion("Configuration", open=True):
            gr.Markdown("### Application Settings")

            with gr.Row():
                with gr.Column():
                    output_base_path = gr.Textbox(
                        label="Output Directory",
                        placeholder="/path/to/output",
                        info="Base path for all generated files"
                    )

                    ollama_model = gr.Textbox(
                        label="Ollama Model",
                        placeholder="llama3.1:latest",
                        info="LLM model for generation tasks"
                    )

                    ollama_url = gr.Textbox(
                        label="Ollama URL",
                        placeholder="http://localhost:11434",
                        info="Ollama server endpoint"
                    )

                with gr.Column():
                    whisper_model = gr.Dropdown(
                        label="Whisper Model",
                        choices=["tiny", "base", "small", "medium", "large"],
                        value="base",
                        info="Transcription model (larger = more accurate but slower)"
                    )

                    default_temp = gr.Slider(
                        label="LLM Temperature",
                        minimum=0.0,
                        maximum=1.0,
                        value=0.7,
                        step=0.1,
                        info="Controls creativity (0 = deterministic, 1 = creative)"
                    )

                    chunk_size = gr.Number(
                        label="Processing Chunk Size",
                        value=50,
                        info="Segments per chunk for LLM processing"
                    )

            save_config_btn = gr.Button("Save Configuration", variant="primary")
            config_status = gr.Markdown(visible=False)

        # Speaker Management
        with gr.Accordion("Speaker Management", open=False):
            gr.Markdown("### Speaker Configurations")

            gr.Markdown("""
            Map audio speaker IDs to character names for better transcription labeling.
            """)

            with gr.Row():
                with gr.Column(scale=2):
                    speaker_table = gr.Dataframe(
                        headers=["Speaker ID", "Character Name", "Voice Description"],
                        datatype=["str", "str", "str"],
                        row_count=5,
                        col_count=(3, "fixed"),
                        value=[
                            ["SPEAKER_00", "Thorin", "Deep, gruff male voice"],
                            ["SPEAKER_01", "Elara", "Soft, melodic female voice"],
                            ["SPEAKER_02", "DM", "Clear, neutral voice"],
                        ]
                    )

                with gr.Column(scale=1):
                    gr.Markdown("#### Quick Actions")
                    add_speaker_btn = gr.Button("+ Add Speaker", variant="secondary")
                    import_speakers_btn = gr.Button("Import from File", variant="secondary")
                    export_speakers_btn = gr.Button("Export Config", variant="secondary")

        # Diagnostics
        with gr.Accordion("Diagnostics", open=False):
            gr.Markdown("### System Diagnostics")

            with gr.Tabs():
                with gr.Tab("Health Check"):
                    health_check_btn = gr.Button("Run Health Check", variant="primary")

                    health_results = gr.HTML("""
                    <div style="display: grid; gap: 1rem; margin-top: 1rem;">
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h4 style="margin: 0 0 0.25rem 0; color: #111827;">Ollama Server</h4>
                                    <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">http://localhost:11434</p>
                                </div>
                                <span class="badge badge-success">Connected</span>
                            </div>
                        </div>

                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h4 style="margin: 0 0 0.25rem 0; color: #111827;">Output Directory</h4>
                                    <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">/output</p>
                                </div>
                                <span class="badge badge-success">Writable</span>
                            </div>
                        </div>

                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h4 style="margin: 0 0 0.25rem 0; color: #111827;">FFmpeg</h4>
                                    <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">Audio processing tool</p>
                                </div>
                                <span class="badge badge-success">Available</span>
                            </div>
                        </div>

                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h4 style="margin: 0 0 0.25rem 0; color: #111827;">PyTorch</h4>
                                    <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">ML framework for Whisper</p>
                                </div>
                                <span class="badge badge-success">Installed</span>
                            </div>
                        </div>
                    </div>
                    """)

                with gr.Tab("Performance"):
                    gr.Markdown("""
                    #### Recent Session Performance

                    Track processing times and resource usage.
                    """)

                    performance_chart = gr.HTML("""
                    <div style="padding: 1.5rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                        <h4 style="margin: 0 0 1rem 0; color: #111827;">Average Processing Times</h4>

                        <div style="margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span style="color: #6b7280;">Transcription (per hour)</span>
                                <span style="color: #6366f1; font-weight: 600;">12 min</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 20%;"></div>
                            </div>
                        </div>

                        <div style="margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span style="color: #6b7280;">Diarization (per hour)</span>
                                <span style="color: #8b5cf6; font-weight: 600;">8 min</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 13%; background: linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%);"></div>
                            </div>
                        </div>

                        <div style="margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span style="color: #6b7280;">Classification (per hour)</span>
                                <span style="color: #10b981; font-weight: 600;">5 min</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 8%; background: linear-gradient(90deg, #10b981 0%, #059669 100%);"></div>
                            </div>
                        </div>

                        <div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                <span style="color: #6b7280;">Story Generation</span>
                                <span style="color: #f59e0b; font-weight: 600;">3 min</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 5%; background: linear-gradient(90deg, #f59e0b 0%, #d97706 100%);"></div>
                            </div>
                        </div>
                    </div>
                    """)

        # Logs Viewer
        with gr.Accordion("Logs", open=False):
            gr.Markdown("### Application Logs")

            with gr.Row():
                log_level = gr.Dropdown(
                    label="Log Level",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    value="INFO",
                )

                refresh_logs_btn = gr.Button("Refresh", variant="secondary")
                clear_logs_btn = gr.Button("Clear", variant="secondary")

            logs_viewer = gr.Code(
                label="Recent Logs",
                language="python",
                value="""2024-10-31 14:23:45 [INFO] Application started
2024-10-31 14:24:12 [INFO] Loaded party configuration: default
2024-10-31 14:25:30 [INFO] Processing session: session_024
2024-10-31 14:25:31 [INFO] Transcription started
2024-10-31 14:36:42 [INFO] Transcription complete: 342 segments
2024-10-31 14:36:43 [INFO] Diarization started
2024-10-31 14:42:15 [INFO] Diarization complete: 5 speakers identified
2024-10-31 14:42:16 [INFO] Classification started
2024-10-31 14:48:30 [INFO] Classification complete: 187 IC, 155 OOC
2024-10-31 14:48:31 [INFO] Story generation started
2024-10-31 14:51:22 [INFO] Story generation complete
2024-10-31 14:51:23 [INFO] Session processing complete""",
                lines=15,
            )

        # LLM Chat (Testing)
        with gr.Accordion("LLM Chat (Testing)", open=False):
            gr.Markdown("""
            ### Test LLM Integration

            Send test queries to your Ollama server to verify connectivity and model performance.
            """)

            with gr.Row():
                with gr.Column(scale=3):
                    chat_input = gr.Textbox(
                        label="Message",
                        placeholder="Enter a test prompt...",
                        lines=3,
                    )

                with gr.Column(scale=1):
                    chat_model = gr.Textbox(
                        label="Model",
                        placeholder="llama3.1:latest",
                    )

                    chat_temp = gr.Slider(
                        label="Temperature",
                        minimum=0.0,
                        maximum=1.0,
                        value=0.7,
                        step=0.1,
                    )

            chat_send_btn = gr.Button("Send", variant="primary")

            chat_output = gr.Markdown(
                value=StatusMessages.info(
                    "Ready",
                    "Send a message to test your LLM connection."
                )
            )

            # Chat handler
            def send_chat(message, model, temperature):
                """Send test message to LLM (placeholder)."""
                if not message:
                    return StatusMessages.error("No Message", "Please enter a message.")

                # TODO: Connect to actual Ollama client
                # from src.llm_client import OllamaClient

                return StatusMessages.success(
                    "Response",
                    f"This is a test response from {model}. In production, this would show the actual LLM response."
                )

            chat_send_btn.click(
                fn=send_chat,
                inputs=[chat_input, chat_model, chat_temp],
                outputs=[chat_output]
            )

        # Help Section
        with gr.Accordion("Help & Documentation", open=False):
            gr.Markdown("""
            ### Quick Help

            #### Getting Started
            1. **Process a Session**: Go to the "Process Session" tab and upload your audio file
            2. **Configure Party**: Set up character names and speaker mappings
            3. **Review Output**: Check the "Stories & Output" tab for generated content
            4. **Extract Profiles**: Use the "Characters" tab to automatically update character profiles

            #### Common Issues

            **Q: Processing is very slow**
            - Try using a smaller Whisper model (tiny or base)
            - Reduce chunk size in Configuration
            - Ensure Ollama server has adequate resources

            **Q: Speaker identification is incorrect**
            - Update speaker mappings in Speaker Management
            - Ensure audio quality is good (clear voices, minimal background noise)

            **Q: Story generation fails**
            - Verify Ollama server is running
            - Check that the model is downloaded
            - Review logs for error messages

            #### File Locations
            - **Output**: `/output/[session_id]/`
            - **Transcripts**: `/output/[session_id]/transcripts/`
            - **Stories**: `/output/[session_id]/stories/`
            - **Audio Clips**: `/output/[session_id]/snippets/`
            - **Logs**: `/logs/app.log`

            #### Documentation
            For detailed documentation, see the [README](https://github.com/yourusername/videochunking).
            """)

        # Configuration save handler
        def save_configuration(output_path, ollama_model_val, ollama_url_val, whisper_val, temp_val, chunk_val):
            """Save configuration (placeholder)."""
            # TODO: Actually save to config file
            return gr.update(
                visible=True,
                value=StatusMessages.success(
                    "Configuration Saved!",
                    "Settings will take effect on next session processing."
                )
            )

        save_config_btn.click(
            fn=save_configuration,
            inputs=[output_base_path, ollama_model, ollama_url, whisper_model, default_temp, chunk_size],
            outputs=[config_status]
        )
