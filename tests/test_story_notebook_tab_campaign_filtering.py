"""Tests for campaign filtering in Story Notebook tab."""
import pytest
import gradio as gr
from pathlib import Path

from src.ui.story_notebook_tab import create_story_notebook_tab
from src.story_notebook import StoryNotebookManager


def test_story_notebook_tab_accepts_refresh_campaign_names():
    """Test that create_story_notebook_tab accepts refresh_campaign_names parameter."""
    project_root = Path(__file__).parent.parent
    story_manager = StoryNotebookManager()

    def mock_refresh_campaign_names():
        return {"campaign_1": "Test Campaign"}

    def mock_get_notebook_context():
        return ""

    def mock_get_notebook_status():
        return "No notebook loaded"

    # Should not raise an error with refresh_campaign_names
    with gr.Blocks() as demo:
        create_story_notebook_tab(
            story_manager,
            mock_get_notebook_context,
            mock_get_notebook_status,
            mock_refresh_campaign_names
        )

    # If we got here without error, the function signature is correct
    assert True


def test_story_notebook_tab_creates_campaign_selector():
    """Test that Story Notebook tab creates campaign selector component."""
    project_root = Path(__file__).parent.parent
    story_manager = StoryNotebookManager()

    def mock_refresh_campaign_names():
        return {"campaign_1": "Test Campaign", "campaign_2": "Another Campaign"}

    def mock_get_notebook_context():
        return ""

    def mock_get_notebook_status():
        return "No notebook loaded"

    with gr.Blocks() as demo:
        create_story_notebook_tab(
            story_manager,
            mock_get_notebook_context,
            mock_get_notebook_status,
            mock_refresh_campaign_names
        )

    # Check that the blocks were created (demo has children)
    assert len(demo.children) > 0


def test_story_notebook_tab_with_empty_campaigns():
    """Test that Story Notebook tab works when no campaigns exist."""
    project_root = Path(__file__).parent.parent
    story_manager = StoryNotebookManager()

    def mock_refresh_campaign_names():
        return {}

    def mock_get_notebook_context():
        return ""

    def mock_get_notebook_status():
        return "No notebook loaded"

    with gr.Blocks() as demo:
        create_story_notebook_tab(
            story_manager,
            mock_get_notebook_context,
            mock_get_notebook_status,
            mock_refresh_campaign_names
        )

    # Should work even with no campaigns
    assert len(demo.children) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
