from __future__ import annotations

import gradio as gr

from src.diarizer import SpeakerProfileManager


def create_speaker_management_tab() -> None:
    def map_speaker_ui(session_id, speaker_id, person_name):
        try:
            manager = SpeakerProfileManager()
            manager.map_speaker(session_id, speaker_id, person_name)
            return f"Mapped {speaker_id} -> {person_name}"
        except Exception as exc:
            return f"Error: {exc}"

    def get_speaker_profiles(session_id):
        try:
            manager = SpeakerProfileManager()
            if session_id not in manager.profiles:
                return "No speaker profiles found for this session"

            profiles = manager.profiles[session_id]
            result = f"## Speaker Profiles for {session_id}\n\n"
            for speaker_id, person_name in profiles.items():
                result += f"- **{speaker_id}**: {person_name}\n"

            return result
        except Exception as exc:
            return f"Error: {exc}"

    with gr.Tab("Speaker Management"):
        gr.Markdown("""
        ### Manage Speaker Profiles

        After processing, you can map speaker IDs (like SPEAKER_00) to actual person names.
        This mapping will be remembered for future sessions.
        """)

        with gr.Row():
            with gr.Column():
                map_session_id = gr.Textbox(label="Session ID")
                map_speaker_id = gr.Textbox(
                    label="Speaker ID",
                    placeholder="e.g., SPEAKER_00",
                )
                map_person_name = gr.Textbox(
                    label="Person Name",
                    placeholder="e.g., Alice",
                )
                map_btn = gr.Button("Map Speaker", variant="primary")
                map_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column():
                view_session_id = gr.Textbox(label="Session ID")
                view_btn = gr.Button("View Speaker Profiles")
                profiles_output = gr.Markdown(label="Profiles")

        map_btn.click(
            fn=map_speaker_ui,
            inputs=[map_session_id, map_speaker_id, map_person_name],
            outputs=[map_status],
        )

        view_btn.click(
            fn=get_speaker_profiles,
            inputs=[view_session_id],
            outputs=[profiles_output],
        )
