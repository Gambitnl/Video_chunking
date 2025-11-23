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

# BUG-20251102-21: Complex scenarios for RRF
def test_reciprocal_rank_fusion_complex_identical_scores(hybrid_searcher):
    """Test RRF with documents that might end up with identical scores."""
    # doc1 is rank 1 in A (score 1/(60+1))
    # doc2 is rank 1 in B (score 1/(60+1))
    results_a = [{"text": "doc1", "metadata": {"id": "A1"}}]
    results_b = [{"text": "doc2", "metadata": {"id": "B1"}}]

    hybrid_searcher._get_doc_id = Mock(side_effect=lambda r: r["metadata"]["id"])

    # With equal weights, they should have identical scores
    # Sorting stability or implementation detail determines order, but both must be present
    merged_results = hybrid_searcher._reciprocal_rank_fusion(results_a, results_b, weights=(0.5, 0.5))
    assert len(merged_results) == 2
    ids = {r["metadata"]["id"] for r in merged_results}
    assert ids == {"A1", "B1"}

def test_reciprocal_rank_fusion_empty_inputs(hybrid_searcher):
    """Test RRF with empty input lists."""
    results = hybrid_searcher._reciprocal_rank_fusion([], [])
    assert results == []

    results = hybrid_searcher._reciprocal_rank_fusion([{"text": "d", "metadata": {"id": "1"}}], [])
    assert len(results) == 1

    results = hybrid_searcher._reciprocal_rank_fusion([], [{"text": "d", "metadata": {"id": "1"}}])
    assert len(results) == 1

def test_reciprocal_rank_fusion_duplicate_docs_in_single_list(hybrid_searcher):
    """Test RRF if a single list somehow contains duplicates (should handle gracefully)."""
    results_a = [
        {"text": "doc1", "metadata": {"id": "A1"}},
        {"text": "doc1", "metadata": {"id": "A1"}}, # Duplicate
    ]
    results_b = []

    hybrid_searcher._get_doc_id = Mock(side_effect=lambda r: r["metadata"]["id"])

    merged_results = hybrid_searcher._reciprocal_rank_fusion(results_a, results_b)
    # Implementation sums scores, so duplicate in same list would boost score
    # Verify it doesn't crash and returns unique doc
    assert len(merged_results) == 1
    assert merged_results[0]["metadata"]["id"] == "A1"


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

# BUG-20251102-19: Test varying top_k and semantic_weight
def test_search_varying_top_k(hybrid_searcher):
    """Test that search respects different top_k values."""
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    # Setup mocks to return enough results
    mock_vector_store.search.return_value = [{"text": f"s{i}", "metadata": {"id": f"s{i}"}} for i in range(10)]
    mock_keyword_retriever.retrieve.return_value = [MockDocument(f"k{i}", {"id": f"k{i}"}) for i in range(10)]

    # We need _reciprocal_rank_fusion to return a list larger than top_k to verify slicing
    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[
        {"text": f"r{i}", "metadata": {"id": f"r{i}"}} for i in range(20)
    ])

    # Case 1: top_k = 1
    results = hybrid_searcher.search("query", top_k=1)
    assert len(results) == 1
    mock_vector_store.search.assert_called_with("query", top_k=2) # top_k * 2
    mock_keyword_retriever.retrieve.assert_called_with("query", top_k=2)

    # Case 2: top_k = 5
    results = hybrid_searcher.search("query", top_k=5)
    assert len(results) == 5
    mock_vector_store.search.assert_called_with("query", top_k=10)

