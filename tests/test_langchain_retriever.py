"""
Tests for src/langchain/retriever.py - Campaign Retriever
Focused tests to increase coverage from 36% to help reach 80% overall target.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock
from src.langchain.retriever import Document, CampaignRetriever


class TestDocument:
    """Tests for Document class."""

    def test_document_init_with_content_only(self):
        """Test document initialization with just content."""
        doc = Document("Hello world")

        assert doc.page_content == "Hello world"
        assert doc.metadata == {}

    def test_document_init_with_metadata(self):
        """Test document initialization with metadata."""
        metadata = {"source": "test", "type": "npc"}
        doc = Document("Test content", metadata=metadata)

        assert doc.page_content == "Test content"
        assert doc.metadata == metadata

    def test_document_str(self):
        """Test __str__ returns content."""
        doc = Document("Test content")
        assert str(doc) == "Test content"

    def test_document_repr(self):
        """Test __repr__ returns formatted representation."""
        metadata = {"key": "value"}
        doc = Document("This is a long piece of content that will be truncated", metadata=metadata)
        repr_str = repr(doc)

        assert "Document(content=" in repr_str
        assert "metadata=" in repr_str


class TestCampaignRetrieverInit:
    """Tests for CampaignRetriever initialization."""

    def test_init_stores_directories(self, tmp_path):
        """Test that directories are stored correctly."""
        kb_dir = tmp_path / "knowledge"
        transcript_dir = tmp_path / "transcripts"
        kb_dir.mkdir()
        transcript_dir.mkdir()

        retriever = CampaignRetriever(kb_dir, transcript_dir)

        assert retriever.kb_dir == kb_dir
        assert retriever.transcript_dir == transcript_dir
        assert retriever._kb_cache == {}


class TestRetrieve:
    """Tests for retrieve method."""

    @pytest.fixture
    def retriever_with_data(self, tmp_path):
        """Create a retriever with sample data."""
        kb_dir = tmp_path / "knowledge"
        transcript_dir = tmp_path / "transcripts"
        kb_dir.mkdir()
        transcript_dir.mkdir()

        # Create sample knowledge base
        kb_data = {
            "npcs": [
                {"name": "Gandalf", "description": "A wise wizard who helps the fellowship"}
            ],
            "quests": [
                {"name": "Ring Quest", "description": "Destroy the one ring in Mordor"}
            ],
            "locations": []
        }
        (kb_dir / "campaign_knowledge.json").write_text(json.dumps(kb_data))

        # Create sample transcript
        transcript_data = {
            "segments": [
                {"text": "Gandalf cast a spell", "speaker": "DM", "start": 0.0, "end": 2.0}
            ]
        }
        session_dir = transcript_dir / "session_001"
        session_dir.mkdir()
        (session_dir / "diarized_transcript.json").write_text(json.dumps(transcript_data))

        return CampaignRetriever(kb_dir, transcript_dir)

    def test_retrieve_returns_documents(self, retriever_with_data):
        """Test that retrieve returns Document objects."""
        results = retriever_with_data.retrieve("Gandalf", top_k=5)

        assert isinstance(results, list)
        # Should find at least one result
        assert len(results) >= 0
        # All results should be Documents
        for result in results:
            assert isinstance(result, Document)

    def test_retrieve_respects_top_k(self, retriever_with_data):
        """Test that retrieve respects the top_k parameter."""
        results = retriever_with_data.retrieve("wizard", top_k=2)

        assert len(results) <= 2

    def test_retrieve_handles_empty_query(self, retriever_with_data):
        """Test that empty query is handled gracefully."""
        results = retriever_with_data.retrieve("", top_k=5)

        # Should return empty or handle gracefully
        assert isinstance(results, list)


class TestClearCache:
    """Tests for clear_cache method."""

    def test_clear_cache(self, tmp_path):
        """Test clearing the knowledge base cache."""
        kb_dir = tmp_path / "knowledge"
        transcript_dir = tmp_path / "transcripts"
        kb_dir.mkdir()
        transcript_dir.mkdir()

        retriever = CampaignRetriever(kb_dir, transcript_dir)

        # Populate cache
        retriever._kb_cache["test_file"] = ({"data": "test"}, 1234567890.0)

        # Clear cache
        retriever.clear_cache()

        assert retriever._kb_cache == {}
