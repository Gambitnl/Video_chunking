"""Modern Characters tab - campaign-aware character management."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import gradio as gr

from src.character_profile import CharacterProfileManager
from src.ui.helpers import Placeholders, StatusMessages, UIComponents


def character_tab_snapshot(
    campaign_id: Optional[str],
) -> Dict[str, object]:
    """Return table data and status messaging for the active campaign."""
    if not campaign_id:
        return {
            "status": StatusMessages.info(
                "No Campaign Selected",
                "Load a campaign to display its character profiles."
            ),
            "table": [],
            "characters": [],
        }

    manager = CharacterProfileManager()

    characters = manager.list_characters(campaign_id=campaign_id)
    if not characters:
        return {
            "status": StatusMessages.warning(
                "No Profiles Found",
                "No character profiles are assigned to this campaign yet."
            ),
            "table": [],
            "characters": [],
        }

    table_data: List[List[object]] = []
    for char_name in characters:
        profile = manager.get_profile(char_name)
        if not profile:
            continue
        table_data.append([
            profile.name,
            profile.player or "Unassigned",
            f"{profile.race or 'Unknown'} / {profile.class_name or 'Unknown'}",
            profile.level or 0,
            profile.total_sessions,
        ])

    status_message = StatusMessages.success(
        "Profiles Loaded",
        f"{len(characters)} character profile(s) available for this campaign."
    )

    return {
        "status": status_message,
        "table": table_data,
        "characters": characters,
    }


def create_characters_tab_modern(
    blocks: gr.Blocks,
    available_parties: List[str],
    *,
    refresh_campaign_names: Callable[[], Dict[str, str]],
    active_campaign_state: Optional[gr.State] = None,
    initial_campaign_id: Optional[str] = None,
) -> Dict[str, gr.components.Component]:
    """Create the Characters tab and return references to campaign-aware components."""

    active_state = active_campaign_state or gr.State(value=initial_campaign_id)
    initial_snapshot = character_tab_snapshot(initial_campaign_id)

    def _default_overview() -> str:
        return StatusMessages.info(
            "Character Overview",
            "Select a character to view their profile summary."
        )

    with gr.Tab("Characters"):
        gr.Markdown(
            """
            # Character Profiles

            Manage, export, and enrich character records for the active campaign.
            """
        )

        profiles_md = gr.Markdown(value=initial_snapshot["status"])

        with gr.Row():
            char_table = gr.Dataframe(
                headers=["Character", "Player", "Race/Class", "Level", "Sessions"],
                datatype=["str", "str", "str", "number", "number"],
                label="Characters",
                interactive=False,
                wrap=True,
                value=initial_snapshot["table"],
            )

            char_overview_output = gr.Markdown(
                value=_default_overview(),
                elem_classes="character-overview-scrollable",
            )

        existing_css = blocks.css or ""
        blocks.css = existing_css + """
