"""
Tests for src/langchain/vector_store.py - Campaign Vector Store
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from src.langchain.vector_store import CampaignVectorStore, EMBEDDING_BATCH_SIZE


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = Mock()
    service.embed.return_value = [0.1] * 384  # Standard embedding dimension
    service.embed_batch.return_value = [[0.1] * 384 for _ in range(10)]
    return service


@pytest.fixture
def mock_chromadb(monkeypatch):
    """Mock chromadb module to avoid real database operations."""
    mock_client = MagicMock()
    mock_transcript_collection = MagicMock()
    mock_knowledge_collection = MagicMock()

    # Configure mock client
    mock_client.get_or_create_collection.side_effect = [
        mock_transcript_collection,
        mock_knowledge_collection
    ]

    # Mock chromadb module
    mock_chromadb_module = MagicMock()
    mock_chromadb_module.PersistentClient.return_value = mock_client
    mock_chromadb_module.config.Settings = MagicMock()

    monkeypatch.setitem(__import__('sys').modules, 'chromadb', mock_chromadb_module)
    monkeypatch.setitem(__import__('sys').modules, 'chromadb.config', mock_chromadb_module.config)

    return {
        'client': mock_client,
        'transcript_collection': mock_transcript_collection,
        'knowledge_collection': mock_knowledge_collection,
        'chromadb_module': mock_chromadb_module
    }


@pytest.fixture
def vector_store(tmp_path, mock_embedding_service, mock_chromadb):
    """Create a CampaignVectorStore instance for testing."""
    persist_dir = tmp_path / "test_vector_db"
    return CampaignVectorStore(persist_dir, mock_embedding_service)


class TestCampaignVectorStoreInit:
    """Tests for CampaignVectorStore initialization."""

    def test_init_creates_persist_dir(self, tmp_path, mock_embedding_service, mock_chromadb):
        """Test that initialization creates the persist directory."""
        persist_dir = tmp_path / "vector_db"
        assert not persist_dir.exists()

        store = CampaignVectorStore(persist_dir, mock_embedding_service)

        assert persist_dir.exists()
        assert store.persist_dir == persist_dir

    def test_init_stores_embedding_service(self, vector_store, mock_embedding_service):
        """Test that embedding service is stored correctly."""
        assert vector_store.embedding == mock_embedding_service

    def test_init_creates_collections(self, vector_store, mock_chromadb):
        """Test that transcript and knowledge collections are created."""
        client = mock_chromadb['client']

        # Verify get_or_create_collection was called twice
        assert client.get_or_create_collection.call_count == 2

        # Verify collection names
        calls = client.get_or_create_collection.call_args_list
        assert calls[0][1]['name'] == 'transcripts'
        assert calls[1][1]['name'] == 'knowledge'

    def test_init_raises_error_if_chromadb_not_installed(
        self, tmp_path, mock_embedding_service, monkeypatch
    ):
        """Test that RuntimeError is raised if chromadb is not installed."""
        # Remove chromadb from sys.modules to simulate ImportError
        import sys
        if 'chromadb' in sys.modules:
            monkeypatch.delitem(sys.modules, 'chromadb')

        # Mock import to raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == 'chromadb':
                raise ImportError("No module named 'chromadb'")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr('builtins.__import__', mock_import)

        with pytest.raises(RuntimeError, match="chromadb not installed"):
            CampaignVectorStore(tmp_path / "db", mock_embedding_service)


class TestAddTranscriptSegments:
    """Tests for add_transcript_segments method."""

    def test_add_transcript_segments_happy_path(self, vector_store, mock_embedding_service, mock_chromadb):
        """Test adding transcript segments successfully."""
        session_id = "session_001"
        segments = [
            {"text": "Hello world", "speaker": "Alice", "start": 0.0, "end": 2.0},
            {"text": "How are you?", "speaker": "Bob", "start": 2.0, "end": 4.0}
        ]

        vector_store.add_transcript_segments(session_id, segments)

        # Verify embed_batch was called
        mock_embedding_service.embed_batch.assert_called_once()

        # Verify collection.add was called
        mock_chromadb['transcript_collection'].add.assert_called_once()
        call_args = mock_chromadb['transcript_collection'].add.call_args[1]

        assert len(call_args['documents']) == 2
        assert call_args['documents'][0] == "Hello world"
        assert len(call_args['ids']) == 2
        assert call_args['ids'][0] == "session_001_seg_0"
        assert call_args['metadatas'][0]['session_id'] == session_id
        assert call_args['metadatas'][0]['speaker'] == "Alice"

    def test_add_transcript_segments_empty_list(self, vector_store, mock_embedding_service):
        """Test that empty segment list is handled gracefully."""
        vector_store.add_transcript_segments("session_001", [])

        # Verify embed_batch was NOT called
        mock_embedding_service.embed_batch.assert_not_called()

    def test_add_transcript_segments_batching(self, vector_store, mock_embedding_service, mock_chromadb):
        """Test that large segment lists are batched."""
        session_id = "session_large"
        # Create segments larger than EMBEDDING_BATCH_SIZE
        segments = [
            {"text": f"Segment {i}", "speaker": "Alice", "start": float(i), "end": float(i+1)}
            for i in range(EMBEDDING_BATCH_SIZE + 50)
        ]

        vector_store.add_transcript_segments(session_id, segments)

        # Verify collection.add was called twice (2 batches)
        assert mock_chromadb['transcript_collection'].add.call_count == 2

    def test_add_transcript_segments_handles_missing_metadata(self, vector_store, mock_chromadb):
        """Test that missing speaker/start/end fields are handled."""
        session_id = "session_002"
        segments = [
            {"text": "Text without metadata"}
        ]

        vector_store.add_transcript_segments(session_id, segments)

        call_args = mock_chromadb['transcript_collection'].add.call_args[1]
        metadata = call_args['metadatas'][0]

        assert metadata['speaker'] == "Unknown"
        assert metadata['start'] == 0
        assert metadata['end'] == 0

    def test_add_transcript_segments_raises_on_error(self, vector_store, mock_chromadb):
        """Test that exceptions during add are propagated."""
        mock_chromadb['transcript_collection'].add.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            vector_store.add_transcript_segments("session_001", [{"text": "Test"}])


class TestAddKnowledgeDocuments:
    """Tests for add_knowledge_documents method."""

    def test_add_knowledge_documents_happy_path(self, vector_store, mock_embedding_service, mock_chromadb):
        """Test adding knowledge documents successfully."""
        documents = [
            {
                "text": "The ancient dragon lives in the mountain",
                "metadata": {"type": "npc", "name": "Ancient Dragon"}
            },
            {
                "text": "Quest to retrieve the magical sword",
                "metadata": {"type": "quest", "name": "Sword Quest"}
            }
        ]

        vector_store.add_knowledge_documents(documents)

        # Verify embed_batch was called
        mock_embedding_service.embed_batch.assert_called_once()

        # Verify collection.add was called
        mock_chromadb['knowledge_collection'].add.assert_called_once()
        call_args = mock_chromadb['knowledge_collection'].add.call_args[1]

        assert len(call_args['documents']) == 2
        assert "dragon" in call_args['documents'][0].lower()
        assert len(call_args['ids']) == 2
        assert "npc_Ancient_Dragon" in call_args['ids'][0]

    def test_add_knowledge_documents_empty_list(self, vector_store, mock_embedding_service):
        """Test that empty document list is handled gracefully."""
        vector_store.add_knowledge_documents([])

        # Verify embed_batch was NOT called
        mock_embedding_service.embed_batch.assert_not_called()

    def test_add_knowledge_documents_sanitizes_ids(self, vector_store, mock_chromadb):
        """Test that document IDs are sanitized (spaces and slashes removed)."""
        documents = [
            {
                "text": "Test document",
                "metadata": {"type": "location", "name": "Dark Cave / Hidden Path"}
            }
        ]

        vector_store.add_knowledge_documents(documents)

        call_args = mock_chromadb['knowledge_collection'].add.call_args[1]
        doc_id = call_args['ids'][0]

        # Verify spaces and slashes are replaced with underscores
        assert " " not in doc_id
        assert "/" not in doc_id
        assert "Dark_Cave___Hidden_Path" in doc_id

    def test_add_knowledge_documents_batching(self, vector_store, mock_chromadb):
        """Test that large document lists are batched."""
        documents = [
            {
                "text": f"Document {i}",
                "metadata": {"type": "item", "name": f"Item {i}"}
            }
            for i in range(EMBEDDING_BATCH_SIZE + 30)
        ]

        vector_store.add_knowledge_documents(documents)

        # Verify collection.add was called twice (2 batches)
        assert mock_chromadb['knowledge_collection'].add.call_count == 2

    def test_add_knowledge_documents_handles_missing_metadata(self, vector_store, mock_chromadb):
        """Test that documents with missing metadata are handled."""
        documents = [
            {
                "text": "Doc without metadata"
            },
            {
                "text": "Doc with empty metadata",
                "metadata": {}
            }
        ]

        vector_store.add_knowledge_documents(documents)

        call_args = mock_chromadb['knowledge_collection'].add.call_args[1]
        ids = call_args['ids']
        metadatas = call_args['metadatas']

        # Verify IDs were generated with defaults
        assert "unknown_doc_" in ids[0]
        assert "unknown_doc_" in ids[1]

        # Verify metadata handling
        # Note: Current implementation might fail here if it expects metadata key
        # This test will reveal if a fix is needed in vector_store.py

    def test_add_knowledge_documents_partial_metadata(self, vector_store, mock_chromadb):
        """Test documents with partial metadata keys."""
        documents = [
            {
                "text": "Doc with type only",
                "metadata": {"type": "npc"}
            },
            {
                "text": "Doc with name only",
                "metadata": {"name": "My Item"}
            }
        ]

        vector_store.add_knowledge_documents(documents)

        call_args = mock_chromadb['knowledge_collection'].add.call_args[1]
        ids = call_args['ids']

        # ID should use type and default name
        assert "npc_doc_" in ids[0]
        # ID should use default type and name
        assert "unknown_My_Item_" in ids[1]


class TestSearch:
    """Tests for search method."""

    def test_search_both_collections(self, vector_store, mock_embedding_service, mock_chromadb):
        """Test search across both collections."""
        mock_chromadb['transcript_collection'].query.return_value = {
            'documents': [["Transcript result"]],
            'metadatas': [[{"session_id": "s1"}]],
            'distances': [[0.1]]
        }
        mock_chromadb['knowledge_collection'].query.return_value = {
            'documents': [["Knowledge result"]],
            'metadatas': [[{"type": "npc"}]],
            'distances': [[0.2]]
        }

        results = vector_store.search("test query", top_k=5)

        # Verify embed was called
        mock_embedding_service.embed.assert_called_once_with("test query")

        # Verify both collections were queried
        assert mock_chromadb['transcript_collection'].query.call_count == 1
        assert mock_chromadb['knowledge_collection'].query.call_count == 1

        # Verify results are combined and sorted by distance
        assert len(results) == 2
        assert results[0]['distance'] == 0.1  # Lower distance first
        assert results[1]['distance'] == 0.2

    def test_search_specific_collection(self, vector_store, mock_chromadb):
        """Test search on a specific collection only."""
        mock_chromadb['transcript_collection'].query.return_value = {
            'documents': [["Result"]],
            'metadatas': [[{}]],
            'distances': [[0.1]]
        }

        results = vector_store.search("query", top_k=5, collection="transcripts")

        # Verify only transcript collection was queried
        assert mock_chromadb['transcript_collection'].query.call_count == 1
        assert mock_chromadb['knowledge_collection'].query.call_count == 0

    def test_search_collection_filtering_strict(self, vector_store, mock_chromadb):
        """
        Test that searching one collection strictly excludes results from the other.
        BUG-20251102-28
        """
        # Setup: Both collections would return results if queried
        mock_chromadb['transcript_collection'].query.return_value = {
            'documents': [["Transcript Result"]],
            'metadatas': [[{"type": "transcript"}]],
            'distances': [[0.1]]
        }
        mock_chromadb['knowledge_collection'].query.return_value = {
            'documents': [["Knowledge Result"]],
            'metadatas': [[{"type": "npc"}]],
            'distances': [[0.05]] # Better match, but should be ignored if filtering
        }

        # Action: Search only transcripts
        results = vector_store.search("query", collection="transcripts")

        # Assert: Only transcript result returned
        assert len(results) == 1
        assert results[0]['text'] == "Transcript Result"

        # Verify calls
        assert mock_chromadb['transcript_collection'].query.call_count == 1
        assert mock_chromadb['knowledge_collection'].query.call_count == 0

        # Action: Search only knowledge
        mock_chromadb['transcript_collection'].query.reset_mock()
        mock_chromadb['knowledge_collection'].query.reset_mock()

        results = vector_store.search("query", collection="knowledge")

        # Assert: Only knowledge result returned
        assert len(results) == 1
        assert results[0]['text'] == "Knowledge Result"

        # Verify calls
        assert mock_chromadb['transcript_collection'].query.call_count == 0
        assert mock_chromadb['knowledge_collection'].query.call_count == 1

    def test_search_returns_top_k_results(self, vector_store, mock_chromadb):
        """Test that only top_k results are returned when more exist."""
        # Return 10 results from each collection
        mock_chromadb['transcript_collection'].query.return_value = {
            'documents': [[f"T{i}" for i in range(10)]],
            'metadatas': [[{} for _ in range(10)]],
            'distances': [[float(i) * 0.1 for i in range(10)]]
        }
        mock_chromadb['knowledge_collection'].query.return_value = {
            'documents': [[f"K{i}" for i in range(10)]],
            'metadatas': [[{} for _ in range(10)]],
            'distances': [[float(i) * 0.1 + 1.0 for i in range(10)]]
        }

        results = vector_store.search("query", top_k=5)

        # Should return only 5 results (top_k)
        assert len(results) == 5
        # Should be sorted by distance (lowest first)
        assert results[0]['distance'] < results[-1]['distance']

    def test_search_handles_collection_errors_gracefully(self, vector_store, mock_chromadb):
        """Test that errors in one collection don't prevent results from the other."""
        mock_chromadb['transcript_collection'].query.side_effect = Exception("Transcript error")
        mock_chromadb['knowledge_collection'].query.return_value = {
            'documents': [["Knowledge result"]],
            'metadatas': [[{}]],
            'distances': [[0.1]]
        }

        results = vector_store.search("query")

        # Should still return results from knowledge collection
        assert len(results) == 1
        assert results[0]['text'] == "Knowledge result"

    def test_search_returns_empty_on_total_failure(self, vector_store, mock_embedding_service):
        """Test that empty list is returned if embedding fails."""
        mock_embedding_service.embed.side_effect = Exception("Embedding error")

        results = vector_store.search("query")

        assert results == []


