# Implementation Plans - Part 3: P2 LangChain Integration

> **Planning Mode Document**
> **Created**: 2025-10-22
> **For**: Development Team
> **Source**: ROADMAP.md

This document contains P2 (Important Enhancements) implementation plans for LangChain-powered features.

**See IMPLEMENTATION_PLANS.md for**:
- Templates (Implementation Notes & Reasoning, Code Review Findings)
- How to invoke Critical Review
- P0 features and refactoring

---

## Table of Contents

- [P2-LANGCHAIN-001: Conversational Campaign Interface](#p2-langchain-001-conversational-campaign-interface)
- [P2-LANGCHAIN-002: Semantic Search with RAG](#p2-langchain-002-semantic-search-with-rag)

---

# P2: LangChain Integration

## P2-LANGCHAIN-001: Conversational Campaign Interface

**Files**: `src/langchain/campaign_chat.py` (new), UI integration
**Effort**: 7-10 days
**Priority**: MEDIUM
**Dependencies**: Knowledge base system (existing)
**Status**: NOT STARTED

### Problem Statement
Users need to query campaign information conversationally instead of manually searching through session transcripts and knowledge bases. Example queries:
- "What happened in the last session?"
- "What do we know about the Shadow Lord?"
- "When did Thorin get his magic sword?"
- "Summarize the Crimson Peak arc"

### Success Criteria
- [_] Natural language queries return accurate answers
- [_] Cites sources (session ID, timestamp, speaker)
- [_] Handles multi-session questions
- [_] Maintains conversation context (follow-up questions)
- [_] UI chat interface with history
- [_] Works with local LLM (Ollama) and OpenAI API

### Implementation Plan

#### Subtask 1.1: Design Conversation Schema
**Effort**: 4 hours

Design schema for conversation history and context.

**Schema Example**:
```json
{
  "conversation_id": "conv_001",
  "created_at": "2025-10-22T14:30:00Z",
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "What happened in session 5?",
      "timestamp": "2025-10-22T14:30:00Z"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "In session 5, the party infiltrated...",
      "sources": [
        {
          "session_id": "session_005",
          "timestamp": "01:23:45",
          "speaker": "DM",
          "content": "You approach the castle gates..."
        }
      ],
      "timestamp": "2025-10-22T14:30:05Z"
    }
  ],
  "context": {
    "campaign": "broken_seekers",
    "relevant_sessions": ["session_005"]
  }
}
```

**Files**: New `schemas/conversation.json`

#### Subtask 1.2: Set Up LangChain Integration
**Effort**: 1 day

Integrate LangChain with existing LLM clients (Ollama, OpenAI).

**Key Components**:
```python
from langchain.llms import Ollama, OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

class CampaignChatClient:
    """LangChain-powered conversational interface for campaign data."""

    def __init__(self, llm_provider: str, model_name: str):
        if llm_provider == "ollama":
            self.llm = Ollama(model=model_name, base_url="http://localhost:11434")
        elif llm_provider == "openai":
            self.llm = OpenAI(model=model_name)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
```

**Dependencies**: Add to `requirements.txt`:
```
langchain>=0.1.0
langchain-community>=0.1.0
```

**Files**: New `src/langchain/campaign_chat.py`, `requirements.txt`

#### Subtask 1.3: Build Knowledge Base Retriever
**Effort**: 2 days

Create retriever to fetch relevant campaign data for queries.

**Retriever Design**:
```python
class CampaignRetriever:
    """Retrieve relevant campaign data for conversational queries."""

    def __init__(self, knowledge_base_dir: Path, transcript_dir: Path):
        self.kb_dir = knowledge_base_dir
        self.transcript_dir = transcript_dir

    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """Retrieve top-k relevant documents for query."""
        # Search knowledge bases (NPCs, quests, locations)
        kb_results = self._search_knowledge_bases(query, top_k=3)

        # Search session transcripts
        transcript_results = self._search_transcripts(query, top_k=2)

        # Combine and rank by relevance
        return self._rank_results(kb_results + transcript_results, top_k)

    def _search_knowledge_bases(self, query: str, top_k: int) -> List[Document]:
        """Search structured knowledge bases."""
        results = []

        # Load all knowledge bases
        for kb_file in self.kb_dir.glob("*_knowledge.json"):
            kb = self._load_knowledge_base(kb_file)

            # Search NPCs
            for npc in kb.get("npcs", []):
                if self._matches_query(query, npc["name"], npc["description"]):
                    results.append(Document(
                        content=f"NPC: {npc['name']} - {npc['description']}",
                        metadata={"type": "npc", "source": kb_file.name}
                    ))

            # Search quests, locations, etc.
            # ...

        return results[:top_k]

    def _search_transcripts(self, query: str, top_k: int) -> List[Document]:
        """Search session transcripts."""
        # Use simple keyword matching initially
        # Can be upgraded to semantic search later (P2-LANGCHAIN-002)
        pass
```

**Files**: `src/langchain/retriever.py` (new)

#### Subtask 1.4: Create Conversational Chain
**Effort**: 2 days

Build LangChain chain for question answering with sources.

**Chain Design**:
```python
from langchain.chains import ConversationalRetrievalChain

class CampaignChatChain:
    """Conversational chain for campaign queries."""

    def __init__(self, llm, retriever: CampaignRetriever):
        self.llm = llm
        self.retriever = retriever

        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            ),
            return_source_documents=True
        )

    def ask(self, question: str) -> Dict:
        """Ask a question and get answer with sources."""
        result = self.chain({"question": question})

        return {
            "answer": result["answer"],
            "sources": [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata
                }
                for doc in result["source_documents"]
            ]
        }
```

**Files**: `src/langchain/campaign_chat.py`

#### Subtask 1.5: Prompt Engineering
**Effort**: 1 day

Design system prompt for campaign assistant persona.

**System Prompt**:
```
You are a helpful D&D campaign assistant. You have access to session transcripts,
NPC information, quest logs, and location data.

When answering questions:
1. Be concise but informative
2. Always cite your sources (session ID, timestamp)
3. If you don't have enough information, say so
4. For character actions, quote dialogue when relevant
5. Maintain continuity with previous conversation context

Campaign Context:
- Campaign Name: {campaign_name}
- Total Sessions: {num_sessions}
- Player Characters: {pc_names}
```

**Files**: New `prompts/campaign_assistant.txt`

#### Subtask 1.6: UI Integration - Chat Interface
**Effort**: 2 days

Add chat tab to Gradio UI.

**Features**:
- Chat input box with send button
- Conversation history display
- Source citations (clickable links to sessions)
- "New conversation" button
- Conversation history sidebar (list past conversations)

**UI Layout**:
```python
with gr.Tab("Campaign Chat"):
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Campaign Assistant", height=500)
            msg_input = gr.Textbox(
                label="Ask a question",
                placeholder="What happened in the last session?"
            )
            send_btn = gr.Button("Send")

        with gr.Column(scale=1):
            gr.Markdown("### Conversation History")
            conversation_list = gr.Dropdown(
                label="Past Conversations",
                choices=[]  # Populated dynamically
            )
            new_conversation_btn = gr.Button("New Conversation")

    # Source citations below chat
    sources_display = gr.Markdown(label="Sources")
```

**Files**: `app.py`, `src/ui/campaign_chat_tab.py` (new)

#### Subtask 1.7: Conversation Persistence
**Effort**: 1 day

Save and load conversation history.

**Storage**:
- Save conversations as JSON in `conversations/` directory
- Auto-save after each message
- Load conversation list on UI startup

**Files**: `src/langchain/conversation_store.py` (new)

#### Subtask 1.8: Testing
**Effort**: 1 day

Test conversational accuracy and source attribution.

**Test Cases**:
- Single-session queries ("What happened in session 5?")
- Multi-session queries ("Summarize the Crimson Peak arc")
- NPC queries ("Who is the Shadow Lord?")
- Character queries ("When did Thorin get his sword?")
- Follow-up questions (context retention)
- Queries with no relevant data (graceful handling)

**Files**: `tests/test_campaign_chat.py`

### Open Questions
- How many messages to keep in conversation memory?
- Should we support voice input/output?
- How to handle conflicting information across sessions?

---

## P2-LANGCHAIN-002: Semantic Search with RAG

**Files**: `src/langchain/semantic_search.py` (new), vector DB integration
**Effort**: 5-7 days
**Priority**: MEDIUM
**Dependencies**: P2-LANGCHAIN-001 (for integration)
**Status**: NOT STARTED

### Problem Statement
Current search (P2-LANGCHAIN-001 Subtask 1.3) uses simple keyword matching, which misses semantically similar queries. Example:
- Query: "Who is the dark wizard?" should match "Shadow Lord" (necromancer)
- Query: "What magical items do we have?" should match "Thorin's Flaming Sword"

Need semantic search with embeddings and vector database.

### Success Criteria
- [_] Semantic similarity search works across transcripts and knowledge bases
- [_] Faster than full-text search for large datasets
- [_] Supports hybrid search (keyword + semantic)
- [_] Embeddings stored persistently (regenerate only when data changes)
- [_] Works with local embedding models (no API dependency)

### Implementation Plan

#### Subtask 2.1: Choose Vector Database
**Effort**: 4 hours (research + decision)

Evaluate vector DB options for local deployment.

**Options**:
1. **ChromaDB** - Lightweight, easy setup, local-first
2. **FAISS** - Fast, but requires more setup
3. **Qdrant** - Production-grade, but heavier

**Recommendation**: Start with ChromaDB for simplicity.

**Decision Criteria**:
- Local deployment (no cloud dependency)
- Python integration
- Persistence support
- Community support

**Files**: Add to `requirements.txt`:
```
chromadb>=0.4.0
sentence-transformers>=2.2.0
```

#### Subtask 2.2: Set Up Embedding Model
**Effort**: 4 hours

Choose and configure embedding model.

**Model Options**:
1. **all-MiniLM-L6-v2** (384 dim, fast, good quality)
2. **all-mpnet-base-v2** (768 dim, slower, better quality)

**Recommendation**: Start with all-MiniLM-L6-v2 for speed.

**Code Example**:
```python
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    """Generate embeddings for text."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        return self.model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return self.model.encode(texts).tolist()
```

**Files**: New `src/langchain/embeddings.py`

#### Subtask 2.3: Build Vector Store
**Effort**: 1 day

Create vector store for campaign data.

**Code Example**:
```python
import chromadb
from chromadb.config import Settings

class CampaignVectorStore:
    """Vector database for semantic search."""

    def __init__(self, persist_dir: Path, embedding_service: EmbeddingService):
        self.client = chromadb.Client(Settings(
            persist_directory=str(persist_dir),
            anonymized_telemetry=False
        ))
        self.embedding = embedding_service

        # Collections for different data types
        self.transcript_collection = self.client.get_or_create_collection(
            name="transcripts",
            metadata={"description": "Session transcripts"}
        )
        self.knowledge_collection = self.client.get_or_create_collection(
            name="knowledge",
            metadata={"description": "NPCs, quests, locations"}
        )

    def add_transcript_segments(self, session_id: str, segments: List[Dict]):
        """Add transcript segments to vector store."""
        texts = [seg["text"] for seg in segments]
        embeddings = self.embedding.embed_batch(texts)
        ids = [f"{session_id}_{i}" for i in range(len(segments))]

        metadatas = [
            {
                "session_id": session_id,
                "speaker": seg["speaker"],
                "start": seg["start"],
                "end": seg["end"]
            }
            for seg in segments
        ]

        self.transcript_collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search across all collections."""
        query_embedding = self.embedding.embed(query)

        results = self.transcript_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        return [
            {
                "text": doc,
                "metadata": meta,
                "distance": dist
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0]
            )
        ]
```

**Files**: New `src/langchain/vector_store.py`

#### Subtask 2.4: Data Ingestion Pipeline
**Effort**: 2 days

Build pipeline to ingest transcripts and knowledge bases into vector store.

**Ingestion Flow**:
```python
class DataIngestor:
    """Ingest campaign data into vector store."""

    def __init__(self, vector_store: CampaignVectorStore):
        self.vector_store = vector_store

    def ingest_session(self, session_dir: Path):
        """Ingest a single session's data."""
        # Load diarized transcript
        transcript = self._load_transcript(session_dir / "diarized_transcript.json")

        # Chunk into segments (use existing segments from diarization)
        segments = self._prepare_segments(transcript)

        # Add to vector store
        session_id = session_dir.name
        self.vector_store.add_transcript_segments(session_id, segments)

    def ingest_knowledge_base(self, kb_file: Path):
        """Ingest knowledge base (NPCs, quests, etc.)."""
        kb = self._load_knowledge_base(kb_file)

        # Convert each NPC/quest/location to document
        documents = []
        for npc in kb.get("npcs", []):
            documents.append({
                "text": f"{npc['name']}: {npc['description']}",
                "metadata": {"type": "npc", "name": npc["name"]}
            })

        # Add to vector store
        self.vector_store.add_knowledge_documents(documents)

    def ingest_all(self, output_dir: Path, knowledge_dir: Path):
        """Ingest all sessions and knowledge bases."""
        # Ingest all sessions
        for session_dir in output_dir.iterdir():
            if session_dir.is_dir():
                self.ingest_session(session_dir)

        # Ingest all knowledge bases
        for kb_file in knowledge_dir.glob("*_knowledge.json"):
            self.ingest_knowledge_base(kb_file)
```

**Files**: New `src/langchain/data_ingestion.py`

#### Subtask 2.5: Hybrid Search (Keyword + Semantic)
**Effort**: 1 day

Combine keyword and semantic search for best results.

**Hybrid Search Strategy**:
```python
class HybridSearcher:
    """Combine keyword and semantic search."""

    def __init__(self, vector_store: CampaignVectorStore,
                 keyword_searcher: KeywordSearcher):
        self.vector = vector_store
        self.keyword = keyword_searcher

    def search(self, query: str, top_k: int = 5,
               semantic_weight: float = 0.7) -> List[Dict]:
        """Hybrid search with weighted ranking."""
        # Get semantic results
        semantic_results = self.vector.search(query, top_k=top_k * 2)

        # Get keyword results
        keyword_results = self.keyword.search(query, top_k=top_k * 2)

        # Merge and re-rank using Reciprocal Rank Fusion
        merged = self._reciprocal_rank_fusion(
            semantic_results,
            keyword_results,
            weights=(semantic_weight, 1 - semantic_weight)
        )

        return merged[:top_k]

    def _reciprocal_rank_fusion(self, results_a: List, results_b: List,
                                weights: Tuple[float, float]) -> List:
        """Merge results using RRF algorithm."""
        # Implementation of RRF ranking
        pass
```

**Files**: `src/langchain/hybrid_search.py` (new)

#### Subtask 2.6: Integrate with Campaign Chat
**Effort**: 1 day

Replace simple retriever in P2-LANGCHAIN-001 with semantic search.

**Code Changes**:
```python
# src/langchain/campaign_chat.py

class CampaignRetriever:
    def __init__(self, vector_store: CampaignVectorStore):
        self.vector_store = vector_store  # Changed from keyword search

    def retrieve(self, query: str, top_k: int = 5) -> List[Document]:
        """Retrieve using semantic search."""
        results = self.vector_store.search(query, top_k=top_k)

        return [
            Document(
                content=result["text"],
                metadata=result["metadata"]
            )
            for result in results
        ]
```

**Files**: `src/langchain/campaign_chat.py`

#### Subtask 2.7: CLI for Ingestion
**Effort**: 4 hours

Add CLI command to rebuild vector index.

**Commands**:
```bash
# Ingest all sessions and knowledge bases
python cli.py ingest --all

# Ingest specific session
python cli.py ingest --session session_005

# Rebuild entire index (clear + ingest)
python cli.py ingest --rebuild
```

**Files**: `cli.py`

#### Subtask 2.8: Testing
**Effort**: 1 day

Test semantic search accuracy.

**Test Cases**:
- Synonym matching ("dark wizard" -> "necromancer")
- Concept matching ("magical items" -> "Flaming Sword")
- Character name variants ("Thorin" vs "Thorin Ironforge")
- Multi-session queries
- Hybrid search vs pure semantic
- Performance with large datasets (10+ sessions)

**Files**: `tests/test_semantic_search.py`

### Open Questions
- Should we support image/audio embeddings for future features?
- How often to rebuild index (after each session, manually, scheduled)?
- What's the embedding update strategy when transcripts are corrected?

---

**See IMPLEMENTATION_PLANS.md for templates and P0 features**
**See IMPLEMENTATION_PLANS_PART2.md for P1 High Impact features**
**See IMPLEMENTATION_PLANS_SUMMARY.md for effort estimates and sprint planning**
