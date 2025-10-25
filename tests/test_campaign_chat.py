"""
Tests for campaign chat functionality (P2-LANGCHAIN-001).
"""
import pytest
from pathlib import Path
import json
import tempfile
import shutil

from src.langchain.conversation_store import ConversationStore
from src.langchain.retriever import CampaignRetriever, Document


class TestConversationStore:
    """Tests for conversation persistence."""

    def test_create_conversation(self, tmp_path):
        """Test creating a new conversation."""
        store = ConversationStore(tmp_path)
        conv_id = store.create_conversation(campaign="Test Campaign")

        assert conv_id.startswith("conv_")

        # Verify conversation file exists
        conv_file = tmp_path / f"{conv_id}.json"
        assert conv_file.exists()

        # Load and verify structure
        conversation = store.load_conversation(conv_id)
        assert conversation is not None
        assert conversation["conversation_id"] == conv_id
        assert conversation["context"]["campaign"] == "Test Campaign"
        assert len(conversation["messages"]) == 0

    def test_add_message(self, tmp_path):
        """Test adding messages to a conversation."""
        store = ConversationStore(tmp_path)
        conv_id = store.create_conversation()

        # Add user message
        user_msg = store.add_message(conv_id, "user", "Test question")
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "Test question"

        # Add assistant message with sources
        sources = [
            {
                "content": "Test source",
                "metadata": {"session_id": "session_001", "type": "transcript"}
            }
        ]
        asst_msg = store.add_message(conv_id, "assistant", "Test answer", sources)
        assert asst_msg["role"] == "assistant"
        assert asst_msg["sources"] == sources

        # Verify messages persisted
        conversation = store.load_conversation(conv_id)
        assert len(conversation["messages"]) == 2
        assert "session_001" in conversation["context"]["relevant_sessions"]

    def test_list_conversations(self, tmp_path):
        """Test listing conversations."""
        store = ConversationStore(tmp_path)

        # Create multiple conversations
        conv_id1 = store.create_conversation(campaign="Campaign 1")
        conv_id2 = store.create_conversation(campaign="Campaign 2")

        # Add messages to first conversation
        store.add_message(conv_id1, "user", "Message 1")
        store.add_message(conv_id1, "assistant", "Response 1")

        # List conversations
        conversations = store.list_conversations()
        assert len(conversations) == 2

        # Verify sorting by updated_at (most recent first)
        assert conversations[0]["conversation_id"] == conv_id1  # Updated more recently
        assert conversations[0]["message_count"] == 2

    def test_delete_conversation(self, tmp_path):
        """Test deleting a conversation."""
        store = ConversationStore(tmp_path)
        conv_id = store.create_conversation()

        # Delete conversation
        result = store.delete_conversation(conv_id)
        assert result is True

        # Verify file deleted
        conv_file = tmp_path / f"{conv_id}.json"
        assert not conv_file.exists()

        # Try to load deleted conversation
        conversation = store.load_conversation(conv_id)
        assert conversation is None


class TestCampaignRetriever:
    """Tests for knowledge base retriever."""

    def test_search_knowledge_bases(self, tmp_path):
        """Test searching knowledge bases."""
        kb_dir = tmp_path / "knowledge"
        kb_dir.mkdir()

        # Create a test knowledge base
        kb_data = {
            "npcs": [
                {
                    "name": "Shadow Lord",
                    "description": "A powerful necromancer seeking the Crystal of Souls"
                }
            ],
            "quests": [
                {
                    "name": "Rescue the Prince",
                    "description": "Save Prince Aldric from the Shadow Lord's fortress"
                }
            ]
        }

        kb_file = kb_dir / "test_knowledge.json"
        with open(kb_file, "w", encoding="utf-8") as f:
            json.dump(kb_data, f)

        # Create retriever and search
        transcript_dir = tmp_path / "transcripts"
        transcript_dir.mkdir()

        retriever = CampaignRetriever(kb_dir, transcript_dir)
        results = retriever.retrieve("Shadow Lord", top_k=5)

        assert len(results) > 0
        assert any("Shadow Lord" in r.page_content for r in results)

    def test_search_transcripts(self, tmp_path):
        """Test searching session transcripts."""
        kb_dir = tmp_path / "knowledge"
        kb_dir.mkdir()

        transcript_dir = tmp_path / "transcripts"
        transcript_dir.mkdir()

        # Create a test session with transcript
        session_dir = transcript_dir / "session_001"
        session_dir.mkdir()

        transcript_data = {
            "segments": [
                {
                    "text": "You approach the Shadow Lord's fortress",
                    "speaker": "DM",
                    "start": 123.45,
                    "end": 130.00
                }
            ]
        }

        transcript_file = session_dir / "diarized_transcript.json"
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f)

        # Search transcripts
        retriever = CampaignRetriever(kb_dir, transcript_dir)
        results = retriever.retrieve("fortress", top_k=5)

        assert len(results) > 0
        assert any("fortress" in r.page_content.lower() for r in results)

    def test_ranking(self, tmp_path):
        """Test that results are ranked by relevance."""
        kb_dir = tmp_path / "knowledge"
        kb_dir.mkdir()

        transcript_dir = tmp_path / "transcripts"
        transcript_dir.mkdir()

        # Create retriever
        retriever = CampaignRetriever(kb_dir, transcript_dir)

        # Test ranking logic
        doc1 = Document("The dark wizard is a powerful necromancer", {"type": "npc"})
        doc2 = Document("The tavern is located in the town square", {"type": "location"})
        doc3 = Document("The dark wizard seeks the crystal", {"type": "quest"})

        results = [doc1, doc2, doc3]
        ranked = retriever._rank_results(results, "dark wizard")

        # Documents mentioning "dark wizard" should rank higher
        assert "dark wizard" in ranked[0].page_content.lower()


@pytest.fixture
def tmp_path():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)
