from __future__ import annotations

from typing import Callable, Dict

import gradio as gr

from src.ui.constants import StatusIndicators
from src.knowledge_base import CampaignKnowledgeBase


def create_campaign_library_tab(
    blocks: gr.Blocks,
    refresh_campaign_names: Callable[[], Dict[str, str]],
) -> None:
    with gr.Tab("Campaign Library"):
        gr.Markdown("""
        ### Campaign Library

        Automatically extracted campaign knowledge from your sessions. View quests, NPCs, plot hooks, locations, and items that have been mentioned across all processed sessions.

        Knowledge is extracted from IC-only transcripts using your local LLM (Ollama) and accumulated over time.
        """)

        with gr.Row():
            with gr.Column(scale=2):
                kb_campaign_choices = ["default"] + list(refresh_campaign_names().keys())
                kb_campaign_selector = gr.Dropdown(
                    choices=kb_campaign_choices,
                    value="default",
                    label="Select Campaign",
                    info="Choose which campaign's knowledge base to view",
                )
            with gr.Column(scale=3):
                kb_search_input = gr.Textbox(
                    label="Search Knowledge Base",
                    placeholder="Search across all quests, NPCs, locations, items, and plot hooks...",
                )
            with gr.Column(scale=1):
                kb_search_btn = gr.Button("[SEARCH] Search", size="sm")
                kb_refresh_btn = gr.Button("[REFRESH] Refresh", size="sm")

        kb_output = gr.Markdown(value="Select a campaign and click Refresh to load knowledge.")

        def format_quest(quest):
            status_emoji = {
                "active": StatusIndicators.QUEST_ACTIVE,
                "completed": StatusIndicators.QUEST_COMPLETE,
                "failed": StatusIndicators.QUEST_FAILED,
                "unknown": StatusIndicators.QUEST_UNKNOWN,
            }
            emoji = status_emoji.get(quest.status, StatusIndicators.QUEST_UNKNOWN)

            md = f"**{emoji} {quest.title}** ({quest.status.upper()})\n\n"
            md += f"{quest.description}\n\n"
            md += f"*First mentioned: {quest.first_mentioned} | Last updated: {quest.last_updated}*"

            if quest.related_npcs:
                md += f"\n\n**Related NPCs:** {', '.join(quest.related_npcs)}"
            if quest.related_locations:
                md += f"\n\n**Related Locations:** {', '.join(quest.related_locations)}"
            if quest.notes:
                md += "\n\n**Notes:**\n" + "\n".join(f"- {note}" for note in quest.notes)

            return md

        def format_npc(npc):
            role_emoji = {
                "quest_giver": "[QUEST GIVER]",
                "merchant": "[MERCHANT]",
                "enemy": "[ENEMY]",
                "ally": "[ALLY]",
                "unknown": "[UNKNOWN]",
            }
            emoji = role_emoji.get(npc.role, "[UNKNOWN]")

            md = f"**{emoji} {npc.name}** ({npc.role or 'unknown'})\n\n"
            md += f"{npc.description}\n\n"

            if npc.location:
                md += f"**Location:** {npc.location}\n\n"

            md += f"*Appearances: {', '.join(npc.appearances)}*"

            if npc.relationships:
                md += "\n\n**Relationships:**\n"
                for character, relation in npc.relationships.items():
                    md += f"- **{character}:** {relation}\n"

            if npc.notes:
                md += "\n**Notes:**\n" + "\n".join(f"- {note}" for note in npc.notes)

            return md

        def format_plot_hook(hook):
            status = "[RESOLVED] Resolved" if hook.resolved else "[UNRESOLVED] Unresolved"

            md = f"**{status}: {hook.summary}**\n\n"
            md += f"{hook.details}\n\n"
            md += f"*First mentioned: {hook.first_mentioned} | Last updated: {hook.last_updated}*"

            if hook.related_npcs:
                md += f"\n\n**Related NPCs:** {', '.join(hook.related_npcs)}"
            if hook.related_quests:
                md += f"\n\n**Related Quests:** {', '.join(hook.related_quests)}"
            if hook.resolved and hook.resolution:
                md += f"\n\n**Resolution:** {hook.resolution}"

            return md

        def format_location(location):
            type_emoji = {
                "city": "[CITY]",
                "dungeon": "[DUNGEON]",
                "wilderness": "[WILDERNESS]",
                "building": "[BUILDING]",
                "unknown": "[LOCATION]",
            }
            emoji = type_emoji.get(location.type, "[LOCATION]")

            md = f"**{emoji} {location.name}** ({location.type or 'unknown'})\n\n"
            md += f"{location.description}\n\n"
            md += f"*Visited: {', '.join(location.visits)}*"

            if location.notable_features:
                md += "\n\n**Notable Features:**\n" + "\n".join(f"- {feat}" for feat in location.notable_features)
            if location.npcs_present:
                md += f"\n\n**NPCs Present:** {', '.join(location.npcs_present)}"

            return md

        def format_item(item):
            md = f"**[ITEM] {item.name}**\n\n"
            md += f"{item.description}\n\n"

            if item.owner:
                md += f"**Owner:** {item.owner}\n\n"
            if item.location:
                md += f"**Location:** {item.location}\n\n"

            md += f"*First mentioned: {item.first_mentioned} | Last updated: {item.last_updated}*"

            if item.properties:
                md += "\n\n**Properties:**\n" + "\n".join(f"- {prop}" for prop in item.properties)
            if item.significance:
                md += f"\n\n**Significance:** {item.significance}"

            return md

        def load_knowledge_base(campaign_id):
            try:
                kb = CampaignKnowledgeBase(campaign_id=campaign_id)

                if not kb.knowledge["sessions_processed"]:
                    return (
                        f"## No Knowledge Found\n\n"
                        f"No sessions have been processed for campaign `{campaign_id}` yet.\n\n"
                        "Process a session with knowledge extraction enabled to start building your campaign library!"
                    )

                output = f"# Campaign Knowledge Base: {campaign_id}\n\n"
                output += f"**Sessions Processed:** {', '.join(kb.knowledge['sessions_processed'])}\n\n"
                output += f"**Last Updated:** {kb.knowledge.get('last_updated', 'Unknown')}\n\n"
                output += "---\n\n"

                active_quests = kb.get_active_quests()
                if active_quests:
                    output += f"## [QUEST] Active Quests ({len(active_quests)})\n\n"
                    for quest in active_quests:
                        output += format_quest(quest) + "\n\n---\n\n"

                all_quests = kb.knowledge["quests"]
                completed = [quest for quest in all_quests if quest.status == "completed"]
                failed = [quest for quest in all_quests if quest.status == "failed"]

                if completed:
                    output += f"## [COMPLETED] Completed Quests ({len(completed)})\n\n"
                    for quest in completed:
                        output += format_quest(quest) + "\n\n---\n\n"

                if failed:
                    output += f"## [FAILED] Failed Quests ({len(failed)})\n\n"
                    for quest in failed:
                        output += format_quest(quest) + "\n\n---\n\n"

                npcs = kb.get_all_npcs()
                if npcs:
                    output += f"## [NPC] Non-Player Characters ({len(npcs)})\n\n"
                    for npc in npcs:
                        output += format_npc(npc) + "\n\n---\n\n"

                plot_hooks = kb.get_unresolved_plot_hooks()
                if plot_hooks:
                    output += f"## [UNRESOLVED] Unresolved Plot Hooks ({len(plot_hooks)})\n\n"
                    for hook in plot_hooks:
                        output += format_plot_hook(hook) + "\n\n---\n\n"

                resolved_hooks = [hook for hook in kb.knowledge["plot_hooks"] if hook.resolved]
                if resolved_hooks:
                    output += f"## [RESOLVED] Resolved Plot Hooks ({len(resolved_hooks)})\n\n"
                    for hook in resolved_hooks:
                        output += format_plot_hook(hook) + "\n\n---\n\n"

                locations = kb.get_all_locations()
                if locations:
                    output += f"## [LOCATION] Locations ({len(locations)})\n\n"
                    for location in locations:
                        output += format_location(location) + "\n\n---\n\n"

                items = kb.knowledge["items"]
                if items:
                    output += f"## [ITEM] Important Items ({len(items)})\n\n"
                    for item in items:
                        output += format_item(item) + "\n\n---\n\n"

                if not any([all_quests, npcs, kb.knowledge["plot_hooks"], locations, items]):
                    output += (
                        "## No Knowledge Found\n\n"
                        "No entities have been extracted yet. Process sessions with knowledge extraction enabled!"
                    )

                return output

            except Exception as exc:
                return f"## Error Loading Knowledge Base\n\n```\n{exc}\n```"

        def search_knowledge_base(campaign_id, query):
            try:
                kb = CampaignKnowledgeBase(campaign_id=campaign_id)
                results = kb.search(query)

                if not any(results.values()):
                    return f"No results found for `{query}`."

                output = f"# Search Results for `{query}`\n\n"

                if results["quests"]:
                    output += f"## [QUEST] Quests ({len(results['quests'])})\n\n"
                    for quest in results["quests"]:
                        output += format_quest(quest) + "\n\n---\n\n"

                if results["npcs"]:
                    output += f"## [NPC] NPCs ({len(results['npcs'])})\n\n"
                    for npc in results["npcs"]:
                        output += format_npc(npc) + "\n\n---\n\n"

                if results["plot_hooks"]:
                    output += f"## [UNRESOLVED] Plot Hooks ({len(results['plot_hooks'])})\n\n"
                    for hook in results["plot_hooks"]:
                        output += format_plot_hook(hook) + "\n\n---\n\n"

                if results["locations"]:
                    output += f"## [LOCATION] Locations ({len(results['locations'])})\n\n"
                    for location in results["locations"]:
                        output += format_location(location) + "\n\n---\n\n"

                if results["items"]:
                    output += f"## [ITEM] Items ({len(results['items'])})\n\n"
                    for item in results["items"]:
                        output += format_item(item) + "\n\n---\n\n"

                return output

            except Exception as exc:
                return f"## Search Error\n\n```\n{exc}\n```"

        kb_refresh_btn.click(
            fn=load_knowledge_base,
            inputs=[kb_campaign_selector],
            outputs=[kb_output],
        )

        kb_search_btn.click(
            fn=search_knowledge_base,
            inputs=[kb_campaign_selector, kb_search_input],
            outputs=[kb_output],
        )

        kb_campaign_selector.change(
            fn=load_knowledge_base,
            inputs=[kb_campaign_selector],
            outputs=[kb_output],
        )

        blocks.load(
            fn=load_knowledge_base,
            inputs=[kb_campaign_selector],
            outputs=[kb_output],
        )