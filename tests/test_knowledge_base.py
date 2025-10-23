
import pytest
from unittest.mock import patch, MagicMock
import json
from pathlib import Path

# Mock the config before other imports
@pytest.fixture(autouse=True)
def mock_config():
    with patch('src.knowledge_base.Config') as MockConfig:
        MockConfig.OLLAMA_BASE_URL = 'http://localhost:11434'
        MockConfig.OLLAMA_MODEL = 'test-model'
        MockConfig.MODELS_DIR = Path("/tmp/models")
        yield MockConfig

from src.knowledge_base import (
    KnowledgeExtractor,
    CampaignKnowledgeBase,
    Quest,
    NPC
)

@pytest.fixture
def mock_ollama_client():
    with patch('ollama.Client') as MockClient:
        yield MockClient.return_value

@pytest.fixture
def knowledge_base(tmp_path):
    """Provides a CampaignKnowledgeBase instance using a temporary directory."""
    # Override the config for this specific test
    with patch('src.knowledge_base.Config') as MockConfig:
        MockConfig.MODELS_DIR = tmp_path
        kb = CampaignKnowledgeBase(campaign_id="test_campaign")
        yield kb

class TestKnowledgeExtractor:

    def test_extract_knowledge_success(self, mock_ollama_client):
        # Arrange
        extractor = KnowledgeExtractor()
        mock_response = {
            'message': {
                'content': '''```json
                {
                  "quests": [{"title": "Test Quest", "description": "A quest", "status": "active"}],
                  "npcs": [{"name": "Test NPC", "description": "An NPC", "role": "ally"}]
                }
                ```'''
            }
        }
        mock_ollama_client.chat.return_value = mock_response

        # Act
        result = extractor.extract_knowledge("some transcript", "session1")

        # Assert
        assert len(result['quests']) == 1
        assert isinstance(result['quests'][0], Quest)
        assert result['quests'][0].title == "Test Quest"
        assert result['quests'][0].first_mentioned == "session1"

        assert len(result['npcs']) == 1
        assert isinstance(result['npcs'][0], NPC)
        assert result['npcs'][0].name == "Test NPC"

    def test_extract_knowledge_failure(self, mock_ollama_client):
        # Arrange
        extractor = KnowledgeExtractor()
        mock_ollama_client.chat.side_effect = Exception("LLM is down")

        # Act
        result = extractor.extract_knowledge("some transcript", "session1")

        # Assert
        assert result == {'quests': [], 'npcs': [], 'plot_hooks': [], 'locations': [], 'items': []}

class TestCampaignKnowledgeBase:

    def test_init_creates_default_kb(self, knowledge_base):
        assert knowledge_base.campaign_id == "test_campaign"
        assert knowledge_base.knowledge['quests'] == []
        assert not knowledge_base.knowledge_file.exists() # Not saved until modified

    def test_merge_new_and_update_existing_knowledge(self, knowledge_base):
        # Arrange: Add initial data
        initial_quest = Quest(title="Initial Quest", description="...", status="active", first_mentioned="s0", last_updated="s0")
        initial_npc = NPC(name="Old Man", description="...", first_mentioned="s0", last_updated="s0", appearances=["s0"])
        knowledge_base.knowledge['quests'].append(initial_quest)
        knowledge_base.knowledge['npcs'].append(initial_npc)

        new_knowledge = {
            'quests': [Quest(title="Initial Quest", description="updated desc", status="completed", first_mentioned="s1", last_updated="s1")],
            'npcs': [
                NPC(name="Old Man", description="...", first_mentioned="s1", last_updated="s1"),
                NPC(name="New Character", description="...", first_mentioned="s1", last_updated="s1")
            ]
        }

        # Act
        knowledge_base.merge_new_knowledge(new_knowledge, "session1")

        # Assert
        # Quest was updated
        assert len(knowledge_base.knowledge['quests']) == 1
        updated_quest = knowledge_base.knowledge['quests'][0]
        assert updated_quest.status == "completed"
        assert updated_quest.description == "updated desc"
        assert updated_quest.last_updated == "session1"

        # NPC was updated and new one was added
        assert len(knowledge_base.knowledge['npcs']) == 2
        updated_npc = next(n for n in knowledge_base.knowledge['npcs'] if n.name == "Old Man")
        assert "session1" in updated_npc.appearances
        assert updated_npc.last_updated == "session1"

        # Session was tracked
        assert "session1" in knowledge_base.knowledge['sessions_processed']

    def test_save_and_load_knowledge(self, knowledge_base, tmp_path):
        # Arrange
        knowledge_base.knowledge['quests'].append(Quest(title="Save Test", description="...", status="active", first_mentioned="s1", last_updated="s1"))
        knowledge_base._save_knowledge()

        # Act: Create a new KB instance to load the file
        new_kb = CampaignKnowledgeBase(campaign_id="test_campaign")

        # Assert
        assert new_kb.knowledge_file.exists()
        assert len(new_kb.knowledge['quests']) == 1
        assert isinstance(new_kb.knowledge['quests'][0], Quest)
        assert new_kb.knowledge['quests'][0].title == "Save Test"

    def test_search_knowledge(self, knowledge_base):
        # Arrange
        knowledge_base.knowledge['quests'].append(Quest(title="Find the sword", description="...", status="active", first_mentioned="s1", last_updated="s1"))
        knowledge_base.knowledge['npcs'].append(NPC(name="The Blacksmith", description="Makes swords", first_mentioned="s1", last_updated="s1"))
        knowledge_base.knowledge['items'] = []

        # Act
        results = knowledge_base.search_knowledge("sword")

        # Assert
        assert len(results['quests']) == 1
        assert len(results['npcs']) == 1
        assert len(results['items']) == 0
        assert results['quests'][0].title == "Find the sword"
        assert results['npcs'][0].name == "The Blacksmith"