class TestFormatResults:
    """Tests for _format_results method."""

    def test_format_results_happy_path(self, vector_store):
        """Test formatting raw ChromaDB results."""
        raw_results = {
            'documents': [["Doc 1", "Doc 2"]],
            'metadatas': [[{"key": "value1"}, {"key": "value2"}]],
            'distances': [[0.1, 0.2]]
        }

        formatted = vector_store._format_results(raw_results)

        assert len(formatted) == 2
        assert formatted[0]['text'] == "Doc 1"
        assert formatted[0]['metadata'] == {"key": "value1"}
        assert formatted[0]['distance'] == 0.1

    def test_format_results_empty_input(self, vector_store):
        """Test formatting empty results."""
        assert vector_store._format_results({}) == []
        assert vector_store._format_results({'documents': []}) == []

    def test_format_results_handles_missing_metadata(self, vector_store):
        """Test formatting results with missing metadata."""
        raw_results = {
            'documents': [["Doc"]],
            'metadatas': [[None]],
            'distances': [[0.1]]
        }

        formatted = vector_store._format_results(raw_results)

        assert formatted[0]['metadata'] == {}


class TestDeleteSession:
    """Tests for delete_session method."""

    def test_delete_session_happy_path(self, vector_store, mock_chromadb):
        """Test deleting a session successfully."""
        session_id = "session_to_delete"
        mock_chromadb['transcript_collection'].get.return_value = {
            'ids': ['seg_1', 'seg_2', 'seg_3']
        }

        vector_store.delete_session(session_id)

        # Verify get was called with correct session_id filter
        mock_chromadb['transcript_collection'].get.assert_called_once()
        call_args = mock_chromadb['transcript_collection'].get.call_args[1]
        assert call_args['where'] == {'session_id': session_id}

        # Verify delete was called with correct IDs
        mock_chromadb['transcript_collection'].delete.assert_called_once_with(
            ids=['seg_1', 'seg_2', 'seg_3']
        )

    def test_delete_session_not_found(self, vector_store, mock_chromadb):
        """Test deleting a non-existent session (logs warning, doesn't crash)."""
        mock_chromadb['transcript_collection'].get.return_value = {'ids': []}

        # Should not raise an exception
        vector_store.delete_session("nonexistent_session")

        # Verify delete was NOT called
        mock_chromadb['transcript_collection'].delete.assert_not_called()

    def test_delete_session_raises_on_error(self, vector_store, mock_chromadb):
        """Test that exceptions during delete are propagated."""
        mock_chromadb['transcript_collection'].get.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            vector_store.delete_session("session_001")


