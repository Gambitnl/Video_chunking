
from __future__ import annotations

import gradio as gr
from src.ui.helpers import UIComponents
from src.diarizer import SpeakerProfileManager

def create_speaker_manager_tab(speaker_profile_manager: SpeakerProfileManager) -> None:
    with gr.Tab("Speaker Manager"):
        gr.Markdown("## Speaker Manager")
        gr.Markdown("Assign names to speaker IDs for each session.")

        with gr.Row():
            session_id_input = gr.Textbox(label="Session ID", placeholder="Enter Session ID")
            load_speakers_btn = gr.Button("Load Speakers")

        speaker_mapping_ui = gr.Dataframe(
            headers=["Speaker ID", "Name"],
            datatype=["str", "str"],
            label="Speaker Mapping",
            interactive=True,
        )

        save_mappings_btn = gr.Button("Save Mappings")

        def load_speakers(session_id: str):
            if not session_id:
                return []
            profiles = speaker_profile_manager._load_profiles()
            session_profiles = profiles.get(session_id, {})
            return [[speaker_id, data.get("name", "")] for speaker_id, data in session_profiles.items()]

        def save_mappings(session_id: str, mappings: list[list[str]]):
            if not session_id:
                return
            for speaker_id, name in mappings:
                speaker_profile_manager.map_speaker(session_id, speaker_id, name)
            gr.Info("Speaker mappings saved!")

        load_speakers_btn.click(
            fn=load_speakers,
            inputs=[session_id_input],
            outputs=[speaker_mapping_ui],
        )

        save_mappings_btn.click(
            fn=save_mappings,
            inputs=[session_id_input, speaker_mapping_ui],
            outputs=[],
        )
