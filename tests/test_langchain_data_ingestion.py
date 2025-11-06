"""
Tests for src/langchain/data_ingestion.py - Data Ingestion Pipeline
"""
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, call
from src.langchain.data_ingestion import DataIngestor


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock()
    store.add_transcript_segments = Mock()
    store.add_knowledge_documents = Mock()
    store.clear_all = Mock()
    return store


@pytest.fixture
def data_ingestor(mock_vector_store):
    """Create a DataIngestor instance for testing."""
    return DataIngestor(mock_vector_store)


@pytest.fixture
def sample_transcript_data():
    """Sample transcript data for testing."""
    return {
        "segments": [
            {"text": "Hello world", "speaker": "Alice", "start": 0.0, "end": 2.0},
            {"text": "How are you?", "speaker": "Bob", "start": 2.0, "end": 4.0},
            {"text": "", "speaker": "Charlie", "start": 4.0, "end": 5.0},  # Empty text (should be filtered)
            {"text": "  ", "speaker": "David", "start": 5.0, "end": 6.0}  # Whitespace only (should be filtered)
        ]
    }


@pytest.fixture
def sample_knowledge_base():
    """Sample knowledge base data for testing."""
    return {
        "npcs": [
            {"name": "Gandalf", "description": "A wise wizard"},
            {"name": "Frodo", "description": "A brave hobbit"}
        ],
        "quests": [
            {"name": "Ring Quest", "description": "Destroy the ring", "status": "active"},
            {"name": "Mountain Quest", "description": "Climb the mountain", "status": "complete"}
        ],
        "locations": [
            {"name": "Shire", "description": "Peaceful hobbit land"},
            {"name": "Mordor", "description": "Dark and dangerous"}
        ]
    }


class TestDataIngestorInit:
    """Tests for DataIngestor initialization."""

    def test_init_stores_vector_store(self, mock_vector_store):
        """Test that vector store is stored correctly."""
        ingestor = DataIngestor(mock_vector_store)
        assert ingestor.vector_store == mock_vector_store


class TestIngestSession:
    """Tests for ingest_session method."""

    def test_ingest_session_happy_path(self, data_ingestor, mock_vector_store, tmp_path, sample_transcript_data):
        """Test ingesting a session successfully."""
        # Create a session directory with transcript file
        session_dir = tmp_path / "session_001"
        session_dir.mkdir()
        transcript_file = session_dir / "diarized_transcript.json"
        transcript_file.write_text(json.dumps(sample_transcript_data))

        result = data_ingestor.ingest_session(session_dir)

        # Verify success
        assert result["success"] is True
        assert result["session_id"] == "session_001"
        assert result["segments_count"] == 2  # Only 2 non-empty segments

        # Verify vector store was called
        mock_vector_store.add_transcript_segments.assert_called_once()
        call_args = mock_vector_store.add_transcript_segments.call_args[0]
        assert call_args[0] == "session_001"
        assert len(call_args[1]) == 2  # 2 valid segments

    def test_ingest_session_directory_not_found(self, data_ingestor, tmp_path):
        """Test ingesting a non-existent session directory."""
        non_existent_dir = tmp_path / "non_existent_session"

        result = data_ingestor.ingest_session(non_existent_dir)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_ingest_session_not_a_directory(self, data_ingestor, tmp_path):
        """Test ingesting when path is not a directory."""
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("content")

        result = data_ingestor.ingest_session(file_path)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_ingest_session_no_transcript_file(self, data_ingestor, tmp_path):
        """Test ingesting a session without a transcript file."""
        session_dir = tmp_path / "session_no_transcript"
        session_dir.mkdir()

        result = data_ingestor.ingest_session(session_dir)

        assert result["success"] is False
        assert "no transcript" in result["error"].lower()

    def test_ingest_session_empty_transcript(self, data_ingestor, tmp_path):
        """Test ingesting a session with empty segments."""
        session_dir = tmp_path / "session_empty"
        session_dir.mkdir()
        transcript_file = session_dir / "diarized_transcript.json"
        transcript_file.write_text(json.dumps({"segments": []}))

        result = data_ingestor.ingest_session(session_dir)

        assert result["success"] is False
        assert "no segments" in result["error"].lower()

    def test_ingest_session_invalid_json(self, data_ingestor, tmp_path):
        """Test ingesting a session with invalid JSON."""
        session_dir = tmp_path / "session_invalid"
        session_dir.mkdir()
        transcript_file = session_dir / "diarized_transcript.json"
        transcript_file.write_text("invalid json {")

        result = data_ingestor.ingest_session(session_dir)

        assert result["success"] is False
        assert "error" in result

    def test_ingest_session_filters_empty_text(self, data_ingestor, mock_vector_store, tmp_path):
        """Test that segments with empty/whitespace-only text are filtered out."""
        session_dir = tmp_path / "session_filter"
        session_dir.mkdir()
        transcript_data = {
            "segments": [
                {"text": "Valid text", "speaker": "Alice", "start": 0.0, "end": 1.0},
                {"text": "", "speaker": "Bob", "start": 1.0, "end": 2.0},
                {"text": "   ", "speaker": "Charlie", "start": 2.0, "end": 3.0}
            ]
        }
        transcript_file = session_dir / "diarized_transcript.json"
        transcript_file.write_text(json.dumps(transcript_data))

        result = data_ingestor.ingest_session(session_dir)

        # Verify only 1 valid segment was added
        call_args = mock_vector_store.add_transcript_segments.call_args[0]
        assert len(call_args[1]) == 1
        assert call_args[1][0]["text"] == "Valid text"


