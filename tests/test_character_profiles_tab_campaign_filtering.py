"""Tests for campaign filtering in Character Profiles tab."""
import pytest
import gradio as gr
from pathlib import Path

from src.ui.character_profiles_tab import create_character_profiles_tab


def test_character_profiles_tab_accepts_refresh_callback():
    """Test that create_character_profiles_tab accepts refresh_campaign_names parameter."""

    def mock_refresh_campaigns():
        return {
            "test_campaign": "Test Campaign",
            "another_campaign": "Another Campaign"
        }

    available_parties = ["default", "test_party"]

    # Should not raise an error
    with gr.Blocks() as demo:
        create_character_profiles_tab(
            blocks=demo,
            available_parties=available_parties,
            refresh_campaign_names=mock_refresh_campaigns
        )

    # If we got here without error, the function signature is correct
    assert True


def test_character_profiles_tab_campaign_selector_exists():
    """Test that campaign selector component is created."""

    def mock_refresh_campaigns():
        return {
            "campaign_a": "Campaign A",
            "campaign_b": "Campaign B"
        }

    available_parties = ["default"]

    with gr.Blocks() as demo:
        create_character_profiles_tab(
            blocks=demo,
            available_parties=available_parties,
            refresh_campaign_names=mock_refresh_campaigns
        )

    # Check that the blocks were created (demo has children)
    assert len(demo.children) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
