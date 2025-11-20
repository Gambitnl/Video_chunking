"""
Tests for src/langchain/prompt_loader.py

Tests BUG-20251102-07: Verify system prompt loading with campaign placeholders.
"""
import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from src.langchain.prompt_loader import (
    SafeFormatDict,
    CampaignContextLoader,
    SystemPromptLoader,
)


# --- Test SafeFormatDict ---


def test_safe_format_dict_with_all_keys():
    """Test SafeFormatDict when all keys are present."""
    template = "Campaign: {campaign_name}, Sessions: {num_sessions}"
    context = SafeFormatDict(campaign_name="Lost Mines", num_sessions=5)

    result = template.format_map(context)

    assert result == "Campaign: Lost Mines, Sessions: 5"


def test_safe_format_dict_with_missing_keys():
    """Test SafeFormatDict leaves missing keys as placeholders."""
    template = "Campaign: {campaign_name}, DM: {dm_name}"
    context = SafeFormatDict(campaign_name="Curse of Strahd")

    result = template.format_map(context)

    # Missing key should remain as placeholder
    assert result == "Campaign: Curse of Strahd, DM: {dm_name}"


def test_safe_format_dict_with_all_missing_keys():
    """Test SafeFormatDict when no keys are provided."""
    template = "Campaign: {campaign_name}, Sessions: {num_sessions}, PCs: {pc_names}"
    context = SafeFormatDict()

    result = template.format_map(context)

    # All placeholders should remain
    assert result == "Campaign: {campaign_name}, Sessions: {num_sessions}, PCs: {pc_names}"


def test_safe_format_dict_with_extra_keys():
    """Test SafeFormatDict ignores extra keys not in template."""
    template = "Campaign: {campaign_name}"
    context = SafeFormatDict(
        campaign_name="Tomb of Annihilation",
        extra_key="ignored",
        another_key="also ignored"
    )

    result = template.format_map(context)

    assert result == "Campaign: Tomb of Annihilation"
    # Extra keys don't cause errors


def test_safe_format_dict_with_special_characters():
    """Test SafeFormatDict handles special characters in values."""
    template = "Message: {msg}"
    context = SafeFormatDict(msg="Hello {world}! <>&\"'")

    result = template.format_map(context)

    # Special characters should be preserved as-is
    assert result == "Message: Hello {world}! <>&\"'"


# --- Test CampaignContextLoader ---


def test_campaign_context_loader_without_campaign_id():
    """Test context loader returns defaults when campaign_id is None."""
    loader = CampaignContextLoader(campaign_id=None)

    context = loader.load_context()

    assert context == {
        "campaign_name": "Unknown",
        "num_sessions": 0,
        "pc_names": "Unknown",
    }


def test_campaign_context_loader_with_valid_campaign():
    """Test context loader with valid campaign data."""
    # Mock campaign with party and sessions
    mock_campaign = Mock()
    mock_campaign.name = "Waterdeep Dragon Heist"
    mock_campaign.party_id = "party_001"

    mock_party = Mock()
    mock_char1 = Mock(name="Thorin Ironforge")
    mock_char2 = Mock(name="Elara Moonshadow")
    mock_char3 = Mock(name="Zyx the Curious")
    mock_party.characters = [mock_char1, mock_char2, mock_char3]

    mock_sessions = ["session_001", "session_002", "session_003"]

    with patch('src.langchain.prompt_loader.CampaignManager') as mock_campaign_mgr_class:
        with patch('src.langchain.prompt_loader.PartyConfigManager') as mock_party_mgr_class:
            with patch('src.langchain.prompt_loader.StoryNotebookManager') as mock_story_mgr_class:
                # Setup mocks
                mock_campaign_mgr = mock_campaign_mgr_class.return_value
                mock_campaign_mgr.get_campaign.return_value = mock_campaign

                mock_party_mgr = mock_party_mgr_class.return_value
                mock_party_mgr.get_party.return_value = mock_party

                mock_story_mgr = mock_story_mgr_class.return_value
                mock_story_mgr.list_sessions.return_value = mock_sessions

                # Load context
                loader = CampaignContextLoader(campaign_id="campaign_001")
                context = loader.load_context()

                # Verify results
                assert context["campaign_name"] == "Waterdeep Dragon Heist"
                assert context["num_sessions"] == 3
                assert context["pc_names"] == "Thorin Ironforge, Elara Moonshadow, Zyx the Curious"


