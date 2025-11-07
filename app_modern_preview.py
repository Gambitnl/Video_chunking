"""Preview of modernized UI - run this to see the new design."""
import gradio as gr

from src.ui.theme import create_modern_theme, MODERN_CSS
from src.ui.process_session_tab_modern import create_process_session_tab_modern
from src.ui.campaign_tab_modern import create_campaign_tab_modern
from src.ui.characters_tab_modern import create_characters_tab_modern
from src.ui.stories_output_tab_modern import create_stories_output_tab_modern
from src.ui.settings_tools_tab_modern import create_settings_tools_tab_modern
from src.party_config import PartyConfigManager, CampaignManager

# Get available parties
party_manager = PartyConfigManager()
available_parties = party_manager.list_parties()
campaign_manager = CampaignManager()


def _refresh_campaign_names():
    return campaign_manager.get_campaign_names()


initial_campaign_id = next(iter(_refresh_campaign_names().keys()), None)
active_campaign_state = gr.State(value=initial_campaign_id)

# Create modern theme
theme = create_modern_theme()

# Create the app
with gr.Blocks(
    title="D&D Session Processor - Modern UI",
    theme=theme,
    css=MODERN_CSS,
) as demo:
    gr.Markdown("""
    # D&D Session Processor Preview
    ### Modern UI - Full Preview

    **16 tabs + 5 consolidated sections** with clean design, clear workflow, and progressive disclosure.
    """)

    with gr.Tabs():
        # Tab 1: Process Session (the main workflow)
        create_process_session_tab_modern(demo, available_parties)

        # Tab 2: Campaign (dashboard, knowledge, library, party)
        create_campaign_tab_modern(demo)

        # Tab 3: Characters (profiles, extraction, import/export)
        create_characters_tab_modern(
            demo,
            available_parties,
            refresh_campaign_names=_refresh_campaign_names,
            active_campaign_state=active_campaign_state,
            initial_campaign_id=initial_campaign_id,
        )

        # Tab 4: Stories & Output (notebooks, transcripts, insights, export)
        create_stories_output_tab_modern(demo)

        # Tab 5: Settings & Tools (config, diagnostics, logs, chat, help)
        create_settings_tools_tab_modern(demo)

if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
    )
