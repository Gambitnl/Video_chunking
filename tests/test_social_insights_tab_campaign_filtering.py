
import pytest
import gradio as gr
from unittest.mock import MagicMock

from src.ui.social_insights_tab import create_social_insights_tab
from src.story_notebook import StoryNotebookManager

@pytest.fixture
def story_manager():
    manager = MagicMock(spec=StoryNotebookManager)
    manager.list_sessions.return_value = ["session1", "session2"]
    return manager

@pytest.fixture
def refresh_campaign_names():
    return MagicMock(return_value={"campaign1": "Campaign 1", "campaign2": "Campaign 2"})

def test_social_insights_tab_creates_components(story_manager, refresh_campaign_names):
    """Test that Social Insights tab creates expected components."""
    with gr.Blocks() as demo:
        refs = create_social_insights_tab(
            story_manager,
            refresh_campaign_names,
            initial_campaign_id="campaign1",
        )

    # Check that the blocks were created (demo has children)
    assert len(demo.children) > 0
    assert {"campaign_selector", "session_dropdown", "keyword_output", "nebula_output"} <= set(refs.keys())
    # Ensure initial campaign selection uses provided campaign_id
    assert refs["campaign_selector"].value == "Campaign 1"
    story_manager.list_sessions.assert_called_with(campaign_id="campaign1")

def test_refresh_sessions_ui(story_manager, refresh_campaign_names):
    """Test that default state falls back to All Campaigns when no campaign is active."""
    story_manager.list_sessions.reset_mock()
    with gr.Blocks() as demo:
        refs = create_social_insights_tab(story_manager, refresh_campaign_names, initial_campaign_id=None)

    assert refs["campaign_selector"].value == "All Campaigns"
    kwargs = story_manager.list_sessions.call_args.kwargs
    assert kwargs.get("campaign_id", None) is None
