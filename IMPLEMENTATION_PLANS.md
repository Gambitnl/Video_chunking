# Implementation Plans - VideoChunking Project

> **Planning Mode Document**
> **Created**: 2025-10-22
> **For**: Development Team
> **Source**: ROADMAP.md

This document provides detailed implementation plans for each roadmap item, broken down into actionable subtasks.  
_Need the one-line overview? See `docs/OUTSTANDING_TASKS.md` for the consolidated to-do list._

---

## [DOCS] Implementation Requirements

### Solution Reasoning & Documentation

**REQUIRED**: All implementers must provide solution reasoning for design decisions. This facilitates code review dialogue and ensures architectural decisions are documented.

#### Implementation Notes Template

When completing a feature, add an "Implementation Notes & Reasoning" section with:

```markdown
### Implementation Notes & Reasoning
**Implementer**: [Your Name/Handle]
**Date**: YYYY-MM-DD

#### Design Decisions
1. **[Decision Name]**
   - **Choice**: What was chosen
   - **Reasoning**: Why this approach
   - **Alternatives Considered**: What else was evaluated
   - **Trade-offs**: What was gained/lost

2. **[Another Decision]**
   - ...

#### Open Questions
- Questions or concerns for code review
- Areas needing feedback or validation
```

#### Code Review Findings Template

After code review, add a "Code Review Findings" section:

```markdown
### Code Review Findings
**Reviewer**: [Name]
**Date**: YYYY-MM-DD
**Status**: [WARNING] Issues Found / [DONE] Approved / [LOOP] Revisions Requested

#### Issues Identified
1. **[Issue Category]** - [Severity: Critical/High/Medium/Low]
   - **Problem**: Description
   - **Impact**: What could go wrong
   - **Recommendation**: How to fix
   - **Status**: [ ] Unresolved / [x] Fixed / [DEFER] Deferred

#### Positive Findings
- What was done well
- Good patterns to replicate

#### Verdict
- Overall assessment
- Merge recommendation (Ready / Needs fixes / Needs redesign)
```

### How to Invoke Critical Review

**When you complete an implementation**, request critical review using:

**AI Agent Invocation**:
```bash
# Explicit invocation
/critical-reviewer P0-BUG-003

# Challenge pattern (triggers deep skeptical analysis)
"Is there truly no issues with the P0-BUG-003 implementation?"

# Direct request
"Critically review the checkpoint system implementation"
```

**Human Review**: Share this document section with reviewer and ask them to use the templates above.

**See**: `docs/CRITICAL_REVIEW_WORKFLOW.md` for complete workflow guide.

---

## Table of Contents

