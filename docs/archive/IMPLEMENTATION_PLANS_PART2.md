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

**Files**: `cli.py`, `src/batch_processor.py` (new)
**Effort**: 1 day
**Priority**: MEDIUM
**Dependencies**: P0-BUG-003 (Checkpoint System)
**Status**: NOT STARTED

### Problem Statement
Users with multiple session recordings must process them one-by-one through the UI. Need CLI support for batch processing with automatic retry and resumption.

### Success Criteria
- [_] CLI accepts directory or file list
- [_] Processes sessions sequentially
- [_] Resumes from checkpoint if session was partially processed
- [_] Generates summary report (successes, failures, time)
- [_] Handles failures gracefully (log and continue)

### Implementation Plan

#### Subtask 3.1: CLI Argument Parsing
**Effort**: 2 hours

Add batch processing arguments to CLI.

**Example Usage**:
```bash
# Process all audio files in directory
python cli.py batch --input-dir ./recordings --output-dir ./processed

# Process specific files
python cli.py batch --files session1.m4a session2.mp3

# With options
python cli.py batch --input-dir ./recordings --resume --parallel 2
```

**Arguments**:
- `--input-dir`: Directory containing audio files
- `--files`: Explicit file list
- `--output-dir`: Where to save outputs
- `--resume`: Resume from checkpoints if they exist
- `--parallel`: Number of sessions to process in parallel (default: 1)

**Files**: `cli.py`

#### Subtask 3.2: Create Batch Processor Module
**Effort**: 4 hours

Implement batch processing logic.

**Code Example**:
```python
class BatchProcessor:
    """Process multiple sessions with retry and resumption."""

    def __init__(self, pipeline: Pipeline, config: Config):
        self.pipeline = pipeline
        self.config = config
        self.results = []

    def process_batch(self, files: List[Path], resume: bool = True) -> BatchReport:
        """Process multiple files sequentially."""
        for file in files:
            try:
                # Check for existing checkpoint
                if resume and self._has_checkpoint(file):
                    self.logger.info(f"Resuming {file.name}")

                result = self.pipeline.process(file)
                self.results.append({"file": file, "status": "success",
                                    "duration": result.duration})

            except Exception as exc:
                self.logger.error(f"Failed to process {file}: {exc}")
                self.results.append({"file": file, "status": "failed",
                                    "error": str(exc)})

        return self._generate_report()
```

**Files**: New `src/batch_processor.py`

#### Subtask 3.3: Summary Report Generation
**Effort**: 2 hours

Generate markdown report after batch completes.

**Report Example**:
```markdown
# Batch Processing Report
**Started**: 2025-10-22 14:30:00
**Completed**: 2025-10-22 16:45:00
**Total Time**: 2h 15m

## Summary
- **Total Sessions**: 10
- **Successful**: 8
- **Failed**: 2
- **Resumed from Checkpoint**: 3

## Details

### Successful (8)
| Session | Duration | Processing Time | Output |
|---------|----------|----------------|--------|
| session_001.m4a | 3h 15m | 45m | outputs/session_001/ |

### Failed (2)
| Session | Error |
|---------|-------|
| session_005.m4a | FileNotFoundError: HF_TOKEN not set |
```

**Files**: `src/batch_processor.py`

#### Subtask 3.4: Testing
**Effort**: 2 hours

Test batch processing with various scenarios.

**Test Cases**:
- Empty directory
- Mixed file formats (M4A, MP3, WAV)
- Some files have checkpoints, some don't
- Processing failure mid-batch (verify continues)
- Invalid audio files

**Files**: `tests/test_batch_processor.py`

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
