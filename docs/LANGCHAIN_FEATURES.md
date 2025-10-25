# LangChain Features Guide

This document describes the LangChain-powered features in the D&D Session Processor:
- **Campaign Chat**: Conversational interface for querying campaign data
- **Semantic Search**: AI-powered semantic search with vector embeddings

---

## Features Overview

### P2-LANGCHAIN-001: Conversational Campaign Interface

Ask natural language questions about your campaign and get answers with source citations.

**Example Queries:**
- "What happened in the last session?"
- "Who is the Shadow Lord?"
- "When did Thorin get his magic sword?"
- "Summarize the Crimson Peak arc"

**Key Features:**
- Natural language understanding
- Source citations (session ID, timestamp, speaker)
- Multi-session context
- Conversation history persistence
- Works with local LLM (Ollama) or OpenAI

### P2-LANGCHAIN-002: Semantic Search with RAG

Semantic similarity search across transcripts and knowledge bases using AI embeddings.

**Benefits:**
- Finds semantically similar content (e.g., "dark wizard" matches "necromancer")
- Faster than full-text search for large datasets
- Hybrid search combines keyword + semantic matching
- 100% local - no API calls required
- Persistent embeddings (only rebuild when data changes)

---

## Installation

### Install Dependencies

```bash
pip install langchain langchain-community chromadb sentence-transformers
```

### Verify Installation

Check that all dependencies are installed:

```bash
python -c "import langchain; import chromadb; import sentence_transformers; print('✓ All dependencies installed')"
```

---

## Quick Start

### Step 1: Process Sessions

First, process your D&D session recordings as usual:

```bash
python cli.py process session_001.m4a --session-id session_001
```

### Step 2: Ingest Data into Vector Database

Build the semantic search index:

```bash
# Ingest all sessions and knowledge bases
python cli.py ingest --all

# Or rebuild the entire index (clears existing data)
python cli.py ingest --rebuild

# Or ingest a specific session
python cli.py ingest --session session_001
```

### Step 3: Use Campaign Chat

#### Via Web UI

1. Start the Gradio interface:
   ```bash
   python app.py
   ```

2. Navigate to the "Campaign Chat" tab

3. Ask questions about your campaign

#### Via Code

```python
from src.langchain.campaign_chat import CampaignChatClient
from src.langchain.semantic_retriever import SemanticCampaignRetriever
from src.langchain.vector_store import CampaignVectorStore
from src.langchain.embeddings import EmbeddingService
from pathlib import Path

# Initialize components
embedding_service = EmbeddingService()
vector_store = CampaignVectorStore(
    persist_dir=Path("vector_db"),
    embedding_service=embedding_service
)
retriever = SemanticCampaignRetriever(vector_store)

# Create chat client
client = CampaignChatClient(retriever=retriever)

# Ask a question
response = client.ask("What happened in session 5?")
print(response["answer"])

# View sources
for source in response["sources"]:
    print(f"- {source['content']}")
```

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────┐
│          Campaign Chat UI               │
│     (Gradio Tab: src/ui/...)            │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│      CampaignChatClient                 │
│   (src/langchain/campaign_chat.py)      │
└───────────────┬─────────────────────────┘
                │
                ▼
        ┌───────┴────────┐
        │                │
        ▼                ▼
┌──────────────┐  ┌──────────────────────┐
│   Retriever  │  │  ConversationStore   │
│   (keyword)  │  │   (persistence)      │
└──────┬───────┘  └──────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│     SemanticCampaignRetriever            │
│ (src/langchain/semantic_retriever.py)    │
└───────────────┬──────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────┐
│       CampaignVectorStore                │
│   (src/langchain/vector_store.py)        │
│                                          │
│  ┌────────────────────────────────┐     │
│  │       ChromaDB                 │     │
│  │   - Transcript Collection       │     │
│  │   - Knowledge Collection        │     │
│  └────────────────────────────────┘     │
└───────────────┬──────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────┐
│       EmbeddingService                   │
│   (src/langchain/embeddings.py)          │
│                                          │
│   Model: all-MiniLM-L6-v2 (384 dim)     │
└──────────────────────────────────────────┘
```

### Data Flow

1. **Ingestion** (`cli.py ingest --all`):
   - Reads session transcripts and knowledge bases
   - Generates embeddings using sentence-transformers
   - Stores in ChromaDB collections

2. **Query** (User asks question in UI):
   - Question → EmbeddingService → Query embedding
   - Query embedding → ChromaDB → Top-k similar documents
   - Documents + Query → LLM → Natural language answer
   - Answer + Sources → UI display

3. **Persistence**:
   - Conversations saved as JSON in `conversations/`
   - Vector embeddings persisted in `vector_db/`

---

## Configuration

### Embedding Models

Default: `all-MiniLM-L6-v2` (384 dimensions, fast, 80MB)

To use a different model:

```python
from src.langchain.embeddings import EmbeddingService

# Higher quality, slower, larger
service = EmbeddingService(model_name="all-mpnet-base-v2")
```

### LLM Backend

Configured via environment variables (`.env` file):

```bash
# Use Ollama (default)
LLM_BACKEND=ollama
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_BASE_URL=http://localhost:11434

# Or use OpenAI
LLM_BACKEND=openai
OPENAI_API_KEY=sk-...
```

---

## CLI Reference

### Ingestion Commands

```bash
# Ingest all sessions and knowledge bases
python cli.py ingest --all

