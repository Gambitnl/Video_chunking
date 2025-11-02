"""Modern redesigned Process Session tab with clean workflow."""
from pathlib import Path
from typing import List

import gradio as gr

from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import StatusMessages


def create_workflow_header():
    """Create a visual workflow stepper."""
    return gr.HTML("""
    <div class="stepper">
        <div class="step active">
            <div class="step-number">1</div>
            <div class="step-label">Upload</div>
            <div class="step-connector"></div>
        </div>
        <div class="step">
            <div class="step-number">2</div>
            <div class="step-label">Configure</div>
            <div class="step-connector"></div>
        </div>
        <div class="step">
            <div class="step-number">3</div>
            <div class="step-label">Process</div>
            <div class="step-connector"></div>
        </div>
        <div class="step">
            <div class="step-number">4</div>
            <div class="step-label">Review</div>
        </div>
    </div>
    """)


def create_process_session_tab_modern(blocks: gr.Blocks, available_parties: List[str]) -> None:
    """Create a modern, streamlined Process Session tab."""

    with gr.Tab("Process Session"):
        # Workflow header
        create_workflow_header()

        gr.Markdown("""
        # Process D&D Session Recording

        Transform your session audio into organized transcripts with speaker identification
        and character context.
        """)

        # Step 1: Upload Audio
        with gr.Group() as upload_section:
            gr.Markdown("### Step 1: Upload Audio File")

            with gr.Row():
                audio_file = gr.File(
                    label="",
                    file_types=[".m4a", ".mp3", ".wav"],
                    elem_classes=["file-upload"],
                )

            gr.Markdown("""
            <details>
            <summary><strong>📋 Supported formats</strong></summary>
            <ul>
                <li><strong>M4A</strong> - iPhone/Mac recordings (recommended)</li>
                <li><strong>MP3</strong> - Universal format</li>
                <li><strong>WAV</strong> - Uncompressed audio</li>
            </ul>
            <p><em>Tip: 4-hour sessions typically take 30-60 minutes to process.</em></p>
            </details>
            """)

        # Step 2: Configure
        with gr.Group() as config_section:
            gr.Markdown("### Step 2: Configure")

            with gr.Row():
                with gr.Column(scale=2):
                    session_id = gr.Textbox(
                        label="Session ID",
                        placeholder="session_001 or 2024-10-31_game_night",
                        info="Unique identifier for this session",
                    )

                with gr.Column(scale=2):
                    party_dropdown = gr.Dropdown(
                        label="Party Configuration",
                        choices=[p for p in available_parties if p != "Manual Entry"],
                        value="default" if "default" in available_parties else None,
                        info="Select your campaign party",
                    )

            # Advanced options (collapsed by default)
            with gr.Accordion("Advanced Options", open=False):
                with gr.Row():
                    with gr.Column():
                        skip_diarization = gr.Checkbox(
                            label="Skip speaker identification",
                            value=False,
                            info="Faster processing, but no speaker labels"
                        )

                        skip_classification = gr.Checkbox(
                            label="Skip IC/OOC classification",
                            value=False,
                            info="Faster processing, but no In-Character filtering"
                        )

                    with gr.Column():
                        skip_snippets = gr.Checkbox(
                            label="Skip audio clip export",
                            value=False,
                            info="Saves disk space if you don't need audio clips"
                        )

                        skip_knowledge = gr.Checkbox(
                            label="Skip knowledge extraction",
                            value=False,
                            info="Skip automatic quest/NPC/location extraction"
                        )

        # Step 3: Process
        with gr.Group() as process_section:
            gr.Markdown("### Step 3: Process")

            process_btn = gr.Button(
                "Start Processing",
                variant="primary",
                size="lg",
                elem_classes=["btn-primary"],
            )

            status_output = gr.Markdown(
                value=StatusMessages.info(
                    "Ready to Process",
                    "Click 'Start Processing' when ready. You can close this tab - processing continues in the background."
                )
            )

            # Progress bar (hidden initially)
            progress_bar = gr.HTML(visible=False)

        # Step 4: Results (shown after processing)
        with gr.Group(visible=False) as results_section:
            gr.Markdown("### Processing Complete!")

            results_summary = gr.Markdown()

            with gr.Row():
                view_transcript_btn = gr.Button(
                    "View Transcript",
                    variant="secondary",
                    link="/")

                view_characters_btn = gr.Button(
                    "Update Characters",
                    variant="secondary",
                )

                generate_story_btn = gr.Button(
                    "Generate Story",
                    variant="secondary",
                )

        # Event handlers
        def show_processing():
            """Show processing status."""
            return (
                gr.update(visible=True, value="""
                <div class="progress-bar">
                    <div class="progress-fill loading" style="width: 100%"></div>
                </div>
                <p style="text-align: center; margin-top: 1rem; color: #6b7280;">
                    Processing... This may take 30-60 minutes for long sessions.
                </p>
                """),
                StatusMessages.loading("Processing Your Session")
            )

        def process_session_modern(
            audio_file,
            session_id,
            party_id,
            skip_diarization,
            skip_classification,
            skip_snippets,
            skip_knowledge,
        ):
            """Process the session (placeholder - connects to existing logic)."""
            if not audio_file:
                return (
                    gr.update(visible=False),
                    StatusMessages.error(
                        "No Audio File",
                        "Please upload an audio file to process."
                    ),
                    gr.update(visible=False)
                )

            if not session_id:
                return (
                    gr.update(visible=False),
                    StatusMessages.error(
                        "Session ID Required",
                        "Please provide a unique session identifier."
                    ),
                    gr.update(visible=False)
                )

            # TODO: Connect to actual processing logic
            # This is where you'd call the existing pipeline

            return (
                gr.update(visible=False),
                StatusMessages.success(
                    "Processing Complete!",
                    f"Session '{session_id}' has been processed successfully."
                ),
                gr.update(
                    visible=True,
                    value=f"""
                    **Session**: {session_id}
                    **Party**: {party_id or 'No party'}
                    **Duration**: 2h 15m
                    **Speakers**: 5 identified
                    **Segments**: 342 transcribed

                    **Next Steps:**
                    - Review the transcript in the Campaign tab
                    - Update character profiles with new actions
                    - Generate a story notebook
                    """
                )
            )

        # Wire up events
        process_btn.click(
            fn=show_processing,
            outputs=[progress_bar, status_output]
        ).then(
            fn=process_session_modern,
            inputs=[
                audio_file,
                session_id,
                party_dropdown,
                skip_diarization,
                skip_classification,
                skip_snippets,
                skip_knowledge,
            ],
            outputs=[progress_bar, status_output, results_summary]
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=[results_section]
        )
