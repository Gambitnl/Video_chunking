# VideoChunking Project Roadmap

> **Last Updated**: 2025-11-20
> **Last Cleanup**: 2025-11-20
> **Multi-Agent Collaboration**: This roadmap consolidates plans from Claude, Gemini, and ChatGPT (Codex)

---

## Vision & Objectives

Transform long-form D&D session recordings into rich, searchable transcripts with:
- Speaker diarization
- IC/OOC classification
- Character context tracking
- Automated campaign knowledge extraction
- Narrative generation capabilities
- Delivered via CLI and Gradio UI

**Target Users**: D&D groups wanting to preserve session history, track character development, and create campaign documentation with minimal manual effort.

---

## Current Status (Updated 2025-11-20)

### Core Pipeline (Production Ready)
- Audio conversion (M4A -> WAV via FFmpeg)
- Hybrid VAD-based chunking with smart pause detection
- Multi-backend transcription (local Whisper, Groq, OpenAI)
- LCS-based overlap merging
- Speaker diarization (PyAnnote.audio)
- IC/OOC classification (Ollama)
- Multi-format output (TXT, JSON, SRT subtitles)
- Audio segment export (optional)

### Campaign Management
- Party configuration system
- Character profiles (individual file storage)
- Campaign Dashboard (health monitoring)
- Knowledge Base (auto-extraction of quests, NPCs, locations, items, plot hooks)
- Import Session Notes (backfill capability)
- Story Notebooks (narrative generation with Google Docs integration)

### User Interfaces
- Gradio Web UI (multi-tab interface)
- Rich CLI (comprehensive commands)
- App Manager (real-time status monitoring)

### Quality Infrastructure
- Pytest test suite (unit + integration)
- Test markers for fast/slow separation
- Unicode compatibility fixes
- Comprehensive documentation

---

## Roadmap by Priority

### P0: Critical / Immediate

✅ **ALL COMPLETE** (Completed 2025-10-26) - See [Archived Completed Work](#archived--completed-work) below for full details.

All 9 P0 tasks completed:
- 6 Bug fixes (stale clip cleanup, type casting, checkpoints, chunking failures, snippet placeholders)
- 3 Refactoring tasks (campaign dashboard extraction, story generation extraction, UI modules split)

---

### P1: High Impact Features

✅ **ALL COMPLETE** (Completed 2025-10-24 to 2025-11-02) - See [Archived Completed Work](#archived--completed-work) below for full details.

All 6 P1 features completed:
1. Automatic Character Profile Extraction (2025-10-31) - 80% reduction in manual data entry
2. UI Modernization (2025-11-01) - 16 tabs -> 5 sections, modern theme
3. Streaming Snippet Export (2025-11-18) - 90% memory footprint reduction
4. Batch Processing (2025-10-24) - Multi-file upload and processing
5. Campaign Lifecycle Manager (2025-11-02) - Multi-campaign management
6. Session Cleanup & Validation (2025-11-01) - Data integrity tools

---

### P2: Important Enhancements (Next 1-2 Months)

#### LangChain Integration (COMPLETED)

**1. Conversational Campaign Interface**
**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] Completed (2025-10-25)
**Effort**: 7-10 days
**Impact**: HIGH - Natural language campaign queries

**Features**:
- Natural language query interface for campaign data
- Source citation (session ID, timestamp, speaker)
- Multi-session context handling
- Conversation history persistence
- Works with Ollama (local) and OpenAI
- Gradio UI integration

**2. Semantic Search with RAG**
**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] Completed (2025-10-25)
**Effort**: 5-7 days
**Impact**: HIGH - AI-powered semantic search

**Features**:
- ChromaDB vector database integration
- Sentence-transformers embeddings (local, no API)
- Semantic similarity search across transcripts and knowledge bases
- Hybrid search (keyword + semantic)
- CLI ingestion commands
- Persistent vector storage

**Known Issues**: [DONE] All critical security issues resolved! (P2.1 completed 2025-10-25)
- ~~Security vulnerabilities (path traversal, prompt injection)~~ **FIXED**
- ~~Performance issues with large datasets~~ **FIXED**
- ~~Missing test coverage for components~~ **FIXED** (improved from 49% to 87% - 2025-11-06)
- UX improvements needed in Campaign Chat UI (deferred to future release)

#### LangChain Quality & Security Fixes (P2.1)

**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] **COMPLETED** (2025-10-25)
**Priority**: HIGH (Critical security issues)
**Effort**: 6 hours (originally estimated 5-7 days)
**Test Coverage**: 17 comprehensive security tests (100% pass rate)
**Documentation**: See [LANGCHAIN_SECURITY_FIXES.md](docs/LANGCHAIN_SECURITY_FIXES.md)

**Critical Security Fixes** (ALL COMPLETED [DONE]):
1. [DONE] **Path Traversal Vulnerability** (ConversationStore)
   - File: `src/langchain/conversation_store.py`
   - Issue: User-controlled conversation IDs used in file paths
   - Impact: CRITICAL - arbitrary file read/write
   - **Fix Applied**: Regex validation (`conv_[8 hex]`), path resolution checks, multi-layer defense
   - **Tests**: 3 tests verify path traversal protection
   - Completed: 2025-10-25

2. [DONE] **Prompt Injection** (CampaignChatClient)
   - File: `src/langchain/campaign_chat.py`
   - Issue: User input directly concatenated into prompts
   - Impact: CRITICAL - LLM manipulation
   - **Fix Applied**: `sanitize_input()` function, pattern detection, structured prompts, 2000 char limit
   - **Tests**: 6 tests verify injection protection
   - Completed: 2025-10-25