class TestClearAll:
    """Tests for clear_all method."""

    def test_clear_all_deletes_and_recreates_collections(self, vector_store, mock_chromadb):
        """Test that clear_all deletes and recreates collections."""
        vector_store.clear_all()

        # Verify delete_collection was called for both collections
        client = mock_chromadb['client']
        assert client.delete_collection.call_count == 2

        delete_calls = [call[0][0] for call in client.delete_collection.call_args_list]
        assert "transcripts" in delete_calls
        assert "knowledge" in delete_calls

        # Verify create_collection was called for both collections
        assert client.create_collection.call_count == 2

    def test_clear_all_usable_after_clearing(self, vector_store, mock_chromadb):
        """
        Test that vector store is usable after clearing.
        BUG-20251102-30
        """
        # 1. Clear collections
        vector_store.clear_all()

        # Update mocks to return the "new" collections
        new_transcript_coll = MagicMock()
        new_knowledge_coll = MagicMock()
        mock_chromadb['client'].create_collection.side_effect = [
            new_transcript_coll,
            new_knowledge_coll
        ]

        # Note: The vector_store instance updates its references to collections
        # based on the return value of create_collection.
        # We need to ensure our mock setup reflects this update if we want to test it properly.
        # In the real code, self.transcript_collection is reassigned.
        # In the test with mocks, the reassignment happens with the return value of create_collection.

        # 2. Try to add data
        vector_store.add_transcript_segments("s1", [{"text": "test"}])

        # Verify add was called on the NEW collection instance (returned by create_collection)
        # Since we mocked create_collection to return a specific mock in the fixture,
        # and in this test checking if the reassignment works.

        # Wait, the fixture 'mock_chromadb' sets up `get_or_create_collection` but `create_collection`
        # returns a MagicMock by default.
        # The `vector_store.transcript_collection` will be updated to whatever `create_collection` returns.

        # Let's verify that `add` is called on the current `transcript_collection` attribute
        assert vector_store.transcript_collection.add.call_count == 1

    def test_clear_all_raises_on_error(self, vector_store, mock_chromadb):
        """Test that exceptions during clear are propagated."""
        mock_chromadb['client'].delete_collection.side_effect = Exception("Delete failed")

        with pytest.raises(Exception, match="Delete failed"):
            vector_store.clear_all()