class TestIngestKnowledgeBase:
    """Tests for ingest_knowledge_base method."""

    def test_ingest_knowledge_base_happy_path(self, data_ingestor, mock_vector_store, tmp_path, sample_knowledge_base):
        """Test ingesting a knowledge base successfully."""
        kb_file = tmp_path / "campaign_knowledge.json"
        kb_file.write_text(json.dumps(sample_knowledge_base))

        result = data_ingestor.ingest_knowledge_base(kb_file)

        # Verify success
        assert result["success"] is True
        assert result["source"] == "campaign_knowledge.json"
        assert result["documents_count"] == 6  # 2 NPCs + 2 quests + 2 locations

        # Verify vector store was called
        mock_vector_store.add_knowledge_documents.assert_called_once()
        call_args = mock_vector_store.add_knowledge_documents.call_args[0]
        documents = call_args[0]

        assert len(documents) == 6

        # Verify NPCs
        npc_docs = [d for d in documents if d["metadata"]["type"] == "npc"]
        assert len(npc_docs) == 2
        assert any("Gandalf" in d["text"] for d in npc_docs)

        # Verify quests
        quest_docs = [d for d in documents if d["metadata"]["type"] == "quest"]
        assert len(quest_docs) == 2
        assert any(d["metadata"]["status"] == "active" for d in quest_docs)

        # Verify locations
        location_docs = [d for d in documents if d["metadata"]["type"] == "location"]
        assert len(location_docs) == 2

    def test_ingest_knowledge_base_file_not_found(self, data_ingestor, tmp_path):
        """Test ingesting a non-existent knowledge base file."""
        non_existent_file = tmp_path / "non_existent.json"

        result = data_ingestor.ingest_knowledge_base(non_existent_file)

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_ingest_knowledge_base_empty(self, data_ingestor, tmp_path):
        """Test ingesting an empty knowledge base."""
        kb_file = tmp_path / "empty_knowledge.json"
        kb_file.write_text(json.dumps({}))

        result = data_ingestor.ingest_knowledge_base(kb_file)

        assert result["success"] is False
        assert "no documents" in result["error"].lower()

    def test_ingest_knowledge_base_handles_missing_fields(self, data_ingestor, mock_vector_store, tmp_path):
        """Test that missing fields are handled gracefully with defaults."""
        kb_data = {
            "npcs": [
                {"name": "NPC1"},  # Missing description
                {"description": "Desc2"}  # Missing name
            ]
        }
        kb_file = tmp_path / "partial_knowledge.json"
        kb_file.write_text(json.dumps(kb_data))

        result = data_ingestor.ingest_knowledge_base(kb_file)

        assert result["success"] is True

        # Verify defaults were used
        call_args = mock_vector_store.add_knowledge_documents.call_args[0]
        documents = call_args[0]

        assert any("NPC1" in d["text"] and "No description" in d["text"] for d in documents)
        assert any("Unknown" in d["text"] and "Desc2" in d["text"] for d in documents)

    def test_ingest_knowledge_base_invalid_json(self, data_ingestor, tmp_path):
        """Test ingesting a knowledge base with invalid JSON."""
        kb_file = tmp_path / "invalid_knowledge.json"
        kb_file.write_text("invalid json {")

        result = data_ingestor.ingest_knowledge_base(kb_file)

        assert result["success"] is False
        assert "error" in result