3. [DONE] **Race Conditions** (Conversation Persistence)
   - File: `src/langchain/conversation_store.py`
   - Issue: Load-modify-save pattern without locking
   - Impact: CRITICAL - data loss in concurrent writes
   - **Fix Applied**: File-based locking via `filelock`, 10s timeout, atomic operations
   - **Tests**: 2 tests verify concurrent operation safety
   - Completed: 2025-10-25

4. [DONE] **Unsafe JSON Deserialization**
   - Files: `conversation_store.py`, `retriever.py`, `data_ingestion.py`
   - Issue: No schema validation on loaded JSON
   - Impact: HIGH - data corruption, injection attacks
   - **Fix Applied**: Schema validation with `CONVERSATION_SCHEMA`, validates all keys and structure
   - **Tests**: 3 tests verify schema validation
   - Completed: 2025-10-25

**Performance Fixes** (ALL COMPLETED [DONE]):
5. [DONE] **Memory Leaks** (Vector Store)
   - File: `src/langchain/vector_store.py`
   - Issue: Batch embedding without batching (OOM on large datasets)
   - Impact: HIGH - crashes on 10k+ segments
   - **Fix Applied**: Batched processing (`EMBEDDING_BATCH_SIZE=100`, inner batch 32)
   - **Result**: Can process 100k+ segments with constant memory usage
   - Completed: 2025-10-25

6. [DONE] **Knowledge Base Caching**
   - File: `src/langchain/retriever.py`
   - Issue: Disk I/O on every search query (~100ms penalty)
   - Impact: HIGH - poor search performance
   - **Fix Applied**: LRU cache with 5-min TTL, cache size 128, `clear_cache()` method
   - **Result**: 100x speedup for cached queries (<1ms vs ~100ms)
   - **Tests**: 3 tests verify caching behavior
   - Completed: 2025-10-25

7. [DONE] **Unbounded Memory Growth** (Conversation Memory)
   - File: `src/langchain/campaign_chat.py`
   - Issue: ConversationBufferMemory grows indefinitely
   - Impact: MEDIUM - memory leak in long conversations
   - **Fix Applied**: Switched to `ConversationBufferWindowMemory` (k=10, keeps last 20 messages)
   - **Result**: Constant ~100KB memory vs unbounded growth
   - Completed: 2025-10-25

**Test Coverage Expansion**:
8. **LangChain Component Tests**
   - Status: [DONE] **COMPLETED** (2025-11-06)
   - **Overall Coverage**: 49% → **87%** (+38 percentage points) - **TARGET EXCEEDED**
   - **New Test Files Created** (4 files, 70 new tests):
     - test_langchain_vector_store.py: 28 tests (vector_store.py: 12% → 96%)
     - test_langchain_embeddings.py: 10 tests (embeddings.py: 0% → 100%)
     - test_langchain_data_ingestion.py: 23 tests (data_ingestion.py: 0% → 97%)
     - test_langchain_retriever.py: 9 tests (retriever.py: 36% → 81%)
   - **Existing Test Coverage**: CampaignChatClient (27 tests), HybridSearcher (15 tests)
   - **Total LangChain Tests**: 152 passing, 1 skipped (153 total)
   - **Files**: tests/test_langchain_*.py (9 test files)
   - Impact: HIGH - prevents regressions, validates security fixes, comprehensive coverage
   - Completed: 2025-11-06 (~20 minutes actual effort for 70 new tests)

9. **Concurrency Tests**
   - No tests for concurrent conversation writes
   - No tests for vector store corruption recovery
   - Effort: 1 day

10. **Performance Tests**
    - No tests for large datasets (10k+ segments)
    - No benchmarks for search performance
    - Effort: 1 day

**UX Improvements** (Campaign Chat Tab): [DONE] **COMPLETED 2025-11-18**
11. **Missing UI Features** - ALL FIXED
    - ✅ Loading indicators during LLM calls (three-step pattern)
    - ✅ Error messages sanitized (no exception exposure)
    - ✅ Conversation management (delete, rename implemented)
    - ✅ Sources display working as designed
    - ✅ Conversation dropdown updates after operations
    - ✅ ASCII-only compliance enforced
    - Actual effort: 2 hours (estimated: 1-2 days)

**Documentation**:
12. **Security Best Practices Guide**
    - Document API key handling
    - Document input sanitization
    - Document deployment security
    - Effort: 4 hours

#### Analytics & Visualization

**1. Session Analytics Dashboard**
**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] **COMPLETED** (2025-11-17)
**Effort**: 2-3 days (actual: ~6 hours)
**Impact**: HIGH - Enables session comparison and campaign analytics

**Features** (ALL COMPLETED):
- [x] Session comparison view (side-by-side tables)
- [x] Character participation tracking (speaking time, message counts)
- [x] Speaking time distribution (bar charts)
- [x] IC/OOC ratio analysis over time (timeline charts)
- [x] Auto-generated insights from session comparison
- [x] Export to JSON, CSV, Markdown formats
- [x] Gradio UI integration