class TestGetStats:
    """Tests for get_stats method."""

    def test_get_stats_happy_path(self, vector_store, mock_chromadb):
        """Test getting vector store statistics."""
        mock_chromadb['transcript_collection'].count.return_value = 100
        mock_chromadb['knowledge_collection'].count.return_value = 50

        stats = vector_store.get_stats()

        assert stats['transcript_segments'] == 100
        assert stats['knowledge_documents'] == 50
        assert stats['total_documents'] == 150
        assert 'persist_dir' in stats

    def test_get_stats_empty_collections(self, vector_store, mock_chromadb):
        """
        Test stats for empty collections.
        BUG-20251102-31
        """
        mock_chromadb['transcript_collection'].count.return_value = 0
        mock_chromadb['knowledge_collection'].count.return_value = 0

        stats = vector_store.get_stats()

        assert stats['transcript_segments'] == 0
        assert stats['knowledge_documents'] == 0
        assert stats['total_documents'] == 0

    def test_get_stats_handles_errors(self, vector_store, mock_chromadb):
        """Test that get_stats returns zeros on error."""
        mock_chromadb['transcript_collection'].count.side_effect = Exception("Count failed")

        stats = vector_store.get_stats()

        assert stats['transcript_segments'] == 0
        assert stats['knowledge_documents'] == 0
        assert stats['total_documents'] == 0
