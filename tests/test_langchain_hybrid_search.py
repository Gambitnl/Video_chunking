import pytest
from unittest.mock import Mock, MagicMock
from src.langchain.hybrid_search import HybridSearcher
from typing import List, Dict

# Mock Document class for keyword_retriever
class MockDocument:
    def __init__(self, page_content: str, metadata: Dict):
        self.page_content = page_content
        self.metadata = metadata

# Fixture for a basic HybridSearcher instance
@pytest.fixture
def hybrid_searcher():
    mock_vector_store = Mock()
    mock_keyword_retriever = Mock()
    return HybridSearcher(mock_vector_store, mock_keyword_retriever)

# Test initialization
def test_hybrid_searcher_init(hybrid_searcher):
    assert hybrid_searcher.vector_store is not None
    assert hybrid_searcher.keyword_retriever is not None

# Test _get_doc_id method
def test_get_doc_id_with_session_and_start(hybrid_searcher):
    result = {"text": "some text", "metadata": {"session_id": "sess1", "start": 123}}
    doc_id = hybrid_searcher._get_doc_id(result)
    assert doc_id == "sess1_123"

def test_get_doc_id_without_session_or_start(hybrid_searcher):
    result = {"text": "some other text", "metadata": {}}
    doc_id = hybrid_searcher._get_doc_id(result)
    assert doc_id == str(hash("some other text"))

def test_get_doc_id_with_empty_text(hybrid_searcher):
    result = {"text": "", "metadata": {"session_id": "sess2", "start": 456}}
    doc_id = hybrid_searcher._get_doc_id(result)
    assert doc_id == "sess2_456"

# Test _reciprocal_rank_fusion method
def test_reciprocal_rank_fusion_basic(hybrid_searcher):
    results_a = [
        {"text": "doc1", "metadata": {"id": "A1"}},
        {"text": "doc2", "metadata": {"id": "A2"}},
    ]
    results_b = [
        {"text": "doc3", "metadata": {"id": "B1"}},
        {"text": "doc1", "metadata": {"id": "A1"}},
    ]
    
    # Mock _get_doc_id to return predictable IDs
    hybrid_searcher._get_doc_id = Mock(side_effect=lambda r: r["metadata"]["id"])

    merged_results = hybrid_searcher._reciprocal_rank_fusion(results_a, results_b)
    
    # doc1 should have a higher score because it appears in both
    # doc3 should be ranked higher than doc2 because it's higher in results_b
    assert len(merged_results) == 3
    assert merged_results[0]["metadata"]["id"] == "A1" # doc1 from results_a rank 1, results_b rank 2
    assert merged_results[1]["metadata"]["id"] == "B1" # doc3 from results_b rank 1
    assert merged_results[2]["metadata"]["id"] == "A2" # doc2 from results_a rank 2

def test_reciprocal_rank_fusion_non_overlapping(hybrid_searcher):
    results_a = [
        {"text": "doc1", "metadata": {"id": "A1"}},
    ]
    results_b = [
        {"text": "doc2", "metadata": {"id": "B1"}},
    ]
    
    hybrid_searcher._get_doc_id = Mock(side_effect=lambda r: r["metadata"]["id"])

    merged_results = hybrid_searcher._reciprocal_rank_fusion(results_a, results_b)
    assert len(merged_results) == 2
    # Order depends on weights and k, but both should be present
    assert {r["metadata"]["id"] for r in merged_results} == {"A1", "B1"}

def test_reciprocal_rank_fusion_weights(hybrid_searcher):
    results_a = [
        {"text": "doc1", "metadata": {"id": "A1"}},
    ]
    results_b = [
        {"text": "doc2", "metadata": {"id": "B1"}},
    ]
    
    hybrid_searcher._get_doc_id = Mock(side_effect=lambda r: r["metadata"]["id"])

    # Give more weight to results_a
    merged_results = hybrid_searcher._reciprocal_rank_fusion(results_a, results_b, weights=(0.8, 0.2))
    assert merged_results[0]["metadata"]["id"] == "A1"

    # Give more weight to results_b
    merged_results = hybrid_searcher._reciprocal_rank_fusion(results_a, results_b, weights=(0.2, 0.8))
    assert merged_results[0]["metadata"]["id"] == "B1"

# Test search method
def test_search_happy_path(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.return_value = [
        {"text": "semantic_doc1", "metadata": {"id": "S1"}},
        {"text": "semantic_doc2", "metadata": {"id": "S2"}},
    ]
    mock_keyword_retriever.retrieve.return_value = [
        MockDocument("keyword_doc1", {"id": "K1"}),
        MockDocument("semantic_doc1", {"id": "S1"}), # Overlap
    ]
    
    # Mock _reciprocal_rank_fusion to return a predictable order
    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[
        {"text": "semantic_doc1", "metadata": {"id": "S1"}},
        {"text": "keyword_doc1", "metadata": {"id": "K1"}},
        {"text": "semantic_doc2", "metadata": {"id": "S2"}},
        {"text": "extra_doc1", "metadata": {"id": "E1"}},
        {"text": "extra_doc2", "metadata": {"id": "E2"}},
    ])

    query = "test query"
    results = hybrid_searcher.search(query)

    mock_vector_store.search.assert_called_once_with(query, top_k=10)
    mock_keyword_retriever.retrieve.assert_called_once_with(query, top_k=10)
    hybrid_searcher._reciprocal_rank_fusion.assert_called_once()
    
    assert len(results) == 5 # Default top_k
    assert results[0]["metadata"]["id"] == "S1"