**Files Created**:
- `src/analytics/data_models.py` - Core data structures (314 lines)
- `src/analytics/session_analyzer.py` - Analytics engine (532 lines)
- `src/analytics/visualizer.py` - Markdown charts (355 lines)
- `src/analytics/exporter.py` - Export functionality (264 lines)
- `src/ui/analytics_tab.py` - Gradio UI tab (323 lines)
- `tests/test_analytics_data_models.py` - 30+ unit tests
- `tests/test_analytics_session_analyzer.py` - 20+ unit tests
- `IMPLEMENTATION_PLAN_SESSION_ANALYTICS.md` - Detailed plan

**Test Coverage**: 50+ tests written for all core modules

**Performance**:
- Analytics calculation: <5s for 10 sessions
- Results cached with LRU cache (max 50 sessions)
- Export: <1s for all formats

**2. Character Analytics & Filtering**
**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] **COMPLETED** (2025-11-18)
**Effort**: 3 days (actual: ~6 hours)
**Impact**: HIGH - Comprehensive character and party analytics

**Features** (ALL COMPLETED):
- [x] Action filtering/search by type or session
- [x] Character statistics and progression timelines
- [x] **Session Timeline View**: Chronological action feed across all sessions with level progression, inventory changes, relationship evolution, goal completion tracking
- [x] **Party-Wide Analytics**: Party composition breakdown, shared relationships/connections, item distribution, action type balance, session participation matrix
- [x] **Data Validation & Warnings**: Detect missing actions for characters in sessions, duplicate items, relationships without "first met" session, invalid session references
- [x] Gradio UI with 3 tabs (Timeline View, Party Analytics, Data Validation)
- [x] Multiple export formats (Markdown, HTML, JSON)

**Files Created**:
- `src/analytics/character_analytics.py` - Core analytics engine (340 lines)
- `src/analytics/timeline_view.py` - Timeline generation (340 lines)
- `src/analytics/party_analytics.py` - Party analysis (390 lines)
- `src/analytics/data_validator.py` - Data quality validation (410 lines)
- `src/ui/character_analytics_tab.py` - Gradio UI (440 lines)
- `tests/test_character_analytics.py` - 30+ unit tests
- `IMPLEMENTATION_PLAN_CHARACTER_ANALYTICS.md` - Detailed implementation plan

**Test Coverage**: 30+ tests written for core analytics modules

**3. OOC Keyword & Topic Analysis**
**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] **COMPLETED** (2025-11-18)
**Effort**: 2 days (actual: ~3 hours)
**Impact**: HIGH - Comprehensive OOC analysis with topics and insights

**Features** (ALL COMPLETED):
- [x] TF-IDF keyword extraction (replaces simple frequency)
- [x] LDA topic modeling with automatic labeling
- [x] Inside joke detection (high-frequency unique terms)
- [x] Discussion pattern analysis
- [x] Text diversity metrics (Shannon entropy, lexical diversity, vocabulary richness)
- [x] Multi-session comparison and theme tracking
- [x] Enhanced Social Insights UI with topics display
- [x] Topic Nebula word cloud visualization
- [x] Comprehensive test suite (50+ tests)

**Files Created/Modified**:
- `src/analyzer.py` - Complete rewrite with TF-IDF, LDA, insights (672 lines)
- `src/ui/social_insights_tab.py` - Enhanced UI with topics and insights (367 lines)
- `tests/test_analyzer.py` - Comprehensive test coverage (529 lines, 50+ tests)
- `IMPLEMENTATION_PLAN_OOC_TOPIC_ANALYSIS.md` - Detailed implementation plan

**Dependencies Added**:
- scikit-learn (TF-IDF and LDA)
- Optional: nltk (better tokenization)

**Test Coverage**: 50+ tests covering all analyzer features

**Performance**:
- Keyword extraction: <2s for 1000-word transcript
- Topic modeling: <10s for 1000-word transcript
- Memory: <100MB for single session analysis

#### Advanced Features

**4. Session Search Functionality**
**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] **COMPLETED** (2025-11-17)
**Effort**: 1 day (actual: 8 hours)
**Impact**: HIGH - Enables quick reference across sessions

**Features** (ALL COMPLETED):
- [x] Full-text search across transcripts (case-insensitive substring matching)
- [x] Filter by speaker, IC/OOC, time range, session ID
- [x] Regex support (advanced pattern matching)
- [x] Exact phrase matching
- [x] Export search results to JSON, CSV, TXT, Markdown
- [x] Context display (2 segments before/after)
- [x] Result ranking by relevance
- [x] Search index caching for performance

**Files Created**:
- `src/transcript_indexer.py` - Index builder (382 lines)
- `src/search_engine.py` - Search engine (335 lines)
- `src/search_exporter.py` - Export functionality (283 lines)
- `src/ui/search_tab.py` - Search UI (387 lines)
- `tests/test_transcript_indexer.py` - 13 tests
- `tests/test_search_engine.py` - 27 tests
- `tests/test_search_exporter.py` - 11 tests

**Test Coverage**: 28 tests, 85%+ coverage

**Performance**:
- Index build: ~2s for 10 sessions
- Query time: <100ms
- Export: <500ms for 100 results

**5. Cross-Link Sessions to Characters**
**Owner**: Claude (backlog item)
**Effort**: 2 days

- Map speaker diarization output to character profiles
- Consistent naming across sessions
- **Voice-to-Character Mapping**: Link speaker diarization IDs to character names, enable cross-session speaker consistency
- Voice embedding comparison (optional)
- **Speaker Voice Samples** (FEATURE-007): Upload voice samples for each player to improve initial identification and reduce manual mapping

#### Process Cancellation Feature

