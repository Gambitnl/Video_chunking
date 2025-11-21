
import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock gradio to avoid UI creation side effects during import
mock_gr = MagicMock()
sys.modules['gradio'] = mock_gr

# Mock dependencies
sys.modules['src.pipeline'] = MagicMock()
sys.modules['src.diarizer'] = MagicMock()
sys.modules['src.character_profile'] = MagicMock()
sys.modules['src.logger'] = MagicMock()
sys.modules['src.audit'] = MagicMock()
sys.modules['src.party_config'] = MagicMock()
sys.modules['src.knowledge_base'] = MagicMock()
sys.modules['src.preflight'] = MagicMock()
sys.modules['src.ui.constants'] = MagicMock()
sys.modules['src.ui.helpers'] = MagicMock()
sys.modules['src.ui.state_store'] = MagicMock()
sys.modules['src.campaign_dashboard'] = MagicMock()
sys.modules['src.story_notebook'] = MagicMock()
sys.modules['src.google_drive_auth'] = MagicMock()
sys.modules['src.restart_manager'] = MagicMock()

# Mock UI modules
sys.modules['src.ui.theme'] = MagicMock()

# Mock function returns for unpacking
mock_process_tab = MagicMock()
mock_process_tab.return_value = (MagicMock(), MagicMock())
sys.modules['src.ui.process_session_tab_modern'] = MagicMock()
sys.modules['src.ui.process_session_tab_modern'].create_process_session_tab_modern = mock_process_tab

sys.modules['src.ui.campaign_tab_modern'] = MagicMock()
sys.modules['src.ui.characters_tab_modern'] = MagicMock()
sys.modules['src.ui.party_management_tab'] = MagicMock()
sys.modules['src.ui.stories_output_tab_modern'] = MagicMock()
sys.modules['src.ui.settings_tools_tab_modern'] = MagicMock()
sys.modules['src.ui.session_artifacts_tab'] = MagicMock()
sys.modules['src.ui.search_tab'] = MagicMock()
sys.modules['src.ui.analytics_tab'] = MagicMock()
sys.modules['src.ui.character_analytics_tab'] = MagicMock()
sys.modules['src.ui.api_key_manager'] = MagicMock()
sys.modules['src.ui.config_manager'] = MagicMock()
sys.modules['src.ui.intermediate_resume_helper'] = MagicMock()

# Setup specific mocks needed for initialization
mock_artifact_counter_cls = MagicMock()
mock_artifact_counter_instance = MagicMock()
mock_counts = MagicMock()
mock_counts.to_tuple.return_value = (0, 0)
mock_artifact_counter_instance.count_artifacts.return_value = mock_counts
mock_artifact_counter_cls.return_value = mock_artifact_counter_instance
sys.modules['src.artifact_counter'] = MagicMock()
sys.modules['src.artifact_counter'].CampaignArtifactCounter = mock_artifact_counter_cls

# Now we can import app.
# NOTE: We should now import from the new helper module directly to verify it handles exceptions.
# However, importing 'app' ensures we are testing what the application actually uses.
try:
    from src.ui.campaign_dashboard_helpers import (
        campaign_overview_markdown,
        knowledge_summary_markdown
    )
    import app
except ImportError as e:
    print(f"Failed to import: {e}")
    raise

@pytest.fixture
def mock_managers():
    import app
    return app.campaign_manager, app.CampaignKnowledgeBase, app.StatusMessages

def test_campaign_overview_corruption(mock_managers):
    """Test _campaign_overview_markdown with a corrupted campaign."""
    mock_cm, mock_kb_cls, mock_status = mock_managers

    # Setup: campaign_manager.get_campaign raises an error
    mock_cm.get_campaign.side_effect = Exception("Corrupted JSON file")

    # Setup StatusMessages.error to return a specific string we can assert on
    mock_status.error.side_effect = lambda title, msg, detail: f"ERROR: {title} - {msg}"

    # Action: Call the function via app's wrapper or directly (app's wrapper just calls this)
    # Using app's wrapper to be integration-like
    result = app._campaign_overview_markdown("campaign_123")

    # Assertion: Should return an error string, NOT raise
    assert "ERROR" in result
    assert "Campaign Data Error" in result

def test_knowledge_summary_corruption(mock_managers):
    """Test _knowledge_summary_markdown when knowledge base loading fails."""
    mock_cm, mock_kb_cls, mock_status = mock_managers

    # Setup: Knowledge base instantiation fails
    mock_kb_cls.side_effect = Exception("Knowledge base corrupted")

    mock_status.error.side_effect = lambda title, msg, detail: f"ERROR: {title} - {msg}"

    # Action
    result = app._knowledge_summary_markdown("campaign_123")

    # Assertion
    assert "ERROR" in result
    assert "Knowledge Base Error" in result