class TestIngestAll:
    """Tests for ingest_all method."""

    def test_ingest_all_happy_path(self, data_ingestor, mock_vector_store, tmp_path, sample_transcript_data, sample_knowledge_base):
        """Test ingesting all sessions and knowledge bases."""
        # Create output directory with sessions
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        session1_dir = output_dir / "session_001"
        session1_dir.mkdir()
        (session1_dir / "diarized_transcript.json").write_text(json.dumps(sample_transcript_data))

        session2_dir = output_dir / "session_002"
        session2_dir.mkdir()
        (session2_dir / "diarized_transcript.json").write_text(json.dumps(sample_transcript_data))

        # Create knowledge directory
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        (knowledge_dir / "campaign_knowledge.json").write_text(json.dumps(sample_knowledge_base))

        stats = data_ingestor.ingest_all(output_dir, knowledge_dir, clear_existing=False)

        # Verify stats
        assert stats["sessions_ingested"] == 2
        assert stats["sessions_failed"] == 0
        assert stats["knowledge_bases_ingested"] == 1
        assert stats["knowledge_bases_failed"] == 0
        assert stats["total_segments"] == 4  # 2 sessions * 2 valid segments each
        assert stats["total_documents"] == 6  # 6 knowledge documents

        # Verify vector store was NOT cleared
        mock_vector_store.clear_all.assert_not_called()

    def test_ingest_all_with_clear_existing(self, data_ingestor, mock_vector_store, tmp_path):
        """Test ingesting with clear_existing=True."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()

        data_ingestor.ingest_all(output_dir, knowledge_dir, clear_existing=True)

        # Verify vector store was cleared
        mock_vector_store.clear_all.assert_called_once()

    def test_ingest_all_output_dir_not_found(self, data_ingestor, tmp_path):
        """Test ingesting when output directory doesn't exist."""
        non_existent_output = tmp_path / "non_existent_output"
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()

        stats = data_ingestor.ingest_all(non_existent_output, knowledge_dir)

        # Should handle gracefully
        assert stats["sessions_ingested"] == 0
        assert stats["sessions_failed"] == 0

    def test_ingest_all_knowledge_dir_not_found(self, data_ingestor, tmp_path):
        """Test ingesting when knowledge directory doesn't exist."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        non_existent_knowledge = tmp_path / "non_existent_knowledge"

        stats = data_ingestor.ingest_all(output_dir, non_existent_knowledge)

        # Should handle gracefully
        assert stats["knowledge_bases_ingested"] == 0
        assert stats["knowledge_bases_failed"] == 0

    def test_ingest_all_handles_session_failures(self, data_ingestor, tmp_path):
        """Test that failed sessions are counted correctly."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a session without transcript (will fail)
        session_bad = output_dir / "session_bad"
        session_bad.mkdir()

        # Create a non-directory item (should be skipped)
        (output_dir / "not_a_directory.txt").write_text("content")

        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()

        stats = data_ingestor.ingest_all(output_dir, knowledge_dir)

        assert stats["sessions_ingested"] == 0
        assert stats["sessions_failed"] == 1  # session_bad failed

    def test_ingest_all_handles_knowledge_base_failures(self, data_ingestor, tmp_path):
        """Test that failed knowledge bases are counted correctly."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()

        # Create an invalid knowledge base
        (knowledge_dir / "invalid_knowledge.json").write_text("invalid json {")

        stats = data_ingestor.ingest_all(output_dir, knowledge_dir)

        assert stats["knowledge_bases_ingested"] == 0
        assert stats["knowledge_bases_failed"] == 1


class TestPrepareSegments:
    """Tests for _prepare_segments method."""

    def test_prepare_segments_filters_empty_text(self, data_ingestor):
        """Test that empty and whitespace-only segments are filtered."""
        transcript_data = {
            "segments": [
                {"text": "Valid", "speaker": "Alice", "start": 0.0, "end": 1.0},
                {"text": "", "speaker": "Bob", "start": 1.0, "end": 2.0},
                {"text": "   ", "speaker": "Charlie", "start": 2.0, "end": 3.0},
                {"text": "Also valid", "speaker": "David", "start": 3.0, "end": 4.0}
            ]
        }

        segments = data_ingestor._prepare_segments(transcript_data)

        assert len(segments) == 2
        assert segments[0]["text"] == "Valid"
        assert segments[1]["text"] == "Also valid"

    def test_prepare_segments_handles_missing_fields(self, data_ingestor):
        """Test that missing fields are handled with defaults."""
        transcript_data = {
            "segments": [
                {"text": "Text only"},
                {"text": "Text with speaker", "speaker": "Alice"}
            ]
        }

        segments = data_ingestor._prepare_segments(transcript_data)

        assert segments[0]["speaker"] == "Unknown"
        assert segments[0]["start"] == 0
        assert segments[0]["end"] == 0
        assert segments[1]["speaker"] == "Alice"

    def test_prepare_segments_empty_input(self, data_ingestor):
        """Test preparing segments from empty transcript data."""
        assert data_ingestor._prepare_segments({}) == []
        assert data_ingestor._prepare_segments({"segments": []}) == []


class TestLoadKnowledgeBase:
    """Tests for _load_knowledge_base method."""

    def test_load_knowledge_base_happy_path(self, data_ingestor, tmp_path):
        """Test loading a knowledge base file."""
        kb_data = {"npcs": [{"name": "Test NPC"}]}
        kb_file = tmp_path / "test_knowledge.json"
        kb_file.write_text(json.dumps(kb_data))

        result = data_ingestor._load_knowledge_base(kb_file)

        assert result == kb_data
        assert "npcs" in result