def test_campaign_context_loader_campaign_not_found():
    """Test context loader when campaign doesn't exist."""
    with patch('src.langchain.prompt_loader.CampaignManager') as mock_campaign_mgr_class:
        mock_campaign_mgr = mock_campaign_mgr_class.return_value
        mock_campaign_mgr.get_campaign.return_value = None  # Campaign not found

        loader = CampaignContextLoader(campaign_id="nonexistent")
        context = loader.load_context()

        # Should return defaults when campaign not found
        assert context == {
            "campaign_name": "Unknown",
            "num_sessions": 0,
            "pc_names": "Unknown",
        }


def test_campaign_context_loader_campaign_without_party():
    """Test context loader when campaign has no party_id."""
    mock_campaign = Mock()
    mock_campaign.name = "Solo Adventure"
    mock_campaign.party_id = None  # No party

    with patch('src.langchain.prompt_loader.CampaignManager') as mock_campaign_mgr_class:
        with patch('src.langchain.prompt_loader.StoryNotebookManager') as mock_story_mgr_class:
            mock_campaign_mgr = mock_campaign_mgr_class.return_value
            mock_campaign_mgr.get_campaign.return_value = mock_campaign

            mock_story_mgr = mock_story_mgr_class.return_value
            mock_story_mgr.list_sessions.return_value = []

            loader = CampaignContextLoader(campaign_id="campaign_001")
            context = loader.load_context()

            # Campaign name loaded, but PC names should be default
            assert context["campaign_name"] == "Solo Adventure"
            assert context["pc_names"] == "Unknown"
            assert context["num_sessions"] == 0


def test_campaign_context_loader_party_without_characters():
    """Test context loader when party has no characters."""
    mock_campaign = Mock()
    mock_campaign.name = "New Campaign"
    mock_campaign.party_id = "party_001"

    mock_party = Mock()
    mock_party.characters = []  # Empty character list

    with patch('src.langchain.prompt_loader.CampaignManager') as mock_campaign_mgr_class:
        with patch('src.langchain.prompt_loader.PartyConfigManager') as mock_party_mgr_class:
            with patch('src.langchain.prompt_loader.StoryNotebookManager') as mock_story_mgr_class:
                mock_campaign_mgr = mock_campaign_mgr_class.return_value
                mock_campaign_mgr.get_campaign.return_value = mock_campaign

                mock_party_mgr = mock_party_mgr_class.return_value
                mock_party_mgr.get_party.return_value = mock_party

                mock_story_mgr = mock_story_mgr_class.return_value
                mock_story_mgr.list_sessions.return_value = []

                loader = CampaignContextLoader(campaign_id="campaign_001")
                context = loader.load_context()

                # PC names should be default when party has no characters
                assert context["campaign_name"] == "New Campaign"
                assert context["pc_names"] == "Unknown"


def test_campaign_context_loader_import_error():
    """Test context loader handles ImportError gracefully."""
    with patch('src.langchain.prompt_loader.CampaignManager', side_effect=ImportError("Module not found")):
        loader = CampaignContextLoader(campaign_id="campaign_001")
        context = loader.load_context()

        # Should return defaults on ImportError
        assert context == {
            "campaign_name": "Unknown",
            "num_sessions": 0,
            "pc_names": "Unknown",
        }


def test_campaign_context_loader_generic_exception():
    """Test context loader handles generic exceptions gracefully."""
    with patch('src.langchain.prompt_loader.CampaignManager') as mock_campaign_mgr_class:
        mock_campaign_mgr = mock_campaign_mgr_class.return_value
        mock_campaign_mgr.get_campaign.side_effect = Exception("Database error")

        loader = CampaignContextLoader(campaign_id="campaign_001")
        context = loader.load_context()

        # Should return defaults on any exception
        assert context == {
            "campaign_name": "Unknown",
            "num_sessions": 0,
            "pc_names": "Unknown",
        }


