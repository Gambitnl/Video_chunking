import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the actual classes we need to instantiate in tests
from src.party_config import Campaign, CampaignSettings, Party, Character

# Import the class we are testing
from src.campaign_dashboard import CampaignDashboard

# This fixture will mock the Config object for all modules that use it.
# autouse=True means it runs for every test in this file.
@pytest.fixture(autouse=True)
def mock_config():
    # We need to patch Config where it is imported in each module
    with patch('src.campaign_dashboard.Config') as mock_dash_config, \
         patch('src.party_config.Config') as mock_party_config, \
         patch('src.knowledge_base.Config') as mock_kb_config:
        
        # Create one mock object and assign it to all patched targets
        # This ensures that when one part of the code sets a value (e.g., MODELS_DIR),
        # another part of the code sees the same value.
        unified_mock = MagicMock()
        unified_mock.OUTPUT_DIR = MagicMock(spec=Path)
        unified_mock.MODELS_DIR = MagicMock(spec=Path)

        mock_dash_config.return_value = unified_mock
        mock_party_config.return_value = unified_mock
        mock_kb_config.return_value = unified_mock
        
        # Yield the unified mock so tests can access it if needed
        yield unified_mock

@pytest.fixture
def dashboard_with_mocks():
    """Provides a CampaignDashboard instance and mocks its direct dependencies."""
    # Patch the managers at the point of instantiation within the dashboard's __init__
    with patch('src.campaign_dashboard.CampaignManager') as MockCampaignManager, \
         patch('src.campaign_dashboard.PartyConfigManager') as MockPartyManager:
        
        dashboard = CampaignDashboard()
        mocks = {
            'campaign': dashboard.campaign_manager,
            'party': dashboard.party_manager
        }
        yield dashboard, mocks

