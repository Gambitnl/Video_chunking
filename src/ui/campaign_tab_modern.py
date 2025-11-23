"""Modern Campaign tab - campaign overview and knowledge summary."""
from typing import Dict, Optional

import gradio as gr

from src.ui.helpers import AccessibilityAttributes, StatusMessages
from src.ui.constants import StatusIndicators as SI


def create_campaign_tab_modern(blocks: gr.Blocks) -> Dict[str, gr.components.Component]:
    """Create the Campaign tab and return references to key components."""

    def _a11y(component: gr.components.Component, *, label: str, described_by: str | None = None, role: str | None = None, live: str | None = None, elem_id: str | None = None):
        return AccessibilityAttributes.apply(
            component,
            label=label,
            described_by=described_by,
            role=role,
            live=live,
            elem_id=elem_id,
        )

    with gr.Tab("Campaign"):
        gr.Markdown(
            """
            # Campaign Management

            Monitor campaign health, knowledge, and processed sessions.
            """
        )

        # Campaign selector and controls
        with gr.Row():
            campaign_selector = _a11y(
                gr.Dropdown(
                    label="Campaign",
                    choices=[],
                    value=None,
                    info="Select a campaign to view its details (updates from Campaign Launcher)",
                    scale=3,
                    elem_id="campaign-selector",
                ),
                label="Campaign selector",
            )
            refresh_btn = _a11y(
                gr.Button(
                    SI.ACTION_REFRESH,
                    variant="secondary",
                    size="sm",
                    scale=0,
                    elem_id="campaign-refresh",
                ),
                label="Refresh campaigns",
                role="button",
            )

        # Campaign Management Section
        with gr.Accordion("Manage Selected Campaign", open=False, elem_id="campaign-manage-accordion"):
            gr.Markdown("### Rename or Delete Campaign")
            with gr.Row():
                new_campaign_name_input = _a11y(
                    gr.Textbox(
                        label="New Campaign Name",
                        placeholder="Enter new name and click rename...",
                        scale=3,
                        elem_id="campaign-rename-input",
                    ),
                    label="New campaign name",
                )
                rename_campaign_btn = _a11y(
                    gr.Button(
                        "Rename Campaign",
                        variant="primary",
                        scale=1,
                        elem_id="campaign-rename-btn",
                    ),
                    label="Rename campaign",
                )
            with gr.Row():
                delete_campaign_btn = _a11y(
                    gr.Button(
                        "Delete Selected Campaign",
                        variant="stop",
                        elem_id="campaign-delete-btn",
                    ),
                    label="Delete selected campaign",
                )
            manage_status_md = _a11y(
                gr.Markdown(value="", elem_id="campaign-manage-status"),
                label="Campaign management status",
                role="status",
                live="polite",
            )

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
