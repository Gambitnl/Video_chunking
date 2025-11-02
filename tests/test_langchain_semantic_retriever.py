import pytest
from unittest.mock import Mock, MagicMock
from src.langchain.semantic_retriever import SemanticCampaignRetriever
from src.langchain.retriever import Document # Assuming Document is defined here or can be mocked
from typing import List, Dict

# Mock Document class if not directly importable or for simpler testing
# If src.langchain.retriever.Document is a simple class, we can use it directly.
# Otherwise, a mock might be needed.

# Fixture for a basic SemanticCampaignRetriever instance
@pytest.fixture
def semantic_retriever():
    mock_vector_store = Mock()
    return SemanticCampaignRetriever(mock_vector_store)

# Test initialization
def test_semantic_retriever_init(semantic_retriever):
    assert semantic_retriever.vector_store is not None

# Test retrieve method (Happy Path)
def test_retrieve_happy_path(semantic_retriever):
    mock_vector_store = semantic_retriever.vector_store
    mock_vector_store.search.return_value = [
        {"text": "doc1 content", "metadata": {"id": "doc1"}},
        {"text": "doc2 content", "metadata": {"id": "doc2"}},
    ]

    query = "test query"
    top_k = 2
    results = semantic_retriever.retrieve(query, top_k)

    mock_vector_store.search.assert_called_once_with(query, top_k=top_k)
    assert len(results) == 2
    assert all(isinstance(r, Document) for r in results)
    assert results[0].page_content == "doc1 content"
    assert results[0].metadata == {"id": "doc1"}

# Test retrieve method (Edge Cases - empty results)
def test_retrieve_empty_results(semantic_retriever):
    mock_vector_store = semantic_retriever.vector_store
    mock_vector_store.search.return_value = []

    query = "test query"
    results = semantic_retriever.retrieve(query)

    assert len(results) == 0

# Test retrieve method (Error Handling)
def test_retrieve_error_handling(semantic_retriever):
    mock_vector_store = semantic_retriever.vector_store
    mock_vector_store.search.side_effect = Exception("Vector store error")

    query = "test query"
    results = semantic_retriever.retrieve(query)

    assert len(results) == 0
    # Optionally, assert that logger.error was called

# Test retrieve_from_session method (Happy Path)
def test_retrieve_from_session_happy_path(semantic_retriever):
    mock_vector_store = semantic_retriever.vector_store
    mock_vector_store.search.return_value = [
        {"text": "sess1_doc1", "metadata": {"session_id": "sess1", "id": "d1"}},
        {"text": "sess2_doc1", "metadata": {"session_id": "sess2", "id": "d2"}},
        {"text": "sess1_doc2", "metadata": {"session_id": "sess1", "id": "d3"}},
        {"text": "sess1_doc3", "metadata": {"session_id": "sess1", "id": "d4"}},
    ]

    query = "session query"
    session_id = "sess1"
    top_k = 2
    results = semantic_retriever.retrieve_from_session(query, session_id, top_k)

    mock_vector_store.search.assert_called_once_with(query, top_k=top_k * 3, collection="transcripts")
    assert len(results) == top_k
    assert all(isinstance(r, Document) for r in results)
    assert all(r.metadata.get("session_id") == session_id for r in results)
    assert results[0].page_content == "sess1_doc1"
    assert results[1].page_content == "sess1_doc2"

# Test retrieve_from_session method (Edge Cases - no matching session_id)
def test_retrieve_from_session_no_match(semantic_retriever):
    mock_vector_store = semantic_retriever.vector_store
    mock_vector_store.search.return_value = [
        {"text": "sess2_doc1", "metadata": {"session_id": "sess2", "id": "d1"}},
    ]

    query = "session query"
    session_id = "sess1"
    results = semantic_retriever.retrieve_from_session(query, session_id)

    assert len(results) == 0

# Test retrieve_from_session method (Edge Cases - empty search results)
def test_retrieve_from_session_empty_search_results(semantic_retriever):
    mock_vector_store = semantic_retriever.vector_store
    mock_vector_store.search.return_value = []

    query = "session query"
    session_id = "sess1"
    results = semantic_retriever.retrieve_from_session(query, session_id)

    assert len(results) == 0

# Test retrieve_from_session method (Error Handling)
def test_retrieve_from_session_error_handling(semantic_retriever):
    mock_vector_store = semantic_retriever.vector_store
    mock_vector_store.search.side_effect = Exception("Vector store error")

    query = "session query"
    session_id = "sess1"
    results = semantic_retriever.retrieve_from_session(query, session_id)

    assert len(results) == 0
    # Optionally, assert that logger.error was called