**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] **COMPLETED** (2025-11-17)
**Effort**: 2-3 hours (actual: ~2 hours)
**Impact**: MEDIUM - Better UX for long sessions
**Source**: [JULES_SESSION_ANALYSIS.md](docs/JULES_SESSION_ANALYSIS.md#todo-002-process-cancellation-feature)

**Features** (ALL COMPLETED):
- [x] Add `cancel_event` parameter to pipeline processing
- [x] Create `CancelledError` exception class
- [x] Thread-safe cancellation mechanism using threading.Event
- [x] Add "Cancel" button to Gradio UI (Process Session tab)
- [x] Handle cancellation gracefully with friendly user message
- [x] Global dictionary to track active cancel events by session_id

**Files Modified**:
- `src/exceptions.py` - Defined CancelledError exception class
- `src/pipeline.py` - Added cancel_event parameter, periodic checks after each stage
- `app.py` - Created cancel_processing function, handle CancelledError, manage cancel_events
- `src/ui/process_session_components.py` - Added Cancel button to UI
- `src/ui/process_session_tab_modern.py` - Added cancel_fn parameter
- `src/ui/process_session_events.py` - Wired Cancel button event handler

**Implementation Details**:
- Cancel button visible during processing, hidden when idle
- Cancellation checks added after each of 9 pipeline stages
- Cancel events stored in global dictionary keyed by session_id
- Cleanup happens automatically in finally block
- Audit logging for cancellation events

**Validation** (Ready for Manual Testing):
- User can click Cancel button during processing
- Pipeline checks for cancellation after each stage (9 checkpoints)
- Cancel event properly cleaned up when processing ends
- User sees "Processing was cancelled by user" message
- Proper audit logging of cancellation events

---

#### Interactive Clarification System

**Owner**: Open
**Status**: Proposed
**Effort**: 5-7 days
**Impact**: HIGH - Significantly improves accuracy for ambiguous cases
**Priority**: P2 (Important Enhancement)

**Problem Statement**:
Current pipeline makes best-guess decisions when uncertain about:
- Speaker identification (confidence < 0.7)
- Character-to-speaker mapping (ambiguous matches)
- IC/OOC classification (borderline confidence scores)
- Speaker count mismatches (detected vs. expected)

These guesses can compound errors throughout the session, reducing transcript quality.

**Proposed Solution**:
Real-time chat interface in Gradio UI where the pipeline pauses to ask users clarifying questions when confidence is low. User responses are stored for learning and improve future accuracy.

**Key Features**:
1. **Question Queue System** - Pause pipeline, queue questions with context
2. **Interactive Chat UI** - Real-time questions during processing with audio playback
3. **Learning System** - Store corrections to improve future confidence
4. **Confidence Thresholds** - Configurable thresholds for triggering questions
5. **Timeout Handling** - Continue with best guess if user doesn't respond

**Example User Experience**:
```
[Pipeline Processing: 45% complete]

AI: "I detected this segment at 12:35"
    [Play Audio Button]
    > "I think we should attack the dragon now!"

    Confidence: 68% (Speaker_01 = "Thorin")

    Is this correct?
    [Yes, that's Thorin] [No, it's someone else] [Skip]
```

**Use Cases**:
- Diarization: "I'm 68% confident this is Thorin. Confirm?"
- Character mapping: "I detected 5 speakers but you specified 4 characters. Who is SPEAKER_04?"
- IC/OOC: "This seems borderline IC/OOC (62% confidence). Which is it?"
- Speaker identification: "This voice is similar to both Alice and Bob. Who's speaking?"

**Components to Implement**:
1. **InteractiveClarifier** (`src/interactive_clarifier.py`) - NEW
   - Question queue with priority levels
   - Context storage (audio snippets, transcript text, timestamps)
   - User response handling and validation
   - Learning from corrections

2. **Background Process Communication** (`app_manager.py`) - MODIFY
   - Pipeline pause/resume mechanism
   - WebSocket/SSE for real-time UI updates
   - Question routing to active UI sessions

3. **Chat UI Component** (`src/ui/process_session_tab_modern.py`) - MODIFY
   - Real-time chat interface during processing
   - Audio playback for context
   - Quick-action buttons for common responses
   - Timeout countdown display

4. **Learning Integration** - MODIFY
   - Update speaker embeddings based on feedback (`src/diarizer.py`)
   - Store corrections in party profiles (`src/party_config.py`)
   - Improve confidence scoring algorithms

**Configuration**:
```python
# .env additions
INTERACTIVE_CLARIFICATION_ENABLED=true
CLARIFICATION_CONFIDENCE_THRESHOLD=0.7  # Ask if below this
CLARIFICATION_TIMEOUT_SECONDS=60        # Auto-skip if no response
CLARIFICATION_MAX_QUESTIONS=20          # Limit per session
```

**Technical Challenges**:
- Real-time communication between background process and UI
- Audio snippet extraction and playback
- State management during pipeline pause
- Graceful degradation if UI disconnected
- Testing interactive flows

**Success Metrics**:
- Reduction in post-processing corrections needed
- Improved speaker identification accuracy (target: >90%)
- User satisfaction with interactive experience
- Learning effectiveness (fewer questions in later sessions)

**Implementation Plan**:
See [IMPLEMENTATION_PLANS_INTERACTIVE_CLARIFICATION.md](IMPLEMENTATION_PLANS_INTERACTIVE_CLARIFICATION.md)

**Dependencies**:
- Requires stable background processing (app_manager.py)
- Requires audio snippet extraction (snipper.py)
- Optional: Real-time status updates (WebSocket/SSE)

---

### P3: Future Enhancements (2-3+ Months)

#### Character Profile Enhancements

**Owner**: Claude
**Status**: Future nice-to-have features

**1. Profile Templates**
- Effort: 1 day
- Class-based templates (Wizard, Cleric, Ranger, etc.)
- Race templates with typical traits
- Merge template + custom data for quick character creation

**2. Enhanced Export Formats**
- Effort: 2 days
- Markdown files (for wikis, Obsidian)
- PDF character sheets (styled)
- Roll20/D&D Beyond compatible formats
- HTML standalone pages

**3. Character Comparison**
- Effort: 1 day
- Side-by-side character analysis
- Compare stats, progression, participation

**4. Character Images**
- Effort: 1 day
- Add portrait images to profiles
- Storage in `models/character_images/` directory
- Display in UI

---

#### Gemini Constellation Features

**Owner**: Gemini
**Theme**: Data-centric visualizations with dark theme

**1. Live Transcription Mode**
- Streaming capture via microphone
- Rolling transcript updates in real-time
- UI: New "Live" tab with `gr.Audio(sources=["microphone"])`
- Estimated effort: 3-4 days

**2. Sound Event Detection**
- Integrate YAMNet or similar model
- Detect: [Laughter], [Applause], [Music], [Dice Rolling]
- Insert event annotations in transcript
- Estimated effort: 2-3 days

**3. Visualization Suite**
- **Speaker Constellation Graph**: Network graph of speaker interactions
- **Session Galaxy View**: Scatter plot of session timeline vs sentiment/pacing
- **Topic Nebula**: Word cloud from OOC analysis
- UI: D3.js or Vis.js integration in Gradio HTML component
- Theme: "Gemini Constellation" dark theme (see GEMINI_FEATURE_PROPOSAL.md)
- Estimated effort: 5-7 days total

#### Advanced Campaign Tools

**4. Combat Encounter Extraction**
**Owner**: Open
**Effort**: 2-3 days

- Detect combat start/end markers
- Parse initiative, attacks, damage
- Generate combat summary
- Track character performance

**5. Campaign Wiki Generation**
**Owner**: Open
**Effort**: 5-7 days

- Auto-generate wiki pages from knowledge base
- NPC directory with relationship web
- Location catalog
- Item compendium
- Timeline of events

**6. Session Notebook Enhancements**
**Status**: Base feature implemented

- Character first-person POV (COMPLETED)
- Narrator perspective (COMPLETED)
- Additional perspectives: Journal entries, session recaps
- Estimated effort: 2 days

---

### P4: Infrastructure & Quality (Ongoing)

#### Testing Expansion
**Owner**: ChatGPT (Codex) + All agents
**Status**: In progress

**Completed**:
- [x] Basic pytest suite (`test_snipper.py`, `test_merger.py`, `test_formatter.py`)
- [x] Test markers (@pytest.mark.slow)
- [x] Lazy loading of Whisper model

**Planned**:
1. **Test Coverage Expansion**
   - Formatter timestamp tests
   - Speaker profile tests
   - Mocked end-to-end pipeline tests
   - Test fixtures library (small audio samples)
   - Target: >85% branch coverage

2. **Integration Tests**
   - Full pipeline test with fixtures
   - UI workflow tests
   - Batch processing tests

3. **UI Integration Tests** (Optional)
   **Owner**: Open (from Jules session analysis)
   **Status**: Not Started
   **Effort**: 1-2 hours
   **Priority**: LOW
   **Source**: [JULES_SESSION_ANALYSIS.md](docs/JULES_SESSION_ANALYSIS.md#todo-003-ui-integration-tests-optional)

   **Features**:
   - Pytest-based tests using gradio_client
   - Test campaign creation, modification, deletion
   - Test session processing workflow
   - Use pytest fixtures for setup/teardown
   - Mock or use test data files (not production)

   **Files**:
   - `tests/integration/test_ui_endpoints.py` (new)

   **Notes**:
   - Lower priority than unit tests
   - Requires running app in background
   - More fragile than unit tests
   - Use as reference: `jules_session_analyzed.patch` (data_integrity_test.py)

#### Logging & Telemetry
**Owner**: ChatGPT (Codex) + Gemini
**Effort**: 1-2 days

- [x] SessionLogger integration in pipeline (COMPLETED)
- [x] Funnel remaining `print()` statements through SessionLogger (2025-11-06)
- [x] Expose log-level controls in UI/CLI (2025-11-06)
- [x] Add audit logging for security (2025-11-06)

#### Performance Optimization

**1. Memory Optimization**
- Current: 1-2GB for 4-hour session processing
- Target: <500MB
- Approach: Streaming, incremental processing

**2. Processing Speed**
- Current: 10-12 hours (CPU local Whisper)
- With GPU: 1-2 hours
- With Groq API: 20-30 minutes
- Document hardware requirements

**3. Scalability Targets**
- Sessions: Support 100+ sessions
- Characters: Support 50+ characters
- Multi-user support (future)

#### Documentation Gaps

**1. Troubleshooting Guide**
- Common errors and solutions
- GPU setup issues
- Ollama connection problems
- FFmpeg installation troubleshooting

**2. API Documentation**
- Python API usage examples
- Custom integration guides
- Webhook/callback system

**3. Architecture Diagrams**
- Visual pipeline flow
- Component interaction diagrams
- Data flow diagrams

---

## MCP Integration Roadmap

**Owner**: Open
**Status**: Planned
**Priority**: P3 (Future)

1. Wrap each pipeline stage as reusable tool function (typed signatures, docstrings)
2. Create LangChain agent module (`src/agent.py`)
3. Add LlamaIndex-based retrieval for transcripts, knowledge bases, profile artifacts
4. Provide OpenAI Function Calling schemas for external orchestrators
5. Support Ollama as local backend (config toggle)
6. Extend tests with mocked LLMs
7. Update documentation with agent/LLM setup and usage examples

---

## Manifest UX Enhancements

**Owner**: ChatGPT (Codex)
**Status**: Planned

1. **CLI/CSV utility for inspecting segment manifests**
   - Command: `cli.py show-manifest <session_id>`
   - Display segment details in formatted table
   - Estimated effort: 0.5 days

2. **Duration summaries**
   - Total duration by speaker
   - IC vs OOC time breakdown
   - Estimated effort: 0.5 days

3. **Enriched manifest with text + classification metadata**
   - Status: PARTIALLY COMPLETE (timing + speaker)
   - Add: Transcript text snippet, IC/OOC label, confidence score
   - Enable sampling clips with context
   - Estimated effort: 1 day

4. **Optional CSV export with spreadsheet workflows**
   - Export manifest as CSV
   - Include all metadata fields
   - Estimated effort: 0.5 days

---

## Advanced Workflow Features

**Owner**: ChatGPT (Codex)
**Status**: Future exploration

**Incremental Config Autofill**
- During pipeline processing, have LLM progressively backfill missing party metadata
- Auto-infer: Character names, player names, factions
- Display newly inferred details without waiting for full session completion
- Estimated effort: 3 days
- Impact: MEDIUM - reduces upfront configuration burden

---

## Coordination Notes

### Multi-Agent Ownership

**Before implementing**, verify no other agent is actively working on the item:
- Check COLLECTIVE_ROADMAP.md
- Check agent-specific review docs (CLAUDE_SONNET_45_ANALYSIS.md, GEMINI_CODE_REVIEW.md, CHATGPT_CODEX_REVIEW.md)
- Update docs after claiming work

**Agent Priorities** (to prevent overlap):

| Agent | Primary Focus Areas |
|-------|---------------------|
| **Claude** | Character profiles, campaign management, UI enhancements, bug fixes |
| **ChatGPT (Codex)** | Testing, streaming optimizations, telemetry, manifest UX |
| **Gemini** | Visualizations, live features, sound detection, UI theme |

### Testing Policy
- Expand pytest coverage alongside new features
- Prefer deterministic fixtures over network-dependent calls
- Every feature should have unit tests

### Documentation Policy
- Every shipped feature updates README/USAGE/QUICKREF
- Update agent review logs to prevent overlap
- Add troubleshooting notes for common issues

---

## Success Metrics

### Phase 1 (P0 Complete) [DONE]
**Status**: [DONE] **COMPLETE** (2025-10-26)

- [x] App.py reduced to <1,000 lines via refactoring
- [x] All existing tests pass
- [x] Checkpoint system enables resumable processing
- [x] Zero data loss on long sessions (checkpoint robustness improved)
- [x] All P0 bugs fixed and deployed

### Phase 2 (P1 Complete)
**Status**: **PARTIALLY COMPLETE** (5 of 6 features done, 83%)

- [x] Character profiles auto-populate from transcripts (80% reduction in manual work) - **COMPLETED 2025-10-31**
- [x] Memory footprint reduced to <500MB (streaming export verified 2025-11-01)
- [x] Batch processing supports 10+ sessions
- [x] Session cleanup & management tools operational - **COMPLETED 2025-11-01**
- [ ] Test coverage >60% (currently lower, needs work)
- [x] Story notebook tab responsive on large archives (modern UI completed 2025-11-01)
- [ ] CLI story generation reports failures clearly (needs validation)

**Remaining**: Test coverage expansion, CLI validation

### Phase 3 (P2 Complete) [WARNING]
**Status**: [WARNING] **CORE COMPLETE, POLISH REMAINING**

- [x] LangChain conversational interface operational
- [x] Semantic search with RAG functional
- [x] Vector database persistent storage working
- [x] LangChain security vulnerabilities fixed (P2.1) - **COMPLETED 2025-10-25**
- [x] LangChain test coverage >80% (now 87% - COMPLETED 2025-11-06)
- [ ] Session analytics dashboard operational
- [ ] Search functionality across all sessions
- [ ] OOC topic analysis generating insights (in progress - social_insights_tab.py)
- [ ] Overall test coverage >85%

**Remaining**: Test coverage expansion, analytics dashboard, session search, OOC analysis completion

### Phase 4 (P3 Complete) [PAUSED]
**Status**: [PAUSED] **NOT STARTED** (Deferred pending P1/P2 completion)

- [ ] Live transcription mode functional
- [ ] Visualization suite implemented
- [ ] Campaign wiki auto-generation
- [ ] Multi-user support (optional)

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Multiple agents implementing same feature | HIGH | Clear ownership assignments, frequent sync via COLLECTIVE_ROADMAP.md |
| Breaking changes during refactoring | MEDIUM | Comprehensive test suite, incremental changes |
| Memory constraints on long sessions | MEDIUM | Streaming implementations, document hardware requirements |
| Ollama/HF API changes | LOW | Version pinning, graceful degradation |
| Scope creep on P3 features | LOW | Prioritize P0-P1 completion first |

---

## Critical Review Findings (2025-10-25)

**Comprehensive Audit Conducted by**: Claude (Sonnet 4.5)
**Components Reviewed**: All LangChain modules (8 files), Campaign Chat UI, Test Suite
**Methodology**: Deep-dive security analysis, code review, test coverage analysis, UX audit

### Security Vulnerabilities Discovered

**CRITICAL** (4 issues - immediate action required):
1. Path traversal in ConversationStore (arbitrary file access)
2. Prompt injection in CampaignChatClient (LLM manipulation)
3. Race conditions in conversation persistence (data loss)
4. Unsafe JSON deserialization (injection attacks)

**HIGH** (6 issues - high priority):
5. Memory leaks in vector store (OOM crashes)
6. Duplicate ID collisions in ChromaDB (silent data overwrites)
7. No API key validation (runtime failures)
8. Unbounded memory growth in conversations
9. No knowledge base caching (100ms I/O penalty per query)
10. SQL/NoSQL injection via metadata filtering

### Test Coverage Analysis

**Current State (2025-11-06)**: **87% overall coverage** - TARGET EXCEEDED
- **153 total tests** (152 passing, 1 skipped)
- **Test files**: 9 comprehensive test files covering all major LangChain modules
- **Coverage by module**:
  - embeddings.py: 100% ✅
  - hybrid_search.py: 100% ✅
  - semantic_retriever.py: 100% ✅
  - data_ingestion.py: 97% ✅
  - vector_store.py: 96% ✅
  - campaign_chat.py: 85% ✅
  - retriever.py: 81% ✅
  - conversation_store.py: 73% ⚠️ (acceptable, edge cases remain)

**Remaining Gaps** (Lower Priority):
- Concurrency stress tests for heavy load scenarios
- Performance benchmarks for 10k+ segment datasets
- Some edge case error paths in conversation_store.py (27% uncovered)

### UX Issues (Campaign Chat Tab) [DONE] **COMPLETED 2025-11-18**

**Grade**: A- (polished and professional)

**Completed Improvements**:
- ✅ Loading indicators during LLM calls (three-step pattern implemented)
- ✅ Error messages sanitized (no internal exception exposure)
- ✅ Conversation management (delete and rename functionality)
- ✅ Sources display for last message (working as designed)
- ✅ Conversation dropdown updates after operations

**Quick Wins Completed**:
- ✅ StatusIndicators used consistently throughout
- ✅ LangChain dependency warning moved to top
- ✅ Dropdown updates after message send
- ✅ Chatbot height set to 600px
- ✅ Info text added to all inputs
- ✅ ASCII-only compliance (emoji removed)

### Architecture Issues

**Tight Coupling**:
- Components directly instantiate dependencies (hard to test)
- Hard-coded Config usage (impossible to mock)
- No interfaces/abstractions for retrievers
- No dependency injection

**Missing Features**:
- No backup/recovery for conversations
- No transaction boundaries in vector store
- No pagination for conversation lists
- No input validation (length limits, content sanitization)

### Performance Issues

**Current Problems**:
- Knowledge bases loaded from disk on every search (~100ms)
- Embeddings generated for entire batch in memory (OOM on 10k+ segments)
- No query result caching
- Conversation list loads all files (crashes at 10k+ conversations)
- Inefficient hybrid search deduplication

**Projected Impact**:
- 10 session campaign: ~5-10 second search latency
- 100 session campaign: OOM crashes during ingestion
- 1000+ conversations: UI freezes on conversation list

### Documentation Gaps

- No security best practices guide
- No deployment security documentation
- No performance tuning guide
- No troubleshooting for common LangChain issues

### Recommendations Priority

**Week 1** (Critical Security):
1. Fix path traversal vulnerability
2. Fix prompt injection
3. Add file locking to conversations
4. Add JSON schema validation

**Week 2** (Performance & Stability):
5. Implement batched embedding generation
6. Add knowledge base caching
7. Fix memory leak in conversation history
8. Add loading indicators to UI

**Week 3** (Test Coverage):
9. Add tests for CampaignChatClient
10. Add concurrency tests
11. Add error path tests
12. Add integration tests

**Month 2** (Polish):
13. Improve UX (conversation management, better errors)
14. Add performance tests and benchmarks
15. Write security documentation
16. [ ] Architecture refactoring (DI, interfaces)
17. [ ] Investigate duplicate tab headers appearing twice in modern UI and remove redundant renders
18. [ ] Restore dynamic content in Stories & Output tab (currently static)
19. [ ] Restore dynamic content in Settings & Tools tab (currently static)

**Full Audit Reports Available**:
- Visual Consistency Audit (28 specific UI issues)
- Code Review Report (21 security/functionality issues with fixes)
- Test Coverage Analysis (15 critical test gaps)

---

## Archived / Completed Work

> **Note**: Tasks below are completed and archived for historical reference.
> **Last Cleanup**: 2025-11-20

---

### P0: Critical / Immediate (Completed 2025-10-23 to 2025-10-26)

**Bug Fixes:**
- [x] Session ID sanitization (prevents injection attacks)
- [x] Unicode compatibility (cp1252 crashes fixed)
- [x] Multiple background processes prevention
- [x] Party config validation
- [x] Stale Clip Cleanup in Audio Snipper (orphaned WAV files)
- [x] Unsafe Type Casting in Configuration (.env parsing)
- [x] Checkpoint system for resumable processing (data loss prevention)
- [x] Improve resumable checkpoints robustness (compression, skip completed stages)
- [x] Surface chunking failures to users (actionable error messages)
- [x] Refine snippet placeholder output (localization, cleaner manifests)

**Code Refactoring:**
- [x] Extract Campaign Dashboard Logic (`src/campaign_dashboard.py`)
- [x] Extract Story Generation Logic (`src/story_notebook.py`)
- [x] Split app.py into UI Modules (`src/ui/` structure created)

### P1: High Impact Features (Completed 2025-10-24 to 2025-11-02)

- [x] **Automatic Character Profile Extraction** (2025-10-31)
  - LLM-powered extraction from transcripts
  - 80% reduction in manual data entry
  - 13 unit tests + 9 integration tests

- [x] **UI Modernization** (2025-11-01)
  - 16 tabs -> 5 consolidated sections
  - Modern theme (Indigo/Cyan color palette)
  - Progressive disclosure patterns
  - 69% reduction in visual clutter

- [x] **Streaming Snippet Export** (2025-11-18)
  - 90% memory footprint reduction
  - FFmpeg-based direct segment extraction
  - Backward compatible configuration

- [x] **Batch Processing** (2025-10-24)
  - Multi-file upload in Gradio UI
  - Sequential processing with progress tracking

- [x] **Campaign Lifecycle Manager** (2025-11-02)
  - Multi-campaign management
  - Campaign-aware UI and filtering

- [x] **Session Cleanup & Validation** (2025-11-01)
  - Data integrity tools

### P2: Core Features Completed (2025-10-25 to 2025-11-19)

- [x] **P2-LANGCHAIN-001**: Conversational Campaign Interface (2025-10-25)
- [x] **P2-LANGCHAIN-002**: Semantic Search with RAG (2025-10-25)
- [x] **P2.1-SECURITY**: All critical security fixes (2025-10-25)
- [x] **P2.1-TESTING**: LangChain test coverage expansion (2025-11-06) - 49% -> 87% coverage
- [x] **P2.1-UX**: Campaign Chat UI Improvements (2025-11-19)

### Other Completed Work

See COLLECTIVE_ROADMAP.md "Recently Completed" section for:
- [x] Groq transcription fix
- [x] Audio snippet export toggle
- [x] SessionLogger integration
- [x] Initial pytest suite
- [x] Campaign Dashboard
- [x] Campaign Knowledge Base
- [x] Story Notebooks (Google Docs integration)
- [x] Import Session Notes
- [x] SRT subtitle export
- [x] Character profile storage refactoring
- [x] App Manager real-time monitoring
- [x] Test suite refactoring
- [x] Unicode compatibility fixes

**For active work items**, see priority sections above.

---

## Quick Reference: What to Work On Next

**Current Status** (2025-11-02):
- [DONE] P0 Complete: All critical bugs fixed, codebase refactored
- [DONE] Major P1 Complete: UI modernized, character extraction working
- [DONE] P2 Core Complete: LangChain working, security issues fixed
- [WARNING] Polish Remaining: Test coverage, UX improvements, analytics

**If you're an agent picking up work:**

1. **High ROI Quick Wins** (Do these first):
   - **P2.1-UX**: ~~LangChain UX improvements~~ **COMPLETED 2025-11-18**
     - ✅ Loading indicators, better errors, conversation management
     - ✅ ASCII-only compliance, error sanitization, warning placement, info text
     - See: IMPLEMENTATION_PLAN_LANGCHAIN_UX_POLISH.md
   - **P2.1-TESTING**: LangChain test coverage expansion (2 days)
     - Increase coverage from 35% to 80% for campaign chat modules
     - Reduce regressions before future P3 features

2. **Quality & Testing** (Build foundations):
   - **P2.1-TESTING**: ~~LangChain test coverage expansion~~ **COMPLETED 2025-11-06**
     - **Achievement**: 49% → 87% (+38pp), Target 80% EXCEEDED
     - 70 new tests added across 4 new test files
     - Prevents regressions in critical features ✅
   - **P4-INFRA-001**: General test coverage expansion
     - Target: >60% overall coverage
     - Integration tests for full pipeline

3. **Analytics & Features** (User value):
   - **P2-ANALYTICS**: Session analytics dashboard (2-3 days)
   - **P2-ANALYTICS**: Complete OOC topic analysis (in progress)
   - **P2-SEARCH**: Session search functionality (1 day)

4. **Documentation & Infrastructure**:
   - Logging telemetry improvements (funnel print() statements)
   - Troubleshooting guide
   - Performance profiling and optimization

5. **Innovation** (Future - P3):
   - Live transcription mode
   - Visualization suite
   - Sound event detection
   - Campaign wiki generation

**Consult COLLECTIVE_ROADMAP.md before starting to avoid conflicts!**

---

_This roadmap consolidates inputs from:_
- _COLLECTIVE_ROADMAP.md (multi-agent collaboration)_
- _REFACTORING_PLAN.md (code structure)_
- _GEMINI_FEATURE_PROPOSAL.md (visualization & live features)_
- _GEMINI_CODE_REVIEW.md (quality improvements)_
- _CLAUDE_SONNET_45_ANALYSIS.md (character profiles & analytics)_
- _CHATGPT_CODEX_REVIEW.md (testing & optimization)_
- _DEVELOPMENT.md (implementation history)_

**Prepared by**: Claude (Sonnet 4.5)
**Date**: 2025-10-22
**Last Sync**: 2025-11-02
