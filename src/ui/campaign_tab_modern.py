"""Modern Campaign tab - consolidates dashboard, library, and party management."""
from pathlib import Path
from typing import List

import gradio as gr

from src.ui.helpers import StatusMessages


def create_campaign_tab_modern(blocks: gr.Blocks) -> None:
    """Create a modern, consolidated Campaign tab.

    Consolidates:
    - Campaign Dashboard
    - Campaign Library
    - Import Notes
    - Party Management
    """

    with gr.Tab("📚 Campaign"):
        gr.Markdown("""
        # Campaign Management

        Organize your campaign knowledge, sessions, and party information in one place.
        """)

        # Dashboard Overview
        with gr.Group():
            gr.Markdown("### Campaign Health")

            with gr.Row():
                with gr.Column(scale=1):
                    campaign_health = gr.HTML("""
                    <div style="padding: 1.5rem; background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%); border-radius: 12px;">
                        <h3 style="margin: 0 0 1rem 0; color: #374151;">Quick Stats</h3>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                            <div>
                                <div style="font-size: 2rem; font-weight: 700; color: #6366f1;">24</div>
                                <div style="color: #6b7280; font-size: 0.875rem;">Sessions</div>
                            </div>
                            <div>
                                <div style="font-size: 2rem; font-weight: 700; color: #06b6d4;">8</div>
                                <div style="color: #6b7280; font-size: 0.875rem;">Active Quests</div>
                            </div>
                            <div>
                                <div style="font-size: 2rem; font-weight: 700; color: #10b981;">42</div>
                                <div style="color: #6b7280; font-size: 0.875rem;">NPCs</div>
                            </div>
                            <div>
                                <div style="font-size: 2rem; font-weight: 700; color: #f59e0b;">15</div>
                                <div style="color: #6b7280; font-size: 0.875rem;">Locations</div>
                            </div>
                        </div>
                    </div>
                    """)

                with gr.Column(scale=1):
                    gr.Markdown("#### Quick Actions")
                    with gr.Row():
                        new_session_btn = gr.Button("+ New Session", variant="primary")
                        new_quest_btn = gr.Button("+ Quest", variant="secondary")
                    with gr.Row():
                        new_npc_btn = gr.Button("+ NPC", variant="secondary")
                        new_location_btn = gr.Button("+ Location", variant="secondary")

        # Knowledge Base
        with gr.Group():
            gr.Markdown("### Knowledge Base")

            with gr.Tabs():
                with gr.Tab("Quests"):
                    quest_search = gr.Textbox(
                        placeholder="Search quests...",
                        show_label=False,
                    )
                    quest_list = gr.HTML("""
                    <div style="display: grid; gap: 1rem; margin-top: 1rem;">
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <h4 style="margin: 0 0 0.5rem 0; color: #111827;">The Missing Artifact</h4>
                                    <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">Retrieve the stolen crown from the dragon's lair</p>
                                </div>
                                <span class="badge badge-warning">In Progress</span>
                            </div>
                        </div>
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <h4 style="margin: 0 0 0.5rem 0; color: #111827;">Save the Village</h4>
                                    <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">Defend Willowdale from goblin raiders</p>
                                </div>
                                <span class="badge badge-success">Complete</span>
                            </div>
                        </div>
                    </div>
                    """)

                with gr.Tab("NPCs"):
                    npc_search = gr.Textbox(
                        placeholder="Search NPCs...",
                        show_label=False,
                    )
                    npc_list = gr.HTML("""
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb; text-align: center;">
                            <div style="width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); margin: 0 auto 0.75rem; display: flex; align-items: center; justify-content: center; color: white; font-size: 1.5rem; font-weight: 700;">
                                B
                            </div>
                            <h4 style="margin: 0 0 0.25rem 0; color: #111827; font-size: 1rem;">Bartok the Wise</h4>
                            <p style="margin: 0; color: #6b7280; font-size: 0.75rem;">Quest Giver</p>
                        </div>
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb; text-align: center;">
                            <div style="width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); margin: 0 auto 0.75rem; display: flex; align-items: center; justify-content: center; color: white; font-size: 1.5rem; font-weight: 700;">
                                D
                            </div>
                            <h4 style="margin: 0 0 0.25rem 0; color: #111827; font-size: 1rem;">Drakon the Red</h4>
                            <p style="margin: 0; color: #6b7280; font-size: 0.75rem;">Antagonist</p>
                        </div>
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb; text-align: center;">
                            <div style="width: 60px; height: 60px; border-radius: 50%; background: linear-gradient(135deg, #10b981 0%, #059669 100%); margin: 0 auto 0.75rem; display: flex; align-items: center; justify-content: center; color: white; font-size: 1.5rem; font-weight: 700;">
                                S
                            </div>
                            <h4 style="margin: 0 0 0.25rem 0; color: #111827; font-size: 1rem;">Selene the Merchant</h4>
                            <p style="margin: 0; color: #6b7280; font-size: 0.75rem;">Ally</p>
                        </div>
                    </div>
                    """)

                with gr.Tab("Locations"):
                    location_search = gr.Textbox(
                        placeholder="Search locations...",
                        show_label=False,
                    )
                    location_list = gr.HTML("""
                    <div style="display: grid; gap: 1rem; margin-top: 1rem;">
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <h4 style="margin: 0 0 0.5rem 0; color: #111827;">Willowdale</h4>
                            <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">A peaceful farming village nestled in the valley</p>
                        </div>
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <h4 style="margin: 0 0 0.5rem 0; color: #111827;">Dragon's Peak</h4>
                            <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">An ancient mountain lair home to Drakon the Red</p>
                        </div>
                    </div>
                    """)

                with gr.Tab("Items"):
                    item_search = gr.Textbox(
                        placeholder="Search items...",
                        show_label=False,
                    )
                    item_list = gr.HTML("""
                    <div style="display: grid; gap: 1rem; margin-top: 1rem;">
                        <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <h4 style="margin: 0 0 0.5rem 0; color: #111827;">Crown of the Ancients</h4>
                                    <p style="margin: 0; color: #6b7280; font-size: 0.875rem;">A legendary artifact with mysterious powers</p>
                                </div>
                                <span class="badge badge-info">Legendary</span>
                            </div>
                        </div>
                    </div>
                    """)

        # Session Library
        with gr.Group():
            gr.Markdown("### Session Library")

            session_library = gr.HTML("""
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem;">
                <div style="padding: 1.25rem; background: white; border-radius: 12px; border: 1px solid #e5e7eb; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.boxShadow='0 4px 6px -1px rgb(0 0 0 / 0.1)'" onmouseout="this.style.boxShadow='none'">
                    <div style="display: flex; justify-content: between; align-items: start; margin-bottom: 0.75rem;">
                        <h4 style="margin: 0; color: #111827;">Session 24</h4>
                        <span class="badge badge-success">Processed</span>
                    </div>
                    <p style="margin: 0 0 0.5rem 0; color: #6b7280; font-size: 0.875rem;">Oct 31, 2024</p>
                    <p style="margin: 0 0 1rem 0; color: #6b7280; font-size: 0.875rem;">Duration: 3h 45m</p>
                    <div style="display: flex; gap: 0.5rem;">
                        <button style="flex: 1; padding: 0.5rem; background: #6366f1; color: white; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer;">View</button>
                        <button style="padding: 0.5rem 0.75rem; background: white; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 0.875rem; cursor: pointer;">⋯</button>
                    </div>
                </div>

                <div style="padding: 1.25rem; background: white; border-radius: 12px; border: 1px solid #e5e7eb; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.boxShadow='0 4px 6px -1px rgb(0 0 0 / 0.1)'" onmouseout="this.style.boxShadow='none'">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                        <h4 style="margin: 0; color: #111827;">Session 23</h4>
                        <span class="badge badge-success">Processed</span>
                    </div>
                    <p style="margin: 0 0 0.5rem 0; color: #6b7280; font-size: 0.875rem;">Oct 24, 2024</p>
                    <p style="margin: 0 0 1rem 0; color: #6b7280; font-size: 0.875rem;">Duration: 4h 12m</p>
                    <div style="display: flex; gap: 0.5rem;">
                        <button style="flex: 1; padding: 0.5rem; background: #6366f1; color: white; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer;">View</button>
                        <button style="padding: 0.5rem 0.75rem; background: white; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 0.875rem; cursor: pointer;">⋯</button>
                    </div>
                </div>

                <div style="padding: 1.25rem; background: white; border-radius: 12px; border: 1px solid #e5e7eb; cursor: pointer; transition: all 0.2s;" onmouseover="this.style.boxShadow='0 4px 6px -1px rgb(0 0 0 / 0.1)'" onmouseout="this.style.boxShadow='none'">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.75rem;">
                        <h4 style="margin: 0; color: #111827;">Session 22</h4>
                        <span class="badge badge-warning">Processing</span>
                    </div>
                    <p style="margin: 0 0 0.5rem 0; color: #6b7280; font-size: 0.875rem;">Oct 17, 2024</p>
                    <p style="margin: 0 0 1rem 0; color: #6b7280; font-size: 0.875rem;">Duration: 2h 30m</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 65%;"></div>
                    </div>
                </div>
            </div>
            """)

        # Party Management (collapsible)
        with gr.Accordion("Party Management", open=False):
            gr.Markdown("#### Current Party")

            party_grid = gr.HTML("""
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem;">
                <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #111827;">Thorin Ironforge</h4>
                    <p style="margin: 0 0 0.25rem 0; color: #6b7280; font-size: 0.875rem;">Fighter • Level 5</p>
                    <p style="margin: 0; color: #6b7280; font-size: 0.75rem;">Player: John</p>
                </div>
                <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #111827;">Elara Moonwhisper</h4>
                    <p style="margin: 0 0 0.25rem 0; color: #6b7280; font-size: 0.875rem;">Wizard • Level 5</p>
                    <p style="margin: 0; color: #6b7280; font-size: 0.75rem;">Player: Sarah</p>
                </div>
                <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #111827;">Zephyr Swift</h4>
                    <p style="margin: 0 0 0.25rem 0; color: #6b7280; font-size: 0.875rem;">Rogue • Level 5</p>
                    <p style="margin: 0; color: #6b7280; font-size: 0.75rem;">Player: Mike</p>
                </div>
                <div style="padding: 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb;">
                    <h4 style="margin: 0 0 0.5rem 0; color: #111827;">Grimm Stonebeard</h4>
                    <p style="margin: 0 0 0.25rem 0; color: #6b7280; font-size: 0.875rem;">Cleric • Level 5</p>
                    <p style="margin: 0; color: #6b7280; font-size: 0.75rem;">Player: Dave</p>
                </div>
            </div>
            """)

            with gr.Row():
                add_character_btn = gr.Button("+ Add Character", variant="secondary")
                edit_party_btn = gr.Button("Edit Party", variant="secondary")
