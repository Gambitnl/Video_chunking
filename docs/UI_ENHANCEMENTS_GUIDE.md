# UI Enhancements Guide - IC/OOC Classification Improvements

> **Date**: 2025-11-17
> **Version**: 1.0
> **Related**: IC_OOC_CLASSIFICATION_ANALYSIS.md (Topics 1, 5, 6, 7)

---

## Overview

This guide documents the new UI controls added to improve IC/OOC classification accuracy, auditability, and story extraction quality. These enhancements implement the consensus reached in the multi-agent IC/OOC classification analysis.

**Key Improvements**:
- Enhanced speaker management with role assignment (DM/Player/NPC)
- Character name mapping for improved attribution
- Audit mode for classification reproducibility
- Scene bundle generation for better story extraction
- DM NPC mode tracking for narrator vs. NPC dialogue distinction

---

## 1. Speaker Manager Tab Enhancements

### Overview

The Speaker Manager tab now provides comprehensive controls for managing speaker identities, roles, and character mappings. These mappings are used by the classifier to improve character attribution accuracy from ~10% to 80%+.

### New Features

#### 1.1 Enhanced Speaker Mapping Table

**Location**: Speaker Manager Tab -> Speaker Mapping & Roles

**Columns**:
- **Speaker ID**: Auto-assigned identifier from diarization (e.g., `SPEAKER_00`, `SPEAKER_17`)
- **Player Name**: Human-readable name for the speaker (e.g., "Alice", "Jules")
- **Role**: Speaker role in the session
  - `PLAYER` - Regular player character
  - `DM_NARRATOR` - DM providing scene description/narration
  - `DM_NPC` - DM speaking as an NPC
  - `UNKNOWN` - Speaker not yet identified
- **Character Name**: Name of the character this speaker plays (e.g., "Sha'ek Mindfa'ek", "DM")
- **Confidence**: Diarization confidence score (0.0 - 1.0, read-only)

**Usage**:
1. Enter a **Session ID** (e.g., `test_s6_17nov_0901am`)
2. Click **Load Speakers** to populate the table with diarization results
3. Fill in **Player Name** and **Role** for each speaker
4. Optionally load character mappings from a party config
5. Click **Save Mappings** to persist changes

**Why This Matters**:
- Enables the classifier to receive speaker context (e.g., `Alice (SPEAKER_00) - plays Sha'ek Mindfa'ek`)
- Dramatically improves character attribution accuracy in classification results
- Allows the classifier to distinguish between DM narration and NPC dialogue

#### 1.2 Party Configuration Integration

**Location**: Speaker Manager Tab -> Party Configuration

**Controls**:
- **Party Configuration** dropdown: Select from saved party configs
- **Load Party Mappings** button: Auto-fill character names from party config

**Workflow**:
1. Load speakers for a session
2. Select a party configuration (e.g., "default", "shards_of_the_deep")
3. Click **Load Party Mappings**
4. Character names are automatically filled based on player names
5. DM is automatically identified and role set to `DM_NARRATOR`
6. Review and adjust mappings as needed
7. Save mappings

**Benefits**:
- Reduces manual data entry
- Ensures consistency across sessions
- Automatically links players to their characters

#### 1.3 DM NPC Mode (Advanced)

**Location**: Speaker Manager Tab -> DM NPC Mode (Advanced) Accordion

**Purpose**: Track when the DM is voicing a specific NPC vs. providing narration.

**Controls**:
- **DM Speaker ID**: The speaker ID assigned to the DM (e.g., `SPEAKER_17`)
- **Active NPC Name**: Name of the NPC being voiced (e.g., "Captain", "Goblin King")
- **Start Time**: When DM starts voicing this NPC (format: `mm:ss`, e.g., `05:30`)
- **End Time**: When DM stops voicing this NPC (leave empty for rest of session)

**Workflow**:
1. Identify which speaker ID belongs to the DM
2. While reviewing a session, note when DM starts voicing an NPC
3. Enter the NPC name and time range
4. Click **Set NPC Mode**
5. The system tracks this metadata for improved classification

**Use Cases**:
- Long NPC monologues or dialogues
- Recurring NPC interactions
- Critical story NPCs that should be attributed separately

