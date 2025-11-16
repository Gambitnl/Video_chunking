# Intermediate Outputs Complete Guide

## Overview

The intermediate output system allows you to save and resume processing from specific pipeline stages, enabling:
- **Manual intervention** between stages
- **Debugging** individual pipeline components
- **Iterative refinement** of outputs
- **Cost savings** by avoiding re-running expensive stages

---

## Quick Start

### 1. Enable Intermediate Outputs

**Via UI:**
1. Open the app: `python app.py`
2. Go to **Settings & Tools** tab
3. Expand **Processing Settings**
4. Check ☑ **"Save Intermediate Stage Outputs"**
5. Click **"Save Processing Settings"**

**Via Configuration:**
Add to `.env`:
```bash
SAVE_INTERMEDIATE_OUTPUTS=true
```

### 2. Process a Session

Process any session normally through the UI. Intermediate outputs will be automatically saved to:
```
output/{session_id}/intermediates/
├── stage_4_merged_transcript.json
├── stage_5_diarization.json
└── stage_6_classification.json
```

### 3. Resume from Intermediate Output

**Using CLI (Recommended - Fully Implemented):**
```bash
# Resume from diarization (Stage 5)
python process_from_intermediate.py \
  --session-dir output/20251115_120000_my_session \
  --from-stage 5 \
  --party-id default \
  --campaign-id broken_seekers

# Show all options
python process_from_intermediate.py --help
```

---

## Stage Reference

| Stage | Name | Contains | Next Steps |
|-------|------|----------|------------|
| **4** | Merged Transcript | Raw transcript after overlap removal | → Diarization → Classification → Outputs |
| **5** | Diarization | Transcript with speaker labels | → Classification → Outputs |
| **6** | Classification | IC/OOC classified segments | → Regenerate Outputs |

---

## CLI Reference

### Basic Usage

```bash
python process_from_intermediate.py \
  --session-dir <path_to_session> \
  --from-stage <4|5|6>
```

### All Options

```bash
--session-dir PATH        Path to session output directory (required)
--from-stage {4,5,6}      Stage to resume from (required)
--skip-diarization        Skip speaker diarization
--skip-classification     Skip IC/OOC classification
--skip-snippets          Skip audio segment export
--skip-knowledge         Skip knowledge extraction
--party-id ID            Party configuration to use
--campaign-id ID         Campaign identifier
--log-level LEVEL        Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Examples

**Resume from merged transcript:**
```bash
python process_from_intermediate.py \
  --session-dir output/20251115_120000_session \
  --from-stage 4 \
  --party-id my_party \
  --campaign-id my_campaign
```

**Regenerate outputs only:**
```bash
python process_from_intermediate.py \
  --session-dir output/20251115_120000_session \
  --from-stage 6 \
  --skip-snippets \
  --skip-knowledge
```

**Debug mode:**
```bash
python process_from_intermediate.py \
  --session-dir output/20251115_120000_session \
  --from-stage 5 \
  --log-level DEBUG
```

---

## File Format Reference

### Stage 4: Merged Transcript

**File:** `stage_4_merged_transcript.json`

```json
{
  "metadata": {
    "session_id": "my_session",
    "stage": "merged_transcript",
    "stage_number": 4,
    "timestamp": "2025-11-15T12:00:00Z",
    "input_file": "session.mp4",
    "version": "1.0"
  },
  "segments": [
    {
      "text": "Welcome adventurers!",
      "start_time": 0.0,
      "end_time": 2.5,
      "confidence": 0.95,
      "words": [
        {"word": "Welcome", "start": 0.0, "end": 0.5}
      ]
    }
  ],
  "statistics": {
    "total_segments": 150,
    "total_duration": 3600.0
  }
}
```

### Stage 5: Diarization

**File:** `stage_5_diarization.json`

```json
{
  "metadata": { ... },
  "segments": [
    {
      "text": "Welcome adventurers!",
      "start_time": 0.0,
      "end_time": 2.5,
      "speaker": "SPEAKER_00",
      "confidence": 0.88,
      "words": [...]
    }
  ],
  "statistics": {
    "unique_speakers": 4,
    "speaker_time": {
      "SPEAKER_00": 1200.0,
      "SPEAKER_01": 800.0
    },
    "total_segments": 150
  }
}
```

### Stage 6: Classification

**File:** `stage_6_classification.json`

Each segment keeps its `segment_index` so resume flows and downstream tooling can rebuild classifier state exactly as it was produced.

```json
{
  "metadata": { ... },
  "segments": [
    {
      "segment_index": 0,
      "text": "Welcome adventurers!",
      "start_time": 0.0,
      "end_time": 2.5,
      "speaker": "SPEAKER_00",
      "classification": "IC",
      "confidence": 0.92,
      "reasoning": "DM opening the session",
      "character": null
    }
  ],
  "statistics": {
    "total_segments": 150,
    "ic_count": 120,
    "ooc_count": 25,
    "mixed_count": 5,
    "ic_percentage": 80.0
  }
}
```

---

## Use Cases

### 1. Manual Editing Workflow

**Scenario:** You want to manually correct speaker labels before classification.

**Steps:**
1. Process session normally (saves all intermediate outputs)
2. Edit `stage_5_diarization.json` manually
   - Fix speaker labels
   - Merge or split segments
   - Update speaker names
3. Resume from Stage 5:
   ```bash
   python process_from_intermediate.py \
     --session-dir output/20251115_120000_session \
     --from-stage 5
   ```

### 2. Testing Classification Models

**Scenario:** You want to test different LLM backends for classification.

**Steps:**
1. Process session up to diarization (saves Stage 5 output)
2. Change LLM backend in `.env`:
   ```bash
   LLM_BACKEND=ollama  # Test with Ollama
   ```
3. Resume from Stage 5:
   ```bash
   python process_from_intermediate.py \
     --session-dir output/20251115_120000_session \
     --from-stage 5
   ```
4. Compare results
5. Change backend again and repeat

### 3. Regenerating Outputs

**Scenario:** You want to regenerate transcript outputs with different formatting.

**Steps:**
1. Modify output formatting code
2. Resume from Stage 6 (just regenerates outputs):
   ```bash
   python process_from_intermediate.py \
     --session-dir output/20251115_120000_session \
     --from-stage 6
   ```

### 4. Cost-Effective Development

**Scenario:** You're developing/testing knowledge extraction but don't want to re-run expensive transcription.

**Steps:**
1. Process one session fully (saves all intermediate outputs)
2. Modify knowledge extraction code
3. Resume from Stage 6 repeatedly:
   ```bash
   python process_from_intermediate.py \
     --session-dir output/20251115_120000_session \
     --from-stage 6
   ```

---

## Programmatic Usage

You can also use the intermediate output system programmatically:

### Python Example

```python
from pathlib import Path
from src.intermediate_output import IntermediateOutputManager
from src.pipeline import DDSessionProcessor