def test_search_varying_semantic_weight(hybrid_searcher):
    """Test that search passes correct weights to RRF."""
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever
    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[])

    # Case 1: Default weight (usually 0.7)
    hybrid_searcher.search("query")
    # Check call args
    args, kwargs = hybrid_searcher._reciprocal_rank_fusion.call_args
    # weights=(semantic_weight, 1-semantic_weight)
    # default semantic_weight is 0.7
    weights = kwargs.get('weights')
    if weights is None:
        weights = args[2]
    assert abs(weights[0] - 0.7) < 1e-6
    assert abs(weights[1] - 0.3) < 1e-6

    # Case 2: Custom weight
    hybrid_searcher.search("query", semantic_weight=0.2)
    args, kwargs = hybrid_searcher._reciprocal_rank_fusion.call_args
    weights = kwargs.get('weights')
    if weights is None:
        weights = args[2]
    assert abs(weights[0] - 0.2) < 1e-6
    assert abs(weights[1] - 0.8) < 1e-6

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

    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[
        {"text": "keyword_doc1", "metadata": {"id": "K1"}},
    ])

    query = "error query"
    results = hybrid_searcher.search(query)

    assert len(results) == 1
    assert results[0]["metadata"]["id"] == "K1"
    hybrid_searcher._reciprocal_rank_fusion.assert_called_once()

