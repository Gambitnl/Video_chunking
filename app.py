"""Gradio web UI for D&D Session Processor"""
import gradio as gr
from pathlib import Path
import json
import requests
from src.pipeline import DDSessionProcessor
from src.config import Config
from src.diarizer import SpeakerProfileManager
from src.party_config import PartyConfigManager


def process_session(
    audio_file,
    session_id,
    party_selection,
    character_names,
    player_names,
    num_speakers,
    skip_diarization,
    skip_classification
):
    """
    Process a D&D session through the Gradio interface.

    Returns:
        Tuple of (status_message, full_transcript, ic_transcript, ooc_transcript, stats_json)
    """
    try:
        if audio_file is None:
            return "Error: Please upload an audio file", "", "", "", ""

        # Determine if using party config or manual entry
        if party_selection and party_selection != "Manual Entry":
            # Use party configuration
            processor = DDSessionProcessor(
                session_id=session_id or "session",
                num_speakers=int(num_speakers),
                party_id=party_selection
            )
        else:
            # Parse names manually
            chars = [c.strip() for c in character_names.split(',') if c.strip()]
            players = [p.strip() for p in player_names.split(',') if p.strip()]

            # Create processor
            processor = DDSessionProcessor(
                session_id=session_id or "session",
                character_names=chars,
                player_names=players,
                num_speakers=int(num_speakers)
            )

        # Process
        result = processor.process(
            input_file=Path(audio_file),
            skip_diarization=skip_diarization,
            skip_classification=skip_classification
        )

        # Read output files
        output_files = result['output_files']

        full_text = output_files['full'].read_text(encoding='utf-8')
        ic_text = output_files['ic_only'].read_text(encoding='utf-8')
        ooc_text = output_files['ooc_only'].read_text(encoding='utf-8')
        stats_json = output_files['json'].read_text(encoding='utf-8')

        # Format statistics for display
        stats = result['statistics']
        stats_display = f"""
## Session Statistics

- **Total Duration**: {stats['total_duration_formatted']}
- **IC Duration**: {stats['ic_duration_formatted']} ({stats['ic_percentage']:.1f}%)
- **Total Segments**: {stats['total_segments']}
- **IC Segments**: {stats['ic_segments']}
- **OOC Segments**: {stats['ooc_segments']}

### Character Appearances
"""
        for char, count in sorted(stats.get('character_appearances', {}).items(), key=lambda x: -x[1]):
            stats_display += f"- **{char}**: {count} times\n"

        status = f"✓ Processing complete! Files saved to: {output_files['full'].parent}"

        return status, full_text, ic_text, ooc_text, stats_display

    except Exception as e:
        error_msg = f"✗ Error: {str(e)}"
        import traceback
        traceback.print_exc()
        return error_msg, "", "", "", ""


def map_speaker_ui(session_id, speaker_id, person_name):
    """Map a speaker ID to a person name"""
    try:
        manager = SpeakerProfileManager()
        manager.map_speaker(session_id, speaker_id, person_name)
        return f"✓ Mapped {speaker_id} → {person_name}"
    except Exception as e:
        return f"✗ Error: {str(e)}"


def get_speaker_profiles(session_id):
    """Get speaker profiles for a session"""
    try:
        manager = SpeakerProfileManager()
        if session_id not in manager.profiles:
            return "No speaker profiles found for this session"

        profiles = manager.profiles[session_id]
        result = f"## Speaker Profiles for {session_id}\n\n"
        for speaker_id, person_name in profiles.items():
            result += f"- **{speaker_id}**: {person_name}\n"

        return result
    except Exception as e:
        return f"Error: {str(e)}"