def test_search_different_top_k_and_weight(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.return_value = [
        {"text": f"s_doc{i}", "metadata": {"id": f"S{i}"}} for i in range(1, 10)
    ]
    mock_keyword_retriever.retrieve.return_value = [
        MockDocument(f"k_doc{i}", {"id": f"K{i}"}) for i in range(1, 10)
    ]
    
    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[
        {"text": f"merged_doc{i}", "metadata": {"id": f"M{i}"}} for i in range(1, 15)
    ])

    query = "another query"
    top_k = 3
    semantic_weight = 0.9
    results = hybrid_searcher.search(query, top_k=top_k, semantic_weight=semantic_weight)

    mock_vector_store.search.assert_called_once_with(query, top_k=top_k * 2)
    mock_keyword_retriever.retrieve.assert_called_once_with(query, top_k=top_k * 2)
    hybrid_searcher._reciprocal_rank_fusion.assert_called_once()
    
    assert len(results) == top_k
    assert results[0]["metadata"]["id"] == "M1"

def test_search_semantic_returns_empty(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.return_value = []
    mock_keyword_retriever.retrieve.return_value = [
        MockDocument("keyword_doc1", {"id": "K1"}),
    ]
    
    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[
        {"text": "keyword_doc1", "metadata": {"id": "K1"}},
    ])

    query = "query"
    results = hybrid_searcher.search(query)
    assert len(results) == 1
    assert results[0]["metadata"]["id"] == "K1"

def test_search_keyword_returns_empty(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.return_value = [
        {"text": "semantic_doc1", "metadata": {"id": "S1"}},
    ]
    mock_keyword_retriever.retrieve.return_value = []
    
    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[
        {"text": "semantic_doc1", "metadata": {"id": "S1"}},
    ])

    query = "query"
    results = hybrid_searcher.search(query)
    assert len(results) == 1
    assert results[0]["metadata"]["id"] == "S1"

def test_search_both_return_empty(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.return_value = []
    mock_keyword_retriever.retrieve.return_value = []
    
    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[])

    query = "query"
    results = hybrid_searcher.search(query)
    assert len(results) == 0

def test_search_error_in_semantic_fallback_to_keyword(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.side_effect = Exception("Semantic search failed")
    mock_keyword_retriever.retrieve.return_value = [
        MockDocument("keyword_doc1", {"id": "K1"}),
    ]
    
    # When semantic search fails, it should fall back to vector_store.search (which is mocked to return an empty list here)
    # The fallback logic in the actual code is `return self.vector_store.search(query, top_k=top_k)`
    # So, if vector_store.search raises an exception, the fallback will also call vector_store.search.
    # To properly test the fallback, we need to ensure the second call to vector_store.search returns something.
    # Or, more simply, test that the exception is caught and a fallback mechanism is triggered.
    
    # For this test, we'll mock the fallback behavior directly.
    hybrid_searcher.vector_store.search.side_effect = [Exception("Semantic search failed"), [{"text": "fallback_doc", "metadata": {"id": "FB1"}}]]

    query = "error query"
    results = hybrid_searcher.search(query)
    
    # Expect the fallback to semantic search only
    assert len(results) == 1
    assert results[0]["metadata"]["id"] == "FB1"
    
    # Ensure logger.error was called (optional, but good practice)
    # from unittest.mock import patch
    # with patch('src.langchain.hybrid_search.logger.error') as mock_logger_error:
    #     results = hybrid_searcher.search(query)
    #     mock_logger_error.assert_called_once()

def test_search_error_in_keyword_fallback_to_semantic(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.return_value = [
        {"text": "semantic_doc1", "metadata": {"id": "S1"}},
    ]
    mock_keyword_retriever.retrieve.side_effect = Exception("Keyword search failed")
    
    # The fallback in the actual code is `return self.vector_store.search(query, top_k=top_k)`
    # So, if keyword_retriever.retrieve raises an exception, the fallback will call vector_store.search.
    # We need to ensure vector_store.search returns something for the fallback.
    hybrid_searcher.vector_store.search.return_value = [{"text": "fallback_doc", "metadata": {"id": "FB1"}}]

    query = "error query"
    results = hybrid_searcher.search(query)
    
    # Expect the fallback to semantic search only
    assert len(results) == 1
    assert results[0]["metadata"]["id"] == "FB1"

def test_search_error_in_both_returns_empty(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.side_effect = Exception("Semantic search failed")
    mock_keyword_retriever.retrieve.side_effect = Exception("Keyword search failed")
    
    # If both fail, the fallback to vector_store.search will also fail, leading to an empty list
    hybrid_searcher.vector_store.search.side_effect = [Exception("Semantic search failed"), []]

    query = "error query"
    results = hybrid_searcher.search(query)
    
    assert len(results) == 0
