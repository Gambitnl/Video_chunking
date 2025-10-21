# Development Chronicle

## Session: 2025-10-15 - Initial Implementation

### Project Setup Phase

**Goal**: Create the foundation for a D&D session transcription system with speaker diarization and IC/OOC classification.

**Approach**:
1. Start with a modular architecture - separate concerns into distinct modules
2. Support multiple backends (local + API) to give users flexibility
3. Build from bottom-up: audio processing → transcription → diarization → classification → UI

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

### Audio Processing Module ✅

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
   - Searches ±30 seconds from ideal chunk end
   - Scores gaps by proximity and width
   - Prefers wider silences closer to target length

**Why This Approach**:
- D&D sessions have natural pauses (dice rolls, thinking, etc.)
- Splitting at silence = better semantic boundaries
- Overlap ensures no words are lost at boundaries
- 10-min chunks = optimal balance of context vs API limits

### Transcription Engine ✅

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

### Speaker Diarization ✅

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

### IC/OOC Classification ✅

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

### Output Generation ✅

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

### Pipeline Orchestration ✅

**Implemented**: `src/pipeline.py`

**Flow**:
1. Convert audio (M4A → WAV)
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

### User Interfaces ✅

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
    ↓
AudioProcessor (→ 16kHz WAV)
    ↓
HybridChunker (→ 10-min chunks with 10s overlap)
    ↓
Transcriber (→ text + timestamps per chunk)
    ↓
Merger (→ single transcript, no duplicates)
    ↓
SpeakerDiarizer (→ who spoke when)
    ↓
Classifier (→ IC/OOC labels)
    ↓
Formatter (→ 4 output formats)
    ↓
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

✅ Full pipeline implemented
✅ Multiple backend support (local + cloud)
✅ Graceful degradation
✅ Two UIs (CLI + Web)
✅ Speaker learning across sessions
✅ 4 output formats
✅ Comprehensive error handling
✅ Statistics generation
✅ Dutch language optimized
✅ Zero-budget compatible

## Final Implementation Summary

### Project Complete! ✅

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
1. ✅ Any audio format (M4A, MP3, WAV, etc.)
2. ✅ Dutch language transcription
3. ✅ 4 speakers (3 players + DM)
4. ✅ 4-hour sessions
5. ✅ Speaker identification
6. ✅ IC/OOC classification
7. ✅ Multiple output formats
8. ✅ Web + CLI interfaces

### Ready for Production Use

Users can now:
- Drop an M4A file into the web UI
- Get 4 different transcript formats
- Map speakers to real names
- Use transcripts for session notes
- Search for specific moments
- Track character participation

**The system works!** 🎉

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
-   **Bug Fixes**: Resolved several startup errors related to the new "Campaign Library" tab and a deprecated format in the Chatbot component.