def view_google_doc(doc_url):
    """Downloads a public Google Doc as plain text."""
    try:
        doc_id_start = doc_url.find("/d/") + 3
        doc_id_end = doc_url.find("/edit")
        if doc_id_end == -1:
            doc_id_end = doc_url.find("/view")
        if doc_id_end == -1:
            doc_id_end = len(doc_url)

        doc_id = doc_url[doc_id_start:doc_id_end]
        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"

        response = requests.get(export_url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return f"Error downloading document: {e}"

# Create Gradio interface
with gr.Blocks(title="D&D Session Processor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🎲 D&D Session Transcription & Diarization

    Upload your D&D session recording and get:
    - Full transcript with speaker labels
    - In-character only transcript (game narrative)
    - Out-of-character only transcript (banter & meta-discussion)
    - Detailed statistics and analysis

    **Supported formats**: M4A, MP3, WAV, and more
    """)

    with gr.Tab("Process Session"):
        with gr.Row():
            with gr.Column():
                audio_input = gr.File(
                    label="Upload Audio File",
                    file_types=["audio"]
                )

                session_id_input = gr.Textbox(
                    label="Session ID",
                    placeholder="e.g., session_2024_01_15",
                    info="Unique identifier for this session"
                )

                # Party configuration selector
                party_manager = PartyConfigManager()
                available_parties = ["Manual Entry"] + party_manager.list_parties()

                party_selection_input = gr.Dropdown(
                    choices=available_parties,
                    value="default",
                    label="Party Configuration",
                    info="Select your party or choose 'Manual Entry' to enter names manually"
                )

                character_names_input = gr.Textbox(
                    label="Character Names (comma-separated)",
                    placeholder="e.g., Thorin, Elara, Zyx",
                    info="Names of player characters in the campaign (only used if Manual Entry selected)"
                )

                player_names_input = gr.Textbox(
                    label="Player Names (comma-separated)",
                    placeholder="e.g., Alice, Bob, Charlie, DM",
                    info="Names of actual players (only used if Manual Entry selected)"
                )

                num_speakers_input = gr.Slider(
                    minimum=2,
                    maximum=10,
                    value=4,
                    step=1,
                    label="Number of Speakers",
                    info="Expected number of speakers (helps accuracy)"
                )

                with gr.Row():
                    skip_diarization_input = gr.Checkbox(
                        label="Skip Speaker Diarization",
                        info="Faster, but no speaker labels"
                    )
                    skip_classification_input = gr.Checkbox(
                        label="Skip IC/OOC Classification",
                        info="Faster, but no content separation"
                    )

                process_btn = gr.Button("🚀 Process Session", variant="primary", size="lg")

            with gr.Column():
                status_output = gr.Textbox(
                    label="Status",
                    lines=2,
                    interactive=False
                )

                stats_output = gr.Markdown(
                    label="Statistics"
                )

        with gr.Row():
            with gr.Tab("Full Transcript"):
                full_output = gr.Textbox(
                    label="Full Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True
                )

            with gr.Tab("In-Character Only"):
                ic_output = gr.Textbox(
                    label="In-Character Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True
                )

            with gr.Tab("Out-of-Character Only"):
                ooc_output = gr.Textbox(
                    label="Out-of-Character Transcript",
                    lines=20,
                    max_lines=50,
                    show_copy_button=True
                )

        process_btn.click(
            fn=process_session,
            inputs=[
                audio_input,
                session_id_input,
                party_selection_input,
                character_names_input,
                player_names_input,
                num_speakers_input,
                skip_diarization_input,
                skip_classification_input
            ],
            outputs=[
                status_output,
                full_output,
                ic_output,
                ooc_output,
                stats_output
            ]
        )

    with gr.Tab("Party Management"):
        gr.Markdown("""
        ### Import/Export Party Configurations

        Save your party configurations to share them or keep backups.
        """)

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### Export Party")
                export_party_dropdown = gr.Dropdown(
                    choices=available_parties,
                    label="Select Party to Export",
                    value="default"
                )
                export_btn = gr.Button("Export Party", variant="primary")
                export_output = gr.File(label="Download Party File")
                export_status = gr.Textbox(label="Status", interactive=False)

            with gr.Column():
                gr.Markdown("#### Import Party")
                import_file = gr.File(
                    label="Upload Party JSON File",
                    file_types=[".json"]
                )
                import_party_id = gr.Textbox(
                    label="Party ID (optional)",
                    placeholder="Leave empty to use ID from file"
                )
                import_btn = gr.Button("Import Party", variant="primary")
                import_status = gr.Textbox(label="Status", interactive=False)

        def export_party_ui(party_id):
            try:
                from tempfile import NamedTemporaryFile
                import os

                # Create temp file
                temp_file = NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                temp_path = Path(temp_file.name)
                temp_file.close()

                # Export party
                party_manager.export_party(party_id, temp_path)

                return temp_path, f"✓ Exported '{party_id}'"
            except Exception as e:
                return None, f"✗ Error: {str(e)}"

        def import_party_ui(file_obj, party_id_override):
            try:
                if file_obj is None:
                    return "✗ Please upload a file"

                # Import the party
                imported_id = party_manager.import_party(
                    Path(file_obj.name),
                    party_id_override if party_id_override else None
                )

                return f"✓ Successfully imported party '{imported_id}'. Refresh the page to use it."
            except Exception as e:
                return f"✗ Error: {str(e)}"

        export_btn.click(
            fn=export_party_ui,
            inputs=[export_party_dropdown],
            outputs=[export_output, export_status]
        )

        import_btn.click(
            fn=import_party_ui,
            inputs=[import_file, import_party_id],
            outputs=[import_status]
        )

    with gr.Tab("Character Profiles"):
        gr.Markdown("""
        ### Character Profiles & Overviews

        Track character development, inventory, relationships, and memorable moments across sessions.
        """)

        # Load characters initially
        from src.character_profile import CharacterProfileManager
        char_mgr = CharacterProfileManager()
        initial_chars = char_mgr.list_characters()

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### View Characters")
                char_refresh_btn = gr.Button("Refresh Character List", size="sm")
                char_list_display = gr.Markdown()

                char_select = gr.Dropdown(
                    label="Select Character",
                    choices=initial_chars,
                    value=initial_chars[0] if initial_chars else None,
                    interactive=True
                )
                view_char_btn = gr.Button("View Character Overview", variant="primary")

            with gr.Column():
                gr.Markdown("#### Export/Import")
                export_char_dropdown = gr.Dropdown(
                    label="Character to Export",
                    choices=initial_chars,
                    value=initial_chars[0] if initial_chars else None,
                    interactive=True
                )
                export_char_btn = gr.Button("Export Character")
                export_char_file = gr.File(label="Download Character Profile")
                export_char_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("---")

                import_char_file = gr.File(label="Upload Character JSON", file_types=[".json"])
                import_char_btn = gr.Button("Import Character")
                import_char_status = gr.Textbox(label="Status", interactive=False)

        with gr.Row():
            char_overview_output = gr.Markdown(
                label="Character Overview",
                value="Select a character to view their profile.",
                elem_classes="character-overview-scrollable"
            )

        # Add custom CSS for scrollable character overview
        demo.css = """
        .character-overview-scrollable {
            max-height: 600px;
            overflow-y: auto;
        }
        """

        # Character profile functions
        def load_character_list():
            from src.character_profile import CharacterProfileManager
            manager = CharacterProfileManager()
            characters = manager.list_characters()

            if not characters:
                return "No characters found.", [], []

            # Create markdown table
            table = "| Character | Player | Race/Class | Level | Sessions |\n"
            table += "|-----------|--------|------------|-------|----------|\n"

            for char_name in characters:
                profile = manager.get_profile(char_name)
                table += f"| {profile.name} | {profile.player} | {profile.race} {profile.class_name} | {profile.level} | {profile.total_sessions} |\n"

            return table, characters, characters

        def view_character_profile(character_name):
            if not character_name:
                return "Please select a character."

            from src.character_profile import CharacterProfileManager
            manager = CharacterProfileManager()
            overview = manager.generate_character_overview(character_name, format="markdown")
            return overview

        def export_character_ui(character_name):
            if not character_name:
                return None, "Please select a character"

            try:
                from src.character_profile import CharacterProfileManager
                from tempfile import NamedTemporaryFile

                manager = CharacterProfileManager()
                temp_file = NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
                temp_path = Path(temp_file.name)
                temp_file.close()

                manager.export_profile(character_name, temp_path)
                return temp_path, f"Exported '{character_name}'"
            except Exception as e:
                return None, f"Error: {str(e)}"

        def import_character_ui(file_obj):
            if file_obj is None:
                return "Please upload a file"

            try:
                from src.character_profile import CharacterProfileManager
                manager = CharacterProfileManager()
                imported_name = manager.import_profile(Path(file_obj.name))
                return f"Successfully imported character '{imported_name}'. Click Refresh to see it."
            except Exception as e:
                return f"Error: {str(e)}"

        # Wire up the buttons
        char_refresh_btn.click(
            fn=load_character_list,
            outputs=[char_list_display, char_select, export_char_dropdown]
        )

        view_char_btn.click(
            fn=view_character_profile,
            inputs=[char_select],
            outputs=[char_overview_output]
        )

        export_char_btn.click(
            fn=export_character_ui,
            inputs=[export_char_dropdown],
            outputs=[export_char_file, export_char_status]
        )

        import_char_btn.click(
            fn=import_character_ui,
            inputs=[import_char_file],
            outputs=[import_char_status]
        )

        # Load character list on page load
        demo.load(
            fn=load_character_list,
            outputs=[char_list_display, char_select, export_char_dropdown]
        )

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
                    placeholder="e.g., SPEAKER_00"
                )
                map_person_name = gr.Textbox(
                    label="Person Name",
                    placeholder="e.g., Alice"
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
            outputs=[map_status]
        )

        view_btn.click(
            fn=get_speaker_profiles,
            inputs=[view_session_id],
            outputs=[profiles_output]
        )

    with gr.Tab("Document Viewer"):
        gr.Markdown("""
        ### View a Public Google Doc

        Paste the URL of a publicly shared Google Doc to view its text content here.
        """)
        with gr.Row():
            with gr.Column():
                gdoc_url_input = gr.Textbox(
                    label="Google Doc URL",
                    placeholder="https://docs.google.com/document/d/..."
                )
                gdoc_view_btn = gr.Button("Load Document", variant="primary")
        with gr.Row():
            gdoc_output = gr.Textbox(
                label="Document Content",
                lines=20,
                max_lines=50,
                show_copy_button=True,
                interactive=False
            )

        gdoc_view_btn.click(
            fn=view_google_doc,
            inputs=[gdoc_url_input],
            outputs=[gdoc_output]
        )

    with gr.Tab("Logs"):
        gr.Markdown("""
        ### System Logs

        View application logs, errors, and processing history.
        """)

        with gr.Row():
            with gr.Column():
                refresh_logs_btn = gr.Button("Refresh Logs", size="sm")
                show_errors_only = gr.Checkbox(label="Show Errors/Warnings Only", value=False)
                log_lines = gr.Slider(minimum=10, maximum=500, value=100, step=10,
                                     label="Number of lines to display")

            with gr.Column():
                clear_old_logs_btn = gr.Button("Clear Old Logs (7+ days)", size="sm")
                clear_logs_status = gr.Textbox(label="Status", interactive=False)

        logs_output = gr.Textbox(label="Log Output", lines=20, max_lines=40, show_copy_button=True, interactive=False)

        def refresh_logs_ui(errors_only, num_lines):
            try:
                from src.logger import _logger_instance
                if errors_only:
                    logs = _logger_instance.get_error_logs(lines=int(num_lines))
                else:
                    logs = _logger_instance.get_recent_logs(lines=int(num_lines))
                return logs
            except Exception as e:
                return f"Error loading logs: {str(e)}"

        def clear_old_logs_ui():
            try:
                from src.logger import _logger_instance
                count = _logger_instance.clear_old_logs(days=7)
                return f"Cleared {count} old log file(s)"
            except Exception as e:
                return f"Error clearing logs: {str(e)}"

        refresh_logs_btn.click(
            fn=refresh_logs_ui,
            inputs=[show_errors_only, log_lines],
            outputs=[logs_output]
        )

        clear_old_logs_btn.click(
            fn=clear_old_logs_ui,
            outputs=[clear_logs_status]
        )

        # Load logs on page load
        demo.load(
            fn=lambda: refresh_logs_ui(False, 100),
            outputs=[logs_output]
        )

    with gr.Tab("Configuration"):
        gr.Markdown(f"""
        ### Current Configuration

        - **Whisper Model**: {Config.WHISPER_MODEL}
        - **Whisper Backend**: {Config.WHISPER_BACKEND}
        - **LLM Backend**: {Config.LLM_BACKEND}
        - **Chunk Length**: {Config.CHUNK_LENGTH_SECONDS}s
        - **Chunk Overlap**: {Config.CHUNK_OVERLAP_SECONDS}s
        - **Sample Rate**: {Config.AUDIO_SAMPLE_RATE} Hz
        - **Output Directory**: {Config.OUTPUT_DIR}

        To change settings, edit the `.env` file in the project root.
        """)

    with gr.Tab("Help"):
        gr.Markdown("""
        ## How to Use

        ### First Time Setup

        1. **Install Dependencies**:
           ```bash
           pip install -r requirements.txt
           ```

        2. **Install FFmpeg**:
           - Download from https://ffmpeg.org
           - Add to system PATH

        3. **Setup Ollama** (for IC/OOC classification):
           ```bash
           # Install Ollama from https://ollama.ai
           ollama pull gpt-oss:20b
           ```

        4. **Setup PyAnnote** (for speaker diarization):
           - Visit https://huggingface.co/pyannote/speaker-diarization
           - Accept terms and create token
           - Add `HF_TOKEN=your_token` to `.env` file

        ### Processing a Session

        1. Upload your D&D session recording (M4A, MP3, WAV, etc.)
        2. Enter a unique session ID
        3. List your character and player names (helps with classification)
        4. Adjust number of speakers if needed
        5. Click "Process Session" and wait
        6. View results in different tabs

        ### Expected Processing Time

        - **4-hour session with local models**: ~2-4 hours
        - **4-hour session with Groq API**: ~30-60 minutes
        - Depends on your hardware (GPU helps a lot!)

        ### Tips

        - First processing takes longer (model downloads)
        - GPU significantly speeds up transcription
        - You can skip diarization/classification for faster results
        - Speaker mappings improve with manual correction

        ### Troubleshooting

        - **FFmpeg not found**: Install FFmpeg and add to PATH
        - **Ollama connection failed**: Start Ollama server
        - **PyAnnote error**: Set HF_TOKEN in .env
        - **Out of memory**: Try processing shorter clips first
        """)

if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False
    )
