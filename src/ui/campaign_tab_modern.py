"""Modern Campaign tab - campaign overview and knowledge summary."""
from typing import Dict, Optional

import gradio as gr

from src.ui.helpers import StatusMessages
from src.ui.constants import StatusIndicators as SI


def create_campaign_tab_modern(blocks: gr.Blocks) -> Dict[str, gr.components.Component]:
    """Create the Campaign tab and return references to key components."""

    with gr.Tab("Campaign"):
        gr.Markdown(
            """
            # Campaign Management

            Monitor campaign health, knowledge, and processed sessions.
            """
        )

        # Campaign selector and controls
        with gr.Row():
            campaign_selector = gr.Dropdown(
                label="Campaign",
                choices=[],
                value=None,
                info="Select a campaign to view its details (updates from Campaign Launcher)",
                scale=3
            )
            refresh_btn = gr.Button(
                SI.ACTION_REFRESH,
                variant="secondary",
                size="sm",
                scale=0
            )

        # Campaign Management Section
        with gr.Accordion("Manage Selected Campaign", open=False):
            with gr.Row():
                new_campaign_name_input = gr.Textbox(
                    label="New Campaign Name",
                    placeholder="Enter new name and click rename...",
                    scale=3
                )
                rename_campaign_btn = gr.Button(
                    "Rename Campaign",
                    variant="primary",
                    scale=1
                )
            with gr.Row():
                delete_campaign_btn = gr.Button(
                    "Delete Selected Campaign",
                    variant="stop",
                )
            manage_status_md = gr.Markdown(value="")

        # Campaign Overview Section
        gr.Markdown("## Campaign Overview")
        overview_md = gr.HTML(
            value="""
            <div class="empty-state-card">
                <div class="empty-state-icon">🎲</div>
                <h3>No Campaign Selected</h3>
                <p>Get started by creating your first campaign or loading an existing one to see campaign metrics, session history, and progress tracking.</p>
                <div class="empty-state-actions">
                    <span class="info-badge">→ Use Campaign Launcher tab to get started</span>
                </div>
            </div>
            """
        )

        # Knowledge Base Section
        gr.Markdown("## Knowledge Base")
        knowledge_md = gr.HTML(
            value="""
            <div class="empty-state-card">
                <div class="empty-state-icon">📚</div>
                <h3>Knowledge Base Empty</h3>
                <p>Your campaign's knowledge base tracks NPCs, locations, quests, items, and factions across all sessions.</p>
                <div class="empty-state-actions">
                    <span class="info-badge">💡 Process sessions to build knowledge</span>
                    <span class="info-badge">🔍 View extracted entities here</span>
                </div>
            </div>
            """
        )

        # Session Library Section
        gr.Markdown("## Session Library")
        session_library_md = gr.HTML(
            value="""
            <div class="empty-state-card">
                <div class="empty-state-icon">🎬</div>
                <h3>No Sessions Yet</h3>
                <p>Process your first D&D session recording to build your campaign library. Sessions appear here with transcripts, timestamps, and speaker identification.</p>
                <div class="empty-state-actions">
                    <span class="info-badge">🎙️ Upload audio in Process Session tab</span>
                    <span class="info-badge">⚙️ Configure speakers and settings</span>
                    <span class="info-badge">🚀 Start processing</span>
                </div>
            </div>
            """
        )

    return {
        "overview": overview_md,
        "knowledge": knowledge_md,
        "session_library": session_library_md,
        "campaign_selector": campaign_selector,
        "refresh_btn": refresh_btn,
        "new_campaign_name_input": new_campaign_name_input,
        "rename_campaign_btn": rename_campaign_btn,
        "delete_campaign_btn": delete_campaign_btn,
        "manage_status": manage_status_md,
    }
