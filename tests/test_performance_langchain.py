"""
Performance tests for LangChain components (BUG-20251102-32).

These tests measure:
1. Vector store ingestion speed (segments/sec)
2. Vector store search latency (ms)
3. Keyword retrieval latency (ms)
4. Hybrid search latency (ms)

They are designed to run as benchmarks and print results to stdout.
"""
import time
import shutil
import tempfile
import pytest
import random
import json
from pathlib import Path
from unittest.mock import MagicMock

from src.langchain.vector_store import CampaignVectorStore
from src.langchain.retriever import CampaignRetriever
from src.langchain.hybrid_search import HybridSearcher

# --- Configuration ---
NUM_SEGMENTS_INGESTION = 2000  # Number of segments to ingest
NUM_SEARCH_ITERATIONS = 20     # Number of searches to average
TARGET_INGESTION_RATE = 50     # Min segments/sec (generous target for CI)
TARGET_SEARCH_LATENCY = 2.0    # Max seconds per search (generous target)


# --- Fixtures ---

@pytest.fixture
def temp_dirs():
    """Create temporary directories for persistence."""
    root_dir = Path(tempfile.mkdtemp())
    vector_dir = root_dir / "chroma_db"
    kb_dir = root_dir / "knowledge"
    transcript_dir = root_dir / "transcripts"

    vector_dir.mkdir()
    kb_dir.mkdir()
    transcript_dir.mkdir()

    yield root_dir, vector_dir, kb_dir, transcript_dir

    shutil.rmtree(root_dir)

@pytest.fixture
def mock_embedding_service():
    """Mock embedding service that returns random vectors."""
    service = MagicMock()
    # Assume 384 dimensions (typical for all-MiniLM-L6-v2)
    service.embed_batch.side_effect = lambda texts, batch_size=32: [
        [random.random() for _ in range(384)] for _ in texts
    ]
    service.embed.side_effect = lambda text: [random.random() for _ in range(384)]
    return service

@pytest.fixture
def synthetic_data():
    """Generate synthetic transcript segments."""
    segments = []
    speakers = ["DM", "Player1", "Player2", "Player3"]

    for i in range(NUM_SEGMENTS_INGESTION):
        segments.append({
            "text": f"This is segment number {i} with some random content to simulate a D&D session. The dragon attacks the party.",
            "speaker": random.choice(speakers),
            "start": float(i * 5),
            "end": float(i * 5 + 4)
        })
    return segments

@pytest.fixture
def populated_kb(temp_dirs):
    """Populate knowledge base directory with dummy files."""
    _, _, kb_dir, _ = temp_dirs

    # Create 50 dummy KB files
    for i in range(50):
        data = {
            "npcs": [{"name": f"NPC_{i}_{j}", "description": "A mysterious figure."} for j in range(5)],
            "quests": [{"name": f"Quest_{i}_{j}", "description": "Retrieve the artifact."} for j in range(5)],
            "locations": [{"name": f"Location_{i}_{j}", "description": "A dark place."} for j in range(5)]
        }
        with open(kb_dir / f"session_{i}_knowledge.json", "w") as f:
            json.dump(data, f)

@pytest.fixture
def populated_transcripts(temp_dirs, synthetic_data):
    """Populate transcript directory with dummy files."""
    _, _, _, transcript_dir = temp_dirs

    # Split synthetic data into 10 sessions
    chunk_size = len(synthetic_data) // 10
    for i in range(10):
        session_dir = transcript_dir / f"session_{i}"
        session_dir.mkdir()

        batch = synthetic_data[i*chunk_size : (i+1)*chunk_size]

        data = {"segments": batch}
        with open(session_dir / "diarized_transcript.json", "w") as f:
            json.dump(data, f)


# --- Tests ---