# Load intermediate outputs
session_dir = Path("output/20251115_120000_session")
manager = IntermediateOutputManager(session_dir)

# Load diarization output
speaker_segments = manager.load_diarization()

# Process from that point
processor = DDSessionProcessor(
    session_id="my_session",
    party_id="default",
)

result = processor.process_from_intermediate(
    session_dir=session_dir,
    from_stage=5,
    skip_snippets=True,
)

print(f"Success: {result['success']}")
print(f"IC Percentage: {result['statistics']['ic_percentage']:.1f}%")
```

---

## Troubleshooting

### Issue: "Intermediate output not found"

**Solution:** Make sure `SAVE_INTERMEDIATE_OUTPUTS=true` was enabled when you processed the session.

### Issue: "No WAV file found"

**Solution:** When resuming from Stage 4, the WAV file is needed for diarization. Make sure the `.wav` file is in the session directory.

### Issue: "Invalid stage number"

**Solution:** Only stages 4, 5, and 6 support resume. You cannot resume from stages 1-3.

---

## Implementation Details

### Architecture

```
IntermediateOutputManager
├── save_merged_transcript()    → stage_4_merged_transcript.json
├── save_diarization()          → stage_5_diarization.json
├── save_classification()       → stage_6_classification.json
├── load_merged_transcript()    ← Parse JSON, create TranscriptionSegment objects
├── load_diarization()          ← Parse JSON, return segment dicts
└── load_classification()       ← Parse JSON, return segments + classifications

DDSessionProcessor
└── process_from_intermediate() → Load outputs, run remaining stages
```

### Test Coverage

**16 unit tests** covering:
- Save/load for each stage
- Roundtrip data integrity
- Error handling
- Validation
- Metadata correctness

Run tests:
```bash
pytest tests/test_intermediate_output.py -v
```

---

## Future Enhancements

### Planned Features

1. **UI Resume Controls** (In Progress)
   - Session selector dropdown
   - Stage selection
   - One-click resume

2. **Diff Viewer**
   - Compare intermediate outputs between runs
   - Highlight changes in speaker labels or classifications

3. **Batch Resume**
   - Resume multiple sessions at once
   - Bulk regeneration of outputs

4. **Intermediate Output Validation**
   - Schema validation
   - Data integrity checks
   - Warning for corrupted outputs

---

## Configuration Reference

### Environment Variables

```bash
# Enable/disable intermediate output saving (default: true)
SAVE_INTERMEDIATE_OUTPUTS=true

# Output directory (default: output/)
OUTPUT_DIR=output
```

### Config Object

```python
from src.config import Config

# Check if intermediate outputs are enabled
if Config.SAVE_INTERMEDIATE_OUTPUTS:
    print("Intermediate outputs will be saved")

# Get output directory
print(f"Outputs saved to: {Config.OUTPUT_DIR}")
```

---

## Support

For issues or questions:
1. Check the logs: `logs/session_processor_YYYYMMDD.log`
2. Run with debug logging: `--log-level DEBUG`
3. Verify intermediate outputs exist: `ls output/{session_id}/intermediates/`
4. Check file integrity: Validate JSON structure

---

## Changelog

### Version 1.0 (2025-11-15)
- ✅ Initial implementation
- ✅ Save/load for stages 4, 5, 6
- ✅ CLI tool (`process_from_intermediate.py`)
- ✅ UI toggle in Settings
- ✅ 16 unit tests
- ✅ Complete documentation
- ⏳ UI resume controls (in progress)