.character-overview-scrollable {
    max-height: 600px;
    overflow-y: auto;
}
"""

        with gr.Row():
            char_select = gr.Dropdown(
                label="Select Character",
                choices=initial_snapshot["characters"],
                value=initial_snapshot["characters"][0] if initial_snapshot["characters"] else None,
                interactive=True,
            )
            view_char_btn = UIComponents.create_action_button(
                "View Character Overview",
                variant="primary",
            )
            char_refresh_btn = UIComponents.create_action_button(
                "Refresh List",
                variant="secondary",
                size="sm",
            )

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Export / Import")
                export_char_dropdown = gr.Dropdown(
                    label="Character to Export",
                    choices=initial_snapshot["characters"],
                    value=initial_snapshot["characters"][0] if initial_snapshot["characters"] else None,
                )
                export_char_btn = UIComponents.create_action_button("Export Character", variant="secondary")
                export_char_file = gr.File(label="Download Character Profile")
                export_char_status = gr.Markdown(
                    value=StatusMessages.info(
                        "Export Character Profile",
                        "Select a character and click Export to download their profile."
                    )
                )

                import_char_file = gr.File(label="Upload Character JSON", file_types=[".json"])
                import_char_btn = UIComponents.create_action_button("Import Character", variant="primary")
                import_char_status = gr.Markdown(
                    value=StatusMessages.info(
                        "Import Character Profile",
                        "Upload a character JSON export to add it to the campaign."
                    )
                )

            with gr.Column():
                gr.Markdown("### Automatic Profile Extraction")
                extract_transcript_file = gr.File(
                    label="IC-Only Transcript (TXT)",
                    file_types=[".txt"],
                )
                extract_party_choices = [party for party in available_parties if party != "Manual Entry"]
                extract_party_dropdown = gr.Dropdown(
                    choices=extract_party_choices,
                    label="Party Configuration",
                    value=(
                        extract_party_choices[0]
                        if extract_party_choices
                        else None
                    ),
                )
                extract_session_id = gr.Textbox(
                    label="Session ID",
                    placeholder=Placeholders.SESSION_ID,
                )
                extract_btn = UIComponents.create_action_button(
                    "Extract from Transcript",
                    variant="primary",
                )
                extract_status = gr.Markdown(
                    value=StatusMessages.info(
                        "Ready for Extraction",
                        "Upload an IC-only transcript, select a party, provide the session ID, and click Extract."
                    )
                )

        def load_character_list(campaign_id: Optional[str]):
            snapshot = character_tab_snapshot(campaign_id)
            characters = snapshot["characters"]
            default_value = characters[0] if characters else None
            dropdown_update = gr.update(choices=characters, value=default_value)
            return (
                snapshot["table"],
                dropdown_update,
                dropdown_update,
                snapshot["status"],
                _default_overview(),
            )

        def view_character_profile(character_name: Optional[str]):
            if not character_name:
                return StatusMessages.warning(
                    "No Character Selected",
                    "Choose a character to view their profile summary."
                )

            overview = CharacterProfileManager().generate_character_overview(character_name, format="markdown")
            if not overview:
                return StatusMessages.warning(
                    "No Profile Data",
                    "No information is available for this character yet."
                )
            return overview

        def export_character_ui(character_name: Optional[str]):
            if not character_name:
                return None, StatusMessages.warning(
                    "No Character Selected",
                    "Choose a character to export its profile."
                )

            try:
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

        def import_character_ui(file_obj):
            if file_obj is None:
                return StatusMessages.warning(
                    "No File Uploaded",
                    "Upload a character JSON export before importing."
                )

            try:
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

        def _begin_extract_placeholder():
            return StatusMessages.loading("Extracting character data")

        def extract_profiles_ui(transcript_file, party_id, session_id, campaign_id):
            if transcript_file is None:
                return StatusMessages.error(
                    "Transcript Required",
                    "Upload an IC-only transcript before running extraction."
                )

            if not party_id:
                return StatusMessages.error(
                    "Party Configuration Required",
                    "Select a saved party configuration before extracting data."
                )

            if not session_id:
                return StatusMessages.error(
                    "Session ID Required",
                    "Provide a session ID so the updates can be tracked."
                )

            effective_campaign_id = campaign_id or party_id

            try:
                from src.character_profile_extractor import CharacterProfileExtractor
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
                    campaign_id=effective_campaign_id,
                )

                if not results:
                    return StatusMessages.warning(
                        "No Updates Found",
                        "Extraction completed but no characters were updated. Verify the transcript content."
                    )

                summary_lines = [
                    StatusMessages.success(
                        "Extraction Complete",
                        f"Updated {len(results)} character profile(s)."
                    ),
                    f"- **Campaign**: `{effective_campaign_id}`",
                    f"- **Party**: `{party_id}`",
                    f"- **Session**: `{session_id}`",
                    "",
                    "### Character Updates",
                ]

                for char_name, extracted_data in results.items():
                    summary_lines.append(f"**{char_name}**")
                    summary_lines.append(f"- Actions: {len(extracted_data.notable_actions)}")
                    summary_lines.append(f"- Items: {len(extracted_data.items_acquired)}")
                    summary_lines.append(f"- Relationships: {len(extracted_data.relationships_mentioned)}")
                    summary_lines.append(f"- Quotes: {len(extracted_data.memorable_quotes)}")
                    summary_lines.append(f"- Developments: {len(extracted_data.character_development)}")
                    summary_lines.append("")

                summary_lines.append("Character list refreshed automatically.")
                return "\n".join(summary_lines)

            except Exception as exc:
                import traceback

                error_details = traceback.format_exc()
                return StatusMessages.error(
                    "Extraction Failed",
                    str(exc),
                    error_details,
                )

        def on_table_select(evt: gr.SelectData, campaign_id: Optional[str]):
            if evt.index and evt.index[0] >= 0:
                snapshot = character_tab_snapshot(campaign_id)
                characters = snapshot["characters"]
                if evt.index[0] < len(characters):
                    return characters[evt.index[0]]
            return None

        char_refresh_btn.click(
            fn=load_character_list,
            inputs=[active_state],
            outputs=[char_table, char_select, export_char_dropdown, profiles_md, char_overview_output],
        )

        view_char_btn.click(
            fn=view_character_profile,
            inputs=[char_select],
            outputs=[char_overview_output],
        )

        char_table.select(
            fn=on_table_select,
            inputs=[active_state],
            outputs=[char_select],
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
            inputs=[extract_transcript_file, extract_party_dropdown, extract_session_id, active_state],
            outputs=[extract_status],
            queue=True,
        ).then(
            fn=load_character_list,
            inputs=[active_state],
            outputs=[char_table, char_select, export_char_dropdown, profiles_md, char_overview_output],
        )

        blocks.load(
            fn=load_character_list,
            inputs=[active_state],
            outputs=[char_table, char_select, export_char_dropdown, profiles_md, char_overview_output],
        )

    return {
        "profiles": profiles_md,
        "table": char_table,
        "character_dropdown": char_select,
        "export_dropdown": export_char_dropdown,
        "overview": char_overview_output,
        "extract_party_dropdown": extract_party_dropdown,
    }