# Ingest a specific session
python cli.py ingest --session session_005

# Rebuild entire index (clears existing data)
python cli.py ingest --rebuild

# Use custom directories
python cli.py ingest --all \
  --output-dir /path/to/sessions \
  --knowledge-dir /path/to/knowledge
```

### View Vector Store Stats

```bash
python cli.py ingest --all  # Shows stats at the end
```

Output:
```
Vector Store Stats:
  Transcript Segments: 1,234
  Knowledge Documents: 56
  Total: 1,290
  Persist Dir: F:\Repos\VideoChunking\vector_db
```

---

## Directory Structure

```
VideoChunking/
├── src/langchain/              # LangChain modules
│   ├── campaign_chat.py        # Chat client
│   ├── retriever.py            # Keyword retriever
│   ├── semantic_retriever.py   # Semantic retriever
│   ├── vector_store.py         # ChromaDB wrapper
│   ├── embeddings.py           # Embedding service
│   ├── data_ingestion.py       # Ingestion pipeline
│   ├── hybrid_search.py        # Hybrid search (keyword + semantic)
│   └── conversation_store.py   # Conversation persistence
├── prompts/
│   └── campaign_assistant.txt  # System prompt template
├── schemas/
│   └── conversation.json       # Conversation schema
├── conversations/              # Saved conversations
│   ├── conv_abc123.json
│   └── conv_def456.json
└── vector_db/                  # ChromaDB persistent storage
    ├── chroma.sqlite3
    └── ...
```

---

## Troubleshooting

### Issue: "LangChain dependencies not installed"

**Solution:**
```bash
pip install langchain langchain-community chromadb sentence-transformers
```

### Issue: "Error loading embedding model"

**Solution:**

The first time you use semantic search, sentence-transformers will download the model (~80MB). Ensure you have internet access, or download manually:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

### Issue: "No results from semantic search"

**Solution:**

1. Ensure you've ingested data:
   ```bash
   python cli.py ingest --all
   ```

2. Check vector store stats to verify data is indexed

3. Try a different query - semantic search works best with natural language

### Issue: "ChromaDB persistence error"

**Solution:**

1. Check that `vector_db/` directory has write permissions

2. If corrupted, rebuild the index:
   ```bash
   python cli.py ingest --rebuild
   ```

---

## Performance Tips

### For Large Campaigns (100+ sessions)

1. **Batch Ingestion**: Ingest sessions in batches rather than all at once
2. **Scheduled Rebuilds**: Run `ingest --rebuild` weekly, not after every session
3. **Query Caching**: Future enhancement - cache frequent queries

### Embedding Performance

- **Default model** (`all-MiniLM-L6-v2`): ~1000 sentences/sec on CPU
- **GPU Acceleration**: Install `torch` with CUDA for 10x speedup
- **Batch Size**: Adjust in `embeddings.py` if needed

### Vector Store

- **ChromaDB** is optimized for < 1M documents
- Current setup handles ~10,000 transcript segments efficiently
- For very large campaigns, consider upgrading to Qdrant

---

## Examples

### Example 1: Single-Session Query

```python
client = CampaignChatClient(retriever=semantic_retriever)
response = client.ask("What happened in session 5?")
print(response["answer"])
```

### Example 2: Multi-Session Arc Summary

```python
response = client.ask("Summarize the Crimson Peak storyline across all sessions")
print(response["answer"])

for source in response["sources"]:
    session = source["metadata"]["session_id"]
    print(f"Referenced: {session}")
```

### Example 3: NPC Lookup

```python
response = client.ask("Tell me about the Shadow Lord")
print(response["answer"])
```

### Example 4: Conversation History

```python
from src.langchain.conversation_store import ConversationStore

store = ConversationStore(Path("conversations"))

# Create conversation
conv_id = store.create_conversation(campaign="Broken Seekers")

# Add messages
store.add_message(conv_id, "user", "What happened last session?")
store.add_message(conv_id, "assistant", "The party defeated the dragon...", sources=[...])

# Load later
conversations = store.list_conversations()
for conv in conversations:
    print(f"{conv['conversation_id']}: {conv['message_count']} messages")
```

---

## Limitations

1. **Context Window**: LLM context is limited - very long answers may be truncated
2. **Source Accuracy**: LLM may occasionally cite incorrect sources (verify important facts)
3. **Hallucinations**: LLM may generate plausible but incorrect information - always check sources
4. **Embedding Quality**: Semantic search quality depends on transcript quality
5. **No Real-Time Updates**: Requires manual `ingest` command after new sessions

---

## Future Enhancements

See `IMPLEMENTATION_PLANS_PART3.md` for planned improvements:

- [ ] Auto-ingestion after session processing
- [ ] Voice input/output support
- [ ] Query caching for performance
- [ ] Multi-modal embeddings (images, audio)
- [ ] Conflict resolution for contradictory information
- [ ] Conversation memory limits for long chats

---

## Support

For issues or questions:
- Check the implementation plans: `IMPLEMENTATION_PLANS_PART3.md`
- Review test files: `tests/test_campaign_chat.py`, `tests/test_semantic_search.py`
- File an issue on GitHub

---

**Last Updated**: 2025-10-25
**Status**: ✅ Production Ready
