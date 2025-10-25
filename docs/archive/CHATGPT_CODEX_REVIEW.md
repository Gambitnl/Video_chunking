# Self-Identity Check Required

Before any automated agent (including me, **ChatGPT (Codex)**) acts in this repository, it **must perform a self-identity verification** to ensure it is aware of its designated role. This reminder exists because multiple agents collaborate here.

---

# ChatGPT (Codex) Review Log

**Identity:** ChatGPT (Codex), GPT-5-based coding agent  
**Review Timestamp:** 2025-10-15  
**Scope:** Latest additions for per-segment audio exports and default GPT-OSS configuration.

## Core Functionality (Use Case Summary)

The repository implements an end-to-end workflow for processing long-form Dungeons & Dragons session recordings. Core capabilities include:
- Converting raw audio (typically single-mic M4A files) to analysis-ready WAV via FFmpeg.
- Smart chunking with Silero VAD, followed by Whisper transcription (local or Groq/OpenAI backends).
- Overlap reconciliation, speaker diarization with PyAnnote, and IC/OOC semantic classification via local LLMs (default GPT-OSS 20B through Ollama).
- Multi-format transcript generation (full, IC-only, OOC-only, JSON metadata) exposed through both a Gradio web UI and a Click-based CLI.
- Party/character context management to improve labeling, and (recently) per-segment audio snippet export aligned with transcript timestamps.

## Findings

1. **Stale Clip Cleanup Missing**  
   - **File:** `src/snipper.py:39`  
   - **Issue:** When reprocessing a session, the exporter saves new clips into `output/segments/<session_id>/` but never removes clips left from previous runs. The manifest overwrites the old file list, yet orphaned WAV files remain on disk, which can confuse downstream consumers that enumerate the directory.  
   - **Recommendation:** Clear the session directory (or remove the files listed there) before writing the new batch.

2. **Memory Footprint Consideration**  
   - **File:** `src/snipper.py:47` (AudioSegment load)  
   - **Issue:** We load the entire converted WAV into memory via `AudioSegment.from_file`. For 4-hour 16 kHz mono sessions this is ~450 MB. That’s acceptable on a 16 GB machine, but worth documenting or guarding, especially for multi-session processing.  
   - **Recommendation:** Document minimum RAM requirements, or explore streaming/FFmpeg segment extraction to avoid full in-memory copies.

## Critique & Risks

- **Operational Risk:** Without cleanup, the `segments/` directory becomes misleading and could overwrite partial results if other tools aggregate by filename pattern.  
- **Resource Risk:** Heavy memory use may trigger crashes on constrained hardware, contradicting the “zero-budget” promise.

## Improvement Plan

1. **Implement Clip Directory Reset**  
   - Add a pre-export cleanup step in `AudioSnipper.export_segments`.  
   - Option: `shutil.rmtree(session_dir)` before recreating it, or iterate and delete individual `.wav` files.

2. **Add Resource Guidance / Optimization Ticket**  
   - Update docs (README/SETUP) to call out RAM expectations for long sessions.  
   - Create follow-up issue to investigate streaming extraction via FFmpeg subprocess to reduce peak memory.

3. **Regression Tests / Samples**  
   - Introduce a lightweight unit/integration test that mocks two export passes and asserts the directory contents match the manifest.  
   - Provide a sample manifest snippet in documentation for clarity.

---

## Additional Opportunities & Issues (2025-10-16)

### A. Feature Request: Optional Audio Segment Export
- **Observation:** Stage 8 always produces per-segment clips. Some users may only need transcripts (especially when storage or RAM is limited).  
- **Proposal:** Add a `--skip-snippets` flag to the CLI and a toggle in the Gradio UI to disable Stage 8. Persist preference in config for repeat runs.

### B. Improvement: Enrich Segment Manifest
- **Observation:** `manifest.json` currently records only timing and speaker ID. Reviewers often want the associated text and IC/OOC label when sampling clips.  
- **Proposal:** Include the transcript text snippet and (when available) the classification result in each manifest entry. Optionally expose a CSV export for spreadsheet workflows.

### C. Bug: Groq Transcriber Word Handling
- **File:** `src/transcriber.py` (GroqTranscriber)  
- **Issue:** The code checks `if 'words' in response:` but the Groq SDK returns an object, not a dict. This raises `TypeError: argument of type 'AudioTranscription' is not iterable` when word timestamps are requested.  
- **Fix Suggestion:** Replace with `if getattr(response, "words", None):` and iterate safely (or adapt to the SDK response structure).

### D. Testing Infrastructure Gap
- **Observation:** There is no `tests/` directory or automated coverage. Given the breadth of features (audio pipeline, UI, party config), unit tests are essential for regression safety.  
- **Proposal:** Establish a `tests/` package using `pytest`, starting with high-leverage modules (e.g., `AudioSnipper`, `TranscriptionMerger`, `PartyConfigManager`). Provide fixtures for small audio snippets and mock LLM responses.

### E. Logging Consistency
- **Observation:** `pipeline.py` and other modules rely heavily on `print()` statements. A central `SessionLogger` already exists but isn’t used in the pipeline, resulting in unstructured console output.  
- **Proposal:** Refactor pipeline stages (and CLI/Gradio entry points) to emit logs via the shared logger, enabling leveled logging, filtering, and easier integration with future monitoring.

### F. Prompt Maintainability (Completed)
- Status: Prompt template now lives in `src/prompts/classifier_prompt.txt`, so no further action required.

---

## Completed Work (2025-10-16)

- Fixed Groq word-alignment bug and added richer segment metadata saved in `manifest.json`.
- Introduced optional audio-snippet export toggle (`skip_snippets`) surfaced in both CLI and UI.
- Refactored `DDSessionProcessor` to use `SessionLogger` for structured stage output and session lifecycle logs.
- Added initial `pytest` suite covering the audio snipper cleanup and transcription merger logic.
- Documented memory requirements and new CLI flag in README/USAGE/QuickRef, updated web UI messaging to expose manifest paths.

## Implementation Plan (Next Steps)

1. **Evaluate Streaming Snippet Export**  
   - Prototype an ffmpeg-based streaming cutter to avoid loading multi-hour WAV files entirely into memory.

2. **Broaden Automated Tests**  
   - Add pytest coverage for the formatter timestamp helpers and speaker profile manager, plus a mocked end-to-end pipeline smoke test.

3. **Manifest UX Enhancements**  
   - Provide a CLI utility (e.g., `cli.py show-manifest`) to inspect segments, and consider optional CSV export with duration totals.

4. **Telemetry & Logging Extensions**  
   - Funnel remaining `print` statements (e.g., in auxiliary utilities) through `SessionLogger` and expose log level selection in CLI/UI.

5. **Incremental Config Autofill**  
   - While the pipeline processes transcripts, have the contextual LLM progressively backfill missing party metadata (character names, player names, factions) so newly inferred details appear in the app without waiting for full session completion.

---

_Prepared by ChatGPT (Codex), GPT-5-based coding agent._