# --- Test SystemPromptLoader ---


def test_system_prompt_loader_default_path():
    """Test SystemPromptLoader uses default template path."""
    loader = SystemPromptLoader()

    # Default path should be project_root/prompts/campaign_assistant.txt
    assert loader.template_path.name == "campaign_assistant.txt"
    assert loader.template_path.parent.name == "prompts"


def test_system_prompt_loader_custom_path():
    """Test SystemPromptLoader with custom template path."""
    custom_path = Path("/custom/prompts/my_template.txt")
    loader = SystemPromptLoader(template_path=custom_path)

    assert loader.template_path == custom_path


def test_load_template_success():
    """Test loading template from file."""
    template_content = "You are a D&D assistant for {campaign_name}."

    with patch('builtins.open', mock_open(read_data=template_content)):
        loader = SystemPromptLoader(template_path=Path("/mock/template.txt"))
        result = loader.load_template()

        assert result == template_content


def test_load_template_file_not_found():
    """Test loading template when file doesn't exist."""
    loader = SystemPromptLoader(template_path=Path("/nonexistent/template.txt"))

    with pytest.raises(FileNotFoundError, match="Template file not found"):
        loader.load_template()


def test_format_prompt_with_complete_context():
    """Test formatting prompt with all placeholders provided."""
    loader = SystemPromptLoader()
    template = "Campaign: {campaign_name}, Sessions: {num_sessions}, PCs: {pc_names}"
    context = {
        "campaign_name": "Princes of the Apocalypse",
        "num_sessions": 12,
        "pc_names": "Aric, Brynn, Cassia"
    }

    result = loader.format_prompt(template, context)

    assert result == "Campaign: Princes of the Apocalypse, Sessions: 12, PCs: Aric, Brynn, Cassia"


def test_format_prompt_with_missing_placeholders():
    """Test formatting prompt with missing placeholders."""
    loader = SystemPromptLoader()
    template = "Campaign: {campaign_name}, DM: {dm_name}, Level: {avg_level}"
    context = {
        "campaign_name": "Storm King's Thunder"
    }

    result = loader.format_prompt(template, context)

    # Missing placeholders should remain
    assert result == "Campaign: Storm King's Thunder, DM: {dm_name}, Level: {avg_level}"


def test_load_and_format_success():
    """Test load_and_format convenience method (happy path)."""
    template_content = "Welcome to {campaign_name} with {pc_names}!"

    mock_campaign = Mock()
    mock_campaign.name = "Hoard of the Dragon Queen"
    mock_campaign.party_id = "party_001"

    mock_party = Mock()
    mock_char = Mock(name="Dragonborn Paladin")
    mock_party.characters = [mock_char]

    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('src.langchain.prompt_loader.CampaignManager') as mock_campaign_mgr_class:
            with patch('src.langchain.prompt_loader.PartyConfigManager') as mock_party_mgr_class:
                with patch('src.langchain.prompt_loader.StoryNotebookManager') as mock_story_mgr_class:
                    mock_campaign_mgr = mock_campaign_mgr_class.return_value
                    mock_campaign_mgr.get_campaign.return_value = mock_campaign

                    mock_party_mgr = mock_party_mgr_class.return_value
                    mock_party_mgr.get_party.return_value = mock_party

                    mock_story_mgr = mock_story_mgr_class.return_value
                    mock_story_mgr.list_sessions.return_value = []

                    loader = SystemPromptLoader(template_path=Path("/mock/template.txt"))
                    result = loader.load_and_format(campaign_id="campaign_001")

                    assert result == "Welcome to Hoard of the Dragon Queen with Dragonborn Paladin!"


def test_load_and_format_file_not_found():
    """Test load_and_format when template file doesn't exist."""
    loader = SystemPromptLoader(template_path=Path("/nonexistent/template.txt"))

    result = loader.load_and_format(campaign_id="campaign_001")

    # Should return default prompt on FileNotFoundError
    assert result == SystemPromptLoader.DEFAULT_PROMPT


