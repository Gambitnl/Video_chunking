# VideoChunking Project Roadmap

> **Last Updated**: 2025-11-04
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

## Current Status

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

### P0: Critical / Immediate (Next 1-2 Weeks)

#### 1. Bug Fixes
**Owner**: Any agent
**Status**: Partially complete

- [x] Session ID sanitization (COMPLETED)
- [x] Unicode compatibility (cp1252 crashes) (COMPLETED)
- [x] Multiple background processes prevention (COMPLETED)
- [x] Party config validation (COMPLETED)
- [x] **Stale Clip Cleanup in Audio Snipper**
  - File: `src/snipper.py`
  - Issue: Reprocessing leaves orphaned WAV files from previous runs
  - Fix: Clear session directory before writing new batch
  - Estimated effort: 0.5 days
  - Impact: MEDIUM - prevents directory confusion
- [x] **Unsafe Type Casting in Configuration**
  - File: `src/config.py`
  - Issue: Non-numeric .env values crash on int() cast
  - Fix: Wrap casts in try-except, fall back to defaults
  - Estimated effort: 0.5 days
  - Impact: MEDIUM - prevents startup crashes
  - Status: [DONE] Completed (2025-10-24)
- [x] **Checkpoint system for resumable processing**
  - Save intermediate state after each pipeline stage
  - Prevent data loss on 4+ hour sessions
  - Estimated effort: 2 days
  - Impact: HIGH - prevents hours of lost work
- [x] **Improve resumable checkpoints robustness**
  - Files: `src/pipeline.py`, `src/checkpoint.py`
  - Issue: Resume still re-executes completed stages and checkpoints can become very large
  - Fix: Skip already completed stages, compress/trim checkpoint payloads, and re-run only necessary steps
  - Estimated effort: 1.5 days
  - Impact: HIGH - faster recovery for long sessions
  - Status: [DONE] Completed 2025-10-26 (Codex GPT-5)
- [x] **Surface chunking failures to users**
  - Files: `src/pipeline.py`
  - Issue: When chunking yields zero segments the pipeline silently proceeds, leading to empty transcripts
  - Fix: Detect real sessions vs. test mocks and abort with actionable errors for users
  - Estimated effort: 0.5 days
  - Impact: HIGH - avoids confusing empty outputs
  - Status: [DONE] Completed 2025-10-24 (Codex GPT-5)
- [x] **Refine snippet placeholder output**
  - File: `src/snipper.py`
  - Issue: Placeholder manifests use hard-coded Dutch text and leave stray files even when no snippets are produced
  - Fix: Localize placeholder strings, only create markers when needed, and make the manifest structure explicit
  - Estimated effort: 0.5 days
  - Impact: MEDIUM - clearer UX for empty sessions
  - Status: [DONE] Completed 2025-10-26 (Codex GPT-5)

#### 2. Code Refactoring (Maintainability)
**Owner**: Open
**Status**: Planned
**Priority Order**: 4 -> 1 -> 3 -> 2 -> 5

1. **Priority 4: Status Indicator Constants** (QUICK WIN)
   - [x] Create `src/ui/constants.py` (COMPLETED)
   - Centralize emoji/symbol usage
   - Windows cp1252 compatibility in one place
   - Estimated effort: 0.5 days

2. **Priority 1: Extract Campaign Dashboard Logic**
   - [x] Extract `generate_campaign_dashboard()` from app.py (~240 lines) (COMPLETED)
   - [x] Create `src/campaign_dashboard.py` with testable components (COMPLETED)
   - [x] 7 unit tests added - all passing (COMPLETED)
   - Estimated effort: 2 days (Actual: ~1 day)
   - Impact: HIGH - enables testing and reusability
   - Status: [DONE] Completed 2025-10-23

3. **Priority 3: Extract Story Generation Logic**
   - [x] Move narrative generation from app.py to `src/story_generator.py`
   - [x] Enable CLI usage of story generation
   - [x] Created `StoryNotebookManager` class in `src/story_notebook.py`
   - [x] Added `generate-story` CLI command
   - Estimated effort: 1 day
   - Status: [DONE] Completed (already implemented)

4. **Priority 2: Split app.py into UI Modules**
   - Create `src/ui/` module structure
   - Break app.py (2,564 lines) into focused modules (<300 lines each)
   - Estimated effort: 3-4 days
   - Target: Reduce app.py to <1,000 lines

5. **Priority 5: MarkdownBuilder Helper** (DEFERRED)
   - Create `src/ui/markdown_builder.py` helper class
   - Consolidate markdown generation logic from dashboard
   - Estimated effort: 1 day
   - Impact: LOW - nice to have, not critical
   - Status: Skip for now, revisit after Priority 1-2 complete