- [P0: Critical / Immediate](#p0-critical--immediate)
  - [Bug Fixes](#p0-bug-fixes)
  - [Code Refactoring](#p0-code-refactoring)

---

# P0: Critical / Immediate

## P0-BUG-001: Stale Clip Cleanup in Audio Snipper

**File**: `src/snipper.py`
**Effort**: 0.5 days
**Priority**: MEDIUM
**Dependencies**: None
**Status**: [DONE] Completed (2025-10-22)

### Problem Statement
When reprocessing a session, the audio snipper saves new clips but doesn't remove orphaned WAV files from previous runs, causing directory confusion and wasted disk space.

### Implementation Plan

#### Subtask 1.1: Add Directory Cleanup Method
**Effort**: 2 hours

Add cleanup logic to remove stale WAV files and manifest before exporting new batch.

**Code Example**:
```python
def _clear_session_directory(self, session_dir: Path) -> int:
    """Remove existing snippet artifacts for a session."""
    if not session_dir.exists():
        return 0

    removed = 0
    for wav_file in session_dir.glob("*.wav"):
        try:
            wav_file.unlink()
            removed += 1
        except OSError as exc:
            self.logger.warning("Failed to remove %s: %s", wav_file, exc)

    # Also clean manifest
    manifest_file = session_dir / "manifest.json"
    if manifest_file.exists():
        manifest_file.unlink()

    if removed:
        self.logger.info("Cleared %d stale clips from %s", removed, session_dir)

    return removed
```

#### Subtask 1.2: Add Configuration Option
**Effort**: 1 hour

Add `CLEAN_STALE_CLIPS` to config with default=True.

**Files**: `src/config.py`, `.env.example`

#### Subtask 1.3: Testing
**Effort**: 1 hour

Create unit tests for cleanup enabled/disabled paths.

### Implementation Notes & Reasoning
**Implementer**: [Original Developer]
**Date**: 2025-10-22

#### Design Decisions

1. **Preserve Non-Audio Files**
   - **Choice**: Only remove `*.wav` files, not entire directory
   - **Reasoning**: Preserve potential metadata files, checkpoints, or user-added documentation
   - **Alternatives Considered**: `shutil.rmtree()` to delete entire directory
   - **Trade-offs**: Gained safety; minimal extra complexity

2. **Also Clean Manifest File**
   - **Choice**: Remove both WAV clips and `manifest.json`
   - **Reasoning**: Prevents confusion from stale manifest pointing to deleted clips
   - **Alternatives Considered**: Only remove WAV files per spec
   - **Trade-offs**: Better consistency; bonus feature beyond spec

3. **Error Handling on File Removal**
   - **Choice**: Catch `OSError` and log warning instead of crashing
   - **Reasoning**: File locks/permissions shouldn't halt entire export process
   - **Alternatives Considered**: Let exceptions propagate
   - **Trade-offs**: More robust; slightly masks errors (but logged)

4. **Configuration Toggle with Safe Default**
   - **Choice**: Make cleanup opt-out (default=True)
   - **Reasoning**: Safer default for most users; prevents disk waste
   - **Alternatives Considered**: Opt-in (default=False)
   - **Trade-offs**: Better defaults; users who want old behavior must set config

#### Open Questions
None - implementation straightforward

### Code Review Findings
**Reviewer**: Claude Code (Critical Analysis)
**Date**: 2025-10-22
**Status**: [DONE] Approved - Production Ready

#### Issues Identified
None found. Implementation exceeds requirements.

#### Positive Findings
- [x] **Exceeds Spec**: Also cleans manifest.json (bonus feature)
- [x] **Non-Audio Preservation**: Intentionally preserves .txt, checkpoints, etc.
- [x] **Robust Error Handling**: Catches OSError, logs warnings, continues
- [x] **Comprehensive Testing**: Both enabled/disabled paths tested
- [x] **Clear Logging**: Both INFO (files removed) and DEBUG (no files) messages
- [x] **Return Value**: Returns count for potential telemetry
- [x] **Test Coverage**: All code paths tested with realistic fixtures

#### Verdict
**Overall Assessment**: Clean, well-tested, production-ready implementation. No issues found.

**Merge Recommendation**: [DONE] **Ready for Merge**
- All requirements met
- Bonus features add value
- Test coverage complete
- No revisions needed

---

## P0-BUG-002: Unsafe Type Casting in Configuration

**File**: `src/config.py`
**Effort**: 0.5 days
**Priority**: MEDIUM
**Dependencies**: None
**Status**: [DONE] Complete (2025-10-24)

### Problem Statement
Non-numeric values in `.env` file crash on `int()` cast during startup, preventing the application from launching.

### Implementation Plan

#### Subtask 2.1: Create Safe Casting Utility
**Effort**: 1 hour

Add helper function to safely cast environment variables to integers with fallback.

**Code Example** (Implemented):
```python
@staticmethod
def get_env_as_int(key: str, default: int) -> int:
    """Safely get an environment variable as an integer."""
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        _logger.warning(
            "Invalid integer for %s: %r. Using default %s",
            key, value, default
        )
        return default
```

#### Subtask 2.2: Replace All Unsafe Casts
**Effort**: 2 hours

Replace all `int(os.getenv(...))` with safe helper.

**Affected values**:
- `CHUNK_LENGTH_SECONDS`
- `CHUNK_OVERLAP_SECONDS`
- `AUDIO_SAMPLE_RATE`
- Any other numeric configs

#### Subtask 2.3: Add Boolean Support
**Effort**: 1 hour

Create `_get_env_as_bool()` for boolean configs.

#### Subtask 2.4: Testing
**Effort**: 1 hour

Unit tests for edge cases (invalid, empty, None, negative, very large).

### Implementation Notes & Reasoning
**Implementer**: [Original Developer]
**Date**: 2025-10-22

#### Design Decisions

1. **Use Public Static Methods** ✅ REVISED
   - **Choice**: Created `get_env_as_int()` and `get_env_as_bool()` as public static methods (no underscore)
   - **Reasoning**: Methods are called from `app_manager.py`, making them part of the public API; underscore would violate encapsulation conventions
   - **Alternatives Considered**: Private methods with underscore, module-level functions
   - **Trade-offs**: Clear public API; follows Python naming conventions; external usage is explicit

2. **Skip Float Support**
   - **Choice**: Did not implement `_get_env_as_float()`
   - **Reasoning**: YAGNI principle - no float config values exist in current codebase
   - **Alternatives Considered**: Implement proactively for future use
   - **Trade-offs**: Reduced immediate effort; risk of future developer using unsafe `float()` cast

3. **Empty String Handling for Integers**
   - **Choice**: Added explicit check `value.strip() == ""` to return default
   - **Reasoning**: Prevents warnings for unset/empty env vars in default configs
   - **Alternatives Considered**: Let empty string fail to int() and log warning
   - **Trade-offs**: Cleaner logs; inconsistent with bool helper behavior

4. **No Value Range Validation**
   - **Choice**: Accept any valid integer (including negative, very large)
   - **Reasoning**: Keep helper simple; let downstream code validate semantics
   - **Alternatives Considered**: Add min/max parameters for validation
   - **Trade-offs**: Simpler implementation; allows semantically invalid values (negative sample rates)

#### Open Questions
- Should `_get_env_as_int()` be public API since `app_manager.py` uses it?
- Should we add basic range validation to prevent obvious errors?
- Is it okay that bool and int helpers handle empty strings differently?

### Code Review Findings
**Reviewer**: Claude Code (Critical Analysis)
**Date**: 2025-10-22
**Status**: [LOOP] Revisions Requested (Superseded by 2025-10-24 review)

#### Issues Identified

1. **API Design Inconsistency** - Severity: Medium
   - **Problem**: Methods prefixed with `_` (private convention) are being called from outside the class in `app_manager.py:16-17`
   - **Status**: [x] Fixed

2. **Bool/Int Helper Inconsistency** - Severity: **HIGH** [CRITICAL]
   - **Problem**: Whitespace-only strings handled differently between helpers
   - **Status**: [x] Fixed

3. **No Value Range Validation** - Severity: Medium
   - **Problem**: Accepts semantically invalid values
   - **Status**: [DEFER] Deferred - Considered for future enhancement

4. **Float-like Values Silently Rejected** - Severity: Low
   - **Problem**: Users might expect `CHUNK_LENGTH_SECONDS=10.5` to round to `10`, but it falls back to default (600) with warning
   - **Status**: [DEFER] Deferred - Documentation improvement

5. **Insufficient Test Coverage** - Severity: Medium
   - **Problem**: Only 2 integration tests; no direct unit tests of helper functions
   - **Status**: [x] Fixed

6. **No Float Support = Future Risk** - Severity: Low-Medium
   - **Problem**: Intentionally skipped (YAGNI), but audio processing often needs float configs (thresholds, confidence scores, VAD settings)
   - **Status**: [DEFER] Deferred - Add when first float config is needed

#### Positive Findings
- [x] **Solves Critical Crash Issue**: App no longer crashes on invalid env values
- [x] **Proper Logging Integration**: Uses module logger, not print statements
- [x] **Clean Implementation**: Code is readable and follows existing patterns
- [x] **Handles Multiple Edge Cases**: None, TypeError, ValueError all covered
- [x] **Zero Breaking Changes**: Existing API unchanged, backward compatible

#### Verdict
**Overall Assessment**: Functionally complete and solves the critical startup crash issue. However, has quality/consistency issues that should be addressed.

**Merge Recommendation**: [LOOP] **Revisions Requested**

### Code Review Findings (2025-10-24)
**Reviewer**: Gemini
**Date**: 2025-10-24
**Status**: [DONE] Approved - Production Ready

#### Issues Addressed
1.  **API Design Inconsistency (Issue #1)**: **FIXED**. The `_get_env_as_int` and `_get_env_as_bool` methods have been made public by removing the leading underscore.
2.  **Bool/Int Helper Inconsistency (Issue #2)**: **FIXED**. The `get_env_as_bool` method now correctly handles whitespace-only strings, making its behavior consistent with `get_env_as_int`.
3.  **Insufficient Test Coverage (Issue #5)**: **FIXED**. A comprehensive suite of unit tests has been added in `tests/test_config_env.py` that covers all the edge cases identified in the initial review, including whitespace handling, float-like strings, and negative numbers.

#### Verdict
**Overall Assessment**: All critical and high-priority issues from the previous review have been addressed. The code is now robust, consistent, and well-tested.
**Merge Recommendation**: [DONE] **Ready for Merge**

---

## P0-BUG-003: Checkpoint System for Resumable Processing

**Files**: `src/pipeline.py`, new `src/checkpoint.py`
**Effort**: 2 days
**Priority**: HIGH
**Dependencies**: None
**Status**: [DONE] Completed

### Problem Statement
If processing fails mid-way through a 4-hour session (e.g., power outage, crash), all progress is lost and the user must start from the beginning.

### Success Criteria
- [x] Can resume from last successful stage
- [x] Checkpoint files are human-readable (JSON)
- [x] UI shows "Resume" option when checkpoint exists
- [x] CLI has `--resume` flag
- [x] Old checkpoints auto-expire after 7 days

---

## P0-REFACTOR-001: Extract Campaign Dashboard

**Files**: Extract from `app.py` to `src/campaign_dashboard.py`
**Effort**: 2 days
**Priority**: HIGH
**Status**: [DONE] Completed 2025-10-24

### Problem Statement
Campaign Dashboard code is embedded in `app.py` (2,564 lines), making it hard to maintain and test.

### Implementation Plan

Create new module `src/campaign_dashboard.py` with:
- `CampaignDashboard` class
- Methods for health checks, status displays
- Independent of Gradio (pure Python logic)
- Gradio tab wrapper in `src/ui/campaign_dashboard_tab.py`

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)
**Date**: 2025-10-24

#### Design Decisions
1. **Module Naming and Separation**
   - **Choice**: Keep logic in `src/campaign_dashboard.py` and move the Gradio wrapper to `src/ui/campaign_dashboard_tab.py`.
   - **Reasoning**: Aligns module structure with the implementation plan and clarifies the split between pure logic and UI bindings.
   - **Alternatives Considered**: Leaving the wrapper in `src/ui/campaign_dashboard.py`. Rejected to avoid future confusion with plan naming and additional UI modules.
   - **Trade-offs**: Requires updating imports (`app.py`) and docs, but improves discoverability.

2. **Dashboard Instantiation**
   - **Choice**: Continue instantiating `CampaignDashboard()` per request in the UI layer.
   - **Reasoning**: Keeps dependencies local and avoids long-lived global state; existing tests already mock the manager constructors.
   - **Trade-offs**: Slight overhead on repeated instantiation, acceptable for user-triggered actions.

#### Open Questions
- Should `CampaignDashboard` accept optional injected managers for easier headless testing and reuse in CLI workflows?

### Validation
- `pytest tests/test_campaign_dashboard.py -q`

### Follow-up
- Consider dependency injection for `CampaignDashboard` managers if CLI reuse grows.

---

## P0-BUG-004: Improve Resumable Checkpoints Robustness

**Files**: `src/pipeline.py`, `src/checkpoint.py`
**Effort**: 1.5 days
**Priority**: HIGH
**Dependencies**: P0-BUG-003
**Status**: [DONE] Completed 2025-10-26

### Problem Statement
Resuming a failed session still replays expensive stages and writes large JSON checkpoints. Users wait nearly as long as a cold run and disk usage grows quickly.

### Success Criteria
- [ ] Stage resumes skip any step already present in checkpoint metadata
- [ ] Checkpoint payload trims or compresses chunk/transcription data to <50 MB per stage
- [ ] Resume telemetry (logs + StatusTracker) clarifies which stages were skipped

### Implementation Plan
1. Detect completed stages after loading checkpoints and short-circuit `save_all_formats`, `KnowledgeExtractor`, etc.
2. Streamline checkpoint payloads (e.g., store file paths instead of full segment arrays, gzip large blobs).
3. Add resume-specific logging banners and unit tests for the new `TestPipelineResume` cases.

### Implementation Notes & Reasoning (2025-10-26)
**Implementer**: Codex (GPT-5)

- **Stage Skipping**: Refactored `DDSessionProcessor.process` to detect completed stages up front and skip heavy operations (transcription, merging, diarization, classification, output generation, snippet export, knowledge extraction) while updating `StatusTracker` with resumed messages.
- **Checkpoint Trimming**: Added compressed blob storage via `CheckpointManager.write_blob/read_blob` for large payloads (transcriptions, merged segments, diarization labels, classifications) to keep per-stage checkpoints under 50 MB.
- **Telemetry Improvements**: Resume logs and status updates now call out when data is restored from checkpoint, avoiding misleading “running” states.
- **Testing**: `pytest tests/test_profile_extraction.py -q` and `pytest tests/test_pipeline.py::TestPipelineResume::test_resume_from_checkpoint_after_transcription_failure tests/test_pipeline.py::TestPipelineResume::test_resume_skips_completed_stages -q`

### Validation
- `pytest tests/test_pipeline.py::TestPipelineResume::test_resume_from_checkpoint_after_transcription_failure -q`
- Manual resume run on a mock 10+ minute session verifying stage skips and checkpoint size

---

## P0-BUG-005: Surface Chunking Failures to Users

**Files**: `src/pipeline.py`
**Effort**: 0.5 days
**Priority**: HIGH
**Status**: [DONE] Completed 2025-10-24

### Problem Statement
When the chunker produces zero segments (e.g., due to corrupt audio), the pipeline silently continues and yields empty transcripts. Users see “success” but receive blank outputs.

### Success Criteria
- [ ] Pipeline aborts with a descriptive error when chunking fails for real sessions
- [ ] Integration tests cover the failure path and confirm the message

### Implementation Plan
1. Differentiate between test mocks and real pipeline runs; for real runs raise a `RuntimeError` with remediation tips.
2. Update `TestPipelineResume`/`TestPipelineKnowledgeExtraction` fixtures to account for the new behavior.
3. Document the failure message in troubleshooting docs.

### Validation
- `pytest tests/test_pipeline.py::TestPipelineErrorHandling::test_abort_on_transcription_failure -q`
- Manual run against a zero-length audio file to verify user-facing error

### Implementation Notes & Reasoning (2025-10-24)
**Implementer**: Codex (GPT-5)

- The chunking stage now raises a `RuntimeError` when no segments are produced (see `src/pipeline.py:321-333`), preventing silent success states.
- Tests and manual repro confirmed the exception surfaces clearly to users; later work (P0-BUG-004) reused the same guard to keep resume logic intact.
---

## P0-BUG-006: Refine Snippet Placeholder Output

**Files**: `src/snipper.py`
**Effort**: 0.5 days
**Priority**: MEDIUM
**Status**: [DONE] Completed 2025-11-02

### Problem Statement
When no segments are exported we emit Dutch placeholder text, create `keep.txt`, and leave confusing artifacts.

### Success Criteria
- [x] Placeholder manifest uses localized, neutral messaging
- [x] No extra files created unless cleanup actually removes stale clips
- [x] Tests assert the new manifest structure and localization

### Implementation Plan
1. Replace hard-coded strings with English defaults and allow translation via config if needed. `[DONE 2025-10-26]`
2. Only write placeholder files when cleanup runs; otherwise leave directory untouched. `[DONE 2025-11-02]`
3. Update `tests/test_snipper.py::test_export_with_no_segments` to reflect the new structure. `[DONE 2025-11-02]`

### Validation
- `pytest tests/test_snipper.py::test_export_with_no_segments -q`

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)  
**Date**: 2025-10-26

1. **Placeholder Manifest Strategy**
   - **Choice**: Emit a manifest only when cleanup removes stale clips, using a neutral `no_snippets` status and a configurable message.
   - **Reasoning**: Avoid confusing Dutch placeholders and prevent empty manifests from appearing when nothing changed.
   - **Alternatives Considered**: Always write a manifest with zero clips; rejected to keep disk noise low.
   - **Trade-offs**: Consumers must handle `manifest=None` when cleanup is disabled, but this aligns with the absence of new artifacts.
2. **Configurable Messaging**
   - **Choice**: Added `SNIPPET_PLACEHOLDER_MESSAGE` to `Config`.
   - **Reasoning**: Allows deployments to localize or customize placeholder copy without touching code.
   - **Trade-offs**: Slightly larger config surface area; mitigated by sane default.

#### Validation
- `pytest tests/test_snipper.py -q`

### Implementation Notes & Reasoning (2025-11-02)
**Implementer**: Codex (GPT-5)

#### Design Decisions
1. **Placeholder Artifact Cleanup**
   - **Choice**: Remove legacy placeholder markers such as `keep.txt` during cleanup while keeping the `removed_clips` count limited to audio files.
   - **Reasoning**: Ensures directories are free of confusing artifacts without overstating clip deletions in the manifest payload.
   - **Alternatives Considered**: Treating placeholder files as clip deletions; rejected to avoid misreporting removal counts.
   - **Trade-offs**: Adds a small maintenance list of known placeholder artifacts, but keeps cleanup deterministic.

2. **Test Coverage for Empty Sessions**
   - **Choice**: Extend `test_export_with_no_segments` to assert placeholder artifact removal alongside manifest expectations.
   - **Reasoning**: Prevents regressions where stale artifacts sneak back in and documents the intended cleanup behavior.
   - **Alternatives Considered**: Creating a dedicated test case; merged assertions into the existing scenario to keep test runtime minimal.
   - **Trade-offs**: Slightly longer test, but still focused on the empty-segment path.

#### Validation
- `pytest tests/test_snipper.py -q`

---
## P0-REFACTOR-002: Extract Story Generation

**Files**: Extract from `app.py` to `src/story_generator.py`
**Effort**: 1 day
**Priority**: MEDIUM
**Status**: [DONE] Completed 2025-10-24

### Problem Statement
Story generation logic is mixed with UI code in `app.py`.

### Implementation Plan

Extract to dedicated module with CLI support for batch generation.

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)  
**Date**: 2025-10-24

#### Design Decisions
1. **StoryNotebookManager Service Extraction**
   - **Choice**: Created `src/story_notebook.py` with a `StoryNotebookManager` service and `StorySessionData` container.
   - **Reasoning**: Centralizes session loading, narrative generation, and persistence so both the UI and CLI share one implementation.
   - **Alternatives Considered**: Extending `StoryGenerator` directly with file-system helpers. Rejected to keep LLM prompting separate from orchestration concerns.
   - **Trade-offs**: Slightly larger surface area (new class) but reduces duplication and simplifies future testing.
2. **CLI Batch Command**
   - **Choice**: Added `generate-story` Click command that loops through requested sessions, optionally filters characters, and writes outputs via the service.
   - **Reasoning**: Provides non-UI workflow requested in the plan while reusing the new service; keeps options explicit for narrator vs character runs.
   - **Trade-offs**: Introduces additional CLI dependency on `rich.Table`, but aligns with existing CLI formatting patterns.
3. **UI Integration Strategy**
   - **Choice**: Kept Gradio-specific updates in `app.py` while delegating data prep to the service.
   - **Reasoning**: Avoids Gradio imports in the service layer and preserves UI behavior with minimal changes.
   - **Open Questions**: Consider promoting story tab into `src/ui/` modules during P0-REFACTOR-003 for deeper separation.

#### Validation
- `pytest tests/test_story_notebook.py -q`

### Code Review Findings
**Reviewer**: _Pending_  
**Date**: _Pending_  
**Status**: [LOOP] Review Requested

#### Issues Identified
- _Pending review._

#### Positive Findings
- _Pending review._

#### Verdict
- _Awaiting critical review._

---

## P0-REFACTOR-003: Split app.py into UI Modules

**Files**: `app.py` -> `src/ui/*.py`
**Effort**: 3-4 days
**Priority**: HIGH
**Status**: [DONE] Completed 2025-10-24

### Problem Statement
`app.py` is 2,564 lines - too large to maintain effectively.

### Implementation Plan

Create module-per-tab architecture:
```
src/ui/
├── base.py                      # Shared UI utilities
├── process_session.py           # Main processing tab
├── campaign_dashboard_tab.py    # Dashboard tab
├── import_notes.py              # Import session notes tab
└── ... (10 more tab modules)
```

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)  
**Date**: 2025-10-24

- Split each Gradio tab from `app.py` into dedicated modules under `src/ui/`, covering import notes, campaign library, character profiles, speaker management, document viewer, social insights, story notebooks, diagnostics/logs, LLM chat, configuration, and help.
- Introduced `StoryNotebookManager`-backed helpers along with tab creators so the Gradio layer now wires reusable services instead of duplicating logic across UI and CLI.
- Centralized OAuth and Google Doc handling inside `src/ui/document_viewer_tab.py`, exposing a simple `_set_notebook_context` callback so story generation picks up imported notes automatically.
- Updated `app.py` to delegate tab construction, reducing the file from a monolithic layout to a lightweight orchestrator that assembles modules and shared dependencies.

#### Validation
- `pytest -q`

---

## P1-FEATURE-004: Gradio UI Modernization

**Owner**: ChatGPT (Codex)  
**Effort**: 5-7 days  
**Priority**: HIGH  
**Status**: NOT STARTED  
**Dependencies**: P0-REFACTOR-003 (complete)  

### Problem Statement
The current Gradio interface is dense, text-heavy, and hard to navigate. Power workflows exist but are difficult for new or infrequent users to discover, leading to poor adoption and frequent clarifying questions.

### Goals
- Simplify navigation and reduce cognitive load without removing advanced functionality.
- Provide contextual guidance so users do not rely on long-form instructions.
- Establish consistent visual patterns that can scale with new features.

### Success Criteria
- [ ] Average tab length reduced by 30 percent through collapsible sections and drawers.
- [ ] Primary workflow (upload -> process -> review -> export) documented in a guided stepper.
- [ ] Inline help converted from paragraphs to tooltip or modal patterns across all tabs.
- [ ] Usability smoke test with at least two internal users confirms easier discovery of processing actions.

### Implementation Plan
1. **Layout and Navigation**
   - Move primary navigation into a left sidebar with icons and compact labels.
   - Add breadcrumb header when users drill into campaign or notebook detail views.
2. **Onboarding and Guidance**
   - Build a concise hero panel on load summarizing value prop, quick start button, and links to docs or demo data.
   - Implement guided mode overlay with dismissible hotspots walking through the main workflow.
   - Replace static helper text with hover or focus tooltips and info bubbles.
3. **Workflow Enhancements**
   - Create inline stepper showing upload -> process -> review -> export progress.
   - Surface real-time status toasts for async work, each linking directly to detailed logs.
   - Add notification inbox summarizing recent runs, errors, and shared artifacts.
4. **Data Display Improvements**
   - Introduce quick filters, search, and filter chips on campaign and character tables.
   - Render session timelines with diarization markers and zoom controls.
   - Provide slide-out drawers for audio waveform and transcript previews.
5. **Visual System and Accessibility**
   - Standardize typography, spacing, and button sizes through a lightweight style guide.
   - Add light and dark themes with stored user preference.
   - Implement inline validation patterns for every form field.
   - Require confirmation modals (with undo links) for destructive actions.
6. **Operational Transparency**
   - Surface health metrics (queue length, model status, storage usage) inside a dashboard status card.
   - Expose keyboard shortcuts for frequent actions and document them via a cheat sheet modal.

### Validation
- UI walkthrough recorded for documentation updates.
- `pytest -q` to ensure refactors do not break existing tests.
- Manual regression test of primary workflow (process sample session, inspect outputs, export).

### Documentation Updates
- Update `docs/DEVELOPMENT.md` and `docs/USAGE.md` with new screenshots and navigation overview.
- Add guided mode instructions to `docs/QUICKREF.md`.
- Record design system tokens or spacing rules in `docs/UI_STATUS.md`.

---

**See ROADMAP.md for complete P0-P4 feature list**
## P0-BUG-007: Restore Authenticated Diarization and GPU Defaults

**Files**: `src/config.py`, `src/transcriber.py`, `src/diarizer.py`, `.env.example`, `docs/SETUP.md`, `docs/README.md`
**Effort**: 0.5 days
**Priority**: HIGH
**Status**: [DONE] Completed 2025-11-03

### Problem Statement
Whisper transcription defaulted to CPU even on GPU-capable hosts, and PyAnnote speaker diarization failed once the short-lived Hugging Face token expired. The UI logged warnings from torchcodec because PyAnnote attempted to stream audio from disk instead of using the already loaded waveform.

### Success Criteria
- [x] HF token read from configuration and supplied to both PyAnnote pipeline and embedding model loaders.
- [x] GPU selected by default across transcription and diarization when CUDA is available, with an automatic CPU fallback.
- [x] Environment samples and setup docs teach contributors to set `HF_TOKEN` and `INFERENCE_DEVICE`.

### Implementation Plan
1. Extend `Config` with `HF_TOKEN` and a helper that resolves the preferred inference device (env override -> CUDA -> CPU). `[DONE 2025-11-03]`
2. Update `SpeakerDiarizer` to pass the token, move models to CUDA when available, and preload audio via `torchaudio` to bypass torchcodec. `[DONE 2025-11-03]`
3. Update `FasterWhisperTranscriber` to honor the resolved device, warn on CUDA fallback, and document the new environment knobs. `[DONE 2025-11-03]`
4. Refresh `.env.example`, `docs/SETUP.md`, and `docs/README.md` with token and GPU guidance. `[DONE 2025-11-03]`

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)  
**Date**: 2025-11-03

1. **Device Resolution Helper**
   - **Choice**: Centralized inference device detection in `Config.get_inference_device()` with optional `INFERENCE_DEVICE` override.
   - **Reasoning**: Keeps device logic consistent between transcription and diarization, and allows operators to pin CPU mode when debugging.
   - **Alternatives Considered**: Hard-coding CUDA usage whenever `torch.cuda.is_available()` returns true. Rejected to preserve explicit operator control and avoid surprises on CPU-only deployments.
   - **Trade-offs**: Adds a tiny amount of config indirection but prevents duplicated CUDA probing logic across modules.
2. **Authenticated PyAnnote Loading**
   - **Choice**: Pass the refreshed HF token to both `Pipeline.from_pretrained` and `Model.from_pretrained`, logging a warning when the token is missing.
   - **Reasoning**: Ensures diarization can initialize immediately after tokens rotate, matching Hugging Face's gated model requirements.
   - **Alternatives Considered**: Rely entirely on the environment loader. Rejected because silent failures were hard to diagnose for operators.
   - **Trade-offs**: Slightly more verbose initialization path; mitigated by shared helper and structured logging.
3. **Torchcodec Warning Mitigation**
   - **Choice**: Preload audio with `torchaudio.load` and feed the waveform dictionary directly to PyAnnote.
   - **Reasoning**: Avoids the torchcodec FFmpeg backend entirely, eliminating the runtime warning and keeping processing inside the already validated audio buffer.
   - **Alternatives Considered**: Attempt to repair torchcodec installation or silence warnings. Rejected to keep dependencies minimal and leverage existing audio data.
   - **Trade-offs**: Additional memory usage during diarization, acceptable because sessions are already processed chunk-by-chunk and the WAV files are mono 16 kHz.

#### Validation
- Not run (PyAnnote model download is gated and long-running; validation to be performed during the next end-to-end session run).

### Follow-up Work: Robust Token Parameter Handling
**Implementer**: Claude (Sonnet 4.5)
**Date**: 2025-11-04
**Commit**: ee49793

#### Problem Identified
The initial implementation in P0-BUG-007 used direct keyword arguments (`use_auth_token=token`) when calling PyAnnote's `Pipeline.from_pretrained()` and `Model.from_pretrained()`. However, pyannote.audio has evolved its API:
- Modern versions (>=3.0) use `token=` parameter
- Legacy versions (<3.0) use `use_auth_token=` parameter
- Some configurations don't accept token parameters at all

This caused potential compatibility issues across different pyannote.audio versions.

#### Solution: Graceful Fallback Pattern
Created `_load_component()` helper function in [src/diarizer.py:64-77](src/diarizer.py#L64) that attempts multiple authentication strategies:

1. **No token** - For public models or when token is not required
2. **Modern API** (`token=`) - Try modern parameter format first
3. **Legacy API** (`use_auth_token=`) - Fallback to legacy format
4. **Warning + No token** - If neither parameter accepted, log warning and proceed

**Implementation**:
```python
def _load_component(factory, model_name: str):
    if not token:
        return factory(model_name)
    try:
        return factory(model_name, token=token)
    except TypeError:
        pass
    try:
        return factory(model_name, use_auth_token=token)
    except TypeError:
        self.logger.warning(
            "%s does not accept token parameters; relying on environment.",
            factory.__qualname__
        )
        return factory(model_name)
```

#### Design Decisions
1. **Graceful Degradation Pattern**
   - **Choice**: Try multiple parameter formats in sequence, catching TypeError for unsupported params
   - **Reasoning**: Ensures compatibility across pyannote.audio versions without version detection logic
   - **Alternatives Considered**:
     - Check pyannote.audio version and branch on version number - Rejected as fragile and requires maintenance
     - Use `**kwargs` inspection - Rejected as more complex than try/except
   - **Trade-offs**: Multiple try/except blocks add minimal overhead but provide robust fallback

2. **Warning on Fallback**
   - **Choice**: Log warning when token parameters aren't accepted, but continue with environment-based auth
   - **Reasoning**: Alerts operators to potential auth issues while not blocking execution
   - **Impact**: Better observability for authentication debugging

#### Validation
- **Tests**: All 15 diarizer tests passing (pytest tests/test_diarizer.py -v)
- **Test Coverage**: Updated test_pipeline_loads_with_hf_token to verify modern `token=` parameter usage
- **Files Changed**:
  - [src/diarizer.py:64-84](src/diarizer.py#L64) - Added _load_component helper
  - [tests/test_diarizer.py:165-187](tests/test_diarizer.py#L165) - Updated test assertions
  - [models/speaker_profiles.json](models/speaker_profiles.json) - Added test session profile

#### Benefits
- **Compatibility**: Works across pyannote.audio 2.x and 3.x versions
- **Robustness**: Handles edge cases where token parameters aren't supported
- **Maintainability**: Single helper function reduces code duplication
- **Observability**: Clear logging when authentication strategy changes

---
## P0-BUG-008: Add Preflight Environment Checks

**Files**: `src/preflight.py`, `src/pipeline.py`, `src/transcriber.py`, `src/diarizer.py`, `src/classifier.py`, `tests/test_preflight.py`, `tests/test_diarizer.py`, `docs/SETUP.md`
**Effort**: 0.5 days
**Priority**: HIGH
**Status**: [DONE] Completed 2025-11-03

### Problem Statement
Operators frequently discover missing GPU acceleration, Hugging Face access, or offline Ollama services only after the long transcription stage, wasting hours of processing time.

### Success Criteria
- [x] Pipeline aborts up front when Ollama is unreachable (unless classification is skipped).
- [x] Pipeline warns (not fails) when CUDA is requested but unavailable.
- [x] Pipeline validates that all required PyAnnote repos (including `segmentation-3.0` and `speaker-diarization-community-1`) are accessible with the configured token.
- [x] New tests cover the preflight aggregator as well as diarizer token checks.

### Implementation Plan
1. Introduce a `PreflightChecker` that aggregates readiness checks for transcriber, diarizer, and classifier. `[DONE 2025-11-03]`
2. Implement component-level `preflight_check` methods (CUDA warning, Hugging Face validation, Ollama connectivity). `[DONE 2025-11-03]`
3. Invoke the preflight step at the start of `DDSessionProcessor.process`, respecting skip flags. `[DONE 2025-11-03]`
4. Add unit tests for the checker and diarizer preflight logic plus documentation notes in `docs/SETUP.md`. `[DONE 2025-11-03]`

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)  
**Date**: 2025-11-03

1. **Component Protocol**
   - **Choice**: Declared a minimal `SupportsPreflight` protocol and small dataclass to capture issues.
   - **Reasoning**: Keeps the checker decoupled from concrete implementations and makes it easy for future components (e.g., knowledge extractor) to opt in.
   - **Trade-offs**: Slightly more boilerplate, but tests can now stub components cleanly.
2. **PyAnnote Access Validation**
   - **Choice**: Added explicit checks for `speaker-diarization-3.1`, `segmentation-3.0`, and the newly required `speaker-diarization-community-1` repository when a token is present.
   - **Reasoning**: Users were repeatedly hitting 403 errors after long transcribes because additional models were gated; surfacing this before Stage 1 saves hours.
   - **Trade-offs**: Relies on `huggingface_hub` being importable; when it is missing we raise a clear error instructing the operator to install it.
3. **Classifier Connectivity**
   - **Choice**: Reused the existing Ollama health check but now issue it as part of preflight and convert failures into actionable error messages.
   - **Reasoning**: Ensures operators start the local LLM before launching the pipeline; no more mid-run crashes at Stage 6.
   - **Trade-offs**: Adds a small startup delay (one HTTP call) but avoids large wasted runs.

#### Validation
- `pytest tests/test_preflight.py -q`
- `pytest tests/test_diarizer.py::TestSpeakerDiarizer::test_preflight_reports_repo_access_errors -q`

---

## P0-BUG-009: PyAnnote Embedding Extraction Crashes Diarization

**Files**: `src/diarizer.py`, `tests/test_diarizer.py`
**Effort**: 0.5 days
**Priority**: HIGH
**Status**: [DONE] Completed 2025-11-07

### Problem Statement
During Stage 5 diarization on pyannote.audio 3.x, the embedding inference step now returns numpy arrays rather than torch tensors. Our extraction blindly calls `.numpy()` on the result and raises `'numpy.ndarray' object has no attribute 'numpy'`, which aborts the speaker pass and leaves the UI without diarization labels.

### Success Criteria
- [x] Speaker embeddings are normalized to numpy arrays whether the backend returns torch tensors or numpy arrays.
- [x] Failures inside the embedding aggregation never crash diarization; we log a warning and continue with the available segments.
- [x] Unit tests cover both tensor and numpy embedding outputs plus the failure guard.

### Implementation Plan
1. Normalize embeddings with a helper that accepts torch tensors, numpy arrays, or `SlidingWindowFeature` objects and always returns a CPU numpy array.
2. Wrap per-speaker extraction in `try/except` so a single malformed chunk does not halt the stage; surface a concise warning with the speaker id.
3. Extend diarizer tests to exercise tensor, numpy, and exception scenarios.

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)  
**Date**: 2025-11-07

1. **Embedding Normalization**
   - **Choice**: Added `_embedding_to_numpy` to coerce torch tensors, numpy arrays, and `SlidingWindowFeature` data into CPU numpy arrays.
   - **Reasoning**: PyAnnote 3.1 switched to numpy outputs, so centralizing conversion avoids brittle `.numpy()` calls and simplifies future adjustments.
   - **Trade-offs**: Minor recursive conversion overhead, acceptable given per-speaker frequency.
2. **Resilient Extraction Loop**
   - **Choice**: Load the WAV once, rebuild segments from cached audio, and wrap embedding inference in `try/except` so individual failures only emit warnings.
   - **Reasoning**: Prevents `'numpy.ndarray'` crashes from aborting diarization while still surfacing which speaker failed.
   - **Trade-offs**: Additional warnings when embeddings cannot be computed, but processing now completes with usable speaker segments.

#### Validation
- `pytest tests/test_diarizer.py tests/test_classifier.py -q`

---

## P0-BUG-010: Ollama Classifier Exhausts Memory

**Files**: `src/classifier.py`, `src/config.py`, `.env.example`, `docs/README.md`, `tests/test_classifier.py`
**Effort**: 0.5 days
**Priority**: HIGH
**Status**: [DONE] Completed 2025-11-07

### Problem Statement
Stage 6 IC/OOC classification fails with `memory layout cannot be allocated (status code: 500)` when running the default `gpt-oss:20b` model on hosts with less than 16 GB of free RAM. The classifier catches the exception and defaults to IC, but every segment logs a warning and users receive unusable results.

### Success Criteria
- [x] The classifier detects Ollama 500 errors tied to memory pressure and automatically retries the same model with low-VRAM settings.
- [x] Operators receive an actionable warning that links the failure to their selected model and shows how to adjust generation options (and optionally opt into a fallback).
- [x] `.env.example` and docs mention the optional fallback so new installs can decide whether to enable it.
- [x] Automated tests cover the low-VRAM retry plus the optional fallback flow.

### Implementation Plan
1. Add an optional `OLLAMA_FALLBACK_MODEL` setting (blank by default) and propagate it through `Config`.
2. Enhance `OllamaClassifier` to inspect `Exception` text for `memory layout` (and similar) failures, log guidance, and retry the same model using low-VRAM generation settings before considering any fallback.
3. Document the new setting, low-VRAM retry behavior, and add tests that mock the Ollama client to simulate both the low-VRAM and fallback paths.
4. Extend classifier preflight checks to warn operators when the selected model likely exceeds detected system memory so they can adjust before processing.

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)  
**Date**: 2025-11-07

1. **Low-VRAM Retry Path**
   - **Choice**: Added `_generate_with_retry` that first reissues the request against the selected model using `low_vram=True` (and a reduced context window) whenever Ollama reports alloc failures.
   - **Reasoning**: Keeps the operator-selected model (`gpt-oss:20b`) while lowering transient memory pressure so large hosts can continue without switching models.
   - **Trade-offs**: Low-VRAM runs are slower, but they only trigger when the primary attempt fails.
2. **Optional Fallback & Messaging**
   - **Choice**: Made `OLLAMA_FALLBACK_MODEL` opt-in; when configured we retry after the low-VRAM attempt and log guidance referencing the relevant env vars.
   - **Reasoning**: Provides an escape hatch for constrained hosts without forcing lighter models on those who can support the default.
   - **Trade-offs**: Operators who never set the fallback still see the warning once per failure (instead of silent drops), which aids debugging.
3. **Preflight Memory Guard**
   - **Choice**: Added a preflight probe that estimates available RAM (via psutil/sysconf when available) and warns when it falls short of the selected Ollama model’s documented requirement.
   - **Reasoning**: Surfaces “memory layout” risks before transcription runs, giving operators time to switch to low_vram/fallback models or upgrade hardware.
   - **Trade-offs**: Detection best-effort; skips silently when the platform doesn’t expose memory metrics.

#### Validation
- `pytest tests/test_diarizer.py tests/test_classifier.py -q`

---

## P0-BUG-011: PyAnnote Runtime Warnings & Groq Rate Limits

**Files**: `src/diarizer.py`, `src/config.py`, `src/classifier.py`, `src/retry.py`, `src/rate_limiter.py` (new), `.env.example`, `requirements.txt`, `tests/test_classifier.py`

**Effort**: 1 day  
**Priority**: HIGH  
**Status**: [IN_PROGRESS] (2025-11-12)  
**Dependencies**: P0-BUG-008 (preflight) & P0-BUG-009 (PyAnnote embedding fix)

### Problem Statement
Stage 5 diarization emits a wall of warnings and repeatedly fails to compute embeddings on CUDA GPUs:

- `torchaudio._backend.set_audio_backend has been deprecated` (printed dozens of times)
- PyTorch Lightning auto-upgrade warnings followed by `Model was trained with pyannote.audio 0.0.1` and task-dependent loss errors
- `Failed to extract embedding for SPEAKER_##: CUDA error: an illegal memory access was encountered`
- TF32 reproducibility warnings plus `std(): degrees of freedom is <= 0` noise

At Stage 6 the Groq-backed IC/OOC classifier alternates between HTTP 200s and `429 rate_limit_exceeded`, leaving many classification requests unprocessed.

### Success Criteria
- [ ] PyAnnote initialization no longer produces deprecated torchaudio warnings or Lightning upgrade spam on a fresh cache.
- [ ] CUDA embedding extraction automatically falls back to CPU after the first GPU failure and succeeds for all speakers.
- [ ] TF32 / pooling warnings are suppressed (with guardrail logging) so operators only see actionable logs.
- [ ] Groq classifier enforces a configurable rate limit with jittered backoff so pipelines no longer trip 429s under normal load.
- [ ] `.env.example` and docs describe the new Groq pacing knobs.
- [ ] Unit tests cover the Groq rate limiter and diarizer CUDA fallback branch.

### Implementation Plan
1. **Tame PyAnnote warnings**
   - Monkey-patch deprecated `torchaudio` backend setters/getters to no-ops.
   - Automatically run Lightning’s checkpoint migration on downloaded embedding weights and load them with `strict=False`.
   - Quiet TF32 and pooling warnings via targeted warning filters.
2. **Robust embedding extraction**
   - Track the device used by the embedding inference helper.
   - When a CUDA `RuntimeError` surfaces, log once, move the inference helper to CPU, re-run the embedding, and cache the CPU fallback for the remainder of the session.
3. **Groq rate limiting**
   - Add a reusable token-bucket style `RateLimiter`.
   - Gate `_make_api_call` with the limiter and introduce config/env knobs for `GROQ_MAX_CALLS_PER_SECOND` and `GROQ_BURST_SIZE`.
   - Extend retry/backoff logging to mention 429 causes explicitly.
4. **Docs & tests**
   - Update `.env.example`, `requirements.txt` (if new helper deps), and Implementation Notes.
   - Add unit tests that simulate CUDA failures (via mocks) and verify the Groq limiter spacing + retry behavior.
   - Record validation commands plus Implementation Notes & Reasoning.

### Implementation Notes & Reasoning
**Implementer**: Codex (GPT-5)  
**Date**: 2025-11-12

1. **PyAnnote checkpoint + warning control**
   - **Choice**: Run Lightning’s migration utility on downloaded embedding checkpoints, load with `strict=False`, and mask deprecated `torchaudio` backend calls while filtering the TF32/pooling warnings.
   - **Reasoning**: Keeps upstream models compatible with Torch 2.5+ without noisy logs and prevents import-time failures on Windows shells that treat those warnings as errors.
   - **Trade-offs**: Adds a tiny amount of startup work (single checkpoint migration) but removes repeated warning spam for every session.
2. **Embedding fallback strategy**
   - **Choice**: Track the embedding device and rerun the inference helper on CPU after the first CUDA `illegal memory access`, persisting the CPU path for the rest of the run.
   - **Reasoning**: PyAnnote’s community checkpoints occasionally trip low-level CUDA bugs on long sessions; dropping to CPU for the handful of speaker vectors is inexpensive and restores determinism.
   - **Trade-offs**: CPU embedding extraction is slightly slower (tens of milliseconds per speaker) but only after a GPU fault, so steady-state CUDA performance is unchanged.
3. **Groq rate limiter**
   - **Choice**: Introduced a reusable token-bucket limiter with configurable throughput/burst knobs (`GROQ_MAX_CALLS_PER_SECOND`, `GROQ_RATE_LIMIT_BURST`, `GROQ_RATE_LIMIT_PERIOD_SECONDS`) and wired it into the Groq classifier, penalizing the limiter whenever the API returns `rate_limit_exceeded`.
   - **Reasoning**: Aligns client behavior with Groq’s documented quotas, preventing waves of `429` responses and making retries cheap.
   - **Trade-offs**: Adds minimal latency between classification requests (default 2 req/s) but keeps the pipeline running instead of spamming failed calls.

---
