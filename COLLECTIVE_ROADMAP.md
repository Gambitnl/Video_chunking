# Multi-Agent Roadmap (VideoChunking)

> **Self-Identity Check**  
> Any AI collaborator must verify its identity before acting in this repository. Multiple agents (Claude, Gemini, ChatGPT/Codex) contribute here; keep logs attributable.

---

## Repository Objective
Transform long-form D&D session recordings into rich, searchable transcripts with speaker diarization, IC/OOC classification, character context, and optional per-segment audio snippets—delivered via CLI and Gradio UI.

---

## Recently Completed (Cross-Agent)
- ✅ Groq transcription fix (`getattr(response, "words", None)`) and manifest enrichment with text + classification metadata.
- ✅ Audio snippet export toggle (`--skip-snippets`, Gradio checkbox) and manifest surfacing in UI/CLI.
- ✅ Pipeline logging now routed through `SessionLogger`; session lifecycle logs recorded.
- ✅ Initial pytest suite (`tests/test_snipper.py`, `tests/test_merger.py`, `tests/test_formatter.py`) for snippet cleanup and overlap merging.
- ✅ Docs updated for RAM expectations, skip-snippets option, and segment manifest location.
- ✅ Session ID sanitization reinstated for filesystem outputs (original IDs retained in metadata/logs).
- ✅ Added real-time stage tracking (status JSON) and landing dashboard indicators.
- ✅ **Campaign Dashboard** - Health monitoring with component status indicators (party, settings, knowledge base, characters, sessions).
- ✅ **Campaign Knowledge Base** - Auto-extraction of quests, NPCs, plot hooks, locations, and items from session transcripts.
- ✅ **Story Notebooks** - Document viewer integration (Google Docs) + narrative generation (narrator + character POV).
- ✅ **Import Session Notes** - Backfill campaign data from written notes (no recording needed).
- ✅ **SRT Subtitle Export** - Full/IC/OOC subtitle files for video overlay workflows.
- ✅ **Character Profile Storage Refactoring** - Individual file storage per character for better scalability.
- ✅ **App Manager** - Real-time status monitoring with per-stage progress tracking and auto-refresh.
- ✅ **Test Suite Refactoring** - Pytest markers (@pytest.mark.slow) for fast/slow test separation; lazy loading of Whisper model.
- ✅ **Unicode Compatibility Fixes** - Replaced emoji/symbols causing Windows cp1252 crashes.

---

## In-Flight / Planned Work by Agent

### ChatGPT (Codex) Priorities
1. **Streaming Snippet Export** – Prototype ffmpeg streaming to avoid loading multi-hour WAVs.
2. **Test Coverage Expansion** – Add formatter timestamp, speaker profile, and mocked end-to-end pipeline tests.
3. **Manifest UX Enhancements** – CLI/CSV utility for inspecting segment manifests and summarising durations.
4. **Telemetry Improvements** – Funnel remaining `print()` usage through `SessionLogger`; expose log-level controls.

### Claude (Sonnet 4.5) Backlog
1. ~~**Automate Character Profiles**~~ – ✅ COMPLETED: Auto-extraction of actions, items, relationships from transcripts via Character Profiles tab.
2. **Analytics & Filtering** – Implement action filtering/search, statistics, and progression timelines for characters.
3. ~~**Logging & Backups**~~ – ✅ COMPLETED: Individual file storage per character with automatic backup/versioning.
4. **Manual Data Entry UX** – Improve markdown visual hierarchy, summary stats, and add interactive tables (ongoing).
5. **Cross-Link Sessions** – Map speaker diarization output to character profiles for consistent naming.

### Gemini Code Review Follow-ups
1. **Pipeline Integration Test** – Build mocked end-to-end test with fixtures to ensure orchestration stability.
2. **Test Fixtures Library** – Maintain small audio samples and config mocks for reproducible testing.
3. **(Done)** Central logger integration, prompt externalisation, and baseline pytest setup.

### Gemini Feature Proposals
1. **Live Transcription Mode** – Streaming capture via microphone with rolling transcript updates.
2. **OOC Keyword & Topic Analysis** – TF-IDF/topic clustering for the OOC transcript; output "Social Insights".
3. **Sound Event Detection** – Integrate YAMNet (or similar) and insert event annotations (e.g., `[Laughter]`).
4. **Visualization Suite ("Gemini Constellation")**
   - Speaker constellation graph (interaction network).
   - Session galaxy scatter (timeline vs. sentiment/pacing).
   - Topic nebula word cloud for OOC content.
5. **UI Theme Alignment** – Apply "Gemini Constellation" dark theme across Gradio tabs for future visualizations.
6. ~~**Bug Fixes**~~ – ✅ COMPLETED: Session ID sanitization and defensive Config casting.

---

## Coordination Notes
- **Ownership**: Before implementing an item, verify no other agent is actively addressing it; update review docs accordingly.
- **Testing**: Expand pytest coverage alongside new features; prefer deterministic fixtures over network-dependent calls.
- **Documentation**: Every shipped feature should update README/USAGE/QUICKREF and, when relevant, the review logs to prevent overlap.

---

*Prepared by ChatGPT (Codex), GPT-5-based coding agent.*  
*Generated: 2025-10-16*