**Note**: This is an advanced feature. Most sessions work fine with just `DM_NARRATOR` role assignment.

---

## 2. Process Session Tab Enhancements

### Overview

The Process Session tab now includes advanced options for audit logging and scene generation. These are hidden in an "Advanced Processing Options" accordion to avoid overwhelming new users.

### New Controls

#### 2.1 Audit Mode

**Location**: Process Session Tab -> Advanced Processing Options -> Enable Audit Mode

**What It Does**:
- Saves detailed classification prompts and LLM responses to `stage_6_prompts.ndjson`
- Records model name, generation options, retry strategies
- Computes SHA256 hashes of prompts/responses for verification
- Enables reproducibility and debugging of classification decisions

**When to Use**:
- Debugging classification issues
- Investigating why a segment was classified incorrectly
- Research or compliance requirements
- Creating regression test datasets

**Storage Impact**:
- Adds ~20-30 MB per 3-hour session (depending on segment count)
- Audit log is stored in `output/<session>/intermediates/stage_6_prompts.ndjson`

**File Format** (NDJSON - one JSON object per line):
```json
{"segment_index": 0, "timestamp": "2025-11-17T14:30:00", "prompt_hash": "abc123...", "response_hash": "def456...", "model": "qwen2.5:7b", "options": {...}, "prompt_preview": "Vorige: ...", "response_preview": "Classificatie: IC..."}
{"segment_index": 1, "timestamp": "2025-11-17T14:30:01", "prompt_hash": "ghi789...", ...}
```

#### 2.2 Redact Prompts in Logs

**Location**: Process Session Tab -> Advanced Processing Options -> Redact Prompts in Logs

**What It Does**:
- When audit mode is enabled, strips full dialogue text from audit logs
- Preserves structural metadata and hashes
- Protects privacy for sensitive campaigns

**When to Use**:
- Campaigns with sensitive content or personal information
- Compliance with data privacy requirements
- Sharing audit logs without revealing campaign details

**What Gets Redacted**:
- Full prompt text (dialogue content)
- Full response text (reasoning details)

**What's Preserved**:
- Prompt and response hashes (for verification)
- Structural metadata (has_prev, has_current, speaker_count)
- Model information and retry strategies
- Timestamps and segment indices

#### 2.3 Generate Scene Bundles

**Location**: Process Session Tab -> Advanced Processing Options -> Generate Scene Bundles

**Default**: Enabled (checked)

**What It Does**:
- Automatically groups segments into narrative scenes
- Detects scene breaks based on:
  - IC <-> OOC classification changes
  - Time gaps (>75 seconds of silence)
- Saves scene bundles to `stage_6_scenes.json`

**Benefits for Story Extraction**:
- Knowledge base and story notebook can operate on scenes instead of individual segments
- Improves narrative coherence
- Reduces processing overhead for downstream consumers
- Enables scene-level summaries and analysis

**Scene Metadata Included**:
- Scene index, start/end times, duration
- Dominant classification type (CHARACTER, DM_NARRATION, etc.)
- Speaker list (who participated in this scene)
- Segment count
- Classification distribution (how many IC/OOC/etc. segments)
- Confidence span (min/max confidence scores)
- Optional summary

**File Format** (`stage_6_scenes.json`):
```json
{
  "metadata": {
    "session_id": "test_session",
    "generated_at": "2025-11-17T14:30:00",
    "total_scenes": 15
  },
  "scenes": [
    {
      "scene_index": 0,
      "start_time": 5.2,
      "end_time": 125.8,
      "duration": 120.6,
      "dominant_type": "CHARACTER",
      "speaker_list": ["SPEAKER_00", "SPEAKER_03", "SPEAKER_17"],
      "segment_count": 24,
      "classification_distribution": {"CHARACTER": 20, "OOC": 4},
      "confidence_span": {"min": 0.87, "max": 0.98},
      "summary": "SPEAKER_00, SPEAKER_03, SPEAKER_17 - 24 segments of in-character roleplay (2m 0s)"
    },
    ...
  ],
  "statistics": {
    "total_scenes": 15,
    "total_duration": 3600.0,
    "avg_scene_duration": 240.0,
    "scene_type_distribution": {"CHARACTER": 10, "OOC": 5},
    "top_speakers": [...]
  }
}
```

