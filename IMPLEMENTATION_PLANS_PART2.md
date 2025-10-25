# Implementation Plans - Part 2: P1 High Impact Features

> **Planning Mode Document**
> **Created**: 2025-10-22
> **For**: Development Team
> **Source**: ROADMAP.md

This document contains P1 (High Impact) feature implementation plans.

**See IMPLEMENTATION_PLANS.md for**:
- Templates (Implementation Notes & Reasoning, Code Review Findings)
- How to invoke Critical Review
- P0 features and refactoring

---

## Table of Contents

- [P1-FEATURE-001: Automatic Character Profile Extraction](#p1-feature-001-automatic-character-profile-extraction)
- [P1-FEATURE-002: Streaming Snippet Export](#p1-feature-002-streaming-snippet-export)
- [P1-FEATURE-003: Batch Processing](#p1-feature-003-batch-processing)
- [P1-FEATURE-004: Gradio UI Modernization](#p1-feature-004-gradio-ui-modernization)
- [P1-MAINTENANCE-001: Session Cleanup & Validation](#p1-maintenance-001-session-cleanup--validation)

---

# P1: High Impact Features

## P1-FEATURE-001: Automatic Character Profile Extraction

**Files**: `src/character_profile.py`, `src/profile_extractor.py` (new)
**Effort**: 3-5 days
**Priority**: HIGH
**Dependencies**: None
**Status**: NOT STARTED

### Problem Statement
Users manually update character profiles after each session. The system should automatically extract character development data from transcripts and suggest profile updates.

### Success Criteria
- [_] Automatically detects character moments (critical hits, roleplay, character development)
- [_] Extracts quotes with speaker attribution
- [_] Suggests profile updates in UI
- [_] Preserves existing manual edits
- [_] Handles multi-session character arcs

### Implementation Plan

#### Subtask 1.1: Design Profile Update Schema
**Effort**: 4 hours

Design JSON schema for automatic profile updates.

**Schema Example**:
```json
{
  "session_id": "session_001",
  "updates": [
    {
      "character": "Thorin",
      "category": "memorable_moments",
      "type": "critical_hit",
      "content": "Rolled natural 20 on intimidation check",
      "timestamp": "01:23:45",
      "confidence": 0.95,
      "context": "Confronting the goblin chief"
    },
    {
      "character": "Elara",
      "category": "character_development",
      "type": "personality_trait",
      "content": "Showed compassion by sparing enemy",
      "timestamp": "02:15:30",
      "confidence": 0.85,
      "context": "After defeating bandit leader"
    }
  ]
}
```

**Files**: New `schemas/profile_update.json`

#### Subtask 1.2: Create Profile Extractor Module
**Effort**: 1 day

Create module to extract character moments from transcripts.

**Key Components**:
```python
class ProfileExtractor:
    """Extracts character profile updates from transcripts."""

    def __init__(self, llm_client, config):
        self.llm = llm_client
        self.config = config

    def extract_moments(self, transcript: List[Dict]) -> List[ProfileUpdate]:
        """Extract character moments from transcript segments."""
        # Filter IC dialogue only
        # Detect critical hits, roleplay moments, character development
        # Use LLM to classify and extract context
        pass

    def suggest_updates(self, moments: List[ProfileUpdate],
                       existing_profile: CharacterProfile) -> Dict:
        """Generate suggested profile updates."""
        # Compare with existing profile
        # Avoid duplicates
        # Rank by confidence
        pass
```

**Files**: New `src/profile_extractor.py`

#### Subtask 1.3: LLM Prompt Engineering
**Effort**: 1 day

Design prompts for character moment detection and classification.

**Prompt Categories**:
1. **Moment Detection**: Identify significant character moments
2. **Quote Extraction**: Extract memorable quotes with context
3. **Development Analysis**: Analyze character growth/changes
4. **Relationship Tracking**: Detect party dynamics

**Files**: New `prompts/profile_extraction.txt`

#### Subtask 1.4: UI Integration
**Effort**: 1 day

Add "Review Profile Updates" tab to UI.

**Features**:
- Display suggested updates by character
- Show timestamp, context, confidence score
- Accept/Reject buttons for each suggestion
- Bulk approve option
- Preview merged profile

**Files**: `app.py` (new tab), `src/ui/profile_review.py` (new)

#### Subtask 1.5: Merge Logic
**Effort**: 4 hours

Implement safe merge of automatic updates with manual edits.

**Merge Rules**:
- Never overwrite manual edits
- Append to arrays (quotes, moments)
- Deduplicate by content similarity
- Preserve user-added custom fields

**Files**: `src/character_profile.py`

#### Subtask 1.6: Testing
**Effort**: 1 day

Test extraction accuracy and merge safety.

**Test Cases**:
- Extract moments from sample transcript
- Test deduplication logic
- Verify manual edits are preserved
- Test confidence scoring
- Edge cases: Empty profiles, multi-character scenes

**Files**: `tests/test_profile_extraction.py`

### Open Questions
- Should we support retroactive extraction for old sessions?
- How to handle character name variants (nicknames)?
- Confidence threshold for auto-approve?

---

## P1-FEATURE-002: Streaming Snippet Export

**Files**: `src/snipper.py`
**Effort**: 2 days
**Priority**: MEDIUM
**Dependencies**: None
**Status**: NOT STARTED

### Problem Statement
Currently, snippet export happens after full processing completes. For 4-hour sessions, users wait 30+ minutes with no audio output. Streaming export would allow listening to early clips while later sections process.

### Success Criteria
- [_] Clips become available as diarization completes each chunk
- [_] Manifest updates incrementally
- [_] UI shows "Available clips: 15/40" progress
- [_] Safe for concurrent access (pipeline writes, user plays)
- [_] Handles processing failures gracefully

### Implementation Plan

#### Subtask 2.1: Add Incremental Manifest Support
**Effort**: 4 hours

Modify manifest to support incremental updates.

**Schema Changes**:
```json
{
  "session_id": "session_001",
  "status": "in_progress",  // NEW: "in_progress" | "complete" | "failed"
  "total_clips": null,       // NEW: null until complete
  "clips": [
    {
      "id": 1,
      "file": "clip_001.wav",
      "speaker": "Speaker 1",
      "start": 0.0,
      "end": 15.3,
      "status": "ready"       // NEW: "processing" | "ready" | "failed"
    }
  ]
}
```

**Files**: `src/snipper.py`

#### Subtask 2.2: Implement Streaming Export
**Effort**: 1 day

Modify snipper to export clips as chunks complete.

**Code Changes**:
```python
class AudioSnipper:
    def export_incremental(self, chunk_diarization: List[Segment],
                           chunk_index: int):
        """Export clips for a single completed chunk."""
        clips = self._create_clips_from_segments(chunk_diarization)

        for clip in clips:
            self._export_clip(clip)
            self._update_manifest(clip, status="ready")

        self.logger.info(f"Exported {len(clips)} clips for chunk {chunk_index}")
```

**Files**: `src/snipper.py`

#### Subtask 2.3: Thread-Safe Manifest Updates
**Effort**: 4 hours

Ensure manifest can be safely updated from pipeline thread and read from UI.

**Synchronization**:
```python
import threading

class AudioSnipper:
    def __init__(self):
        self._manifest_lock = threading.Lock()

    def _update_manifest(self, clip: Clip, status: str):
        with self._manifest_lock:
            # Read existing manifest
            manifest = self._load_manifest()
            # Append new clip
            manifest["clips"].append(clip.to_dict())
            # Write atomically
            self._save_manifest_atomic(manifest)
```

**Files**: `src/snipper.py`

#### Subtask 2.4: UI Progress Display
**Effort**: 4 hours

Show streaming export progress in UI.

**Features**:
- "Processing clips: 15/40 ready"
- Link to output directory (auto-refresh)
- Play button for ready clips (inline player)

**Files**: `app.py`

#### Subtask 2.5: Testing
**Effort**: 4 hours

Test concurrent access and failure scenarios.

**Test Cases**:
- Concurrent manifest read/write
- Processing failure mid-stream
- Restart from checkpoint (partial clips exist)
- Empty chunk (no speech detected)

**Files**: `tests/test_streaming_export.py`

---

## P1-FEATURE-003: Batch Processing

**Files**: `cli.py`, `src/batch_processor.py`
**Effort**: 1 day
**Priority**: MEDIUM
**Dependencies**: P0-BUG-003 (Checkpoint System)
**Status**: [DONE] Completed (2025-10-24)

### Problem Statement
Users with multiple session recordings must process them one-by-one through the UI. Need CLI support for batch processing with automatic retry and resumption.

### Success Criteria
- [x] CLI accepts directory or file list
- [x] Processes sessions sequentially
- [x] Resumes from checkpoint if session was partially processed
- [x] Generates summary report (successes, failures, time)
- [x] Handles failures gracefully (log and continue)

### Implementation Plan

#### Subtask 3.1: CLI Argument Parsing
**Effort**: 2 hours
**Status**: [DONE]

Add batch processing arguments to CLI.

**Files**: `cli.py`

#### Subtask 3.2: Create Batch Processor Module
**Effort**: 4 hours
**Status**: [DONE]

Implement batch processing logic in `src/batch_processor.py`.

**Files**: `src/batch_processor.py`

#### Subtask 3.3: Summary Report Generation
**Effort**: 2 hours
**Status**: [DONE]

Generate markdown report after batch completes.

**Files**: `src/batch_processor.py`

#### Subtask 3.4: Testing
**Effort**: 2 hours
**Status**: [DONE]

Test batch processing with various scenarios.

**Files**: `tests/test_batch_processor.py`

### Implementation Notes & Reasoning
**Implementer**: Gemini
**Date**: 2025-10-24

#### Design Decisions

1.  **`BatchProcessor` and `BatchReport` Classes**:
    *   **Choice**: Created two distinct classes: `BatchProcessor` to handle the processing logic and `BatchReport` to manage the results and reporting.
    *   **Reasoning**: This separation of concerns makes the code cleaner and more maintainable. `BatchProcessor` focuses on the "how" of processing, while `BatchReport` focuses on the "what" of the results.
2.  **Constructor Alignment with `cli.py`**:
    *   **Choice**: The `BatchProcessor` constructor was designed to align with the arguments already present in the `batch` command in `cli.py`.
    *   **Reasoning**: This ensures that the CLI and the backend module are perfectly in sync, avoiding any mismatches in arguments.
3.  **Use of `DDSessionProcessor`**:
    *   **Choice**: The `BatchProcessor` instantiates and uses the existing `DDSessionProcessor` for each file.
    *   **Reasoning**: This promotes code reuse and ensures that the batch processing uses the same underlying logic as single-file processing.
4.  **Exception Handling**:
    *   **Choice**: Implemented a `try...except` block within the file processing loop.
    *   **Reasoning**: This ensures that if one file fails to process, the entire batch is not aborted. The failure is logged, and the processing continues with the next file.

### Code Review Findings
**Reviewer**: Gemini
**Date**: 2025-10-24
**Status**: [DONE] Approved - Production Ready

#### Issues Identified
None. The implementation follows the plan and the existing code structure. The tests pass.

#### Positive Findings
-   [x] **Clean Implementation**: The code is well-structured and easy to read.
-   [x] **Good Test Coverage**: Basic test cases for success and failure scenarios are implemented.
-   [x] **Adherence to Plan**: The implementation follows the plan outlined in this document.

#### Verdict
**Overall Assessment**: The feature is implemented correctly and is ready for use.
**Merge Recommendation**: [DONE] **Ready for Merge**

---

## P1-FEATURE-004: Gradio UI Modernization

**Owner**: ChatGPT (Codex)  
**Effort**: 5-7 days  
**Priority**: HIGH  
**Dependencies**: P0-REFACTOR-003 (completed modular UI)  
**Status**: NOT STARTED  

### Problem Statement
The current Gradio UI is cluttered, text-heavy, and inconsistent. New users struggle to find core actions, while returning users want faster feedback, richer previews, and shortcuts. We need a cohesive overhaul that simplifies navigation, adds contextual guidance, and improves visual clarity without sacrificing advanced workflows.

### Success Criteria
- [_] Sidebar navigation with icons replaces the long tab bar and improves discoverability (validated in internal walkthrough)
- [_] Hero panel, guided mode overlay, and tooltip pattern reduce reliance on long-form helper text
- [_] Workflow stepper and status toasts cover upload -> process -> review -> export lifecycle
- [_] Inline validation, confirmation modals with undo, and keyboard shortcuts implemented for key flows
- [_] Light/dark themes plus documented design tokens ensure consistent spacing, typography, and components

### Implementation Plan

#### Subtask 4.1: Navigation Refresh
- Implement sidebar navigation with compact labels and tooltips
- Add breadcrumb header when drilling into campaign/session-specific views
- Ensure layout scales down gracefully to 1280px width by collapsing sections

#### Subtask 4.2: Guided Onboarding
- Build hero panel with value proposition, quick-start CTA, and doc/demo links
- Add guided mode overlay with dismissible hotspots covering primary workflow actions
- Replace static helper paragraphs with tooltip/info bubble pattern across tabs

#### Subtask 4.3: Workflow Feedback
- Introduce inline workflow stepper highlighting upload, process, review, export stages
- Emit toast notifications for async tasks (processing, errors, successes) with “View log” shortcut
- Add notification inbox summarizing recent runs, errors, and shared artifacts

#### Subtask 4.4: Data Presentation Enhancements
- Add search, quick filters, and chips to campaign and character tables
- Render session timelines with diarization markers, zoom, and speaker hover states
- Use slide-out drawers for waveform and transcript previews to cut tab hopping

#### Subtask 4.5: Visual System and Accessibility
- Define spacing, typography, and button tokens; document in `docs/UI_STATUS.md`
- Add light/dark themes with preference persistence
- Implement inline validation, confirmation modals with undo, and keyboard shortcut cheat sheet
- Surface health metrics (queue length, model status, storage usage) in dashboard card

#### Subtask 4.6: Documentation and QA
- Record UI walkthrough for onboarding and changelog
- Update `docs/DEVELOPMENT.md`, `docs/USAGE.md`, and `docs/QUICKREF.md`
- Add guided mode overview to `docs/STATUS_INDICATORS.md` or relevant doc
- Run `pytest -q` and manual regression through sample campaign workflow

### Open Questions
- Should we introduce per-user settings storage to sync theme/shortcuts across browsers?
- Do we need to support tablet portrait mode for in-session note takers?
- What telemetry do we need to measure improved discoverability post-launch?

### Risks & Mitigations
- **Risk**: Major layout changes may disorient existing users  
  **Mitigation**: Provide changelog banner, offer temporary “classic view”, capture feedback via in-app survey
- **Risk**: Increased interactivity could slow load times  
  **Mitigation**: Lazy-load heavy components, profile Gradio Blocks, cache expensive lookups
- **Risk**: Additional notifications might overwhelm users  
  **Mitigation**: Aggregate messages into inbox with filters and allow user preference toggles

### Validation
- `pytest -q`
- Manual regression of upload -> process -> review -> export workflow
- Internal usability session notes stored in `docs/UI_STATUS.md`

---

## P1-MAINTENANCE-001: Session Cleanup & Validation

**Files**: `src/session_manager.py` (new), CLI command
**Effort**: 2-3 days
**Priority**: MEDIUM
**Dependencies**: None
**Status**: NOT STARTED

### Problem Statement
Over time, the `outputs/` directory accumulates:
- Orphaned sessions (no source audio)
- Incomplete sessions (processing failed)
- Stale checkpoints (>7 days old)
- Duplicate outputs (same source processed multiple times)

Users need tools to audit and clean up their session data.

### Success Criteria
- [_] CLI command to audit sessions (`cli.py sessions audit`)
- [_] Identify orphaned, incomplete, and stale sessions
- [_] Interactive cleanup (prompt before deleting)
- [_] Dry-run mode (show what would be deleted)
- [_] Generate cleanup report

### Implementation Plan

#### Subtask 4.1: Create Session Manager Module
**Effort**: 1 day

Build module to scan and analyze session outputs.

**Code Example**:
```python
class SessionManager:
    """Manage session lifecycle and cleanup."""

    def __init__(self, output_dir: Path, checkpoint_dir: Path):
        self.output_dir = output_dir
        self.checkpoint_dir = checkpoint_dir

    def audit_sessions(self) -> AuditReport:
        """Scan all sessions and identify issues."""
        sessions = self._discover_sessions()

        report = AuditReport()
        for session in sessions:
            if self._is_orphaned(session):
                report.orphaned.append(session)
            elif self._is_incomplete(session):
                report.incomplete.append(session)
            elif self._has_stale_checkpoint(session):
                report.stale_checkpoints.append(session)

        return report

    def _is_incomplete(self, session: Session) -> bool:
        """Check if session has all expected outputs."""
        required_files = [
            "transcript.json",
            "diarized_transcript.json",
            "snippets/manifest.json"
        ]
        return not all((session.path / f).exists() for f in required_files)
```

**Files**: New `src/session_manager.py`

#### Subtask 4.2: Add CLI Commands
**Effort**: 4 hours

Add session management commands to CLI.

**Commands**:
```bash
# Audit sessions (read-only)
python cli.py sessions audit

# Cleanup with confirmation
python cli.py sessions cleanup --interactive

# Cleanup dry-run
python cli.py sessions cleanup --dry-run

# Force cleanup (no prompts)
python cli.py sessions cleanup --force
```

**Files**: `cli.py`

#### Subtask 4.3: Interactive Cleanup
**Effort**: 4 hours

Implement safe interactive cleanup.

**User Flow**:
```
Found 3 orphaned sessions:
  1. session_old_001 (250 MB, created 2025-09-15)
  2. session_old_002 (180 MB, created 2025-09-12)
  3. test_session (50 MB, created 2025-10-01)

Delete orphaned sessions? [y/N]: y
Deleted session_old_001 (freed 250 MB)
Deleted session_old_002 (freed 180 MB)
Deleted test_session (freed 50 MB)

Found 2 stale checkpoints (>7 days):
  1. session_003.checkpoint (created 2025-09-01)
  2. session_007.checkpoint (created 2025-08-20)

Delete stale checkpoints? [y/N]: y
Deleted 2 checkpoints (freed 15 MB)
```

**Files**: `src/session_manager.py`

#### Subtask 4.4: Cleanup Report
**Effort**: 2 hours

Generate markdown report after cleanup.

**Report Example**:
```markdown
# Session Cleanup Report
**Date**: 2025-10-22 15:30:00

## Summary
- **Total Sessions Scanned**: 25
- **Orphaned Sessions**: 3 (480 MB)
- **Incomplete Sessions**: 2 (120 MB)
- **Stale Checkpoints**: 2 (15 MB)
- **Total Space Freed**: 615 MB

## Actions Taken
- Deleted 3 orphaned sessions
- Kept 2 incomplete sessions (user declined)
- Deleted 2 stale checkpoints
```

**Files**: `src/session_manager.py`

#### Subtask 4.5: Testing
**Effort**: 4 hours

Test audit and cleanup logic.

**Test Cases**:
- Empty output directory
- All sessions valid (no issues)
- Orphaned sessions (no source audio found)
- Incomplete sessions (missing required files)
- Stale checkpoints (>7 days old)
- Dry-run mode (verify no files deleted)

**Files**: `tests/test_session_manager.py`

---

**See IMPLEMENTATION_PLANS.md for templates and P0 features**
**See IMPLEMENTATION_PLANS_PART3.md for P2 LangChain Integration**
**See IMPLEMENTATION_PLANS_SUMMARY.md for effort estimates and sprint planning**
