import sys
from unittest.mock import MagicMock
from collections import defaultdict

# Mock dependencies before any project imports to avoid installation
# We need to be thorough with submodules for 'from x.y import z' to work
sys.modules['torch'] = MagicMock()
sys.modules['torchaudio'] = MagicMock()
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.signal'] = MagicMock()
sys.modules['librosa'] = MagicMock()
sys.modules['soundfile'] = MagicMock()
sys.modules['chromadb'] = MagicMock()
sys.modules['langchain'] = MagicMock()
sys.modules['langchain_community'] = MagicMock()
sys.modules['langchain_core'] = MagicMock()
sys.modules['langchain_text_splitters'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()

# Google mocks - mocking the local module is safer/easier
sys.modules['src.google_drive_auth'] = MagicMock()

# Also mock google just in case
sys.modules['google'] = MagicMock()
sys.modules['google.auth'] = MagicMock()
sys.modules['google.auth.transport'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google.oauth2'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['google_auth_oauthlib'] = MagicMock()
sys.modules['google_auth_oauthlib.flow'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.http'] = MagicMock()

import pytest
from unittest.mock import patch
from pathlib import Path
from contextlib import ExitStack

# Add project root to path
sys.path.append(str(Path(__file__).parents[1]))

def setup_mocks(stack):
    # Pre-import modules to ensure they exist for patching
    try:
        import src.ui.theme
        import src.ui.process_session_tab_modern
        import src.ui.campaign_tab_modern
        import src.ui.characters_tab_modern
        import src.ui.party_management_tab
        import src.ui.stories_output_tab_modern
        import src.ui.session_artifacts_tab
        import src.ui.search_tab
        import src.ui.analytics_tab
        import src.ui.character_analytics_tab
        import src.ui.settings_tools_tab_modern
        import src.party_config
    except ImportError as e:
        print(f"Import failed in setup_mocks: {e}")

    mock_refs = defaultdict(MagicMock)

    stack.enter_context(patch('gradio.Blocks'))
    stack.enter_context(patch('gradio.Row'))
    stack.enter_context(patch('gradio.Column'))
    stack.enter_context(patch('gradio.Dropdown'))
    stack.enter_context(patch('gradio.Button'))
    stack.enter_context(patch('gradio.Markdown'))
    stack.enter_context(patch('gradio.State'))
    stack.enter_context(patch('gradio.Textbox'))
    stack.enter_context(patch('gradio.Tab'))
    stack.enter_context(patch('gradio.File'))
    stack.enter_context(patch('gradio.Checkbox'))
    stack.enter_context(patch('gradio.Number'))
    stack.enter_context(patch('gradio.Group'))
    stack.enter_context(patch('gradio.Accordion'))
    stack.enter_context(patch('src.ui.theme.create_modern_theme'))
    stack.enter_context(patch('src.ui.theme.MODERN_CSS', "css"))

    # Patch creating functions to return mock references
    stack.enter_context(patch('src.ui.process_session_tab_modern.create_process_session_tab_modern', return_value=(MagicMock(), mock_refs)))
    stack.enter_context(patch('src.ui.campaign_tab_modern.create_campaign_tab_modern', return_value=mock_refs))
    stack.enter_context(patch('src.ui.characters_tab_modern.create_characters_tab_modern', return_value=mock_refs))
    stack.enter_context(patch('src.ui.party_management_tab.create_party_management_tab'))
    stack.enter_context(patch('src.ui.stories_output_tab_modern.create_stories_output_tab_modern', return_value=mock_refs))
    stack.enter_context(patch('src.ui.session_artifacts_tab.create_session_artifacts_tab', return_value=mock_refs))
    stack.enter_context(patch('src.ui.search_tab.create_search_tab'))
    stack.enter_context(patch('src.ui.analytics_tab.create_analytics_tab'))
    stack.enter_context(patch('src.ui.character_analytics_tab.create_character_analytics_tab'))
    stack.enter_context(patch('src.ui.settings_tools_tab_modern.create_settings_tools_tab_modern', return_value=mock_refs))

    MockCampaignManager = stack.enter_context(patch('src.party_config.CampaignManager'))
    mock_cm_instance = MockCampaignManager.return_value
    mock_cm_instance.get_campaign_names.return_value = {"c1": "Initial Campaign"}
    mock_cm_instance._load_campaigns.return_value = {"c1": MagicMock()}

# Import app inside a fixture or setup
@pytest.fixture(scope="module")
def app_module():
    with ExitStack() as stack:
        setup_mocks(stack)
        import app
        return app

def test_refresh_campaign_names_updates_from_manager(app_module):
    """Test that _refresh_campaign_names calls load_campaigns and returns updated names."""

    # Setup the mock for the test
    with patch.object(app_module, 'campaign_manager') as mock_cm:
        # Initial state
        mock_cm.get_campaign_names.return_value = {"c1": "Campaign 1"}
        mock_cm._load_campaigns.return_value = {"c1": MagicMock()}

        # Call the function
        names = app_module._refresh_campaign_names()

        # Verify it reloaded
        mock_cm._load_campaigns.assert_called_once()

        # Update mock to simulate external change
        mock_cm.get_campaign_names.return_value = {"c1": "Campaign 1", "c2": "Campaign 2"}

        # Call again
        names_updated = app_module._refresh_campaign_names()

        # Verify result reflects new state
        assert "c2" in names_updated
        assert names_updated["c2"] == "Campaign 2"