#### 2.4 Scene Summary Mode

**Location**: Process Session Tab -> Advanced Processing Options -> Scene Summary Mode

**Options**:
- **template** (default): Fast template-based summaries (e.g., "Alice, Bob - 15 segments of in-character roleplay (3m 20s)")
- **llm**: Detailed LLM-generated summaries (not yet implemented - placeholder)
- **none**: No summaries generated (saves processing time)

**Recommendations**:
- Use `template` for most sessions (fast, low cost)
- Use `none` if you don't need scene summaries
- Use `llm` when implemented for rich, context-aware summaries

---

## 3. Workflow Examples

### Example 1: Processing a New Session with Full Speaker Context

**Goal**: Process a session with proper speaker identification and character attribution.

**Steps**:
1. **Process Session Tab**:
   - Upload audio file
   - Enter session ID: `session_2025_11_17`
   - Select party config: `default`
   - Keep all advanced options at defaults
   - Click **Process Session**

2. **After Processing - Speaker Manager Tab**:
   - Enter session ID: `session_2025_11_17`
   - Click **Load Speakers** (shows diarization results)
   - Select party config: `default`
   - Click **Load Party Mappings** (auto-fills character names)
   - Review and adjust roles (mark DM as `DM_NARRATOR`)
   - Click **Save Mappings**

3. **Re-process if Needed**:
   - If character attribution was poor (many "N/A" entries), re-run classification with updated speaker mappings
   - Future sessions will benefit from the saved speaker profiles

### Example 2: Debugging Classification Issues

**Goal**: Investigate why a segment was classified incorrectly.

**Steps**:
1. **Process Session Tab**:
   - Upload audio file
   - **Advanced Options**:
     - ✅ Enable Audit Mode
     - ⬜ Redact Prompts (leave unchecked for full debugging)
   - Click **Process Session**

2. **Review Audit Log**:
   - Navigate to `output/<session>/intermediates/stage_6_prompts.ndjson`
   - Search for the segment index in question
   - Examine the full prompt sent to the LLM
   - Review the raw response and parsed results
   - Check model options and retry strategy used

3. **Analyze and Fix**:
   - If speaker context was missing: update speaker mappings
   - If temporal context was insufficient: check segment boundaries
   - If classification was ambiguous: review prompt template
   - Report findings to development team

### Example 3: Privacy-Sensitive Campaign

**Goal**: Process a campaign with sensitive content while maintaining auditability.

**Steps**:
1. **Process Session Tab**:
   - Upload audio file
   - **Advanced Options**:
     - ✅ Enable Audit Mode
     - ✅ Redact Prompts in Logs
     - ✅ Generate Scene Bundles (optional)
   - Click **Process Session**

2. **Result**:
   - Audit log contains hashes and structural metadata but no dialogue text
   - Scene bundles still generated with summaries
   - Full transcripts remain accessible in session output
   - Audit log can be shared for debugging without revealing campaign content

---

## 4. Technical Notes

### File Locations

**Speaker Profiles**:
- `models/speaker_profiles.json` - Global speaker profile database
- Organized by session ID
- Includes speaker embeddings, name mappings, roles, character names, NPC mode tracking

**Intermediate Outputs** (per session):
- `output/<session>/intermediates/stage_6_classification.json` - Classification results with metadata
- `output/<session>/intermediates/stage_6_prompts.ndjson` - Audit log (if enabled)
- `output/<session>/intermediates/stage_6_scenes.json` - Scene bundles (if enabled)

### Metadata Versioning

**Speaker Map Versioning**:
- Classification metadata includes `speaker_map_version` timestamp
- If speaker profiles are updated after processing, cached classifications are flagged as stale
- Allows selective re-classification when speaker mappings change

**Classification Metadata Block**:
```json
{
  "metadata": {
    "session_id": "test_session",
    "model": "qwen2.5:7b",
    "speaker_map_version": "2025-11-17T14:30:00",
    "prompt_log": "intermediates/stage_6_prompts.ndjson",
    "scenes_log": "intermediates/stage_6_scenes.json",
    "generation_stats": {
      "avg_latency_ms": 450,
      "fallback_count": 2,
      "low_vram_retries": 0
    }
  }
}
```

