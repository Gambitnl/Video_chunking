from __future__ import annotations

from pathlib import Path
from typing import List

import gradio as gr

from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import StatusMessages, UIComponents, Placeholders, InfoText


def create_character_profiles_tab(blocks: gr.Blocks, available_parties: List[str]) -> None:
    from src.character_profile import CharacterProfileManager

    with gr.Tab("Character Profiles"):
        gr.Markdown("""
        ### Character Profiles & Overviews

        This tab is your central hub for managing detailed character profiles. It allows you to track character development, view comprehensive overviews, and automatically extract new information from session transcripts.

        #### Key Features:

        -   **Centralized Tracking**: Keep a detailed record for each character, including their player, race, class, level, notable actions, inventory, relationships, and memorable quotes.
        -   **Dynamic Overviews**: Select a character to view a dynamically generated overview of their entire profile.
        -   **Automatic Profile Extraction**: Use the power of an LLM to automatically analyze an in-character session transcript. The system will extract and append new information to the relevant character profiles, such as:
            -   Notable actions performed.
            -   Items acquired or lost.
            -   New relationships formed.
            -   Memorable quotes.
        -   **Import/Export**: Save individual character profiles to a `.json` file for backup or sharing, and import them back into the system.

        This powerful tool helps you maintain a living document for each character, ensuring no detail from your campaign is ever lost.
        """)

        char_mgr = CharacterProfileManager()
        initial_chars = char_mgr.list_characters()

        with gr.Row():
            with gr.Column():
                gr.Markdown("#### View Characters")
                char_refresh_btn = UIComponents.create_action_button(
                    SI.ACTION_REFRESH,
                    variant="secondary",
                    size="sm",
                )
                char_table = gr.Dataframe(
                    headers=["Character", "Player", "Race/Class", "Level", "Sessions"],
                    datatype=["str", "str", "str", "number", "number"],
                    label="Characters",
                    interactive=False,
                    wrap=True,
                )

                char_select = gr.Dropdown(
                    label="Select Character",
                    choices=initial_chars,
                    value=initial_chars[0] if initial_chars else None,
                    interactive=True,
                )
                view_char_btn = UIComponents.create_action_button(
                    "View Character Overview",
                    variant="primary",
                )

            with gr.Column():
                gr.Markdown("#### Export/Import")
                export_char_dropdown = gr.Dropdown(
                    label="Character to Export",
                    choices=initial_chars,
                    value=initial_chars[0] if initial_chars else None,
                    interactive=True,
                )
                export_char_btn = UIComponents.create_action_button("Export Character", variant="secondary")
                export_char_file = gr.File(label="Download Character Profile")
                export_char_status = gr.Markdown(
                    value=StatusMessages.info(
                        "Export Character Profile",
                        "Select a character and click Export to download their profile."
                    )
                )

                gr.Markdown("---")

                import_char_file = gr.File(label="Upload Character JSON", file_types=[".json"])
                import_char_btn = UIComponents.create_action_button("Import Character", variant="primary")
                import_char_status = gr.Markdown(
                    value=StatusMessages.info(
                        "Import Character Profile",
                        "Upload a character JSON export to add it to the campaign."
                    )
                )

        with gr.Row():
            gr.Markdown("### [AUTO] Automatic Profile Extraction")

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
                    file_types=[".txt"],
                )
                extract_party_choices = [party for party in available_parties if party != "Manual Entry"]
                extract_party_dropdown = gr.Dropdown(
                    choices=extract_party_choices,
                    label="Party Configuration",
                    value=(
                        "default"
                        if "default" in extract_party_choices
                        else (extract_party_choices[0] if extract_party_choices else None)
                    ),
                )
                extract_session_id = gr.Textbox(
                    label="Session ID",
                    placeholder=Placeholders.SESSION_ID,
                    info=InfoText.SESSION_ID,
                )
                extract_btn = UIComponents.create_action_button(
                    "Extract Character Data",
                    variant="primary",
                )
                extract_status = gr.Markdown(
                    label="Extraction Status",
                    value=StatusMessages.info(
                        "Automatic Profile Extraction",
                        "Upload an IC-only transcript and click Extract to update character profiles."
                    ),
                )

        with gr.Row():
            char_overview_output = gr.Markdown(
                label="Character Overview",
                value=StatusMessages.info(
                    "Character Overview",
                    "Select a character to view their profile summary."
                ),
                elem_classes="character-overview-scrollable",
            )

        existing_css = blocks.css or ""
        blocks.css = existing_css + """
.character-overview-scrollable {
    max-height: 600px;
    overflow-y: auto;
}
.scrollable-log {
    max-height: 600px;
    overflow-y: auto !important;
}
"""

        def load_character_list():
            from src.character_profile import CharacterProfileManager

            manager = CharacterProfileManager()
            characters = manager.list_characters()

            if not characters:
                return [], [], []

            table_data = []
            for char_name in characters:
                profile = manager.get_profile(char_name)
                table_data.append([
                    profile.name,
                    profile.player,
                    f"{profile.race} {profile.class_name}",
                    profile.level,
                    profile.total_sessions,
                ])

            return table_data, characters, characters

        def view_character_profile(character_name):
            if not character_name:
                return StatusMessages.warning(
                    "No Character Selected",
                    "Choose a character to view their profile summary."
                )

            from src.character_profile import CharacterProfileManager

            manager = CharacterProfileManager()
            overview = manager.generate_character_overview(character_name, format="markdown")
            if not overview:
                return StatusMessages.warning(
                    "No Profile Data",
                    "No information is available for this character yet."
                )
            return overview

        def export_character_ui(character_name):
            if not character_name:
                return None, StatusMessages.warning(
                    "No Character Selected",
                    "Choose a character to export its profile."
                )

            try:
                from src.character_profile import CharacterProfileManager
                from tempfile import NamedTemporaryFile

                manager = CharacterProfileManager()
                temp_file = NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
                temp_path = Path(temp_file.name)
                temp_file.close()

                manager.export_profile(character_name, temp_path)
                return temp_path, StatusMessages.success(
                    "Export Complete",
                    f"Character '{character_name}' exported successfully."
                )
            except Exception as exc:
                return None, StatusMessages.error(
                    "Export Failed",
                    "The character profile could not be exported.",
                    str(exc),
                )

        def _begin_extract_placeholder():
            return StatusMessages.loading(
                "Extracting character data"
            )


        def import_character_ui(file_obj):
            if file_obj is None:
                return StatusMessages.warning(
                    "No File Uploaded",
                    "Upload a character JSON export before importing."
                )

            try:
                from src.character_profile import CharacterProfileManager

                manager = CharacterProfileManager()
                imported_name = manager.import_profile(Path(file_obj.name))
                return StatusMessages.success(
                    "Import Complete",
                    f"Character '{imported_name}' imported successfully. Click Refresh to update the list."
                )
            except Exception as exc:
                return StatusMessages.error(
                    "Import Failed",
                    "The character profile could not be imported.",
                    str(exc),
                )

        def extract_profiles_ui(transcript_file, party_id, session_id):
            if transcript_file is None:
                return StatusMessages.error(
                    "Transcript Required",
                    "Upload an IC-only transcript before running extraction."
                )

            if not party_id or party_id == "Manual Entry":
                return StatusMessages.error(
                    "Party Configuration Required",
                    "Select a saved party configuration before extracting data."
                )

            if not session_id:
                return StatusMessages.error(
                    "Session ID Required",
                    "Provide a session ID so the updates can be tracked."
                )

            try:
                from src.profile_extractor import CharacterProfileExtractor
                from src.character_profile import CharacterProfileManager
                from src.party_config import PartyConfigManager

                extractor = CharacterProfileExtractor()
                profile_mgr = CharacterProfileManager()
                party_mgr = PartyConfigManager()

                results = extractor.batch_extract_and_update(
                    transcript_path=Path(transcript_file.name),
                    party_id=party_id,
                    session_id=session_id,
                    profile_manager=profile_mgr,
                    party_manager=party_mgr,
                )

                summary_lines = [
                    StatusMessages.success(
                        "Extraction Complete",
                        f"Updated {len(results)} character profile(s)."
                    ),
                    f"**Party**: {party_id}",
                    f"**Session**: {session_id}",
                    "",
                    "### Character Updates",
                ]

                if not results:
                    summary_lines.append("No characters were updated in this extraction run.")
                else:
                    for char_name, extracted_data in results.items():
                        summary_lines.append(f"**{char_name}**")
                        summary_lines.append(f"- Actions: {len(extracted_data.notable_actions)}")
                        summary_lines.append(f"- Items: {len(extracted_data.items_acquired)}")
                        summary_lines.append(f"- Relationships: {len(extracted_data.relationships_mentioned)}")
                        summary_lines.append(f"- Quotes: {len(extracted_data.memorable_quotes)}")
                        summary_lines.append(f"- Developments: {len(extracted_data.character_development)}")
                        summary_lines.append("")

                summary_lines.append("Refresh the character list to view the latest changes.")
                return "\n".join(summary_lines)

            except Exception as exc:
                import traceback

                error_details = traceback.format_exc()
                return StatusMessages.error(
                    "Extraction Failed",
                    str(exc),
                    error_details,
                )

        def on_table_select(evt: gr.SelectData):
            if evt.index[0] >= 0:
                from src.character_profile import CharacterProfileManager

                manager = CharacterProfileManager()
                characters = manager.list_characters()
                if evt.index[0] < len(characters):
                    return characters[evt.index[0]]
            return None

        char_refresh_btn.click(
            fn=load_character_list,
            outputs=[char_table, char_select, export_char_dropdown],
        )

        char_table.select(
            fn=on_table_select,
            outputs=[char_select],
        )

        view_char_btn.click(
            fn=view_character_profile,
            inputs=[char_select],
            outputs=[char_overview_output],
        )

        export_char_btn.click(
            fn=export_character_ui,
            inputs=[export_char_dropdown],
            outputs=[export_char_file, export_char_status],
        )

        import_char_btn.click(
            fn=import_character_ui,
            inputs=[import_char_file],
            outputs=[import_char_status],
        )

        extract_btn.click(
            fn=_begin_extract_placeholder,
            outputs=[extract_status],
            queue=True,
        ).then(
            fn=extract_profiles_ui,
            inputs=[extract_transcript_file, extract_party_dropdown, extract_session_id],
            outputs=[extract_status],
            queue=True,
        )

        blocks.load(
            fn=load_character_list,
            outputs=[char_table, char_select, export_char_dropdown],
        )

