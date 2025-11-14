import pytest
from unittest.mock import Mock, MagicMock
from src.langchain.semantic_retriever import SemanticCampaignRetriever
from src.langchain.retriever import Document
from typing import List, Dict
import tempfile
import shutil
from pathlib import Path

# Try to import integration test dependencies
try:
    from src.langchain.embeddings import EmbeddingService
    from src.langchain.vector_store import CampaignVectorStore
    INTEGRATION_DEPS_AVAILABLE = True
except ImportError:
    INTEGRATION_DEPS_AVAILABLE = False

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


# ============================================================================
# INTEGRATION TESTS
# ============================================================================
# These tests use real EmbeddingService and VectorStore to test actual
# semantic retrieval with realistic transcript data


@pytest.fixture
def integration_tmp_path():
    """Create a temporary directory for integration tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def real_transcript_data():
    """
    Provide realistic D&D session transcript segments.

    These segments cover various aspects of a D&D session including:
    - Combat encounters
    - Character roleplay
    - Exploration
    - NPC interactions
    - Tavern scenes
    """
    return [
        # Combat encounter
        {
            "text": "The ancient dragon unfurls its massive wings and roars, breathing fire across the battlefield.",
            "speaker": "DM",
            "start": 0.0,
            "end": 5.0
        },
        {
            "text": "I cast fireball at the dragon, aiming for its head!",
            "speaker": "Player_Wizard",
            "start": 5.5,
            "end": 8.0
        },
        {
            "text": "I draw my greatsword and charge at the dragon's flank, attempting to strike its weak spot.",
            "speaker": "Player_Fighter",
            "start": 8.5,
            "end": 12.0
        },

        # Tavern roleplay
        {
            "text": "You enter the Prancing Pony tavern. The air is thick with pipe smoke and the smell of ale.",
            "speaker": "DM",
            "start": 20.0,
            "end": 24.0
        },
        {
            "text": "I approach the bartender and ask if he's heard any rumors about the missing caravan.",
            "speaker": "Player_Rogue",
            "start": 24.5,
            "end": 28.0
        },
        {
            "text": "The bartender leans in close and whispers that strange figures were seen near the old ruins at midnight.",
            "speaker": "DM",
            "start": 28.5,
            "end": 33.0
        },

        # Exploration
        {
            "text": "As you venture deeper into the ancient forest, the trees grow taller and the shadows darker.",
            "speaker": "DM",
            "start": 40.0,
            "end": 44.0
        },
        {
            "text": "I want to search for any tracks or signs of passage through this area.",
            "speaker": "Player_Ranger",
            "start": 44.5,
            "end": 47.0
        },
        {
            "text": "You find fresh goblin tracks leading northeast, along with signs of a struggle.",
            "speaker": "DM",
            "start": 47.5,
            "end": 51.0
        },

        # Magic and spells
        {
            "text": "I examine the magical runes carved into the ancient stone archway using detect magic.",
            "speaker": "Player_Wizard",
            "start": 60.0,
            "end": 63.5
        },
        {
            "text": "The runes glow with an eerie blue light, revealing powerful abjuration magic protecting this portal.",
            "speaker": "DM",
            "start": 64.0,
            "end": 68.0
        },

        # NPC interaction
        {
            "text": "The mysterious hooded figure introduces herself as Elara, a member of the Arcane Council.",
            "speaker": "DM",
            "start": 75.0,
            "end": 79.0
        },
        {
            "text": "I ask Elara if she knows anything about the prophecy regarding the chosen one.",
            "speaker": "Player_Paladin",
            "start": 79.5,
            "end": 82.5
        },

        # Treasure and items
        {
            "text": "Inside the ancient chest you find a gleaming longsword with elvish inscriptions and 500 gold pieces.",
            "speaker": "DM",
            "start": 90.0,
            "end": 94.5
        },
        {
            "text": "I carefully examine the sword's inscriptions to determine its magical properties.",
            "speaker": "Player_Fighter",
            "start": 95.0,
            "end": 98.0
        }
    ]


@pytest.mark.skipif(
    not INTEGRATION_DEPS_AVAILABLE,
    reason="Integration test dependencies (sentence-transformers, chromadb) not installed"
)
class TestSemanticRetrieverIntegration:
    """
    Integration tests for SemanticCampaignRetriever using real embeddings
    and vector store with realistic transcript data.
    """

    def test_integration_semantic_retrieval_with_real_embeddings(
        self, integration_tmp_path, real_transcript_data
    ):
        """
        Test semantic retrieval with real embedding service and realistic D&D transcript data.

        This test verifies:
        - Embeddings are generated correctly
        - Semantic search retrieves relevant content
        - Results are returned as proper Document objects
        """
        # Setup real components
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(integration_tmp_path, embedding_service)
        retriever = SemanticCampaignRetriever(vector_store)

        # Add real transcript data
        vector_store.add_transcript_segments("session_001", real_transcript_data)

        # Test semantic retrieval for combat-related query
        results = retriever.retrieve("dragon fight battle", top_k=3)

        # Assertions
        assert len(results) > 0, "Should retrieve at least one result"
        assert all(isinstance(doc, Document) for doc in results), "All results should be Document objects"

        # First result should be combat-related (dragon, fireball, or greatsword)
        first_result_text = results[0].content.lower()
        assert any(word in first_result_text for word in ["dragon", "fireball", "sword", "charge"]), \
            f"First result should be combat-related, got: {results[0].content}"

        # Verify metadata structure
        assert "session_id" in results[0].metadata
        assert "speaker" in results[0].metadata
        assert results[0].metadata["session_id"] == "session_001"

    def test_integration_similarity_scoring(
        self, integration_tmp_path, real_transcript_data
    ):
        """
        Test that similarity scoring works correctly.

        This test verifies:
        - Similar queries retrieve similar results
        - Different queries retrieve different results
        - Semantic understanding (not just keyword matching)
        """
        # Setup
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(integration_tmp_path, embedding_service)
        retriever = SemanticCampaignRetriever(vector_store)

        vector_store.add_transcript_segments("session_001", real_transcript_data)

        # Test similar queries
        results_combat_1 = retriever.retrieve("fighting a dragon", top_k=3)
        results_combat_2 = retriever.retrieve("battle with dragon", top_k=3)

        # Both combat queries should retrieve combat-related content
        for results in [results_combat_1, results_combat_2]:
            assert len(results) > 0
            combat_keywords = ["dragon", "fire", "sword", "charge", "attack"]
            assert any(
                keyword in results[0].content.lower()
                for keyword in combat_keywords
            ), f"Combat query should retrieve combat content, got: {results[0].content}"

        # Test different semantic domains
        results_tavern = retriever.retrieve("inn bartender rumors", top_k=3)
        results_magic = retriever.retrieve("magical spells arcane", top_k=3)

        # Tavern query should get tavern content
        tavern_text = results_tavern[0].content.lower()
        assert any(word in tavern_text for word in ["tavern", "bartender", "ale", "rumors"]), \
            f"Tavern query should retrieve tavern content, got: {results_tavern[0].content}"

        # Magic query should get magic content
        magic_text = results_magic[0].content.lower()
        assert any(word in magic_text for word in ["magic", "rune", "spell", "arcane", "wizard"]), \
            f"Magic query should retrieve magic content, got: {results_magic[0].content}"

    def test_integration_result_ranking_by_relevance(
        self, integration_tmp_path, real_transcript_data
    ):
        """
        Test that results are properly ranked by semantic similarity.

        This test verifies:
        - Most relevant results appear first
        - Results are ordered by similarity/distance
        - Ranking is semantically meaningful
        """
        # Setup
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(integration_tmp_path, embedding_service)
        retriever = SemanticCampaignRetriever(vector_store)

        vector_store.add_transcript_segments("session_001", real_transcript_data)

        # Query specifically about wizards and magic
        results = retriever.retrieve("wizard casting magical spells", top_k=5)

        assert len(results) >= 2, "Should retrieve multiple results for ranking test"

        # First result should be highly relevant to wizards/magic
        first_text = results[0].content.lower()
        magic_keywords = ["wizard", "magic", "spell", "fireball", "rune", "arcane"]
        assert any(keyword in first_text for keyword in magic_keywords), \
            f"First result should be magic-related, got: {results[0].content}"

        # If we have access to distance scores, verify they're in ascending order
        # (lower distance = more similar)
        raw_results = vector_store.search("wizard casting magical spells", top_k=5)
        if len(raw_results) >= 2:
            distances = [r["distance"] for r in raw_results]
            assert distances == sorted(distances), \
                f"Results should be sorted by distance (ascending), got: {distances}"

    def test_integration_retrieve_from_session_filtering(
        self, integration_tmp_path, real_transcript_data
    ):
        """
        Test session filtering in retrieve_from_session method.

        This test verifies:
        - Results are filtered to specific session
        - Ranking works within session results
        - No results from other sessions leak through
        """
        # Setup
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(integration_tmp_path, embedding_service)
        retriever = SemanticCampaignRetriever(vector_store)

        # Add transcripts from multiple sessions
        vector_store.add_transcript_segments("session_001", real_transcript_data[:7])
        vector_store.add_transcript_segments("session_002", real_transcript_data[7:])

        # Retrieve from specific session
        results = retriever.retrieve_from_session("dragon battle", "session_001", top_k=3)

        # All results should be from session_001
        assert len(results) > 0, "Should retrieve results from session_001"
        assert all(
            doc.metadata.get("session_id") == "session_001"
            for doc in results
        ), "All results should be from session_001"

        # Results should still be ranked by relevance
        assert any(
            word in results[0].content.lower()
            for word in ["dragon", "fire", "sword"]
        ), "First result should be relevant to dragon battle"

    def test_integration_top_k_parameter(
        self, integration_tmp_path, real_transcript_data
    ):
        """
        Test that top_k parameter correctly limits result count.

        This test verifies:
        - Exactly top_k results are returned (when available)
        - Results are still properly ranked
        - Works with different top_k values
        """
        # Setup
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(integration_tmp_path, embedding_service)
        retriever = SemanticCampaignRetriever(vector_store)

        vector_store.add_transcript_segments("session_001", real_transcript_data)

        # Test different top_k values
        for k in [1, 3, 5, 10]:
            results = retriever.retrieve("adventure quest", top_k=k)
            expected_count = min(k, len(real_transcript_data))
            assert len(results) <= expected_count, \
                f"Should return at most {expected_count} results for top_k={k}, got {len(results)}"

            # For k=1, verify only one result
            if k == 1:
                assert len(results) == 1, "top_k=1 should return exactly 1 result"

    def test_integration_real_transcript_diverse_queries(
        self, integration_tmp_path, real_transcript_data
    ):
        """
        Test semantic retrieval with diverse query types on realistic transcript data.

        This test verifies semantic understanding across various query types:
        - Character/NPC queries
        - Location queries
        - Item/treasure queries
        - Action/event queries
        """
        # Setup
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(integration_tmp_path, embedding_service)
        retriever = SemanticCampaignRetriever(vector_store)

        vector_store.add_transcript_segments("session_001", real_transcript_data)

        # Test various query types
        test_cases = [
            {
                "query": "treasure gold sword",
                "expected_keywords": ["chest", "sword", "gold", "treasure"],
                "description": "treasure query"
            },
            {
                "query": "forest exploration tracking",
                "expected_keywords": ["forest", "track", "goblin", "search"],
                "description": "exploration query"
            },
            {
                "query": "tavern innkeeper information",
                "expected_keywords": ["tavern", "bartender", "rumors", "ale"],
                "description": "tavern query"
            },
            {
                "query": "mysterious hooded figure NPC",
                "expected_keywords": ["elara", "hooded", "council", "arcane"],
                "description": "NPC query"
            }
        ]

        for test_case in test_cases:
            results = retriever.retrieve(test_case["query"], top_k=3)
            assert len(results) > 0, f"Should retrieve results for {test_case['description']}"

            # Check that at least one expected keyword appears in top result
            first_text = results[0].content.lower()
            has_keyword = any(
                keyword in first_text
                for keyword in test_case["expected_keywords"]
            )
            assert has_keyword, \
                f"{test_case['description']} should retrieve relevant content. " \
                f"Expected one of {test_case['expected_keywords']}, got: {results[0].content}"

    def test_integration_empty_results_handling(
        self, integration_tmp_path
    ):
        """
        Test that retriever handles empty results gracefully.

        This test verifies:
        - Empty vector store returns empty results (not errors)
        - No matching documents returns empty list
        """
        # Setup with empty vector store
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(integration_tmp_path, embedding_service)
        retriever = SemanticCampaignRetriever(vector_store)

        # Query empty store
        results = retriever.retrieve("any query", top_k=5)

        assert isinstance(results, list), "Should return a list"
        assert len(results) == 0, "Should return empty list for empty vector store"

    def test_integration_semantic_vs_keyword_matching(
        self, integration_tmp_path, real_transcript_data
    ):
        """
        Test that semantic search understands meaning, not just keywords.

        This test verifies semantic understanding by using synonyms
        and related concepts that don't share exact keywords.
        """
        # Setup
        embedding_service = EmbeddingService()
        vector_store = CampaignVectorStore(integration_tmp_path, embedding_service)
        retriever = SemanticCampaignRetriever(vector_store)

        vector_store.add_transcript_segments("session_001", real_transcript_data)

        # Test semantic similarity with synonyms/related terms
        # "flying reptile" should match "dragon" semantically
        results = retriever.retrieve("flying reptile breathing flames", top_k=3)

        assert len(results) > 0, "Should retrieve results"

        # Should retrieve dragon-related content even without exact word "dragon" in query
        first_text = results[0].content.lower()
        # The content should be about the dragon even though we queried "flying reptile"
        assert "dragon" in first_text or "fire" in first_text or "wing" in first_text, \
            f"Semantic search should understand 'flying reptile' relates to 'dragon', got: {results[0].content}"