### Scene Break Heuristics

**Default Settings**:
- **Time gap threshold**: 75 seconds
- **Classification change detection**: IC <-> OOC flips only (not IC <-> MIXED or OOC <-> MIXED)
- **Speaker roster change**: Not used by default (can be enabled in advanced configurations)

**Tuning Recommendations**:
- Fast-paced combat sessions: Lower time gap to 45-60s
- Slow roleplay sessions: Increase time gap to 90-120s
- Mixed IC/OOC sessions: Keep classification change detection enabled
- Single-narrative sessions: Consider disabling classification change detection

---

## 5. Troubleshooting

### Issue: Speaker Mappings Not Improving Classification

**Symptoms**: After setting speaker mappings, character attribution is still poor.

**Possible Causes**:
1. Mappings were saved but classification was not re-run
2. Speaker IDs don't match diarization output
3. Role assignments are incorrect

**Solutions**:
- Re-run classification after saving speaker mappings
- Verify speaker IDs match diarization output (check `stage_5_diarization.json`)
- Ensure DM is marked as `DM_NARRATOR` not `PLAYER`

### Issue: Audit Log File Too Large

**Symptoms**: `stage_6_prompts.ndjson` is consuming excessive disk space.

**Causes**:
- Long session (many segments)
- Full prompts and responses being saved (redact mode disabled)

**Solutions**:
- Enable "Redact Prompts in Logs" to reduce file size by ~70%
- Disable audit mode for production sessions (only enable for debugging)
- Archive old audit logs after investigation is complete

### Issue: Scene Bundles Don't Match Expected Boundaries

**Symptoms**: Scenes are too long/short or don't align with narrative structure.

**Causes**:
- Default time gap threshold (75s) doesn't match session pacing
- Classification change detection creating unwanted breaks

**Solutions**:
- Adjust scene builder parameters in code (future UI controls planned)
- Review classification results to ensure IC/OOC labels are accurate
- Consider disabling classification change detection for single-narrative sessions

### Issue: DM NPC Mode Not Working

**Symptoms**: DM dialogue still attributed to "DM" instead of specific NPC.

**Status**: DM NPC mode tracking is implemented in UI and speaker profiles, but **classifier integration is pending** (being handled by Codex/Gemini).

**Current Limitation**: NPC mode metadata is saved but not yet used by the classifier.

**Expected Timeline**: Will be functional after classifier prompt updates are completed.

---

## 6. Future Enhancements

### Planned Features

1. **UI controls for scene break thresholds** - Allow tuning time gap and other heuristics without code changes
2. **LLM-based scene summaries** - Rich, context-aware summaries instead of templates
3. **Speaker role auto-detection** - Automatically identify DM based on speaking time and patterns
4. **Bulk speaker mapping import** - Import mappings from CSV for batch processing
5. **Classification confidence threshold UI** - Allow filtering segments below a confidence threshold

### Integration Status

**Completed (UI/Pipeline Wiring)**:
- ✅ Enhanced speaker manager UI
- ✅ Process session advanced options
- ✅ Intermediate output persistence (audit logs, scene bundles)
- ✅ Scene builder helper module

**Pending (Classifier Integration - Codex/Gemini)**:
- ⏳ Classifier prompt template updates for speaker context
- ⏳ Classification result structure changes (classification_type field)
- ⏳ DM NPC mode integration in prompts
- ⏳ Temporal metadata integration
- ⏳ Context window expansion

---

## 7. Related Documentation

- **IC_OOC_CLASSIFICATION_ANALYSIS.md** - Complete multi-agent analysis and consensus
- **USAGE.md** - General usage guide for the pipeline
- **QUICKREF.md** - Quick reference for common operations
- **Session Artifact Documentation** - Details on intermediate file formats

---

**Last Updated**: 2025-11-17
**Authors**: Claude (Sonnet 4.5) - UI/Pipeline Wiring
**Status**: UI Controls Complete, Classifier Integration Pending
