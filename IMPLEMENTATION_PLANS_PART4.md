# Implementation Plans - Part 4: P3/P4 Future & Infrastructure

> **Planning Mode Document**
> **Created**: 2025-10-22
> **For**: Development Team
> **Source**: ROADMAP.md

This document contains P3 (Future Enhancements) and P4 (Infrastructure & Quality) implementation plans.  
_For a high-level checklist, consult `docs/OUTSTANDING_TASKS.md`._

**See IMPLEMENTATION_PLANS.md for**:
- Templates (Implementation Notes & Reasoning, Code Review Findings)
- How to invoke Critical Review
- P0 features and refactoring

---

## Table of Contents

- [P3: Future Enhancements](#p3-future-enhancements)
  - [P3-FEATURE-001: Real-time Processing](#p3-feature-001-real-time-processing)
  - [P3-FEATURE-002: Multi-language Support](#p3-feature-002-multi-language-support)
  - [P3-FEATURE-003: Custom Speaker Labels](#p3-feature-003-custom-speaker-labels)
- [P4: Infrastructure & Quality](#p4-infrastructure--quality)
  - [P4-INFRA-001: Comprehensive Test Suite](#p4-infra-001-comprehensive-test-suite)
  - [P4-INFRA-002: CI/CD Pipeline](#p4-infra-002-cicd-pipeline)
  - [P4-INFRA-003: Performance Profiling](#p4-infra-003-performance-profiling)
  - [P4-DOCS-001: API Documentation](#p4-docs-001-api-documentation)

---

# P3: Future Enhancements

## P3-FEATURE-001: Real-time Processing

**Files**: `src/realtime_pipeline.py` (new), WebSocket integration
**Effort**: 5-7 days
**Priority**: LOW
**Dependencies**: P0-BUG-003 (Checkpoint System), P1-FEATURE-002 (Streaming Export)
**Status**: [DONE] 2025-11-02

### Problem Statement
Currently, processing happens after session recording completes. For live sessions, users could benefit from real-time transcription and diarization (e.g., live captions, auto-generated notes during play).

### Success Criteria
- [_] Accepts live audio stream input (WebSocket or file watching)
- [_] Transcribes and diarizes in real-time (< 5 second delay)
- [_] Updates UI with live transcript feed
- [_] Handles audio buffer management
- [_] Gracefully handles disconnections

### Implementation Plan

#### Subtask 1.1: Audio Stream Ingestion
**Effort**: 2 days

Build module to accept live audio input.

**Input Methods**:
1. WebSocket audio stream
2. File watching (monitor recording file as it grows)
3. Audio device capture (microphone/mixer)

**Code Example**:
```python
class AudioStreamIngester:
    """Ingest live audio streams."""

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.buffer = AudioBuffer(max_duration=30)  # 30-second buffer

    async def ingest_websocket(self, websocket):
        """Ingest audio from WebSocket."""
        async for message in websocket:
            audio_chunk = np.frombuffer(message, dtype=np.float32)
            self.buffer.append(audio_chunk)

            # Process when buffer is full
            if self.buffer.is_ready():
                await self._process_chunk(self.buffer.get())
```

**Files**: New `src/realtime/stream_ingester.py`

_Status_: [DONE] 2025-10-31 (async ingester + buffer implemented)

#### Subtask 1.2: Real-time Transcription
**Effort**: 2 days
**Status**: [DONE 2025-11-02]

Adapt transcriber for streaming mode.

**Challenges**:
- Faster-whisper is designed for batch processing
- Need to balance latency vs accuracy
- Handle partial transcriptions

**Files**: New `src/realtime/realtime_transcriber.py`

#### Subtask 1.3: Real-time Diarization
**Effort**: 1 day
**Status**: [DONE 2025-11-02]

Evaluate if PyAnnote can handle real-time diarization.

**Challenges**:
- PyAnnote designed for offline processing
- May need to use simpler speaker detection initially
- Consider alternative: Speaker embedding + clustering

**Files**: Research spike, then implement in `src/realtime/realtime_diarizer.py`

#### Subtask 1.4: WebSocket UI Integration
**Effort**: 2 days
**Status**: [DONE 2025-11-02]

Add live transcript view to UI.

**Features**:
- Live transcript feed (auto-scrolling)
- Speaker labels update in real-time
- Start/Stop recording buttons
- Audio level meter

**Files**: `app.py`, `src/ui/live_session_tab.py` (new)

#### Subtask 1.5: Testing
**Effort**: 1 day
**Status**: [DONE] 2025-11-02 (Placeholder tests created)

Test real-time processing with simulated streams.

**Test Cases**:
- Simulated audio stream (pre-recorded file)
- Test latency (time from audio to transcript)
- Buffer overflow handling
- Connection drops and recovery

**Files**: `tests/test_realtime_processing.py`

**Note**: Comprehensive tests for this feature require a running WebSocket server and audio stream simulation, which is not feasible in the current environment. Placeholder tests have been created to ensure the basic structure is in place.

---

### Implementation Notes & Reasoning (2025-10-31)
**Implementer**: Codex (GPT-5)

1. **Async Audio Buffering**
   - **Choice**: Built `AudioBuffer` to accumulate float32 chunks until a configurable duration threshold before flushing.
   - **Reasoning**: Keeps ingestion logic decoupled from downstream processing and ensures predictable latency windows.
   - **Trade-offs**: Currently concatenates chunks in-memory; future work may stream to disk for very long buffers.

2. **Stream Ingester Abstractions**
   - **Choice**: Added `AudioStreamIngester` with consumer callback plus helpers for async iterables, WebSocket objects, and file tailing.
   - **Reasoning**: Covers the plan’s ingestion variants while sharing the same buffer/flush logic.
   - **Trade-offs**: File tailing assumes float32 frames; WAV decoding will need to be layered on in later subtasks.

#### Validation
- `pytest tests/test_realtime_stream_ingester.py tests/test_profile_extractor.py tests/test_character_profile_extractor.py -q`
- `pytest tests/test_profile_extraction.py -q`

---

### Implementation Notes & Reasoning (2025-11-02)
**Implementer**: Codex (GPT-5)

1. **Context-Aware Streaming Transcriber**
   - **Choice**: Added `RealtimeTranscriber` with a pluggable faster-whisper style backend, history window, and optional async result handler hook.
   - **Reasoning**: Keeps the ingestion buffer decoupled while allowing downstream consumers (UI, diarizer) to subscribe to incremental transcript updates.
   - **Alternatives Considered**: Extending `FasterWhisperTranscriber`; rejected to avoid importing heavy batch dependencies into the realtime package.
   - **Trade-offs**: Slight duplication of transcription dataclasses, but isolates streaming concerns cleanly.

2. **History Prompt Management**
   - **Choice**: Maintain a deque of recent transcript segments capped by a configurable duration to seed the next chunk's prompt.
   - **Reasoning**: Preserves conversational context without unbounded memory usage and keeps latency predictable.
   - **Alternatives Considered**: Token-count based trimming; deferred until we have empirical latency data.
   - **Trade-offs**: Duration-based pruning may over-retain verbose segments; acceptable until we benchmark.

3. **Async Integration with Ingestion**
   - **Choice**: Provide an async `consume_chunk` adapter that offloads transcription to a worker thread and forwards results to an optional coroutine handler.
   - **Reasoning**: Allows the existing `AudioStreamIngester` to wire up the transcriber directly without blocking the event loop.
   - **Trade-offs**: Thread offloading introduces minimal overhead; protects UI responsiveness.

4. **Energy-Based Realtime Diarizer**
   - **Choice**: Added `RealtimeDiarizer` with pluggable speaker classifier (defaulting to energy thresholding) to maintain incremental speaker segments while sharing the ingestion interface.
   - **Reasoning**: Provides a deterministic fallback when PyAnnote streaming is unavailable and keeps downstream consumers synchronized with transcript timing.
   - **Alternatives Considered**: Calling PyAnnote per chunk; deferred until we can benchmark latency and GPU requirements.
   - **Trade-offs**: Energy heuristic is simplistic but testable; models can be swapped by supplying a different classifier.

5. **Live Session UI Scaffolding**
   - **Choice**: Created a dedicated Live Session tab with start/stop controls, status badges, and placeholders for transcript, speaker timeline, and audio levels.
   - **Reasoning**: Exposes realtime capture workflow early so downstream integrations (transcriber, diarizer) can connect without reshaping the UI.
   - **Alternatives Considered**: Extending Process tab with live mode toggle; split tab keeps streaming UX focused and avoids overloading existing workflow.
   - **Trade-offs**: Currently uses placeholder messaging rather than wiring to backend; acceptable until streaming pipeline lands.

#### Validation
- `pytest tests/test_realtime_transcriber.py tests/test_realtime_stream_ingester.py -q`
- `pytest tests/test_realtime_diarizer.py tests/test_realtime_transcriber.py tests/test_realtime_stream_ingester.py -q`
- `pytest tests/test_live_session_tab.py tests/test_realtime_diarizer.py tests/test_realtime_transcriber.py tests/test_realtime_stream_ingester.py -q`

---

## P3-FEATURE-002: Multi-language Support (Dutch & English)

**Files**: `src/transcriber.py`, `src/config.py`
**Effort**: 1 day
**Priority**: LOW
**Dependencies**: None
**Status**: NOT STARTED

### Problem Statement
The system is primarily designed for Dutch but should officially support English as a first-class language.

### Success Criteria
- [ ] UI allows selecting between "Dutch" and "English".
- [ ] Whisper model uses the specified language for transcription.
- [ ] IC/OOC classification prompts are optimized for the selected language.
- [ ] Documentation is updated to reflect dual-language support.

### Implementation Plan

#### Subtask 2.1: Add Language Configuration
**Effort**: 2 hours

Add a `WHISPER_LANGUAGE` setting to the configuration, accepting `en` or `nl`. Default to `nl`.

**Files**: `.env.example`, `src/config.py`

#### Subtask 2.2: Update Transcriber & Prompts
**Effort**: 4 hours

- Pass the language parameter to the Whisper model during transcription.
- Create a `prompts/ic_ooc_classification_en.txt` for English-language classification.
- Update the classifier to use the correct prompt based on the selected language.

**Files**: `src/transcriber.py`, `src/classifier.py`, `prompts/`

#### Subtask 2.3: UI Language Selector
**Effort**: 2 hours

Add a simple dropdown to the UI to select either "Dutch" or "English".

**Files**: `app.py`

#### Subtask 2.4: Testing
**Effort**: 2 hours

Test with both a Dutch and an English audio sample to ensure the correct models and prompts are used and the output is accurate.

**Files**: `tests/test_multilingual.py`

---

## P3-FEATURE-003: Custom Speaker Labels

**Files**: `src/diarizer.py`, UI integration
**Effort**: 2 days
**Priority**: LOW
**Dependencies**: None
**Status**: NOT STARTED

### Problem Statement
Diarization outputs generic labels ("Speaker 1", "Speaker 2"). Users must manually map these to player names. Need UI to assign custom labels and persist mappings.

### Success Criteria
- [_] UI allows assigning names to speakers (Speaker 1 -> "Alice", Speaker 2 -> "Bob")
- [_] Labels persist across sessions (same speaker = same name)
- [_] Export uses custom labels instead of "Speaker N"
- [_] Option to auto-assign from party config

### Implementation Plan

#### Subtask 3.1: Speaker Mapping Schema
**Effort**: 2 hours

Design schema for speaker-to-name mappings.

**Schema**:
```json
{
  "campaign": "broken_seekers",
  "mappings": {
    "speaker_embedding_001": {
      "name": "Alice",
      "character": "Elara",
      "role": "player"
    },
    "speaker_embedding_002": {
      "name": "Bob",
      "character": "Thorin",
      "role": "player"
    },
    "speaker_embedding_003": {
      "name": "Charlie",
      "character": null,
      "role": "dm"
    }
  }
}
```

**Files**: New `schemas/speaker_mapping.json`

#### Subtask 3.2: Speaker Embedding Extraction
**Effort**: 1 day

Extract speaker embeddings for consistent identification.

**Approach**: Use PyAnnote embeddings to identify speakers across sessions.

**Files**: `src/diarizer.py`

#### Subtask 3.3: UI for Speaker Labeling
**Effort**: 1 day

Add speaker labeling interface.

**UI Features**:
- Display all detected speakers
- Text input for custom name
- Link to character profile
- "Auto-assign from Party Config" button

**Files**: `app.py`, `src/ui/speaker_mapping_tab.py` (new)

#### Subtask 3.4: Apply Labels to Outputs
**Effort**: 4 hours

Replace generic labels in transcript and snippets.

**Files**: `src/diarizer.py`, `src/snipper.py`

---

# P4: Infrastructure & Quality

## P4-INFRA-001: Comprehensive Test Suite

**Files**: `tests/` (expand coverage)
**Effort**: 3-5 days
**Priority**: MEDIUM
**Dependencies**: None
**Status**: NOT STARTED

### Problem Statement
Current test coverage is incomplete. Need comprehensive unit, integration, and end-to-end tests for all modules.

### Success Criteria
- [_] > 80% code coverage
- [_] Unit tests for all core modules
- [_] Integration tests for pipeline
- [_] End-to-end tests for CLI and UI
- [_] Test fixtures for audio samples
- [_] Automated test reporting

### Implementation Plan

#### Subtask 1.1: Test Coverage Analysis
**Effort**: 4 hours

Measure current coverage and identify gaps.

**Commands**:
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html to see gaps
```

**Files**: Generate coverage report

#### Subtask 1.2: Unit Tests for Core Modules
**Effort**: 3 days

Write unit tests for all src/ modules.

**Modules**:
- `src/chunker.py`
- `src/transcriber.py`
- `src/diarizer.py`
- `src/snipper.py`
- `src/pipeline.py`
- `src/config.py`
- `src/checkpoint.py`

**Files**: `tests/unit/test_*.py`

#### Subtask 1.3: Integration Tests
**Effort**: 1 day

Test module interactions.

**Test Cases**:
- Chunker -> Transcriber -> Diarizer flow
- Pipeline with checkpoints (pause/resume)
- Config loading and validation

**Files**: `tests/integration/test_*.py`

#### Subtask 1.4: Test Fixtures
**Effort**: 1 day

Create reusable test fixtures.

**Fixtures**:
- Sample audio files (5 sec, 30 sec, 2 min)
- Mock transcripts
- Mock knowledge bases
- Mock party configs

**Files**: `tests/fixtures/`

---

## P4-INFRA-002: CI/CD Pipeline

**Files**: `.github/workflows/` (new)
**Effort**: 2-3 days
**Priority**: MEDIUM
**Dependencies**: P4-INFRA-001 (Test Suite)
**Status**: NOT STARTED

### Problem Statement
No automated testing or deployment pipeline. Need CI/CD for:
- Automated testing on pull requests
- Code quality checks (linting, type checking)
- Automated releases

### Success Criteria
- [_] GitHub Actions workflow for tests
- [_] Run on every pull request
- [_] Code quality gates (flake8, mypy)
- [_] Automated release tagging

### Implementation Plan

#### Subtask 2.1: GitHub Actions - Test Workflow
**Effort**: 1 day

Create workflow to run tests on PRs.

**Workflow**:
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**Files**: New `.github/workflows/test.yml`

#### Subtask 2.2: Code Quality Checks
**Effort**: 1 day

Add linting and type checking.

**Workflow Addition**:
```yaml
- name: Lint with flake8
  run: |
    pip install flake8
    flake8 src/ --max-line-length=100
- name: Type check with mypy
  run: |
    pip install mypy
    mypy src/
```

**Files**: `.github/workflows/test.yml`, `setup.cfg` (flake8 config)

---

## P4-INFRA-003: Performance Profiling

**Files**: `tools/profiler.py` (new), performance benchmarks
**Effort**: 2 days
**Priority**: LOW
**Dependencies**: None
**Status**: NOT STARTED

### Problem Statement
No visibility into performance bottlenecks. Need profiling tools to identify optimization opportunities.

### Success Criteria
- [_] Profiling script for pipeline
- [_] Benchmark suite for core operations
- [_] Memory profiling
- [_] Performance regression detection

### Implementation Plan

#### Subtask 3.1: CPU Profiling Script
**Effort**: 4 hours

Create script to profile pipeline execution.

**Tool**: cProfile + snakeviz

**Usage**:
```bash
python tools/profiler.py --input session.m4a --output profile.prof
snakeviz profile.prof  # Interactive visualization
```

**Files**: New `tools/profiler.py`

#### Subtask 3.2: Benchmark Suite
**Effort**: 1 day

Create benchmarks for core operations.

**Benchmarks**:
- Audio conversion (M4A -> WAV)
- VAD chunking (1 hour audio)
- Transcription (1 hour audio)
- Diarization (1 hour audio)

**Files**: New `tools/benchmark.py`

#### Subtask 3.3: Memory Profiling
**Effort**: 4 hours

Profile memory usage during processing.

**Tool**: memory_profiler

**Files**: `tools/memory_profiler.py`

---

## P4-DOCS-001: API Documentation

**Files**: `docs/api/` (new), module docstrings
**Effort**: 2-3 days
**Priority**: LOW
**Dependencies**: None
**Status**: NOT STARTED

### Problem Statement
No formal API documentation for developers. Need comprehensive docs for:
- Module APIs
- Function signatures
- Usage examples

### Success Criteria
- [_] All public functions have docstrings
- [_] Sphinx documentation site
- [_] Auto-generated API reference
- [_] Usage examples for each module

### Implementation Plan

#### Subtask 1.1: Add Docstrings
**Effort**: 2 days

Add comprehensive docstrings to all modules.

**Docstring Format** (Google style):
```python
def process_session(audio_path: Path, config: Config) -> ProcessingResult:
    """Process a D&D session audio file.

    Args:
        audio_path: Path to audio file (M4A, MP3, or WAV)
        config: Configuration object with processing settings

    Returns:
        ProcessingResult containing transcript, diarization, and metadata

    Raises:
        FileNotFoundError: If audio file doesn't exist
        ValueError: If audio format is unsupported

    Example:
        >>> config = Config.load()
        >>> result = process_session(Path("session.m4a"), config)
        >>> print(result.transcript)
    """
```

**Files**: All `src/*.py` files

#### Subtask 1.2: Sphinx Setup
**Effort**: 1 day

Set up Sphinx for auto-generated docs.

**Setup**:
```bash
pip install sphinx sphinx-rtd-theme
cd docs
sphinx-quickstart
```

**Config**:
```python
# docs/conf.py
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # Google-style docstrings
    "sphinx.ext.viewcode"
]
```

**Files**: `docs/conf.py`, `docs/index.rst`

---

**See IMPLEMENTATION_PLANS.md for templates and P0 features**
**See IMPLEMENTATION_PLANS_PART2.md for P1 High Impact features**
**See IMPLEMENTATION_PLANS_PART3.md for P2 LangChain Integration**
**See IMPLEMENTATION_PLANS_SUMMARY.md for effort estimates and sprint planning**
