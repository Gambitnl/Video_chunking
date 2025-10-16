"""Gradio web UI for D&D Session Processor"""
import gradio as gr
from pathlib import Path
import json
import requests
import socket
import sys
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
    skip_classification,
    skip_snippets
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
            skip_classification=skip_classification,
            skip_snippets=skip_snippets
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

        status = f"Processing complete! Files saved to: {output_files['full'].parent}"
        segments_info = result.get('audio_segments', {})
        manifest_path = segments_info.get('manifest') if segments_info else None
        if manifest_path:
            status += f"\nSegment manifest: {manifest_path}"

        return status, full_text, ic_text, ooc_text, stats_display

    except Exception as e:
        error_msg = f"Error: {e}"
        import traceback
        traceback.print_exc()
        return error_msg, "", "", "", ""


def map_speaker_ui(session_id, speaker_id, person_name):
    """Map a speaker ID to a person name"""
    try:
        manager = SpeakerProfileManager()
        manager.map_speaker(session_id, speaker_id, person_name)
        return f"Mapped {speaker_id} -> {person_name}"
    except Exception as e:
        return f"Error: {e}"


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
                batch_mode = gr.Checkbox(
                    label="🔄 Batch Mode - Process Multiple Sessions",
                    value=False,
                    info="Upload multiple audio files to process them sequentially"
                )

                audio_input = gr.File(
                    label="Upload Audio File(s)",
                    file_types=["audio"],
                    file_count="multiple"
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
                    skip_snippets_input = gr.Checkbox(
                        label="Skip Audio Snippets",
                        info="Skip per-segment audio export"
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
                skip_classification_input,
                skip_snippets_input
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
                return f"Error: {e}"

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
                char_table = gr.Dataframe(
                    headers=["Character", "Player", "Race/Class", "Level", "Sessions"],
                    datatype=["str", "str", "str", "number", "number"],
                    label="Characters",
                    interactive=False,
                    wrap=True
                )

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

        # Automatic extraction section
        with gr.Row():
            gr.Markdown("### 🤖 Automatic Profile Extraction")

        with gr.Row():
            with gr.Column():
                gr.Markdown("""
                **Extract character data from session transcripts automatically!**

                Upload an IC-only transcript and select the party - the AI will:
                - Extract notable actions
                - Find items acquired
                - Identify relationships
                - Capture memorable quotes
                - Note character development
                """)

            with gr.Column():
                extract_transcript_file = gr.File(
                    label="IC-Only Transcript (TXT)",
                    file_types=[".txt"]
                )
                extract_party_dropdown = gr.Dropdown(
                    choices=available_parties,
                    label="Party Configuration",
                    value="default"
                )
                extract_session_id = gr.Textbox(
                    label="Session ID",
                    placeholder="e.g., Session 1"
                )
                extract_btn = gr.Button("🚀 Extract Character Data", variant="primary")
                extract_status = gr.Textbox(label="Extraction Status", lines=5, interactive=False)

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
                return [], [], []

            # Create data for Dataframe
            table_data = []
            for char_name in characters:
                profile = manager.get_profile(char_name)
                table_data.append([
                    profile.name,
                    profile.player,
                    f"{profile.race} {profile.class_name}",
                    profile.level,
                    profile.total_sessions
                ])

            return table_data, characters, characters

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

        def extract_profiles_ui(transcript_file, party_id, session_id):
            """Extract character profiles from IC transcript using LLM"""
            if transcript_file is None:
                return "❌ Please upload an IC-only transcript file"

            if not party_id or party_id == "Manual Entry":
                return "❌ Please select a party configuration (not Manual Entry)"

            if not session_id:
                return "❌ Please enter a session ID"

            try:
                from src.profile_extractor import CharacterProfileExtractor
                from src.character_profile import CharacterProfileManager
                from src.party_config import PartyConfigManager

                # Initialize managers
                extractor = CharacterProfileExtractor()
                profile_mgr = CharacterProfileManager()
                party_mgr = PartyConfigManager()

                # Extract and update profiles
                status = f"🔄 Extracting character data from transcript...\n"
                status += f"Party: {party_id}\n"
                status += f"Session: {session_id}\n\n"

                results = extractor.batch_extract_and_update(
                    transcript_path=Path(transcript_file.name),
                    party_id=party_id,
                    session_id=session_id,
                    profile_manager=profile_mgr,
                    party_manager=party_mgr
                )

                status += f"✅ Extraction complete!\n\n"
                status += f"Updated {len(results)} character profile(s):\n"

                for char_name, extracted_data in results.items():
                    status += f"\n**{char_name}**:\n"
                    status += f"  - Actions: {len(extracted_data.notable_actions)}\n"
                    status += f"  - Items: {len(extracted_data.items_acquired)}\n"
                    status += f"  - Relationships: {len(extracted_data.relationships_mentioned)}\n"
                    status += f"  - Quotes: {len(extracted_data.memorable_quotes)}\n"
                    status += f"  - Developments: {len(extracted_data.character_development)}\n"

                status += "\n✅ Click 'Refresh Character List' to see updates!"

                return status

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                return f"❌ Extraction failed:\n{str(e)}\n\nDetails:\n{error_details}"

        # Handler for clicking on table rows
        def on_table_select(evt: gr.SelectData):
            """When a row is clicked, select that character"""
            if evt.index[0] >= 0:  # evt.index is (row, col)
                from src.character_profile import CharacterProfileManager
                manager = CharacterProfileManager()
                characters = manager.list_characters()
                if evt.index[0] < len(characters):
                    selected_char = characters[evt.index[0]]
                    return selected_char
            return None

        # Wire up the buttons
        char_refresh_btn.click(
            fn=load_character_list,
            outputs=[char_table, char_select, export_char_dropdown]
        )

        # When table row is clicked, update dropdown
        char_table.select(
            fn=on_table_select,
            outputs=[char_select]
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

        extract_btn.click(
            fn=extract_profiles_ui,
            inputs=[extract_transcript_file, extract_party_dropdown, extract_session_id],
            outputs=[extract_status]
        )

        # Load character list on page load
        demo.load(
            fn=load_character_list,
            outputs=[char_table, char_select, export_char_dropdown]
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

    with gr.Tab("Social Insights"):
        gr.Markdown("""
        ### OOC Keyword Analysis (Topic Nebula)

        Analyze the out-of-character banter to find the most common topics and keywords.
        """)
        with gr.Row():
            with gr.Column():
                insight_session_id = gr.Textbox(
                    label="Session ID",
                    placeholder="Enter the ID of a completed session"
                )
                insight_btn = gr.Button("☁️ Analyze Banter", variant="primary")
            with gr.Column():
                keyword_output = gr.Markdown(label="Top Keywords")
        with gr.Row():
            nebula_output = gr.Image(label="Topic Nebula")

        def analyze_ooc_ui(session_id):
            try:
                from src.analyzer import OOCAnalyzer
                from src.config import Config
                from wordcloud import WordCloud
                import matplotlib.pyplot as plt

                if not session_id:
                    return "Please enter a session ID.", None

                # Sanitize session_id for file path
                from src.formatter import sanitize_filename
                sanitized_session_id = sanitize_filename(session_id)

                ooc_file = Config.OUTPUT_DIR / f"{sanitized_session_id}_ooc_only.txt"
                if not ooc_file.exists():
                    return f"OOC transcript not found for session: {session_id}", None

                # Analyze
                analyzer = OOCAnalyzer(ooc_file)
                keywords = analyzer.get_keywords(top_n=30)

                if not keywords:
                    return "No significant keywords found in the OOC transcript.", None

                # Generate Word Cloud (Topic Nebula)
                wc = WordCloud(
                    width=800, 
                    height=400, 
                    background_color="#0C111F", # Deep Space Blue
                    colormap="cool", # A good starting point, can be customized
                    max_words=100,
                    contour_width=3,
                    contour_color='#89DDF5' # Cyan Dwarf
                )
                wc.generate_from_frequencies(dict(keywords))

                # Save to a temporary file
                temp_path = Config.TEMP_DIR / f"{sanitized_session_id}_nebula.png"
                wc.to_file(str(temp_path))

                # Format keyword list for display
                keyword_md = "### Top Keywords\n\n| Rank | Keyword | Frequency |\n|---|---|---|"
                for i, (word, count) in enumerate(keywords, 1):
                    keyword_md += f"| {i} | {word} | {count} |\n"

                return keyword_md, temp_path

            except Exception as e:
                return f"Error during analysis: {e}", None

        insight_btn.click(
            fn=analyze_ooc_ui,
            inputs=[insight_session_id],
            outputs=[keyword_output, nebula_output]
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

def is_port_in_use(port):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True

if __name__ == "__main__":
    # Check if port is already in use
    if is_port_in_use(7860):
        print("=" * 80)
        print("⚠️  ERROR: Gradio app already running on port 7860!")
        print("=" * 80)
        print("\nAnother instance of the application is already running.")
        print("Please close the existing instance before starting a new one.")
        print("\nTo kill existing instances:")
        print("  1. Check running processes: netstat -ano | findstr :7860")
        print("  2. Kill the process: taskkill /PID <process_id> /F")
        print("=" * 80)
        sys.exit(1)

    print("Starting Gradio web UI on http://127.0.0.1:7860")
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False
    )
