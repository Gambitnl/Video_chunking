from __future__ import annotations

from typing import Callable, Dict

import gradio as gr

from src.config import Config
from src.party_config import PartyConfigManager


def create_import_notes_tab(refresh_campaign_names: Callable[[], Dict[str, str]]) -> None:
    with gr.Tab("Import Session Notes"):
        gr.Markdown("""
        ### [IMPORT] Import Session Notes

        **Backfill your campaign with sessions you didn't record!**

        This tool automatically extracts:
        - [QUEST] **Quests** - Started, progressed, or completed
        - [NPC] **NPCs** - Characters the party met
        - [LOCATION] **Locations** - Places visited
        - [ITEM] **Items** - Important objects found
        - [HOOK] **Plot Hooks** - Mysteries and future threads

        Perfect for importing sessions 1-5 before you started recording!
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

        validation_status = gr.Markdown(value="", visible=False)

        with gr.Row():
            with gr.Column(scale=2):
                notes_session_id = gr.Textbox(
                    label="[1] Session ID (Required)",
                    placeholder="e.g., Session_01, Session_02, Direlambs_Session_01",
                    info="[TIP] Tip: Use a consistent naming scheme like 'Session_01', 'Session_02', etc."
                )
                notes_campaign_choices = ["default"] + list(refresh_campaign_names().keys())
                notes_campaign = gr.Dropdown(
                    choices=notes_campaign_choices,
                    value="default",
                    label="[2] Campaign (Required)",
                    info="Select which campaign these notes belong to. 'default' works if you only have one campaign."
                )
            with gr.Column(scale=1):
                gr.Markdown("### Options:")
                notes_extract_knowledge = gr.Checkbox(
                    label="[EXTRACT] Extract Knowledge (Recommended)",
                    value=True,
                    info="AI will automatically find: NPCs, quests, locations, items, plot hooks"
                )
                notes_generate_narrative = gr.Checkbox(
                    label="[NARRATIVE] Generate Narrative Summary",
                    value=False,
                    info="Creates a story-style summary (takes extra time)"
                )

        notes_input = gr.Textbox(
            label="[3] Session Notes (Required)",
            placeholder="Paste your session notes here...\n\nExample:\n'Session 1 - The party met at the tavern. They spoke with Guard Captain Thorne who gave them a quest to find Marcus, a missing merchant. They traveled to the Waterdeep Road and found...\n\nClick 'Quick Start Guide' above for more examples!",
            lines=15,
            max_lines=30
        )

        notes_file_upload = gr.File(
            label="[UPLOAD] Or Upload Notes File (.txt or .md)",
            file_types=[".txt", ".md"],
            type="filepath"
        )

        ready_indicator = gr.Markdown(value="", visible=True)

        with gr.Row():
            notes_import_btn = gr.Button(
                "[IMPORT] Import Session Notes",
                variant="primary",
                size="lg",
                scale=3
            )
            notes_clear_btn = gr.Button(
                "[CLEAR] Clear All Fields",
                variant="secondary",
                scale=1
            )

        notes_output = gr.Markdown(label="Import Results")

        def load_notes_from_file(file_path):
            if not file_path:
                return ""
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    return handle.read()
            except Exception as exc:
                return f"Error reading file: {exc}"

        def validate_import_inputs(session_id, notes_text):
            has_session_id = session_id and session_id.strip()
            has_notes = notes_text and notes_text.strip()

            if has_session_id and has_notes:
                return "[SUCCESS] **Ready to import!** All required fields are filled. Click the button below to start."
            if has_session_id and not has_notes:
                return "[ERROR] **Missing**: Session notes are required. Paste your notes or upload a file."
            if not has_session_id and has_notes:
                return "[ERROR] **Missing**: Session ID is required. Enter an ID like 'Session_01'."
            return "[INFO] Fill in the required fields above to get started."

        def clear_import_fields():
            return "", "default", "", None, ""

        def import_session_notes(session_id, campaign_id, notes_text, extract_knowledge, generate_narrative):
            if not session_id or not session_id.strip():
                return "[ERROR] **Error**: Please provide a Session ID"

            if not notes_text or not notes_text.strip():
                return "[ERROR] **Error**: Please provide session notes (paste text or upload a file)"

            session_id_clean = session_id.strip()
            results = f"# Import Results: {session_id_clean}\n\n"
            results += f"**Campaign**: {campaign_id}\n\n"
            results += "---\n\n"

            if extract_knowledge:
                try:
                    from src.knowledge_base import KnowledgeExtractor, CampaignKnowledgeBase

                    results += "## [EXTRACT] Knowledge Extraction\n\n"
                    results += "Analyzing your notes with LLM...\n\n"

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

                    results += f"[SUCCESS] **Extracted {total} entities:**\n\n"
                    if counts["quests"] > 0:
                        results += f"- [QUEST] **Quests**: {counts['quests']}\n"
                        for quest in extracted["quests"]:
                            results += f"  - {quest.title} ({quest.status})\n"
                        results += "\n"

                    if counts["npcs"] > 0:
                        results += f"- [NPC] **NPCs**: {counts['npcs']}\n"
                        for npc in extracted["npcs"]:
                            results += f"  - {npc.name} ({npc.role or 'unknown'})\n"
                        results += "\n"

                    if counts["plot_hooks"] > 0:
                        results += f"- [HOOK] **Plot Hooks**: {counts['plot_hooks']}\n"
                        for hook in extracted["plot_hooks"]:
                            results += f"  - {hook.summary}\n"
                        results += "\n"

                    if counts["locations"] > 0:
                        results += f"- [LOCATION] **Locations**: {counts['locations']}\n"
                        for loc in extracted["locations"]:
                            results += f"  - {loc.name} ({loc.type or 'unknown'})\n"
                        results += "\n"

                    if counts["items"] > 0:
                        results += f"- [ITEM] **Items**: {counts['items']}\n"
                        for item in extracted["items"]:
                            results += f"  - {item.name}\n"
                        results += "\n"

                    results += f"\n**Knowledge saved to**: `{kb.knowledge_file}`\n\n"
                    results += "[TIP] *Visit the Campaign Library tab to view all extracted knowledge!*"
                    results += "\n\n"

                except Exception as exc:
                    import traceback

                    results += f"[ERROR] **Knowledge extraction failed**: {exc}\n\n"
                    results += f"```\n{traceback.format_exc()}\n```\n\n"

            if generate_narrative:
                try:
                    import ollama

                    results += "---\n\n## [NARRATIVE] Narrative Generation\n\n"
                    results += "Generating narrative summary...\n\n"

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

                    results += f"**Narrative saved to**: `{narrative_file}`\n\n"

                except Exception as exc:
                    results += f"[ERROR] **Narrative generation failed**: {exc}\n\n"

            results += "---\n\n"
            results += "## [SUCCESS] Import Complete!\n\n"
            if extract_knowledge:
                results += "- Check the **Campaign Library** tab to view extracted knowledge\n"
            if generate_narrative:
                results += "- Narrative saved to `output/imported_narratives/`\n"

            return results

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
            fn=import_session_notes,
            inputs=[
                notes_session_id,
                notes_campaign,
                notes_input,
                notes_extract_knowledge,
                notes_generate_narrative,
            ],
            outputs=[notes_output],
        )

        notes_clear_btn.click(
            fn=clear_import_fields,
            outputs=[notes_session_id, notes_campaign, notes_input, notes_file_upload, notes_output],
        )
