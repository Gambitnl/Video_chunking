# Implementation Plans - VideoChunking Project

> **Planning Mode Document**
> **Created**: 2025-10-22
> **For**: Development Team
> **Source**: ROADMAP.md

This document provides detailed implementation plans for each roadmap item, broken down into actionable subtasks.

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

**See ROADMAP.md for complete P0-P4 feature list**
