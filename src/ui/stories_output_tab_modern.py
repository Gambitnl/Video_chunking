"""Modern Stories & Output tab - view and export content."""
from pathlib import Path
from typing import List

import gradio as gr

from src.ui.helpers import StatusMessages


def create_stories_output_tab_modern(blocks: gr.Blocks) -> None:
    """Create a modern Stories & Output tab.

    Consolidates:
    - Story Notebooks
    - Document Viewer
    - Social Insights
    - Export options
    """

    with gr.Tab("📖 Stories & Output"):
        gr.Markdown("""
        # View Your Content

        Browse generated stories, transcripts, and session insights.
        """)

        # Content Type and Session Selectors
        with gr.Row():
            content_type = gr.Dropdown(
                label="Content Type",
                choices=[
                    "Story Notebooks",
                    "Full Transcripts",
                    "IC-Only Transcripts",
                    "Social Insights",
                ],
                value="Story Notebooks",
            )

            session_selector = gr.Dropdown(
                label="Session",
                choices=[
                    "Session 24 (Oct 31, 2024)",
                    "Session 23 (Oct 24, 2024)",
                    "Session 22 (Oct 17, 2024)",
                ],
                value="Session 24 (Oct 31, 2024)",
            )

        # Content Viewer
        with gr.Group():
            content_viewer = gr.HTML("""
            <div style="background: white; border-radius: 12px; padding: 2rem; border: 1px solid #e5e7eb; min-height: 500px;">
                <div class="markdown-content">
                    <h1>Session 24: The Dragon's Challenge</h1>

                    <p style="color: #6b7280; font-style: italic; margin-bottom: 2rem;">
                        October 31, 2024 • 3h 45m • Generated Story
                    </p>

                    <h2>The Journey Begins</h2>

                    <p>
                        The morning sun cast long shadows across the courtyard of Willowdale as our heroes prepared
                        for their most dangerous quest yet. Thorin Ironforge checked his battle axe one final time,
                        the weight familiar and comforting in his calloused hands.
                    </p>

                    <blockquote style="border-left: 4px solid #6366f1; padding-left: 1rem; margin: 1.5rem 0; color: #4b5563; font-style: italic;">
                        "By my beard, we will not fall today!" Thorin's voice rang out across the courtyard,
                        rallying his companions for the trials ahead.
                    </blockquote>

                    <p>
                        Elara Moonwhisper stood apart from the group, her fingers tracing arcane symbols in the air
                        as she prepared her spells. The mysterious elf mage had been quieter than usual, her thoughts
                        clearly on the powerful dragon they would soon face.
                    </p>

                    <h2>Into the Dragon's Lair</h2>

                    <p>
                        The path to Dragon's Peak wound treacherously through the mountains, each step taking them
                        higher into the clouds. Zephyr Swift scouted ahead, his halfling eyes sharp for any signs
                        of danger lurking in the rocky crags.
                    </p>

                    <p>
                        As they rounded a bend, the massive cave entrance loomed before them, steam rising from
                        the darkness within. This was it—the lair of Drakon the Red.
                    </p>

                    <blockquote style="border-left: 4px solid #8b5cf6; padding-left: 1rem; margin: 1.5rem 0; color: #4b5563; font-style: italic;">
                        "The weave guides my hand," Elara whispered, channeling magical energy as they approached
                        the cave entrance.
                    </blockquote>

                    <h2>The Final Confrontation</h2>

                    <p>
                        The battle was fierce and chaotic. Thorin charged forward with his axe raised high, while
                        Elara unleashed devastating spells from behind. Zephyr darted in and out of the shadows,
                        striking at vulnerable points. Through it all, Grimm Stonebeard kept his companions alive
                        with divine healing magic.
                    </p>

                    <p>
                        When the dust settled and the dragon lay defeated, the party stood victorious. They had
                        recovered the Crown of the Ancients and saved Willowdale from certain destruction. But
                        more importantly, they had grown closer as a team, their bonds forged stronger through
                        shared adversity.
                    </p>

                    <hr style="margin: 2rem 0; border: none; border-top: 1px solid #e5e7eb;">

                    <p style="color: #6b7280; font-size: 0.875rem; text-align: center;">
                        Story generated from session transcript • Total segments: 342 • IC segments: 187
                    </p>
                </div>
            </div>
            """)

        # Export Options
        with gr.Group():
            gr.Markdown("### Export Options")

            with gr.Row():
                export_pdf_btn = gr.Button("📄 Export PDF", variant="secondary")
                export_txt_btn = gr.Button("📝 Export TXT", variant="secondary")
                export_json_btn = gr.Button("💾 Export JSON", variant="secondary")
                export_audio_btn = gr.Button("🔊 Export Audio Clips", variant="secondary")

            export_status = gr.Markdown(visible=False)

        # Content type change handler
        def update_content(content_type_val, session_val):
            """Update displayed content based on selection."""
            if content_type_val == "Story Notebooks":
                return gr.update(value="""
                <div style="background: white; border-radius: 12px; padding: 2rem; border: 1px solid #e5e7eb; min-height: 500px;">
                    <div class="markdown-content">
                        <h1>Session 24: The Dragon's Challenge</h1>
                        <p style="color: #6b7280; font-style: italic; margin-bottom: 2rem;">
                            October 31, 2024 • 3h 45m • Generated Story
                        </p>
                        <p>The morning sun cast long shadows across the courtyard...</p>
                    </div>
                </div>
                """)

            elif content_type_val == "Full Transcripts":
                return gr.update(value="""
                <div style="background: white; border-radius: 12px; padding: 2rem; border: 1px solid #e5e7eb; min-height: 500px; font-family: monospace; font-size: 0.875rem;">
                    <h3 style="margin: 0 0 1.5rem 0; color: #111827;">Full Transcript - Session 24</h3>
                    <div style="line-height: 1.8;">
                        <div style="margin-bottom: 1rem;">
                            <span style="color: #6b7280;">[00:00:12]</span>
                            <span style="color: #6366f1; font-weight: 600;">DM:</span>
                            <span style="color: #374151;">Welcome everyone! Let's pick up where we left off...</span>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <span style="color: #6b7280;">[00:01:23]</span>
                            <span style="color: #10b981; font-weight: 600;">Thorin:</span>
                            <span style="color: #374151;">I check my equipment before we head out.</span>
                        </div>
                        <div style="margin-bottom: 1rem; background: #fef3c7; padding: 0.5rem; border-radius: 4px;">
                            <span style="color: #6b7280;">[00:02:45]</span>
                            <span style="color: #92400e; font-weight: 600;">Sarah (OOC):</span>
                            <span style="color: #92400e;">Wait, do I still have that healing potion from last session?</span>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <span style="color: #6b7280;">[00:03:12]</span>
                            <span style="color: #6366f1; font-weight: 600;">DM:</span>
                            <span style="color: #374151;">Yes, you have two healing potions remaining.</span>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <span style="color: #6b7280;">[00:04:30]</span>
                            <span style="color: #8b5cf6; font-weight: 600;">Elara:</span>
                            <span style="color: #374151;">I prepare my spell slots for the day.</span>
                        </div>
                    </div>
                </div>
                """)

            elif content_type_val == "IC-Only Transcripts":
                return gr.update(value="""
                <div style="background: white; border-radius: 12px; padding: 2rem; border: 1px solid #e5e7eb; min-height: 500px; font-family: monospace; font-size: 0.875rem;">
                    <h3 style="margin: 0 0 1.5rem 0; color: #111827;">IC-Only Transcript - Session 24</h3>
                    <p style="margin-bottom: 1.5rem; color: #6b7280; font-size: 0.875rem;">
                        All out-of-character dialogue removed • 187 IC segments
                    </p>
                    <div style="line-height: 1.8;">
                        <div style="margin-bottom: 1rem;">
                            <span style="color: #6b7280;">[00:00:12]</span>
                            <span style="color: #6366f1; font-weight: 600;">DM:</span>
                            <span style="color: #374151;">Welcome everyone! Let's pick up where we left off...</span>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <span style="color: #6b7280;">[00:01:23]</span>
                            <span style="color: #10b981; font-weight: 600;">Thorin:</span>
                            <span style="color: #374151;">I check my equipment before we head out.</span>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <span style="color: #6b7280;">[00:04:30]</span>
                            <span style="color: #8b5cf6; font-weight: 600;">Elara:</span>
                            <span style="color: #374151;">I prepare my spell slots for the day.</span>
                        </div>
                        <div style="margin-bottom: 1rem;">
                            <span style="color: #6b7280;">[00:06:15]</span>
                            <span style="color: #10b981; font-weight: 600;">Thorin:</span>
                            <span style="color: #374151;">"By my beard, we will not fall today!"</span>
                        </div>
                    </div>
                </div>
                """)

            else:  # Social Insights
                return gr.update(value="""
                <div style="background: white; border-radius: 12px; padding: 2rem; border: 1px solid #e5e7eb; min-height: 500px;">
                    <div class="markdown-content">
                        <h1>Social Insights - Session 24</h1>

                        <p style="color: #6b7280; font-style: italic; margin-bottom: 2rem;">
                            Out-of-character analysis and session dynamics
                        </p>

                        <h2>Participation Statistics</h2>

                        <div style="display: grid; gap: 1rem; margin-bottom: 2rem;">
                            <div style="background: #f9fafb; padding: 1rem; border-radius: 8px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                    <span style="font-weight: 600;">John (Thorin)</span>
                                    <span style="color: #6366f1; font-weight: 600;">28%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 28%;"></div>
                                </div>
                            </div>

                            <div style="background: #f9fafb; padding: 1rem; border-radius: 8px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                    <span style="font-weight: 600;">Sarah (Elara)</span>
                                    <span style="color: #8b5cf6; font-weight: 600;">25%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 25%; background: linear-gradient(90deg, #8b5cf6 0%, #7c3aed 100%);"></div>
                                </div>
                            </div>

                            <div style="background: #f9fafb; padding: 1rem; border-radius: 8px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                                    <span style="font-weight: 600;">DM</span>
                                    <span style="color: #06b6d4; font-weight: 600;">35%</span>
                                </div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: 35%; background: linear-gradient(90deg, #06b6d4 0%, #0891b2 100%);"></div>
                                </div>
                            </div>
                        </div>

                        <h2>Session Highlights</h2>

                        <ul style="line-height: 1.75;">
                            <li>High energy throughout - minimal OOC interruptions</li>
                            <li>Great roleplay moment: Thorin's rallying speech (01:24:10)</li>
                            <li>Combat encounter ran smoothly - 45 minutes</li>
                            <li>Players engaged well with NPC interactions</li>
                            <li>Some rules clarification needed for spell casting</li>
                        </ul>

                        <h2>Sentiment Analysis</h2>

                        <div style="background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 1rem; margin: 1rem 0;">
                            <p style="margin: 0; color: #1e40af;">
                                <strong>Overall Mood:</strong> Positive and Engaged
                            </p>
                        </div>

                        <p>
                            Players were highly engaged throughout the session, with particularly strong
                            moments during the dragon encounter. The party worked well together, both
                            in-character and out-of-character.
                        </p>
                    </div>
                </div>
                """)

        content_type.change(
            fn=update_content,
            inputs=[content_type, session_selector],
            outputs=[content_viewer]
        )

        session_selector.change(
            fn=update_content,
            inputs=[content_type, session_selector],
            outputs=[content_viewer]
        )

        # Export handlers
        def export_content(format_type):
            """Export content (placeholder)."""
            return gr.update(
                visible=True,
                value=StatusMessages.success(
                    f"Exported as {format_type}!",
                    f"File saved to output directory."
                )
            )

        export_pdf_btn.click(
            fn=lambda: export_content("PDF"),
            outputs=[export_status]
        )

        export_txt_btn.click(
            fn=lambda: export_content("TXT"),
            outputs=[export_status]
        )

        export_json_btn.click(
            fn=lambda: export_content("JSON"),
            outputs=[export_status]
        )

        export_audio_btn.click(
            fn=lambda: export_content("Audio Clips"),
            outputs=[export_status]
        )