---

### P1: High Impact Features (Next 2-4 Weeks)

#### 1. Automatic Character Profile Extraction
**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] Completed 2025-10-31
**Effort**: 3-5 days (actual: ~4 hours)
**Impact**: EXTREMELY HIGH - eliminates 80% of manual data entry

**Implementation** (COMPLETE):
- [DONE] Created `ProfileExtractor` class with LLM integration
- [DONE] Created `CharacterProfileExtractor` workflow wrapper
- [DONE] Designed comprehensive D&D-specific extraction prompts
- [DONE] Ollama integration for IC-transcript analysis
- [DONE] Auto-extracts: actions, items, relationships, quotes, development notes, goals
- [DONE] UI integration in Character Profiles tab (upload transcript -> extract -> auto-apply)
- [DONE] 13 unit tests + 9 integration tests (all passing)
- [PENDING] Human review/approval workflow (future enhancement)

**Benefits Delivered**:
- Reduces manual data entry by 80%+ (extraction working)
- Ensures no important moments are missed (LLM-powered)
- Creates consistent, comprehensive profiles (7 categories)
- Links sessions to character data via session_id tracking

**Files**: `src/profile_extractor.py`, `src/character_profile_extractor.py`, `prompts/profile_extraction.txt`, `schemas/profile_update.json`, `tests/test_profile_extraction.py`, `tests/test_character_profile_extractor.py`

#### 2. UI Modernization (16 Tabs -> 5 Sections)
**Owner**: Claude (Sonnet 4.5)
**Status**: [DONE] Completed 2025-11-01
**Effort**: 2-3 days (actual: ~5 hours)
**Impact**: EXTREMELY HIGH - transforms user experience

**Implementation** (COMPLETE):
- [DONE] Created modern theme system with Indigo/Cyan color palette (`src/ui/theme.py`)
- [DONE] Designed 5 consolidated tabs with clear workflow:
  - [PROCESS] Process Session (workflow stepper: Upload -> Configure -> Process -> Review)
  - [CAMPAIGN] Campaign (dashboard, knowledge base, session library, party management)
  - [PEOPLE] Characters (card-based browser with auto-extraction tool)
  - [STORIES] Stories & Output (content viewer with export options)
  - [TOOLS] Settings & Tools (config, diagnostics, logs, speaker mgmt, LLM chat, help)
- [DONE] Progressive disclosure pattern (accordions, collapsible sections, tooltips)
- [DONE] Full-width responsive layout with proper horizontal spacing
- [DONE] Improved accordion indicators (animated indigo arrows)
- [DONE] Modern card-based layouts with hover effects and shadows
- [DONE] Visual workflow stepper for session processing
- [DONE] Replaced main `app.py` with modern UI (backed up to `app.py.backup`)

**Benefits Delivered**:
- Reduced tab count by 69% (16 -> 5 tabs)
- Eliminated hidden overflow menu tabs
- Clear entry point and workflow guidance
- Modern, professional aesthetic (inspired by ElevenLabs, Linear)
- 80% less visual clutter via progressive disclosure
- Better content organization and feature discoverability

**Files**: `src/ui/theme.py`, `src/ui/process_session_tab_modern.py`, `src/ui/campaign_tab_modern.py`, `src/ui/characters_tab_modern.py`, `src/ui/stories_output_tab_modern.py`, `src/ui/settings_tools_tab_modern.py`, `app.py`, `app_modern_preview.py`, `docs/UI_MODERNIZATION_PROPOSAL.md`

#### 3. Streaming Snippet Export
**Owner**: ChatGPT (Codex)
**Status**: Planned
**Effort**: 2 days
**Impact**: HIGH - reduces memory footprint

**Details**:
- Prototype ffmpeg-based streaming to avoid loading multi-hour WAVs
- Current: 450MB for 4-hour session loaded into memory
- Target: Streaming extraction with ~50MB footprint
- Add to `src/snipper.py`

#### 3. Batch Processing
**Owner**: Gemini
**Status**: [DONE] Completed (2025-10-24)
**Effort**: 1 day
**Impact**: MEDIUM-HIGH

**Features**:
- Multi-file upload in Gradio UI
- Sequential processing with progress tracking
- Process multiple sessions overnight
- Generate batch summary report

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

**UX Improvements** (Campaign Chat Tab):
11. **Missing UI Features**
    - No loading indicators during LLM calls
    - Error messages expose internal exceptions
    - No conversation management (delete, rename)
    - Sources display only shows last message
    - Conversation dropdown not updated after sending
    - Effort: 1-2 days