def test_vector_store_ingestion_performance(temp_dirs, mock_embedding_service, synthetic_data):
    """Benchmark ingestion speed of CampaignVectorStore."""
    _, vector_dir, _, _ = temp_dirs

    store = CampaignVectorStore(persist_dir=vector_dir, embedding_service=mock_embedding_service)

    print(f"\n[Perf] Ingesting {len(synthetic_data)} segments...")
    start_time = time.time()

    store.add_transcript_segments("perf_session_1", synthetic_data)

    end_time = time.time()
    duration = end_time - start_time
    rate = len(synthetic_data) / duration

    print(f"[Perf] Ingestion took {duration:.2f}s ({rate:.1f} segments/sec)")

    # Soft assertion (warning only)
    if rate < TARGET_INGESTION_RATE:
        print(f"WARNING: Ingestion rate {rate:.1f} < target {TARGET_INGESTION_RATE}")

    # Verify data was actually added
    assert store.transcript_collection.count() == len(synthetic_data)

def test_vector_store_search_performance(temp_dirs, mock_embedding_service, synthetic_data):
    """Benchmark search latency of CampaignVectorStore."""
    _, vector_dir, _, _ = temp_dirs

    # Setup: Ingest data first
    store = CampaignVectorStore(persist_dir=vector_dir, embedding_service=mock_embedding_service)
    store.add_transcript_segments("perf_session_1", synthetic_data)

    print(f"\n[Perf] Running {NUM_SEARCH_ITERATIONS} vector searches...")

    start_time = time.time()
    for i in range(NUM_SEARCH_ITERATIONS):
        store.search(f"query {i}", top_k=5)
    end_time = time.time()

    avg_latency = (end_time - start_time) / NUM_SEARCH_ITERATIONS
    print(f"[Perf] Average vector search latency: {avg_latency*1000:.2f}ms")

    if avg_latency >= TARGET_SEARCH_LATENCY:
        print(f"WARNING: Vector search latency {avg_latency:.3f}s >= target {TARGET_SEARCH_LATENCY}s")

def test_keyword_retrieval_performance(temp_dirs, populated_kb, populated_transcripts):
    """Benchmark retrieval latency of CampaignRetriever (file I/O + search)."""
    _, _, kb_dir, transcript_dir = temp_dirs

    retriever = CampaignRetriever(knowledge_base_dir=kb_dir, transcript_dir=transcript_dir)

    print(f"\n[Perf] Running {NUM_SEARCH_ITERATIONS} keyword retrievals...")

    start_time = time.time()
    for i in range(NUM_SEARCH_ITERATIONS):
        # Search for something that likely exists
        retriever.retrieve("NPC_0_0", top_k=5)
    end_time = time.time()

    avg_latency = (end_time - start_time) / NUM_SEARCH_ITERATIONS
    print(f"[Perf] Average keyword retrieval latency: {avg_latency*1000:.2f}ms")

    if avg_latency >= TARGET_SEARCH_LATENCY:
        print(f"WARNING: Keyword retrieval latency {avg_latency:.3f}s >= target {TARGET_SEARCH_LATENCY}s")

def test_hybrid_search_performance(temp_dirs, mock_embedding_service, synthetic_data, populated_kb, populated_transcripts):
    """Benchmark combined hybrid search latency."""
    _, vector_dir, kb_dir, transcript_dir = temp_dirs

    # Setup components
    vector_store = CampaignVectorStore(persist_dir=vector_dir, embedding_service=mock_embedding_service)
    vector_store.add_transcript_segments("perf_session_1", synthetic_data)

    retriever = CampaignRetriever(knowledge_base_dir=kb_dir, transcript_dir=transcript_dir)

    hybrid = HybridSearcher(vector_store=vector_store, keyword_retriever=retriever)

    print(f"\n[Perf] Running {NUM_SEARCH_ITERATIONS} hybrid searches...")

    start_time = time.time()
    for i in range(NUM_SEARCH_ITERATIONS):
        hybrid.search("dragon attack", top_k=5)
    end_time = time.time()

    avg_latency = (end_time - start_time) / NUM_SEARCH_ITERATIONS
    print(f"[Perf] Average hybrid search latency: {avg_latency*1000:.2f}ms")

    if avg_latency >= TARGET_SEARCH_LATENCY:
        print(f"WARNING: Hybrid search latency {avg_latency:.3f}s >= target {TARGET_SEARCH_LATENCY}s")
