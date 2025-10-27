from __future__ import annotations

from typing import Callable, Dict

import gradio as gr

from src.config import Config
from src.party_config import PartyConfigManager
from src.ui.constants import StatusIndicators as SI
from src.ui.helpers import (
    StatusMessages,
    UIComponents,
    Placeholders,
    InfoText,
)


def create_import_notes_tab(refresh_campaign_names: Callable[[], Dict[str, str]]) -> None:
    with gr.Tab("Import Session Notes"):
        gr.Markdown("""
        ### Import Session Notes

        **Backfill your campaign with sessions you did not record.**

        This tool automatically extracts:
        - Quests (started, progressed, completed)
        - NPCs (roles, descriptions, relationships)
        - Locations (visited or referenced)
        - Items (important finds and rewards)
        - Plot hooks (unresolved mysteries and threads)

        Perfect for importing early sessions before you began recording.
        """)

        with gr.Accordion("[GUIDE] Quick Start Guide & Example Format", open=False):
            gr.Markdown("""
            ### How to Use This Tool:

            1. **Enter Session ID** (e.g., `Session_01`) - Required [REQUIRED]
            2. **Select Campaign** - Choose which campaign these notes belong to
            3. **Paste Your Notes** - Copy/paste from your document OR upload a .txt/.md file
            4. **Check Options**:
               - [EXTRACT] **Extract Knowledge** (Recommended) - Finds NPCs, quests, locations automatically
               - [NARRATIVE] **Generate Narrative** (Optional) - Creates a story-style summary
            5. **Click "Import Session Notes"**

            ---

            ### [EXAMPLE] Example Notes Format:

            ```markdown
            Session 1 - The Adventure Begins

            The party met at the Broken Compass tavern in Neverwinter.
            Guard Captain Thorne approached them with a quest to find
            Marcus, a merchant who disappeared on the Waterdeep Road.

            NPCs Met:
            - Guard Captain Thorne (stern but fair, quest giver)
            - Innkeeper Mara (friendly, provided rumors)

            Locations Visited:
            - The Broken Compass tavern
            - Waterdeep Road

            Quests:
            - Find Marcus the Missing Merchant (active)

            The party set out at dawn...
            ```

            **Don't worry about perfect formatting!** The AI can understand natural language notes.
            Even a simple paragraph describing what happened works fine.
            """)

        with gr.Row():
            with gr.Column(scale=2):
                notes_session_id = gr.Textbox(
                    label="Session ID",
                    placeholder=Placeholders.SESSION_ID,
                    info=InfoText.SESSION_ID
                )
                notes_campaign_choices = ["default"] + list(refresh_campaign_names().keys())
                notes_campaign = gr.Dropdown(
                    choices=notes_campaign_choices,
                    value="default",
                    label="Campaign",
                    info=InfoText.CAMPAIGN_SELECT
                )
            with gr.Column(scale=1):
                notes_extract_knowledge = gr.Checkbox(
                    label="Extract Knowledge (Recommended)",
                    value=True,
                    info="AI will automatically find: NPCs, quests, locations, items, plot hooks"
                )
                notes_generate_narrative = gr.Checkbox(
                    label="Generate Narrative Summary",
                    value=False,
                    info="Creates a story-style summary (takes extra time)"
                )

        notes_input = gr.Textbox(
            label="Session Notes",
            placeholder=Placeholders.SESSION_NOTES,
            info=InfoText.SESSION_NOTES,
            lines=15,
            max_lines=30
        )

        notes_file_upload = gr.File(
            label="[UPLOAD] Or Upload Notes File (.txt or .md)",
            file_types=[".txt", ".md"],
            type="filepath"
        )

        ready_indicator = gr.Markdown(
            value=StatusMessages.info(
                "Ready",
                "Fill in the required fields above to begin."
            )
        )

        with gr.Row():
            notes_import_btn = UIComponents.create_action_button(
                f"{SI.ACTION_IMPORT} Session Notes",
                variant="primary",
                size="lg",
                full_width=True
            )
            notes_clear_btn = UIComponents.create_action_button(
                f"{SI.ACTION_CLEAR} All Fields",
                variant="secondary",
                size="md"
            )

        notes_output = gr.Markdown(
            label="Import Results",
            value=StatusMessages.info(
                "Import Session Notes",
                "Results will appear here after you import a session."
            )
        )

        def load_notes_from_file(file_path):
            if not file_path:
                return ""
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    return handle.read()
            except Exception as exc:
                return StatusMessages.error(
                    "Unable to Read File",
                    "The uploaded notes file could not be read.",
                    str(exc),
                )

        def validate_import_inputs(session_id, notes_text):
            has_session_id = session_id and session_id.strip()
            has_notes = notes_text and notes_text.strip()

            if has_session_id and has_notes:
                return StatusMessages.success(
                    "Ready to Import",
                    "All required fields are filled. Click Import Session Notes to begin."
                )
            if has_session_id and not has_notes:
                return StatusMessages.warning(
                    "Missing Notes",
                    "Session notes are required before importing.",
                    "Paste your notes or upload a supported file."
                )
            if not has_session_id and has_notes:
                return StatusMessages.warning(
                    "Missing Session ID",
                    "A session ID is required before importing.",
                    "Enter an identifier such as 'Session_01'."
                )
            return StatusMessages.info(
                "Ready",
                "Provide a session ID and notes to enable importing."
            )

        def clear_import_fields():
            ready_message = StatusMessages.info(
                "Ready",
                "Fill in the required fields above to begin."
            )
            output_message = StatusMessages.info(
                "Import Session Notes",
                "Results will appear here after you import a session."
            )
            return (
                "",
                "default",
                "",
                None,
                ready_message,
                output_message,
            )

        def _begin_import_placeholder():
            return StatusMessages.loading("Importing session notes")

        def import_session_notes(session_id, campaign_id, notes_text, extract_knowledge, generate_narrative):
            if not session_id or not session_id.strip():
                return StatusMessages.error(
                    "Session ID Required",
                    "Please provide a session ID before importing."
                )

            if not notes_text or not notes_text.strip():
                return StatusMessages.error(
                    "Session Notes Required",
                    "Please paste session notes or upload a notes file before importing."
                )

            session_id_clean = session_id.strip()
            sections = [
                f"# Import Results: {session_id_clean}",
                f"**Campaign**: {campaign_id}",
                "---",
            ]

            if extract_knowledge:
                try:
                    from src.knowledge_base import KnowledgeExtractor, CampaignKnowledgeBase

                    sections.append("## Knowledge Extraction")
                    sections.append("Analyzing notes and updating the campaign knowledge base...")

                    party_context_dict = None
                    if campaign_id and campaign_id != "default":
                        party_mgr = PartyConfigManager()
                        party = party_mgr.get_party(campaign_id)
                        if party:
                            party_context_dict = {
                                "character_names": [c.name for c in party.characters],
                                "campaign": party.campaign or "Unknown",
                            }

                    extractor = KnowledgeExtractor()
                    extracted = extractor.extract_knowledge(
                        notes_text,
                        session_id_clean,
                        party_context_dict,
                    )

                    kb = CampaignKnowledgeBase(campaign_id=campaign_id)
                    kb.merge_new_knowledge(extracted, session_id_clean)

                    counts = {
                        "quests": len(extracted.get("quests", [])),
                        "npcs": len(extracted.get("npcs", [])),
                        "plot_hooks": len(extracted.get("plot_hooks", [])),
                        "locations": len(extracted.get("locations", [])),
                        "items": len(extracted.get("items", [])),
                    }
                    total = sum(counts.values())

                    knowledge_lines = [
                        f"{SI.SUCCESS} Extracted {total} entities:",
                        "",
                    ]
                    if counts["quests"] > 0:
                        knowledge_lines.append(f"- Quests: {counts['quests']}")
                        for quest in extracted["quests"]:
                            knowledge_lines.append(f"  - {quest.title} ({quest.status})")

                    if counts["npcs"] > 0:
                        knowledge_lines.append(f"- NPCs: {counts['npcs']}")
                        for npc in extracted["npcs"]:
                            knowledge_lines.append(f"  - {npc.name} ({npc.role or 'unknown'})")

                    if counts["plot_hooks"] > 0:
                        knowledge_lines.append(f"- Plot Hooks: {counts['plot_hooks']}")
                        for hook in extracted["plot_hooks"]:
                            knowledge_lines.append(f"  - {hook.summary}")

                    if counts["locations"] > 0:
                        knowledge_lines.append(f"- Locations: {counts['locations']}")
                        for loc in extracted["locations"]:
                            knowledge_lines.append(f"  - {loc.name} ({loc.type or 'unknown'})")

                    if counts["items"] > 0:
                        knowledge_lines.append(f"- Items: {counts['items']}")
                        for item in extracted["items"]:
                            knowledge_lines.append(f"  - {item.name}")

                    knowledge_lines.append("")
                    knowledge_lines.append(f"Knowledge saved to `{kb.knowledge_file}`.")
                    knowledge_lines.append("Visit the Campaign Library tab to review the extracted entities.")

                    sections.extend(knowledge_lines)

                except Exception as exc:
                    sections.append(
                        StatusMessages.error(
                            "Knowledge Extraction Failed",
                            "An error occurred while extracting knowledge.",
                            str(exc),
                        )
                    )

            if generate_narrative:
                try:
                    import ollama

                    sections.append("---")
                    sections.append("## Narrative Generation")
                    sections.append("Generating narrative summary from the provided session notes...")

                    prompt = f"""You are a D&D session narrator. Based on the following session notes, create a concise narrative summary (3-5 paragraphs) capturing the key events, character actions, and story developments.

Session: {session_id_clean}

Session Notes:
{notes_text[:4000]}

Write a narrative summary that:
- Captures the main events and story beats
- Highlights character actions and decisions
- Maintains a consistent narrative voice
- Stays under 500 words

Narrative:"""

                    client = ollama.Client(host=Config.OLLAMA_BASE_URL)
                    response = client.generate(
                        model=Config.OLLAMA_MODEL,
                        prompt=prompt,
                        options={"temperature": 0.6, "num_predict": 800},
                    )

                    narrative = response.get("response", "(No narrative generated)")

                    results += f"### {session_id_clean} - Narrator Summary\n\n"
                    results += f"{narrative}\n\n"

                    narratives_dir = Config.OUTPUT_DIR / "imported_narratives"
                    narratives_dir.mkdir(exist_ok=True, parents=True)
                    narrative_file = narratives_dir / f"{session_id_clean}_narrator.md"
                    narrative_file.write_text(narrative, encoding="utf-8")

                    sections.append(f"**Narrative saved to**: `{narrative_file}`")

                except Exception as exc:
                    sections.append(
                        StatusMessages.error(
                            "Narrative Generation Failed",
                            "The narrative could not be generated.",
                            str(exc),
                        )
                    )

            summary_lines = []
            if extract_knowledge:
                summary_lines.append("- Review the **Campaign Library** tab to see the new knowledge.")
            if generate_narrative:
                summary_lines.append("- The generated narrative is available under `output/imported_narratives/`.")

            sections.append(
                StatusMessages.success(
                    "Import Complete",
                    "Session notes were processed successfully." + ("\n\n" + "\n".join(summary_lines) if summary_lines else "")
                )
            )

            return "\n\n".join(sections)

        notes_file_upload.change(
            fn=load_notes_from_file,
            inputs=[notes_file_upload],
            outputs=[notes_input],
        )

        notes_session_id.change(
            fn=validate_import_inputs,
            inputs=[notes_session_id, notes_input],
            outputs=[ready_indicator],
        )

        notes_input.change(
            fn=validate_import_inputs,
            inputs=[notes_session_id, notes_input],
            outputs=[ready_indicator],
        )

        notes_import_btn.click(
            fn=_begin_import_placeholder,
            outputs=[notes_output],
            queue=True,
        ).then(
            fn=import_session_notes,
            inputs=[
                notes_session_id,
                notes_campaign,
                notes_input,
                notes_extract_knowledge,
                notes_generate_narrative,
            ],
            outputs=[notes_output],
            queue=True,
        )

        notes_clear_btn.click(
            fn=clear_import_fields,
            outputs=[
                notes_session_id,
                notes_campaign,
                notes_input,
                notes_file_upload,
                ready_indicator,
                notes_output,
            ],
        )
