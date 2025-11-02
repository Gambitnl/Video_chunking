"""Modern Live Session tab scaffolding for realtime capture."""
from __future__ import annotations

from typing import Dict, Tuple

import gradio as gr

from src.ui.helpers import StatusMessages, UIComponents


def _initial_status() -> str:
    return StatusMessages.info(
        "Live Session",
        "Live capture idle. Click Start Live Capture to begin streaming."
    )


def _initial_speaker_timeline() -> str:
    return "### Speaker Timeline\n\nNo speaker segments yet."


def _initial_audio_meter() -> str:
    return "### Audio Level\n\nNo samples received."


def _start_session(
    state: str,
    transcript_text: str,
    speaker_md: str
) -> Tuple[str, str, str, str, str, Dict[str, object], Dict[str, object]]:
    """Handle Start button interactions."""
    if state == "running":
        return (
            StatusMessages.warning(
                "Live Session",
                "Live capture is already running.",
                "Use Stop Capture before starting a new session."
            ),
            transcript_text,
            speaker_md,
            "### Audio Level\n\nListening...",
            "running",
            gr.update(interactive=False),
            gr.update(interactive=True),
        )

    return (
        StatusMessages.loading("Initializing live audio capture"),
        "",
        "### Speaker Timeline\n\nAwaiting initial diarization segments.",
        "### Audio Level\n\nListening...",
        "running",
        gr.update(interactive=False),
        gr.update(interactive=True),
    )


def _stop_session(
    state: str,
    transcript_text: str,
    speaker_md: str
) -> Tuple[str, str, str, str, str, Dict[str, object], Dict[str, object]]:
    """Handle Stop button interactions."""
    if state != "running":
        return (
            StatusMessages.info(
                "Live Session",
                "Live capture is not currently running."
            ),
            transcript_text,
            speaker_md,
            _initial_audio_meter(),
            "idle",
            gr.update(interactive=False),
            gr.update(interactive=False),
        )

    return (
        StatusMessages.success(
            "Live Session",
            "Capture stopped. Transcript and speaker data preserved below."
        ),
        transcript_text,
        speaker_md,
        _initial_audio_meter(),
        "idle",
        gr.update(interactive=True),
        gr.update(interactive=False),
    )


def create_live_session_tab(blocks: gr.Blocks) -> Dict[str, gr.components.Component]:
    """Create the Live Session tab and return component references for integration."""
    with gr.Tab("Live Session"):
        gr.Markdown(
            """
            # Live Session Monitoring

            Stream audio directly from your table, view realtime transcripts, and monitor speaker activity.
            """
        )

        live_state = gr.State(value="idle")

        with gr.Row():
            start_button = UIComponents.create_action_button(
                "Start Live Capture",
                variant="primary",
                size="md",
            )
            stop_button = UIComponents.create_action_button(
                "Stop Capture",
                variant="stop",
                size="md",
            )

        status_display = UIComponents.create_status_display(_initial_status())

        with gr.Row():
            speaker_timeline = gr.Markdown(value=_initial_speaker_timeline())
            audio_meter = gr.Markdown(value=_initial_audio_meter())

        transcript_stream = gr.Textbox(
            label="Transcript Stream",
            value="",
            placeholder="Realtime transcript output will appear here when capture is active.",
            lines=12,
            interactive=False,
        )

        start_button.click(
            _start_session,
            inputs=[live_state, transcript_stream, speaker_timeline],
            outputs=[
                status_display,
                transcript_stream,
                speaker_timeline,
                audio_meter,
                live_state,
                start_button,
                stop_button,
            ],
        )

        stop_button.click(
            _stop_session,
            inputs=[live_state, transcript_stream, speaker_timeline],
            outputs=[
                status_display,
                transcript_stream,
                speaker_timeline,
                audio_meter,
                live_state,
                start_button,
                stop_button,
            ],
        )

    return {
        "start_button": start_button,
        "stop_button": stop_button,
        "status": status_display,
        "transcript_stream": transcript_stream,
        "speaker_timeline": speaker_timeline,
        "audio_meter": audio_meter,
        "state": live_state,
    }
