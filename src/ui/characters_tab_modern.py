"""Modern Characters tab - profiles and extraction tools."""
from pathlib import Path
from typing import List

import gradio as gr

from src.ui.helpers import StatusMessages


def create_characters_tab_modern(blocks: gr.Blocks, available_parties: List[str]) -> None:
    """Create a modern Characters tab with card-based layout.

    Consolidates:
    - Character Profiles (viewing/editing)
    - Auto-extraction feature
    - Import/Export
    """

    with gr.Tab("👥 Characters"):
        gr.Markdown("""
        # Character Profiles

        Manage character information and automatically extract updates from session transcripts.
        """)

        # Character Browser
        with gr.Group():
            with gr.Row():
                gr.Markdown("### Your Party")
                with gr.Row():
                    add_char_btn = gr.Button("+ Add Character", variant="secondary", scale=0)
                    extract_btn = gr.Button("Extract from Session", variant="primary", scale=0)
                    import_btn = gr.Button("Import", variant="secondary", scale=0)

            # Character cards
            character_grid = gr.HTML("""
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; margin-top: 1rem;">
                <!-- Thorin Card -->
                <div style="background: white; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.boxShadow='0 4px 6px -1px rgb(0 0 0 / 0.1)'" onmouseout="this.style.boxShadow='none'">
                    <div style="height: 120px; background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); display: flex; align-items: center; justify-content: center;">
                        <div style="width: 80px; height: 80px; border-radius: 50%; background: rgba(255, 255, 255, 0.2); display: flex; align-items: center; justify-content: center; color: white; font-size: 2.5rem; font-weight: 700; border: 3px solid rgba(255, 255, 255, 0.3);">
                            T
                        </div>
                    </div>
                    <div style="padding: 1.25rem;">
                        <h3 style="margin: 0 0 0.5rem 0; color: #111827; font-size: 1.25rem;">Thorin Ironforge</h3>
                        <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                            <span class="badge badge-info">Fighter</span>
                            <span class="badge badge-success">Level 5</span>
                        </div>
                        <p style="margin: 0 0 1rem 0; color: #6b7280; font-size: 0.875rem; line-height: 1.5;">Brave dwarf warrior with a heart of gold and an axe to match.</p>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1rem 0; border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; margin-bottom: 1rem;">
                            <div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #6366f1;">12</div>
                                <div style="color: #6b7280; font-size: 0.75rem;">Sessions</div>
                            </div>
                            <div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #06b6d4;">28</div>
                                <div style="color: #6b7280; font-size: 0.75rem;">Actions</div>
                            </div>
                        </div>
                        <button style="width: 100%; padding: 0.625rem; background: #6366f1; color: white; border: none; border-radius: 8px; font-weight: 500; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#4f46e5'" onmouseout="this.style.background='#6366f1'">
                            View Profile
                        </button>
                    </div>
                </div>

                <!-- Elara Card -->
                <div style="background: white; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.boxShadow='0 4px 6px -1px rgb(0 0 0 / 0.1)'" onmouseout="this.style.boxShadow='none'">
                    <div style="height: 120px; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); display: flex; align-items: center; justify-content: center;">
                        <div style="width: 80px; height: 80px; border-radius: 50%; background: rgba(255, 255, 255, 0.2); display: flex; align-items: center; justify-content: center; color: white; font-size: 2.5rem; font-weight: 700; border: 3px solid rgba(255, 255, 255, 0.3);">
                            E
                        </div>
                    </div>
                    <div style="padding: 1.25rem;">
                        <h3 style="margin: 0 0 0.5rem 0; color: #111827; font-size: 1.25rem;">Elara Moonwhisper</h3>
                        <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                            <span class="badge badge-info">Wizard</span>
                            <span class="badge badge-success">Level 5</span>
                        </div>
                        <p style="margin: 0 0 1rem 0; color: #6b7280; font-size: 0.875rem; line-height: 1.5;">Mysterious elf mage wielding ancient arcane knowledge.</p>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1rem 0; border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; margin-bottom: 1rem;">
                            <div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #6366f1;">12</div>
                                <div style="color: #6b7280; font-size: 0.75rem;">Sessions</div>
                            </div>
                            <div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #06b6d4;">34</div>
                                <div style="color: #6b7280; font-size: 0.75rem;">Spells Cast</div>
                            </div>
                        </div>
                        <button style="width: 100%; padding: 0.625rem; background: #6366f1; color: white; border: none; border-radius: 8px; font-weight: 500; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#4f46e5'" onmouseout="this.style.background='#6366f1'">
                            View Profile
                        </button>
                    </div>
                </div>

                <!-- Zephyr Card -->
                <div style="background: white; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.boxShadow='0 4px 6px -1px rgb(0 0 0 / 0.1)'" onmouseout="this.style.boxShadow='none'">
                    <div style="height: 120px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); display: flex; align-items: center; justify-content: center;">
                        <div style="width: 80px; height: 80px; border-radius: 50%; background: rgba(255, 255, 255, 0.2); display: flex; align-items: center; justify-content: center; color: white; font-size: 2.5rem; font-weight: 700; border: 3px solid rgba(255, 255, 255, 0.3);">
                            Z
                        </div>
                    </div>
                    <div style="padding: 1.25rem;">
                        <h3 style="margin: 0 0 0.5rem 0; color: #111827; font-size: 1.25rem;">Zephyr Swift</h3>
                        <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                            <span class="badge badge-info">Rogue</span>
                            <span class="badge badge-success">Level 5</span>
                        </div>
                        <p style="margin: 0 0 1rem 0; color: #6b7280; font-size: 0.875rem; line-height: 1.5;">Nimble halfling thief with a silver tongue and quick fingers.</p>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1rem 0; border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; margin-bottom: 1rem;">
                            <div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #6366f1;">12</div>
                                <div style="color: #6b7280; font-size: 0.75rem;">Sessions</div>
                            </div>
                            <div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #06b6d4;">42</div>
                                <div style="color: #6b7280; font-size: 0.75rem;">Sneak Attacks</div>
                            </div>
                        </div>
                        <button style="width: 100%; padding: 0.625rem; background: #6366f1; color: white; border: none; border-radius: 8px; font-weight: 500; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#4f46e5'" onmouseout="this.style.background='#6366f1'">
                            View Profile
                        </button>
                    </div>
                </div>

                <!-- Grimm Card -->
                <div style="background: white; border-radius: 12px; border: 1px solid #e5e7eb; overflow: hidden; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.boxShadow='0 4px 6px -1px rgb(0 0 0 / 0.1)'" onmouseout="this.style.boxShadow='none'">
                    <div style="height: 120px; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); display: flex; align-items: center; justify-content: center;">
                        <div style="width: 80px; height: 80px; border-radius: 50%; background: rgba(255, 255, 255, 0.2); display: flex; align-items: center; justify-content: center; color: white; font-size: 2.5rem; font-weight: 700; border: 3px solid rgba(255, 255, 255, 0.3);">
                            G
                        </div>
                    </div>
                    <div style="padding: 1.25rem;">
                        <h3 style="margin: 0 0 0.5rem 0; color: #111827; font-size: 1.25rem;">Grimm Stonebeard</h3>
                        <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                            <span class="badge badge-info">Cleric</span>
                            <span class="badge badge-success">Level 5</span>
                        </div>
                        <p style="margin: 0 0 1rem 0; color: #6b7280; font-size: 0.875rem; line-height: 1.5;">Stalwart dwarf priest devoted to protecting his allies.</p>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1rem 0; border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; margin-bottom: 1rem;">
                            <div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #6366f1;">12</div>
                                <div style="color: #6b7280; font-size: 0.75rem;">Sessions</div>
                            </div>
                            <div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #06b6d4;">156</div>
                                <div style="color: #6b7280; font-size: 0.75rem;">HP Healed</div>
                            </div>
                        </div>
                        <button style="width: 100%; padding: 0.625rem; background: #6366f1; color: white; border: none; border-radius: 8px; font-weight: 500; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.background='#4f46e5'" onmouseout="this.style.background='#6366f1'">
                            View Profile
                        </button>
                    </div>
                </div>
            </div>
            """)

        # Extraction Tool (collapsible)
        with gr.Accordion("Auto-Extraction Tool", open=False):
            gr.Markdown("""
            ### Extract Character Updates from Session Transcripts

            Automatically identify character actions, quotes, relationships, and development
            from your IC-only transcript files.
            """)

            with gr.Row():
                with gr.Column():
                    extract_transcript = gr.File(
                        label="IC-Only Transcript",
                        file_types=[".txt"],
                    )

                with gr.Column():
                    extract_party = gr.Dropdown(
                        label="Party",
                        choices=[p for p in available_parties if p != "Manual Entry"],
                        value="default" if "default" in available_parties else None,
                    )

                    extract_session_id = gr.Textbox(
                        label="Session ID",
                        placeholder="session_001",
                    )

            extract_run_btn = gr.Button(
                "Run Extraction",
                variant="primary",
                size="lg",
            )

            extract_status = gr.Markdown(
                value=StatusMessages.info(
                    "Ready",
                    "Upload an IC-only transcript to begin extraction."
                )
            )

            # Results preview (hidden initially)
            with gr.Group(visible=False) as extract_results:
                gr.Markdown("### Extracted Updates Preview")

                results_preview = gr.JSON(
                    label="Extracted Data",
                )

                with gr.Row():
                    approve_btn = gr.Button("Apply to Profiles", variant="primary")
                    discard_btn = gr.Button("Discard", variant="secondary")

            # Event handlers
            def run_extraction(transcript_file, party_id, session_id):
                """Run profile extraction (placeholder)."""
                if not transcript_file:
                    return (
                        StatusMessages.error("Missing File", "Please upload a transcript file."),
                        gr.update(visible=False),
                        None
                    )

                if not party_id or not session_id:
                    return (
                        StatusMessages.error("Missing Info", "Please select a party and provide a session ID."),
                        gr.update(visible=False),
                        None
                    )

                # TODO: Connect to actual extraction logic
                # from src.character_profile_extractor import CharacterProfileExtractor

                sample_results = {
                    "Thorin": {
                        "notable_actions": [
                            "Charged into battle against goblin raiders [01:23:45]",
                            "Defended the merchant caravan from bandits [02:15:22]"
                        ],
                        "memorable_quotes": [
                            '"By my beard, we will not fall today!" - rallying the party [01:24:10]'
                        ],
                        "character_development": [
                            "Showed compassion by sparing the goblin child [01:45:30]"
                        ]
                    },
                    "Elara": {
                        "notable_actions": [
                            "Cast Fireball to clear the cave entrance [00:45:12]"
                        ],
                        "memorable_quotes": [
                            '"The weave guides my hand" - before casting spell [00:45:00]'
                        ]
                    }
                }

                return (
                    StatusMessages.success(
                        "Extraction Complete!",
                        f"Found updates for {len(sample_results)} characters."
                    ),
                    gr.update(visible=True),
                    sample_results
                )

            extract_run_btn.click(
                fn=run_extraction,
                inputs=[extract_transcript, extract_party, extract_session_id],
                outputs=[extract_status, extract_results, results_preview]
            )