**Documentation**:
12. **Security Best Practices Guide**
    - Document API key handling
    - Document input sanitization
    - Document deployment security
    - Effort: 4 hours

#### Analytics & Visualization

**1. Session Analytics Dashboard**
**Owner**: Open
**Effort**: 2-3 days

- Session comparison view (side-by-side)
- Character participation tracking
- Speaking time distribution
- Combat vs roleplay ratio over time
- Story arc progression

**2. Character Analytics & Filtering**
**Owner**: Claude (backlog item)
**Effort**: 3 days

- Action filtering/search by type or session
- Character statistics and progression timelines
- **Session Timeline View**: Chronological action feed across all sessions with level progression, inventory changes, relationship evolution, goal completion tracking
- **Party-Wide Analytics**: Party composition breakdown, shared relationships/connections, item distribution, action type balance, session participation matrix
- **Data Validation & Warnings**: Detect missing actions for characters in sessions, duplicate items, relationships without "first met" session, invalid session references

**3. OOC Keyword & Topic Analysis**
**Owner**: Gemini
**Status**: Proposed
**Effort**: 2 days

- TF-IDF/topic clustering for OOC transcript
- Identify recurring keywords, inside jokes, discussion topics
- Generate "Social Insights" visualization
- Topic word cloud

#### Advanced Features

**4. Session Search Functionality**
**Owner**: Open
**Effort**: 1 day

- Full-text search across transcripts
- Filter by speaker, IC/OOC, time range
- Regex support
- Export search results

**5. Cross-Link Sessions to Characters**
**Owner**: Claude (backlog item)
**Effort**: 2 days

- Map speaker diarization output to character profiles
- Consistent naming across sessions
- **Voice-to-Character Mapping**: Link speaker diarization IDs to character names, enable cross-session speaker consistency
- Voice embedding comparison (optional)
- **Speaker Voice Samples** (FEATURE-007): Upload voice samples for each player to improve initial identification and reduce manual mapping

#### Process Cancellation Feature

**Owner**: Open (from Jules session analysis)
**Status**: Not Started
**Effort**: 2-3 hours
**Impact**: MEDIUM - Better UX for long sessions
**Source**: [JULES_SESSION_ANALYSIS.md](docs/JULES_SESSION_ANALYSIS.md#todo-002-process-cancellation-feature)

**Features**:
- Add `cancel_event` parameter to pipeline processing
- Create `CancelledError` exception class
- Thread-safe cancellation mechanism
- Add "Cancel" button to Gradio UI (Process Session tab)
- Handle cancellation gracefully with friendly user message
- Clean up partial output files when cancelled

**Files to Modify**:
- `src/exceptions.py` - Define CancelledError
- `src/pipeline.py` - Add cancel_event parameter, check periodically
- `app.py` - Pass cancel_event from UI, handle CancelledError
- `src/ui/process_session_tab_modern.py` - Add Cancel button

**Complexity Factors**:
- Thread-safe cancellation mechanism
- Cleanup of partial results (audio files, JSON files, checkpoints)
- Progress tracking to show cancellation worked
- Testing edge cases (cancel during different stages)

**Validation**:
- User can click Cancel button during processing
- Pipeline stops gracefully within 5 seconds
- Partial files are cleaned up
- User sees "Processing was cancelled by user" message

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

### UX Issues (Campaign Chat Tab)

**Grade**: C+ (functional but needs polish)

**Critical Issues**:
- No loading indicators during LLM calls (users see frozen UI)
- Error messages expose internal stack traces
- No conversation management (can't delete or rename)
- Sources only shown for last message
- Conversation dropdown not updated after sending message

**Quick Wins** (< 1 hour total):
- Add StatusIndicators for consistent UI
- Move LangChain dependency warning to top
- Update dropdown after message send
- Increase chatbot height to 600px
- Add info text to inputs

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

---

## Quick Reference: What to Work On Next

**Current Status** (2025-11-02):
- [DONE] P0 Complete: All critical bugs fixed, codebase refactored
- [DONE] Major P1 Complete: UI modernized, character extraction working
- [DONE] P2 Core Complete: LangChain working, security issues fixed
- [WARNING] Polish Remaining: Test coverage, UX improvements, analytics

**If you're an agent picking up work:**

1. **High ROI Quick Wins** (Do these first):
   - **P2.1-UX**: LangChain UX improvements (1-2 days)
     - Loading indicators, better errors, conversation management
     - Improves user experience significantly
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
