"""Tests for campaign filtering in LLM Chat tab."""
import pytest
import gradio as gr
from pathlib import Path

from src.ui.llm_chat_tab import create_llm_chat_tab


def test_llm_chat_tab_accepts_campaign_id():
    """Test that create_llm_chat_tab accepts campaign_id parameter."""
    project_root = Path(__file__).parent.parent

    # Should not raise an error with campaign_id
    with gr.Blocks() as demo:
        create_llm_chat_tab(project_root, campaign_id="test_campaign")

    # If we got here without error, the function signature is correct
    assert True


def test_llm_chat_tab_without_campaign_id():
    """Test that create_llm_chat_tab works without campaign_id (shows all characters)."""
    project_root = Path(__file__).parent.parent

    # Should work without campaign_id (backward compatible)
    with gr.Blocks() as demo:
        create_llm_chat_tab(project_root, campaign_id=None)

    assert True


def test_llm_chat_tab_creates_components():
    """Test that LLM chat tab creates expected components."""
    project_root = Path(__file__).parent.parent

    with gr.Blocks() as demo:
        create_llm_chat_tab(project_root, campaign_id="test_campaign")

    # Check that the blocks were created (demo has children)
    assert len(demo.children) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
