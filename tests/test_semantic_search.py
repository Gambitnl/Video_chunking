"""
Tests for semantic search functionality (P2-LANGCHAIN-002).
"""
import pytest
from pathlib import Path
import json
import tempfile
import shutil

# Mark all tests in this file to be skipped if dependencies not available
pytest_plugins = []

try:
    from src.langchain.embeddings import EmbeddingService
    from src.langchain.vector_store import CampaignVectorStore
    from src.langchain.data_ingestion import DataIngestor
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not LANGCHAIN_AVAILABLE,
    reason="LangChain dependencies not installed"
)


class TestEmbeddingService:
    """Tests for embedding generation."""

    def test_embed_single_text(self):
        """Test generating embedding for single text."""
        service = EmbeddingService()
        text = "This is a test sentence"

        embedding = service.embed(text)

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_batch(self):
        """Test batch embedding generation."""
        service = EmbeddingService()
        texts = [
            "First test sentence",
            "Second test sentence",
            "Third test sentence"
        ]

        embeddings = service.embed_batch(texts)

        assert len(embeddings) == len(texts)
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) > 0 for emb in embeddings)

    def test_embedding_dimension(self):
        """Test getting embedding dimension."""
        service = EmbeddingService()
        dim = service.get_embedding_dimension()

        assert isinstance(dim, int)
        assert dim > 0


class TestCampaignVectorStore:
    """Tests for vector store operations."""

    def test_add_transcript_segments(self, tmp_path):
        """Test adding transcript segments to vector store."""
        service = EmbeddingService()
        vector_store = CampaignVectorStore(tmp_path, service)

        segments = [
            {
                "text": "You enter the dark forest",
                "speaker": "DM",
                "start": 0.0,
                "end": 5.0
            },
            {
                "text": "I want to search for tracks",
                "speaker": "Player 1",
                "start": 5.0,
                "end": 8.0
            }
        ]

        vector_store.add_transcript_segments("session_001", segments)

        # Verify stats
        stats = vector_store.get_stats()
        assert stats["transcript_segments"] == 2
        assert stats["knowledge_documents"] == 0

    def test_add_knowledge_documents(self, tmp_path):
        """Test adding knowledge base documents."""
        service = EmbeddingService()
        vector_store = CampaignVectorStore(tmp_path, service)

        documents = [
            {
                "text": "Shadow Lord: A powerful necromancer",
                "metadata": {"type": "npc", "name": "Shadow Lord"}
            },
            {
                "text": "Crystal of Souls: An ancient artifact",
                "metadata": {"type": "quest", "name": "Crystal of Souls"}
            }
        ]

        vector_store.add_knowledge_documents(documents)

        # Verify stats
        stats = vector_store.get_stats()
        assert stats["knowledge_documents"] == 2
        assert stats["transcript_segments"] == 0

    def test_semantic_search(self, tmp_path):
        """Test semantic search."""
        service = EmbeddingService()
        vector_store = CampaignVectorStore(tmp_path, service)

        # Add some documents
        segments = [
            {
                "text": "The dark wizard casts a powerful spell",
                "speaker": "DM",
                "start": 0.0,
                "end": 5.0
            },
            {
                "text": "The tavern is crowded with adventurers",
                "speaker": "DM",
                "start": 10.0,
                "end": 15.0
            }
        ]

        vector_store.add_transcript_segments("session_001", segments)

        # Search for related content
        results = vector_store.search("wizard magic", top_k=5)

        assert len(results) > 0
        # First result should be about the wizard
        assert "wizard" in results[0]["text"].lower()

    def test_delete_session(self, tmp_path):
        """Test deleting session data."""
        service = EmbeddingService()
        vector_store = CampaignVectorStore(tmp_path, service)

        # Add segments
        segments = [
            {
                "text": "Test segment",
                "speaker": "DM",
                "start": 0.0,
                "end": 5.0
            }
        ]

        vector_store.add_transcript_segments("session_001", segments)

        # Delete session
        vector_store.delete_session("session_001")

        # Verify deletion
        stats = vector_store.get_stats()
        assert stats["transcript_segments"] == 0

    def test_clear_all(self, tmp_path):
        """Test clearing all data."""
        service = EmbeddingService()
        vector_store = CampaignVectorStore(tmp_path, service)

        # Add some data
        segments = [{"text": "Test", "speaker": "DM", "start": 0.0, "end": 5.0}]
        vector_store.add_transcript_segments("session_001", segments)

        documents = [{"text": "Test NPC", "metadata": {"type": "npc", "name": "Test"}}]
        vector_store.add_knowledge_documents(documents)

        # Clear all
        vector_store.clear_all()

        # Verify empty
        stats = vector_store.get_stats()
        assert stats["transcript_segments"] == 0
        assert stats["knowledge_documents"] == 0


class TestDataIngestor:
    """Tests for data ingestion pipeline."""

    def test_ingest_session(self, tmp_path):
        """Test ingesting a single session."""
        service = EmbeddingService()
        vector_store = CampaignVectorStore(tmp_path / "vector_db", service)
        ingestor = DataIngestor(vector_store)

        # Create a test session
        session_dir = tmp_path / "session_001"
        session_dir.mkdir()

        transcript_data = {
            "segments": [
                {
                    "text": "Welcome to the adventure",
                    "speaker": "DM",
                    "start": 0.0,
                    "end": 5.0
                }
            ]
        }

        transcript_file = session_dir / "diarized_transcript.json"
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(transcript_data, f)

        # Ingest session
        result = ingestor.ingest_session(session_dir)

        assert result["success"] is True
        assert result["session_id"] == "session_001"
        assert result["segments_count"] == 1

    def test_ingest_knowledge_base(self, tmp_path):
        """Test ingesting a knowledge base."""
        service = EmbeddingService()
        vector_store = CampaignVectorStore(tmp_path / "vector_db", service)
        ingestor = DataIngestor(vector_store)

        # Create a test knowledge base
        kb_data = {
            "npcs": [
                {"name": "Test NPC", "description": "A test character"}
            ],
            "quests": [],
            "locations": []
        }

        kb_file = tmp_path / "test_knowledge.json"
        with open(kb_file, "w", encoding="utf-8") as f:
            json.dump(kb_data, f)

        # Ingest knowledge base
        result = ingestor.ingest_knowledge_base(kb_file)

        assert result["success"] is True
        assert result["documents_count"] == 1

    def test_ingest_all(self, tmp_path):
        """Test ingesting all data."""
        service = EmbeddingService()
        vector_store = CampaignVectorStore(tmp_path / "vector_db", service)
        ingestor = DataIngestor(vector_store)

        # Create output directory with session
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        session_dir = output_dir / "session_001"
        session_dir.mkdir()

        transcript_data = {
            "segments": [
                {"text": "Test", "speaker": "DM", "start": 0.0, "end": 5.0}
            ]
        }

        with open(session_dir / "diarized_transcript.json", "w", encoding="utf-8") as f:
            json.dump(transcript_data, f)

        # Create knowledge directory
        kb_dir = tmp_path / "knowledge"
        kb_dir.mkdir()

        kb_data = {"npcs": [{"name": "Test", "description": "Test"}], "quests": [], "locations": []}

        with open(kb_dir / "test_knowledge.json", "w", encoding="utf-8") as f:
            json.dump(kb_data, f)

        # Ingest all
        stats = ingestor.ingest_all(output_dir, kb_dir, clear_existing=True)

        assert stats["sessions_ingested"] == 1
        assert stats["knowledge_bases_ingested"] == 1
        assert stats["total_segments"] == 1
        assert stats["total_documents"] == 1


@pytest.fixture
def tmp_path():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)