class TestCampaignDashboard:

    def test_generate_manual_setup(self, dashboard_with_mocks):
        dashboard, _ = dashboard_with_mocks
        result = dashboard.generate("Manual Setup")
        assert "No campaign profile selected" in result

    def test_generate_campaign_not_found(self, dashboard_with_mocks):
        dashboard, mocks = dashboard_with_mocks
        mocks['campaign'].get_campaign_names.return_value = {"id1": "My Campaign"}
        result = dashboard.generate("Non-existent Campaign")
        assert "Campaign 'Non-existent Campaign' not found" in result

    def test_check_party_config_not_found(self, dashboard_with_mocks):
        dashboard, mocks = dashboard_with_mocks
        mocks['party'].get_party.return_value = None
        campaign = Campaign(name="Test", party_id="p1", settings=CampaignSettings())
        status = dashboard._check_party_config(campaign)
        assert not status.is_ok
        assert "Not configured" in status.details

    def test_check_party_config_success(self, dashboard_with_mocks):
        dashboard, mocks = dashboard_with_mocks
        party = Party(party_name="Heroes", dm_name="DM", characters=[
            Character(name="Aragorn", player="John", race="Human", class_name="Ranger", aliases=["Strider"])
        ])
        mocks['party'].get_party.return_value = party
        campaign = Campaign(name="Test", party_id="p1", settings=CampaignSettings())
        
        status = dashboard._check_party_config(campaign)
        assert status.is_ok
        assert "Aragorn" in status.details
        assert "Strider" in status.details

    @patch('src.campaign_dashboard.CampaignKnowledgeBase')
    def test_check_knowledge_base_states(self, MockKB, dashboard_with_mocks):
        dashboard, _ = dashboard_with_mocks

        # Test Empty State
        mock_kb_instance_empty = MockKB.return_value
        mock_kb_instance_empty.knowledge = {}
        status_empty = dashboard._check_knowledge_base("test_campaign")
        assert not status_empty.is_ok
        assert status_empty.title == "Knowledge Base (empty)"

        # Test Error State
        MockKB.side_effect = Exception("DB Load Error")
        status_error = dashboard._check_knowledge_base("test_campaign")
        assert not status_error.is_ok
        assert "Error loading" in status_error.details

    # Patch the manager where it is imported, inside the method's namespace
    @patch('src.character_profile.CharacterProfileManager')
    def test_check_character_profiles_logic(self, MockCharManager, dashboard_with_mocks):
        dashboard, mocks = dashboard_with_mocks
        mock_char_mgr_instance = MockCharManager.return_value
        party = Party(party_name="H", dm_name="DM", characters=[
            Character("Aragorn", "J", "H", "R"), Character("Gimli", "J2", "D", "F")
        ])
        mocks['party'].get_party.return_value = party
        campaign = Campaign(name="Test", party_id="p1", settings=CampaignSettings())

        # Case 1: All profiles exist
        mock_char_mgr_instance.profiles = {"Aragorn": MagicMock(), "Gimli": MagicMock()}
        mock_char_mgr_instance.get_profile.return_value = MagicMock(personality="Brave")
        status_complete = dashboard._check_character_profiles(campaign)
        assert status_complete.is_ok
        assert "Complete" in status_complete.details

        # Case 2: Some profiles are missing
        mock_char_mgr_instance.profiles = {"Aragorn": MagicMock()}
        status_partial = dashboard._check_character_profiles(campaign)
        assert not status_partial.is_ok
        assert "Partial" in status_partial.details
        assert "Missing**: Gimli" in status_partial.details

    @patch('builtins.open')
    @patch('json.load')
    def test_check_processed_sessions(self, mock_json_load, mock_open, dashboard_with_mocks):
        # Import here to access the mocked version from the autouse fixture
        from src.campaign_dashboard import Config
        dashboard, _ = dashboard_with_mocks

        # Case 1: Sessions found for the campaign
        Config.OUTPUT_DIR.exists.return_value = True
        mock_session_dir = MagicMock(spec=Path)
        mock_session_dir.name = "session_123"
        mock_session_dir.is_dir.return_value = True
        mock_data_file = MagicMock()
        mock_session_dir.glob.return_value = [mock_data_file]
        Config.OUTPUT_DIR.iterdir.return_value = [mock_session_dir]
        
        mock_json_load.return_value = {"campaign_id": "test_campaign"}

        mock_stat_result = MagicMock()
        mock_stat_result.st_mtime = 1
        mock_session_dir.stat.return_value = mock_stat_result

        status_found = dashboard._check_processed_sessions("test_campaign")
        assert status_found.is_ok
        assert "1 session(s) found" in status_found.details

        # Case 2: No sessions found
        Config.OUTPUT_DIR.exists.return_value = False
        status_none = dashboard._check_processed_sessions("test_campaign")
        assert not status_none.is_ok
        assert "No sessions processed yet" in status_none.details

    def test_generate_with_all_checks_failing(self, dashboard_with_mocks):
        dashboard, mocks = dashboard_with_mocks
        campaign = Campaign(name="Test Campaign", party_id="p1", settings=CampaignSettings())
        mocks['campaign'].get_campaign_names.return_value = {"test_id": "Test Campaign"}
        mocks['campaign'].get_campaign.return_value = campaign

        # This is the key insight: the mock needs to behave like the ComponentStatus object.
        from src.campaign_dashboard import ComponentStatus
        mock_failed_status = ComponentStatus(is_ok=False, title="Failed Check", details="This is a failure message.")

        with patch.object(dashboard, '_check_party_config', return_value=mock_failed_status), \
             patch.object(dashboard, '_check_processing_settings', return_value=mock_failed_status), \
             patch.object(dashboard, '_check_knowledge_base', return_value=mock_failed_status), \
             patch.object(dashboard, '_check_character_profiles', return_value=mock_failed_status), \
             patch.object(dashboard, '_check_processed_sessions', return_value=mock_failed_status), \
             patch.object(dashboard, '_check_session_narratives', return_value=mock_failed_status):

            result = dashboard.generate("Test Campaign")
            assert "Health: Needs Setup (0%)" in result
            assert "This is a failure message." in result