def test_load_and_format_without_campaign_id():
    """Test load_and_format without campaign_id uses defaults."""
    template_content = "Campaign: {campaign_name}, Sessions: {num_sessions}"

    with patch('builtins.open', mock_open(read_data=template_content)):
        loader = SystemPromptLoader(template_path=Path("/mock/template.txt"))
        result = loader.load_and_format(campaign_id=None)

        # Should use default context values
        assert result == "Campaign: Unknown, Sessions: 0"


def test_load_and_format_generic_exception():
    """Test load_and_format handles unexpected exceptions."""
    with patch('builtins.open', side_effect=Exception("Unexpected error")):
        loader = SystemPromptLoader(template_path=Path("/mock/template.txt"))
        result = loader.load_and_format(campaign_id="campaign_001")

        # Should return default prompt on unexpected error
        assert result == SystemPromptLoader.DEFAULT_PROMPT


def test_campaign_context_loader_with_party_missing_name_attribute():
    """Test context loader when character objects missing name attribute."""
    mock_campaign = Mock()
    mock_campaign.name = "Test Campaign"
    mock_campaign.party_id = "party_001"

    mock_party = Mock()
    # Characters without 'name' attribute
    mock_char1 = Mock(spec=[])  # Empty spec, no 'name' attribute
    del mock_char1.name  # Ensure name doesn't exist
    mock_party.characters = [mock_char1]

    with patch('src.langchain.prompt_loader.CampaignManager') as mock_campaign_mgr_class:
        with patch('src.langchain.prompt_loader.PartyConfigManager') as mock_party_mgr_class:
            with patch('src.langchain.prompt_loader.StoryNotebookManager') as mock_story_mgr_class:
                mock_campaign_mgr = mock_campaign_mgr_class.return_value
                mock_campaign_mgr.get_campaign.return_value = mock_campaign

                mock_party_mgr = mock_party_mgr_class.return_value
                mock_party_mgr.get_party.return_value = mock_party

                mock_story_mgr = mock_story_mgr_class.return_value
                mock_story_mgr.list_sessions.return_value = []

                loader = CampaignContextLoader(campaign_id="campaign_001")
                context = loader.load_context()

                # Should gracefully handle missing attribute and return defaults
                assert context["campaign_name"] == "Test Campaign"
                assert context["pc_names"] == "Unknown"


# --- Integration Tests ---


def test_integration_full_prompt_loading_pipeline():
    """Integration test: Full pipeline from template to formatted prompt."""
    # Setup test data
    template_content = """You are assisting with campaign: {campaign_name}.
The party consists of: {pc_names}.
You have processed {num_sessions} sessions so far."""

    mock_campaign = Mock()
    mock_campaign.name = "Out of the Abyss"
    mock_campaign.party_id = "party_001"

    mock_party = Mock()
    mock_party.characters = [
        Mock(name="Grimjaw"),
        Mock(name="Sariel"),
        Mock(name="Topsy"),
        Mock(name="Turvy")
    ]

    mock_sessions = ["s1", "s2", "s3", "s4", "s5"]

    with patch('builtins.open', mock_open(read_data=template_content)):
        with patch('src.langchain.prompt_loader.CampaignManager') as mock_campaign_mgr_class:
            with patch('src.langchain.prompt_loader.PartyConfigManager') as mock_party_mgr_class:
                with patch('src.langchain.prompt_loader.StoryNotebookManager') as mock_story_mgr_class:
                    # Setup mocks
                    mock_campaign_mgr = mock_campaign_mgr_class.return_value
                    mock_campaign_mgr.get_campaign.return_value = mock_campaign

                    mock_party_mgr = mock_party_mgr_class.return_value
                    mock_party_mgr.get_party.return_value = mock_party

                    mock_story_mgr = mock_story_mgr_class.return_value
                    mock_story_mgr.list_sessions.return_value = mock_sessions

                    # Load and format
                    loader = SystemPromptLoader(template_path=Path("/mock/template.txt"))
                    result = loader.load_and_format(campaign_id="campaign_001")

                    # Verify full formatted prompt
                    expected = """You are assisting with campaign: Out of the Abyss.
The party consists of: Grimjaw, Sariel, Topsy, Turvy.
You have processed 5 sessions so far."""

                    assert result == expected
