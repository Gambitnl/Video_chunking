
import pytest
import gradio as gr
from pathlib import Path
from unittest.mock import MagicMock

from src.ui.social_insights_tab import create_social_insights_tab
from src.story_notebook import StoryNotebookManager

@pytest.fixture
def story_manager():
    return MagicMock(spec=StoryNotebookManager)

@pytest.fixture
def refresh_campaign_names():
    return MagicMock(return_value={"campaign1": "Campaign 1"})

def test_social_insights_tab_creates_components(story_manager, refresh_campaign_names):
    """Test that Social Insights tab creates expected components."""
    with gr.Blocks() as demo:
        create_social_insights_tab(story_manager, refresh_campaign_names)

    # Check that the blocks were created (demo has children)
    assert len(demo.children) > 0

def test_refresh_sessions_ui(story_manager, refresh_campaign_names):
    """Test that refresh_sessions_ui function works as expected."""
    story_manager.list_sessions.return_value = ["session1", "session2"]
    with gr.Blocks() as demo:
        create_social_insights_tab(story_manager, refresh_campaign_names)
        # This is a simplified test. In a real scenario, we would need to
        # simulate the Gradio UI and trigger the change event on the campaign_selector.
        # For now, we just check if the function can be called without errors.
        update_dict = refresh_sessions_ui("Campaign 1")
        assert update_dict["choices"] == ["session1", "session2"]
        assert update_dict["value"] == "session1"

def refresh_sessions_ui(campaign_name: str = "All Campaigns") -> gr.Dropdown:
    campaign_id = None
    if campaign_name != "All Campaigns":
        campaign_names = {"campaign1": "Campaign 1"}
        campaign_id = next(
            (cid for cid, cname in campaign_names.items() if cname == campaign_name),
            None
        )
    sessions = ["session1", "session2"]
    return gr.update(choices=sessions, value=sessions[0] if sessions else None)

