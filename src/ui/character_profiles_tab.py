from __future__ import annotations

from pathlib import Path
from typing import List

import gradio as gr


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
                char_refresh_btn = gr.Button("Refresh Character List", size="sm")
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
                view_char_btn = gr.Button("View Character Overview", variant="primary")

            with gr.Column():
                gr.Markdown("#### Export/Import")
                export_char_dropdown = gr.Dropdown(
                    label="Character to Export",
                    choices=initial_chars,
                    value=initial_chars[0] if initial_chars else None,
                    interactive=True,
                )
                export_char_btn = gr.Button("Export Character")
                export_char_file = gr.File(label="Download Character Profile")
                export_char_status = gr.Textbox(label="Status", interactive=False)

                gr.Markdown("---")

                import_char_file = gr.File(label="Upload Character JSON", file_types=[".json"])
                import_char_btn = gr.Button("Import Character")
                import_char_status = gr.Textbox(label="Status", interactive=False)

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
                    placeholder="e.g., Session 1",
                )
                extract_btn = gr.Button("[EXTRACT] Extract Character Data", variant="primary")
                extract_status = gr.Textbox(label="Extraction Status", lines=5, interactive=False)

        with gr.Row():
            char_overview_output = gr.Markdown(
                label="Character Overview",
                value="Select a character to view their profile.",
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
                return "Please select a character."

            from src.character_profile import CharacterProfileManager

            manager = CharacterProfileManager()
            return manager.generate_character_overview(character_name, format="markdown")

        def export_character_ui(character_name):
            if not character_name:
                return None, "Please select a character"

            try:
                from src.character_profile import CharacterProfileManager
                from tempfile import NamedTemporaryFile

                manager = CharacterProfileManager()
                temp_file = NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
                temp_path = Path(temp_file.name)
                temp_file.close()

                manager.export_profile(character_name, temp_path)
                return temp_path, f"Exported '{character_name}'"
            except Exception as exc:
                return None, f"Error: {exc}"

        def import_character_ui(file_obj):
            if file_obj is None:
                return "Please upload a file"

            try:
                from src.character_profile import CharacterProfileManager

                manager = CharacterProfileManager()
                imported_name = manager.import_profile(Path(file_obj.name))
                return f"Successfully imported character '{imported_name}'. Click Refresh to see it."
            except Exception as exc:
                return f"Error: {exc}"

        def extract_profiles_ui(transcript_file, party_id, session_id):
            if transcript_file is None:
                return "[ERROR] Please upload an IC-only transcript file"

            if not party_id or party_id == "Manual Entry":
                return "[ERROR] Please select a party configuration (not Manual Entry)"

            if not session_id:
                return "[ERROR] Please enter a session ID"

            try:
                from src.profile_extractor import CharacterProfileExtractor
                from src.character_profile import CharacterProfileManager
                from src.party_config import PartyConfigManager

                extractor = CharacterProfileExtractor()
                profile_mgr = CharacterProfileManager()
                party_mgr = PartyConfigManager()

                status = "[INFO] Extracting character data from transcript...\n"
                status += f"Party: {party_id}\n"
                status += f"Session: {session_id}\n\n"

                results = extractor.batch_extract_and_update(
                    transcript_path=Path(transcript_file.name),
                    party_id=party_id,
                    session_id=session_id,
                    profile_manager=profile_mgr,
                    party_manager=party_mgr,
                )

                status += "[SUCCESS] Extraction complete!\n\n"
                status += f"Updated {len(results)} character profile(s):\n"

                for char_name, extracted_data in results.items():
                    status += f"\n**{char_name}**:\n"
                    status += f"  - Actions: {len(extracted_data.notable_actions)}\n"
                    status += f"  - Items: {len(extracted_data.items_acquired)}\n"
                    status += f"  - Relationships: {len(extracted_data.relationships_mentioned)}\n"
                    status += f"  - Quotes: {len(extracted_data.memorable_quotes)}\n"
                    status += f"  - Developments: {len(extracted_data.character_development)}\n"

                status += "\n[SUCCESS] Click 'Refresh Character List' to see updates!"
                return status

            except Exception as exc:
                import traceback

                error_details = traceback.format_exc()
                return f"[ERROR] Extraction failed:\n{exc}\n\nDetails:\n{error_details}"

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
            fn=extract_profiles_ui,
            inputs=[extract_transcript_file, extract_party_dropdown, extract_session_id],
            outputs=[extract_status],
        )

        blocks.load(
            fn=load_character_list,
            outputs=[char_table, char_select, export_char_dropdown],
        )