def test_search_error_in_keyword_fallback_to_semantic(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.return_value = [
        {"text": "semantic_doc1", "metadata": {"id": "S1"}},
    ]
    mock_keyword_retriever.retrieve.side_effect = Exception("Keyword search failed")

    hybrid_searcher._reciprocal_rank_fusion = Mock(return_value=[
        {"text": "semantic_doc1", "metadata": {"id": "S1"}},
    ])

    query = "error query"
    results = hybrid_searcher.search(query)

    assert len(results) == 1
    assert results[0]["metadata"]["id"] == "S1"
    hybrid_searcher._reciprocal_rank_fusion.assert_called_once()

def test_search_error_in_both_returns_empty(hybrid_searcher):
    mock_vector_store = hybrid_searcher.vector_store
    mock_keyword_retriever = hybrid_searcher.keyword_retriever

    mock_vector_store.search.side_effect = Exception("Semantic search failed")
    mock_keyword_retriever.retrieve.side_effect = Exception("Keyword search failed")

    hybrid_searcher._reciprocal_rank_fusion = Mock()

    query = "error query"
    results = hybrid_searcher.search(query)

    assert len(results) == 0
    hybrid_searcher._reciprocal_rank_fusion.assert_not_called()


# ============================================================================
# INTEGRATION TESTS - Using real vector store and retriever instances
# ============================================================================

import tempfile
import shutil
import json
from pathlib import Path

@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    temp_root = tempfile.mkdtemp()
    try:
        vector_store_dir = Path(temp_root) / "vector_store"
        kb_dir = Path(temp_root) / "knowledge_base"
        transcript_dir = Path(temp_root) / "transcripts"

        vector_store_dir.mkdir(parents=True, exist_ok=True)
        kb_dir.mkdir(parents=True, exist_ok=True)
        transcript_dir.mkdir(parents=True, exist_ok=True)

        yield {
            "root": Path(temp_root),
            "vector_store": vector_store_dir,
            "kb": kb_dir,
            "transcript": transcript_dir
        }
    finally:
        # Cleanup after test - guaranteed even if setup fails
        shutil.rmtree(temp_root, ignore_errors=True)


@pytest.fixture
def sample_knowledge_base(temp_dirs):
    """Create a sample knowledge base JSON file."""
    kb_data = {
        "npcs": [
            {
                "name": "Gandalf the Grey",
                "description": "A powerful wizard who guides the Fellowship",
                "first_appearance": "session_001"
            },
            {
                "name": "Aragorn",
                "description": "The rightful heir to the throne of Gondor, a skilled ranger",
                "first_appearance": "session_001"
            },
            {
                "name": "Saruman",
                "description": "A corrupted wizard who betrayed the White Council",
                "first_appearance": "session_002"
            }
        ],
        "quests": [
            {
                "name": "Destroy the One Ring",
                "description": "Travel to Mount Doom to destroy the One Ring in the fires where it was forged",
                "status": "active"
            },
            {
                "name": "Find the Palantir",
                "description": "Locate and secure the seeing stones to prevent Sauron from using them",
                "status": "completed"
            }
        ],
        "locations": [
            {
                "name": "Rivendell",
                "description": "The elven stronghold where the Fellowship was formed, a place of wisdom and healing"
            },
            {
                "name": "Mordor",
                "description": "The dark land where Sauron rules, filled with orcs and darkness"
            },
            {
                "name": "Isengard",
                "description": "Saruman's tower fortress where he breeds his Uruk-hai army"
            }
        ]
    }

    kb_file = temp_dirs["kb"] / "campaign_001_knowledge.json"
    with open(kb_file, "w", encoding="utf-8") as f:
        json.dump(kb_data, f, indent=2)

    return kb_file


@pytest.fixture
def sample_transcripts(temp_dirs):
    """Create sample transcript files."""
    transcripts_data = {
        "session_001": {
            "segments": [
                {
                    "text": "Gandalf warns the party about the dangers of using the One Ring",
                    "speaker": "DM",
                    "start": 120.5,
                    "end": 125.3
                },
                {
                    "text": "We should head to Rivendell to consult with Elrond about our quest",
                    "speaker": "Aragorn_Player",
                    "start": 126.0,
                    "end": 130.5
                },
                {
                    "text": "The wizard Saruman has betrayed us, we must be cautious",
                    "speaker": "Gandalf_Player",
                    "start": 135.2,
                    "end": 139.8
                }
            ]
        },
        "session_002": {
            "segments": [
                {
                    "text": "The tower of Isengard looms before us, dark and foreboding",
                    "speaker": "DM",
                    "start": 45.0,
                    "end": 49.5
                },
                {
                    "text": "I sense dark magic at work here, Saruman's influence is strong",
                    "speaker": "Gandalf_Player",
                    "start": 50.0,
                    "end": 54.2
                }
            ]
        }
    }

    session_dirs = []
    for session_id, data in transcripts_data.items():
        session_dir = temp_dirs["transcript"] / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        with open(session_dir / "diarized_transcript.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        session_dirs.append(session_dir)

    return session_dirs


@pytest.fixture
def real_embedding_service():
    """Create a real embedding service for testing."""
    try:
        from src.langchain.embeddings import EmbeddingService
        return EmbeddingService(model_name="all-MiniLM-L6-v2")
    except (ImportError, RuntimeError, OSError, Exception) as e:
        pytest.skip(f"EmbeddingService not available: {e}")


@pytest.fixture
def real_vector_store(temp_dirs, real_embedding_service, sample_transcripts):
    """Create a real vector store with test data."""
    try:
        from src.langchain.vector_store import CampaignVectorStore

        vector_store = CampaignVectorStore(
            persist_dir=temp_dirs["vector_store"],
            embedding_service=real_embedding_service
        )

        # Load transcript segments from the sample file (avoids data duplication)
        session_001_transcript_path = temp_dirs["transcript"] / "session_001" / "diarized_transcript.json"
        with open(session_001_transcript_path, "r", encoding="utf-8") as f:
            transcript_data = json.load(f)
        vector_store.add_transcript_segments("session_001", transcript_data["segments"])

        # Add knowledge documents
        knowledge_docs = [
            {
                "text": "Gandalf the Grey is a powerful wizard who guides the Fellowship on their quest to destroy the One Ring",
                "metadata": {"type": "npc", "name": "Gandalf"}
            },
            {
                "text": "Rivendell is the elven stronghold where the Fellowship was formed, a place of wisdom and healing",
                "metadata": {"type": "location", "name": "Rivendell"}
            },
            {
                "text": "The quest to destroy the One Ring requires traveling to Mount Doom in the heart of Mordor",
                "metadata": {"type": "quest", "name": "Destroy the One Ring"}
            },
            {
                "text": "Saruman is a corrupted wizard who betrayed the White Council and now serves the enemy",
                "metadata": {"type": "npc", "name": "Saruman"}
            },
            {
                "text": "Isengard is Saruman's tower fortress where he breeds his Uruk-hai army",
                "metadata": {"type": "location", "name": "Isengard"}
            }
        ]
        vector_store.add_knowledge_documents(knowledge_docs)

        return vector_store

    except (ImportError, RuntimeError) as e:
        pytest.skip(f"CampaignVectorStore not available: {e}")


@pytest.fixture
def real_retriever(temp_dirs, sample_knowledge_base, sample_transcripts):
    """Create a real retriever with test data."""
    try:
        from src.langchain.retriever import CampaignRetriever

        retriever = CampaignRetriever(
            knowledge_base_dir=temp_dirs["kb"],
            transcript_dir=temp_dirs["transcript"]
        )

        return retriever

    except ImportError as e:
        pytest.skip(f"CampaignRetriever not available: {e}")


@pytest.fixture
def real_hybrid_searcher(real_vector_store, real_retriever):
    """Create a real HybridSearcher with real components."""
    return HybridSearcher(real_vector_store, real_retriever)


# Integration Tests

def test_integration_basic_hybrid_search(real_hybrid_searcher):
    """Test basic hybrid search with real vector store and retriever."""
    query = "Tell me about Gandalf"
    results = real_hybrid_searcher.search(query, top_k=5)

    assert len(results) > 0
    assert len(results) <= 5

    # Check that results have expected structure
    for result in results:
        assert "text" in result
        assert "metadata" in result
        assert isinstance(result["text"], str)
        assert isinstance(result["metadata"], dict)


def test_integration_semantic_keyword_combination(real_hybrid_searcher):
    """Test that hybrid search combines semantic and keyword results."""
    # Query that should match both semantic and keyword results
    query = "wizard Saruman"
    results = real_hybrid_searcher.search(query, top_k=5)

    assert len(results) > 0

    # Check that we get results mentioning Saruman
    saruman_results = [r for r in results if "saruman" in r["text"].lower()]
    assert len(saruman_results) > 0, "Should find results about Saruman"


def test_integration_semantic_understanding(real_hybrid_searcher):
    """Test semantic search capabilities (related concepts)."""
    # Query using synonyms/related terms
    query = "magical advisor"  # Should match Gandalf via semantic similarity
    results = real_hybrid_searcher.search(query, top_k=5)

    assert len(results) > 0

    # Check that we get relevant results (wizard/Gandalf related)
    relevant_results = [
        r for r in results
        if any(term in r["text"].lower() for term in ["gandalf", "wizard", "magic"])
    ]
    assert len(relevant_results) > 0, "Semantic search should find related concepts"


def test_integration_keyword_exact_match(real_hybrid_searcher):
    """Test that keyword search finds exact matches."""
    query = "Rivendell"  # Exact location name
    results = real_hybrid_searcher.search(query, top_k=5)

    assert len(results) > 0

    # Should definitely find Rivendell in results
    rivendell_results = [r for r in results if "rivendell" in r["text"].lower()]
    assert len(rivendell_results) > 0, "Should find exact keyword match for Rivendell"


def test_integration_different_weights(real_hybrid_searcher):
    """Test hybrid search with different semantic weights."""
    query = "One Ring quest"

    # High semantic weight (favor semantic results)
    semantic_heavy_results = real_hybrid_searcher.search(
        query, top_k=5, semantic_weight=0.9
    )

    # High keyword weight (favor keyword results)
    keyword_heavy_results = real_hybrid_searcher.search(
        query, top_k=5, semantic_weight=0.1
    )

    # Both should return results
    assert len(semantic_heavy_results) > 0
    assert len(keyword_heavy_results) > 0

    # Results might differ due to different weighting
    # (but not guaranteed to be different with small dataset)
    assert isinstance(semantic_heavy_results, list)
    assert isinstance(keyword_heavy_results, list)


def test_integration_top_k_limiting(real_hybrid_searcher):
    """Test that top_k properly limits results."""
    query = "wizard"

    # Test different top_k values
    results_1 = real_hybrid_searcher.search(query, top_k=1)
    results_3 = real_hybrid_searcher.search(query, top_k=3)
    results_5 = real_hybrid_searcher.search(query, top_k=5)

    assert len(results_1) <= 1
    assert len(results_3) <= 3
    assert len(results_5) <= 5

    # Verify ordering is consistent (top result should be the same)
    if len(results_1) > 0 and len(results_3) > 0:
        # The top result should be similar across different top_k values
        assert results_1[0]["text"] == results_3[0]["text"]


def test_integration_rrf_deduplication(real_hybrid_searcher):
    """Test that RRF properly deduplicates overlapping results."""
    # Query that likely appears in both semantic and keyword results
    query = "Gandalf wizard"
    results = real_hybrid_searcher.search(query, top_k=10)

    # Check for duplicate content using doc_id logic
    seen_ids = set()
    duplicates = []

    for result in results:
        doc_id = real_hybrid_searcher._get_doc_id(result)
        if doc_id in seen_ids:
            duplicates.append(doc_id)
        seen_ids.add(doc_id)

    # Should not have duplicates
    assert len(duplicates) == 0, f"Found duplicate documents: {duplicates}"
    assert len(results) == len(seen_ids), "Each result should be unique"


def test_integration_empty_query_handling(real_hybrid_searcher):
    """Test handling of edge case queries."""
    # Empty query
    results = real_hybrid_searcher.search("", top_k=5)
    # Should not crash, may return empty or some results
    assert isinstance(results, list)

    # Very short query
    results = real_hybrid_searcher.search("a", top_k=5)
    assert isinstance(results, list)


def test_integration_no_results_query(real_hybrid_searcher):
    """Test query that shouldn't match anything."""
    # Query with terms not in our dataset
    query = "xyzabc123 notfound"
    results = real_hybrid_searcher.search(query, top_k=5)

    # Should return a list (possibly empty, or semantic results with low relevance)
    assert isinstance(results, list)


def test_integration_metadata_preservation(real_hybrid_searcher):
    """Test that metadata is properly preserved in results."""
    query = "Gandalf"
    results = real_hybrid_searcher.search(query, top_k=5)

    assert len(results) > 0

    # Check that metadata contains expected fields
    for result in results:
        assert "metadata" in result
        metadata = result["metadata"]

        # Should have type information
        if "type" in metadata:
            assert metadata["type"] in ["transcript", "npc", "location", "quest"]


def test_integration_vector_store_stats(real_vector_store):
    """Test that vector store contains our test data."""
    stats = real_vector_store.get_stats()

    assert stats["transcript_segments"] > 0, "Should have transcript segments"
    assert stats["knowledge_documents"] > 0, "Should have knowledge documents"
    assert stats["total_documents"] > 0, "Should have total documents"


def test_integration_retriever_knowledge_base(real_retriever):
    """Test that retriever can access knowledge base."""
    # Test keyword retrieval
    results = real_retriever.retrieve("Gandalf", top_k=3)

    assert len(results) > 0
    assert all(hasattr(doc, "page_content") for doc in results)
    assert all(hasattr(doc, "metadata") for doc in results)


def test_integration_full_pipeline_with_complex_query(real_hybrid_searcher):
    """Test full hybrid search pipeline with a complex multi-term query."""
    query = "What did Gandalf say about Saruman and the dangers we face?"
    results = real_hybrid_searcher.search(query, top_k=5, semantic_weight=0.7)

    assert len(results) > 0
    assert len(results) <= 5

    # Should get relevant results about Gandalf and Saruman
    relevant_terms = ["gandalf", "saruman", "wizard", "betray", "danger", "cautious"]
    results_text = " ".join([r["text"].lower() for r in results])

    # At least some of these terms should appear
    matches = sum(1 for term in relevant_terms if term in results_text)
    assert matches >= 2, f"Should find at least 2 relevant terms in results, found {matches}"


def test_integration_balanced_weights(real_hybrid_searcher):
    """Test hybrid search with balanced semantic and keyword weights."""
    query = "fortress tower Isengard"

    # Balanced weights should give equal consideration to both
    results = real_hybrid_searcher.search(query, top_k=5, semantic_weight=0.5)

    assert len(results) > 0

    # Should find results about Isengard
    isengard_results = [r for r in results if "isengard" in r["text"].lower()]
    assert len(isengard_results) > 0, "Should find results about Isengard with balanced weights"
