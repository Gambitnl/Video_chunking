# Development Chronicle

## Session: 2025-10-15 - Initial Implementation

### Project Setup Phase

**Goal**: Create the foundation for a D&D session transcription system with speaker diarization and IC/OOC classification.

**Approach**:
1. Start with a modular architecture - separate concerns into distinct modules
2. Support multiple backends (local + API) to give users flexibility
3. Build from bottom-up: audio processing â†’ transcription â†’ diarization â†’ classification â†’ UI

**Files Created So Far**:
- `requirements.txt` - Chose libraries based on:
  - `faster-whisper` over `openai-whisper` for 4x speed improvement
  - `pyannote.audio` for state-of-the-art speaker diarization
  - `gradio` for quick UI prototyping
  - `rich` for beautiful CLI output

- `.env.example` - Configuration template allowing users to:
  - Choose between local/cloud processing
  - Adjust chunk sizes based on their hardware
  - Configure different LLM backends

- `src/config.py` - Centralized configuration with sensible defaults:
  - 600s chunks with 10s overlap (based on research)
  - 16kHz sample rate (Whisper optimal)
  - Automatic directory creation

### Audio Processing Module âœ…

**Implemented**:
- `src/audio_processor.py` - Audio conversion and utilities
- `src/chunker.py` - Hybrid VAD + fixed-length chunking

**Key Design Decisions**:

1. **FFmpeg for Conversion**
   - Handles all formats (M4A, MP3, etc.)
   - Converts to 16kHz mono WAV (Whisper's optimal format)
   - Fast and reliable

2. **Hybrid Chunking Strategy**
   - Uses Silero VAD to detect speech/silence
   - Primary: Split at natural pauses near 10-min mark
   - Fallback: Hard split at 10 minutes if no pause found
   - 10-second overlap between chunks (prevents word cutting)

3. **Smart Pause Detection**
   - Searches Â±30 seconds from ideal chunk end
   - Scores gaps by proximity and width
   - Prefers wider silences closer to target length

**Why This Approach**:
- D&D sessions have natural pauses (dice rolls, thinking, etc.)
- Splitting at silence = better semantic boundaries
- Overlap ensures no words are lost at boundaries
- 10-min chunks = optimal balance of context vs API limits

### Transcription Engine âœ…

**Implemented**:
- `src/transcriber.py` - Multi-backend transcription system
- `src/merger.py` - LCS-based overlap merging

**Backends**:
1. **FasterWhisperTranscriber** (local, free)
   - 4x faster than original Whisper
   - Auto-detects GPU/CPU
   - Word-level timestamps
   - Built-in VAD filtering

2. **GroqTranscriber** (cloud, free tier)
   - Hardware-accelerated Whisper
   - Much faster than local
   - Verbose JSON output with word timestamps

**Key Innovation - LCS Merger**:
- Problem: 10s overlap = duplicate text
- Solution: Find longest common subsequence between overlaps
- Falls back to time-based splitting if no match
- Preserves all timestamps accurately

### Speaker Diarization âœ…

**Implemented**: `src/diarizer.py`

**Components**:
1. **SpeakerDiarizer**
   - Uses PyAnnote.audio 3.1 (state-of-the-art)
   - GPU acceleration when available
   - Graceful fallback if HF token missing
   - Assigns speakers to transcription segments

2. **SpeakerProfileManager**
   - Persists speaker mappings across sessions
   - JSON-based storage
   - Manual labeling support

**Design Choice**:
- Calculate overlap between diarization and transcription
- Assign speaker with maximum overlap to each segment
- Allows for future voice embedding comparison

### IC/OOC Classification âœ…

**Implemented**: `src/classifier.py`

**Approach**:
- Uses Ollama with Llama 3.1 (local, free)
- Context window: previous + current + next segment
- Few-shot prompting in Dutch
- Structured output parsing

**Prompt Design**:
- Clear task definition
- 3 examples showing IC vs OOC patterns
- Character/player name context
- Confidence scoring

**Classification Output**:
- Type: IC, OOC, or MIXED
- Confidence: 0.0-1.0
- Reasoning: Why this classification
- Character: Name if IC speech

### Output Generation âœ…

**Implemented**: `src/formatter.py`

**Formats**:
1. **Full Transcript** - Everything with labels
2. **IC-Only** - Game narrative only
3. **OOC-Only** - Meta discussion only
4. **JSON** - Complete metadata for processing

**Statistics**:
- Duration (total, IC, OOC)
- Segment counts
- Speaker distribution
- Character appearances

### Pipeline Orchestration âœ…

**Implemented**: `src/pipeline.py`

**Flow**:
1. Convert audio (M4A â†’ WAV)
2. Chunk with VAD
3. Transcribe chunks
4. Merge overlaps
5. Diarize speakers
6. Classify IC/OOC
7. Generate outputs

**Features**:
- Progress reporting at each stage
- Graceful degradation (continue if component fails)
- Optional stages (can skip diarization/classification)
- Comprehensive error handling

### User Interfaces âœ…

**Implemented**:
1. **CLI** (`cli.py`)
   - Rich terminal output with tables
   - Commands: process, map-speaker, show-speakers, config, check-setup
   - Dependency checker

2. **Web UI** (`app.py`)
   - Gradio interface
   - File upload with drag & drop
   - Real-time progress
   - Tabbed output views
   - Speaker management
   - Built-in help documentation

## Final Architecture

```
Input (M4A)
    â†“
AudioProcessor (â†’ 16kHz WAV)
    â†“
HybridChunker (â†’ 10-min chunks with 10s overlap)
    â†“
Transcriber (â†’ text + timestamps per chunk)
    â†“
Merger (â†’ single transcript, no duplicates)
    â†“
SpeakerDiarizer (â†’ who spoke when)
    â†“
Classifier (â†’ IC/OOC labels)
    â†“
Formatter (â†’ 4 output formats)
    â†“
Output (TXT + JSON)
```

## Technology Choices - Final

| Component | Technology | Why |
|-----------|-----------|-----|
| Audio Conversion | FFmpeg | Universal, reliable, fast |
| VAD | Silero VAD | Best free VAD, PyTorch-based |
| Chunking | Custom hybrid | Smart pauses + fixed length |
| Transcription | faster-whisper | 4x speed, excellent Dutch |
| Diarization | PyAnnote 3.1 | State-of-the-art, open source |
| Classification | Ollama + Llama 3.1 | Free, local, good Dutch support |
| UI | Gradio | Fast prototyping, great UX |
| CLI | Click + Rich | Professional, user-friendly |

## Achievements

âœ… Full pipeline implemented
âœ… Multiple backend support (local + cloud)
âœ… Graceful degradation
âœ… Two UIs (CLI + Web)
âœ… Speaker learning across sessions
âœ… 4 output formats
âœ… Comprehensive error handling
âœ… Statistics generation
âœ… Dutch language optimized
âœ… Zero-budget compatible

## Final Implementation Summary

### Project Complete! âœ…

**Total Time**: ~1 development session
**Status**: Production-ready system

### What Was Built

**23 files total**:
- 10 core modules
- 2 user interfaces
- 6 documentation files
- 3 configuration files
- 1 example file
- 1 development chronicle

**~6,000 total lines**:
- ~3,500 lines of code
- ~2,500 lines of documentation

### End-to-End Capability

The system now handles:
1. âœ… Any audio format (M4A, MP3, WAV, etc.)
2. âœ… Dutch language transcription
3. âœ… 4 speakers (3 players + DM)
4. âœ… 4-hour sessions
5. âœ… Speaker identification
6. âœ… IC/OOC classification
7. âœ… Multiple output formats
8. âœ… Web + CLI interfaces

### Ready for Production Use

Users can now:
- Drop an M4A file into the web UI
- Get 4 different transcript formats
- Map speakers to real names
- Use transcripts for session notes
- Search for specific moments
- Track character participation

**The system works!** ðŸŽ‰

---

**End of Development Chronicle**
**Date**: 2025-10-15
**Final Status**: Complete and functional

## Session: 2025-10-20 - Refactoring and UI Enhancements

### Character Profile Storage Refactoring

**Goal**: Improve the character profile storage system for better organization and to prevent data conflicts.

**Problem**: The original implementation stored all character profiles in a single JSON file (`models/character_profiles.json`). This could lead to write conflicts and made manual management of individual characters difficult.

**Solution**:
1.  **Individual File Storage**: The `CharacterProfileManager` in `src/character_profile.py` was refactored to store each character profile as a separate `.json` file in a new `models/character_profiles/` directory.
2.  **Efficient Saving**: The saving mechanism was updated to only write the single file for the character being added or updated, rather than rewriting the entire collection each time.
3.  **Data Migration**: A one-time migration process was added to the manager's initialization. It checks for the old `character_profiles.json` file, reads its content, and automatically creates the new individual files, then renames the old file to `.migrated` to prevent re-running.

**Why This Approach**:
-   **Scalability**: Easier to manage a large number of characters.
-   **Safety**: Reduces the risk of corrupting all profiles if a single save operation fails.
-   **Clarity**: The file system now directly reflects the character list.

### UI/UX Enhancements

-   **LLM Chat Tab**: Added a new tab to the Gradio UI for direct interaction with the local Ollama model.
-   **Character Role-Playing**: The LLM Chat tab includes a dropdown to select a character, which injects a system prompt for the LLM to adopt that character's persona.
-   **Log Tab Scrolling**: Implemented CSS to make the log viewer in the "Logs" tab scrollable for better usability with long logs.
-   **Improved Explanations**: Added more detailed descriptions to the "Party Management" and "Character Profiles" tabs to better explain their purpose and functionality to users.
- **Bug Fixes**: Resolved several startup errors related to the new "Campaign Library" tab and a deprecated format in the Chatbot component.

### Test Suite Refactoring

**Problem**: The test suite was taking nearly 6 minutes to run, even when only collecting tests. This was caused by the `FasterWhisperTranscriber` loading its large AI model as soon as the module was imported, rather than when it was first used.

**Solution**:
1.  **Lazy Loading**: Refactored `src/transcriber.py` to defer the expensive model loading until the `transcribe_chunk` method is actually called. This reduced test collection time from ~6 minutes to under 10 seconds.
2.  **Redundancy Removal**: Deleted the `test_everything.py` file, which was largely a duplicate of `test_system.py` and contained code that interfered with the test runner's lifecycle.

## Session: 2025-10-21 - Campaign Management Features & Documentation

### Campaign Dashboard Implementation

**Goal**: Provide users with a comprehensive overview of their campaign health and configuration status.

**Implemented**:
- **Campaign Dashboard Tab** - Centralized view of campaign components
  - Party configuration status (characters, players, DM info)
  - Settings validation (Whisper, LLM, processing options)
  - Knowledge base tracking (quests, NPCs, locations, items, plot hooks)
  - Character profiles overview
  - Session history with narratives
  - Health indicators: ðŸŸ¢ Green (90-100%), ðŸŸ¡ Yellow (70-89%), ðŸŸ  Orange (50-69%), ðŸ”´ Red (0-49%)
  - Status badges: âœ… Configured | âš ï¸ Needs attention | âŒ Missing

**Why This Approach**:
- Single-page health check for campaign readiness
- Identifies missing configurations before processing
- Tracks knowledge base growth across sessions
- Helps users understand system completeness at a glance

### Campaign Knowledge Base

**Goal**: Automatically extract and track campaign elements across sessions for DM reference.

**Implemented**:
- **Automatic Knowledge Extraction** from session transcripts
  - ðŸŽ¯ Quests: Active and completed objectives
  - ðŸ‘¥ NPCs: Named characters with descriptions and relationships
  - ðŸ”“ Plot Hooks: Potential story threads
  - ðŸ“ Locations: Places visited or mentioned
  - âš¡ Items: Significant objects and artifacts

- **Campaign Library Tab**
  - Load and view knowledge base by campaign
  - Auto-extraction toggle during session processing
  - JSON storage per campaign: `models/knowledge/{campaign}_knowledge.json`
  - Integration with Campaign Dashboard for health tracking

**Design Decisions**:
- Extract from IC-only transcript for narrative focus
- LLM-based extraction using structured prompts
- Cumulative knowledge across all sessions
- Campaign-specific storage for multi-campaign support

### Story Notebooks Feature

**Goal**: Transform session transcripts into narrative story formats from different perspectives.

**Implemented**:
- **Document Viewer Integration**
  - Fetch Google Docs (with view-only share link)
  - Use as context/style guide for narrative generation
  - Refresh notebook context on demand

- **Story Notebooks Tab**
  - Narrator perspective: Third-person omniscient storytelling
  - Character POV: First-person from each character's viewpoint
  - Output saved to `output/{session}/narratives/`
  - Session selection from existing processed sessions
  - Integration with Google Docs for style consistency

**Why This Approach**:
- Leverages Google Docs for collaborative style guides
- Multiple perspective options for different use cases
- LLM-powered narrative transformation
- Organized storage alongside session outputs

### Import Session Notes

**Goal**: Backfill campaign data for early sessions that weren't recorded.

**Implemented**:
- **Import Session Notes Tab**
  - Import from text notes (paste or upload)
  - Campaign association for knowledge base integration
  - Optional knowledge extraction from notes
  - Optional narrative generation from notes
  - Output to `output/imported_narratives/`

**Use Cases**:
- Add early campaign sessions that predate recording
- Integrate written session notes into knowledge base
- Generate narratives from DM notes
- Complete campaign history for Dashboard tracking

### SRT Subtitle Export

**Goal**: Support video overlay workflows for session recordings.

**Implemented**:
- **Subtitle Generation** in `src/formatter.py`
  - Full transcript subtitles (IC + OOC with labels)
  - IC-only subtitles (game narrative)
  - OOC-only subtitles (player banter)
  - Proper SRT formatting with sequential numbering
  - Timestamp precision for video sync

**Output Files**:
- `{session}_full.srt`
- `{session}_ic_only.srt`
- `{session}_ooc_only.srt`

**Why This Feature**:
- Enables video recording workflows
- Supports content creation (YouTube, streaming)
- Provides accessibility for hearing-impaired viewers
- Complements audio-only transcription

### App Manager Tool

**Goal**: Provide real-time monitoring of processing pipelines with stage-level detail.

**Implemented**:
- **App Manager** (`app_manager.py`)
  - Auto-refreshing status display
  - Per-stage progress tracking with clocks
  - Options recap showing enabled/disabled features
  - "Next" hints when stages complete
  - Idle detection when no active processing

**Why This Approach**:
- Long-running pipelines need visibility
- Stage timing helps identify bottlenecks
- Status JSON integration with pipeline
- Better UX for 4+ hour session processing

### Additional Test Suite Improvements

**Goal**: Further improve test organization and execution speed.

**Implemented**:
- **pytest Marker System**
  - Added `@pytest.mark.slow` to integration tests in `test_sample.py`
  - Fast unit tests remain unmarked for quick execution
  - System verification test (`test_system.py`) with optional Whisper loading

- **Merged System Verification**
  - Consolidated `test_everything.py` into `test_system.py`
  - Added unique Whisper model test from test_everything.py
  - Implemented `--skip-whisper` flag for faster environment checks
  - Single source of truth for system verification

**Test Execution Strategies**:
```bash
pytest tests/                    # Fast unit tests only (< 1 second)
pytest -m slow                   # Integration tests only (5+ minutes)
pytest -m "not slow"             # All except integration tests
python test_system.py            # Full system check (includes Whisper)
python test_system.py --skip-whisper  # Quick check (skips model loading)
```

### Bug Fixes (2025-10-21)

**Unicode Compatibility**:
- `app.py:2548` - Warning emoji (âš ï¸) â†’ "WARNING:" for Windows cp1252 compatibility
- `src/chunker.py:82` - Approximation symbol (â‰ˆ) â†’ tilde (~) in log messages

**Rationale**: Windows console uses cp1252 encoding by default, which doesn't support these Unicode characters, causing crashes during logging.

### Documentation Updates

**Major Updates**:
- `README.md` - Added Campaign Dashboard, Knowledge Base, Story Notebooks
- `USAGE.md` - Added detailed guides for new features
- `QUICKREF.md` - Added quick reference sections and cheatsheets
- `SESSION_NOTEBOOK.md` - Changed status from "Planned" to "Implemented"
- `CAMPAIGN_DASHBOARD.md` - **NEW** comprehensive guide with health indicators
- `CAMPAIGN_KNOWLEDGE_BASE.md` - Updated with Import Session Notes integration

### Current Feature Set Summary

The VideoChunking system now includes:

**Core Processing Pipeline**:
- âœ… Audio conversion (M4A â†’ WAV)
- âœ… Hybrid VAD-based chunking
- âœ… Multi-backend transcription (local/Groq/OpenAI)
- âœ… LCS-based overlap merging
- âœ… Speaker diarization (PyAnnote)
- âœ… IC/OOC classification (Ollama)
- âœ… Multi-format output (TXT, JSON, SRT)

**Campaign Management**:
- âœ… Party configuration system
- âœ… Character profiles (individual file storage)
- âœ… Campaign Dashboard (health monitoring)
- âœ… Knowledge Base (auto-extraction)
- âœ… Import Session Notes (backfill)
- âœ… Story Notebooks (narrative generation)

**User Interfaces**:
- âœ… Gradio Web UI (multi-tab interface)
- âœ… Rich CLI (comprehensive commands)
- âœ… App Manager (status monitoring)

**Quality Assurance**:
- âœ… Pytest test suite (unit + integration)
- âœ… Test markers for fast/slow separation
- âœ… System verification tool
- âœ… Unicode compatibility fixes
- âœ… Graceful degradation

**Documentation**:
- âœ… 6+ comprehensive guides
- âœ… Quick reference card
- âœ… API examples
- âœ… Troubleshooting guides
- âœ… Feature-specific documentation

---

**End of 2025-10-21 Session**
**Status**: Feature-complete campaign management system with robust testing infrastructure and comprehensive documentation

## MCP Integration Roadmap

1. Start by wrapping each pipeline stage as a reusable tool function (typed signatures, docstrings).
2. Create a LangChain agent module (`src/agent.py`), register the tool set, wire the agent into CLI/Gradio.
3. Add LlamaIndex-based retrieval for transcripts, knowledge bases, and profile artifacts.
4. Provide OpenAI Function Calling schemas so external orchestrators can invoke the pipeline.
5. Support Ollama as a local backend (config toggle) alongside OpenAI.
6. Extend tests (unit & integration) with mocked LLMs; target >85% branch coverage.
7. Update documentation (README, QUICKREF, USAGE) with agent/LLM setup and usage examples.
