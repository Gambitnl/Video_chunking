
from __future__ import annotations

import gradio as gr
from src.ui.helpers import UIComponents
from src.diarizer import SpeakerProfileManager
from src.party_config import PartyConfigManager

def create_speaker_manager_tab(speaker_profile_manager: SpeakerProfileManager) -> None:
    """
    Create the Speaker Manager tab with enhanced controls for:
    - Speaker ID to player name mapping
    - DM/Player role assignment
    - DM narrator vs. NPC mode toggles
    - Character name mapping
    - Diarization confidence display
    """
    party_manager = PartyConfigManager()

    with gr.Tab("Speaker Manager"):
        gr.Markdown("## Speaker Manager")
        gr.Markdown(
            "Assign names to speaker IDs, configure DM roles, and map players to characters. "
            "These mappings improve character attribution accuracy in classification."
        )

        with gr.Row():
            session_id_input = gr.Textbox(
                label="Session ID",
                placeholder="Enter Session ID",
                info="Session ID to load speaker profiles for"
            )
            load_speakers_btn = gr.Button("Load Speakers", variant="primary")

        with gr.Row():
            party_selection = gr.Dropdown(
                choices=["Manual Entry"] + party_manager.list_parties(),
                value="Manual Entry",
                label="Party Configuration",
                info="Load character mappings from party config"
            )
            load_party_btn = gr.Button("Load Party Mappings", variant="secondary")

        # Enhanced speaker mapping UI with role controls
        speaker_mapping_ui = gr.Dataframe(
            headers=[
                "Speaker ID",
                "Player Name",
                "Role",
                "Character Name",
                "Confidence"
            ],
            datatype=["str", "str", "str", "str", "number"],
            label="Speaker Mapping & Roles",
            interactive=True,
            col_count=(5, "fixed"),
            row_count=(10, "dynamic"),
        )

        gr.Markdown(
            "**Role Options**: "
            "- `PLAYER` - Regular player character\n"
            "- `DM_NARRATOR` - DM providing scene description/narration\n"
            "- `DM_NPC` - DM speaking as an NPC\n"
            "- `UNKNOWN` - Speaker not yet identified\n\n"
            "**Note**: Role hints help the classifier distinguish between DM narration and NPC dialogue."
        )

        with gr.Row():
            save_mappings_btn = gr.Button("Save Mappings", variant="primary")
            clear_session_btn = gr.Button("Clear Session", variant="stop")

        mapping_status = gr.Markdown(value="Ready to load speaker mappings.")

        # DM NPC Mode Controls
        with gr.Accordion("DM NPC Mode (Advanced)", open=False):
            gr.Markdown(
                "Configure which NPC the DM is currently voicing. "
                "This allows the classifier to attribute DM speech to specific NPCs."
            )

            with gr.Row():
                dm_speaker_id = gr.Textbox(
                    label="DM Speaker ID",
                    placeholder="e.g., SPEAKER_17",
                    info="The speaker ID assigned to the DM"
                )
                current_npc_name = gr.Textbox(
                    label="Active NPC Name",
                    placeholder="e.g., Captain, Goblin King",
                    info="Which NPC the DM is currently voicing"
                )

            with gr.Row():
                npc_start_time = gr.Textbox(
                    label="Start Time (mm:ss)",
                    placeholder="e.g., 05:30",
                    info="When DM starts voicing this NPC"
                )
                npc_end_time = gr.Textbox(
                    label="End Time (mm:ss)",
                    placeholder="e.g., 08:45",
                    info="When DM stops voicing this NPC (leave empty for rest of session)"
                )

            set_npc_mode_btn = gr.Button("Set NPC Mode", variant="secondary")
            npc_mode_status = gr.Markdown(value="No NPC mode active.")

        def load_speakers(session_id: str):
            """Load speaker profiles for a session with enhanced role information."""
            if not session_id:
                return [], "Please enter a session ID."

            profiles = speaker_profile_manager._load_profiles()
            session_profiles = profiles.get(session_id, {})

            if not session_profiles:
                return [], f"No speaker profiles found for session '{session_id}'."

            # Build enhanced mapping rows
            rows = []
            for speaker_id, data in session_profiles.items():
                player_name = data.get("name", "")
                role = data.get("role", "UNKNOWN")
                character_name = data.get("character_name", "")
                confidence = data.get("confidence", 0.0)

                rows.append([
                    speaker_id,
                    player_name,
                    role,
                    character_name,
                    round(confidence, 2) if confidence else 0.0
                ])

            status = f"Loaded {len(rows)} speaker(s) for session '{session_id}'."
            return rows, status

        def load_party_mappings(party_id: str, current_mappings: list[list]):
            """Load character mappings from party config and merge with current speaker data."""
            if party_id == "Manual Entry" or not party_id:
                return current_mappings, "Using manual entry mode."

            try:
                party = party_manager.load_party(party_id)
                player_to_character = {}

                # Build player -> character mapping from party config
                for char in party.characters:
                    player_name = char.get("player_name")
                    char_name = char.get("name")
                    if player_name and char_name:
                        player_to_character[player_name] = char_name

                # Add DM if present
                if party.dm_name:
                    player_to_character[party.dm_name] = "DM"

                # Update character names in current mappings
                updated_mappings = []
                for row in current_mappings:
                    if len(row) >= 5:
                        speaker_id, player_name, role, char_name, confidence = row

                        # Auto-fill character name from party config
                        if player_name in player_to_character:
                            char_name = player_to_character[player_name]
                            # Auto-set role for DM
                            if char_name == "DM" and role == "UNKNOWN":
                                role = "DM_NARRATOR"
                            elif role == "UNKNOWN":
                                role = "PLAYER"

                        updated_mappings.append([
                            speaker_id, player_name, role, char_name, confidence
                        ])
                    else:
                        updated_mappings.append(row)

                status = f"Loaded party config '{party_id}' and mapped {len(player_to_character)} characters."
                return updated_mappings, status

            except Exception as e:
                return current_mappings, f"Error loading party config: {str(e)}"

        def save_mappings(session_id: str, mappings: list[list[str]]):
            """Save enhanced speaker mappings with role and character information."""
            if not session_id:
                return [], "Please enter a session ID."

            if not mappings:
                return [], "No mappings to save."

            # Load existing profiles to preserve additional metadata
            profiles = speaker_profile_manager._load_profiles()
            session_profiles = profiles.get(session_id, {})

            # Update profiles with new mapping data
            for row in mappings:
                if len(row) >= 4:
                    speaker_id = row[0]
                    player_name = row[1]
                    role = row[2] if len(row) > 2 else "UNKNOWN"
                    character_name = row[3] if len(row) > 3 else ""

                    # Preserve existing metadata, update with new values
                    existing = session_profiles.get(speaker_id, {})
                    existing["name"] = player_name
                    existing["role"] = role
                    existing["character_name"] = character_name

                    session_profiles[speaker_id] = existing

            # Save updated profiles
            profiles[session_id] = session_profiles
            speaker_profile_manager._save_profiles(profiles)

            status = f"✅ Saved {len(mappings)} speaker mapping(s) for session '{session_id}'."
            gr.Info("Speaker mappings saved successfully!")
            return mappings, status

        def clear_session(session_id: str):
            """Clear speaker profiles for a session."""
            if not session_id:
                return [], "Please enter a session ID."

            profiles = speaker_profile_manager._load_profiles()
            if session_id in profiles:
                del profiles[session_id]
                speaker_profile_manager._save_profiles(profiles)
                status = f"✅ Cleared speaker profiles for session '{session_id}'."
                gr.Warning(f"Cleared session '{session_id}'")
                return [], status
            else:
                return [], f"No profiles found for session '{session_id}'."

        def set_npc_mode(session_id: str, dm_speaker: str, npc_name: str, start: str, end: str):
            """Set DM NPC mode for a specific time range."""
            if not all([session_id, dm_speaker, npc_name, start]):
                return "⚠️ Please fill in session ID, DM speaker ID, NPC name, and start time."

            try:
                profiles = speaker_profile_manager._load_profiles()
                session_profiles = profiles.get(session_id, {})

                if dm_speaker not in session_profiles:
                    return f"⚠️ Speaker '{dm_speaker}' not found in session '{session_id}'."

                # Initialize NPC mode tracking if not exists
                if "npc_modes" not in session_profiles[dm_speaker]:
                    session_profiles[dm_speaker]["npc_modes"] = []

                # Add NPC mode entry
                npc_mode_entry = {
                    "npc_name": npc_name,
                    "start_time": start,
                    "end_time": end if end else None
                }
                session_profiles[dm_speaker]["npc_modes"].append(npc_mode_entry)

                # Save updated profiles
                profiles[session_id] = session_profiles
                speaker_profile_manager._save_profiles(profiles)

                time_range = f"{start} to {end}" if end else f"{start} onwards"
                return f"✅ Set NPC mode: {dm_speaker} voicing '{npc_name}' from {time_range}"

            except Exception as e:
                return f"❌ Error setting NPC mode: {str(e)}"

        # Wire up event handlers
        load_speakers_btn.click(
            fn=load_speakers,
            inputs=[session_id_input],
            outputs=[speaker_mapping_ui, mapping_status],
        )

        load_party_btn.click(
            fn=load_party_mappings,
            inputs=[party_selection, speaker_mapping_ui],
            outputs=[speaker_mapping_ui, mapping_status],
        )

        save_mappings_btn.click(
            fn=save_mappings,
            inputs=[session_id_input, speaker_mapping_ui],
            outputs=[speaker_mapping_ui, mapping_status],
        )

        clear_session_btn.click(
            fn=clear_session,
            inputs=[session_id_input],
            outputs=[speaker_mapping_ui, mapping_status],
        )

        set_npc_mode_btn.click(
            fn=set_npc_mode,
            inputs=[session_id_input, dm_speaker_id, current_npc_name, npc_start_time, npc_end_time],
            outputs=[npc_mode_status],
        )
