# Refactor Candidate #7: Replace Magic Strings and Numbers with Enums and Constants

## Problem Statement

Throughout the codebase, there are numerous hard-coded strings and magic numbers, particularly for classification types ("IC", "OOC", "MIXED"), status indicators, and processing stages. This leads to typo-prone code, lack of IDE autocomplete, and difficulties in refactoring.

## Current State Analysis

### Locations

Multiple files throughout the codebase contain magic strings:

1. **Classification Strings** (`classifier.py`, `formatter.py`, `pipeline.py`)
   - `"IC"`, `"OOC"`, `"MIXED"`
   - Used in comparisons, assignments, and string formatting
   - Risk of typos: `"ic"` vs `"IC"` vs `"In-Character"`

2. **Status Strings** (`status_tracker.py`, `pipeline.py`, `checkpoint.py`)
   - `"running"`, `"completed"`, `"failed"`, `"skipped"`, `"pending"`
   - Stage status tracking
   - Processing status

3. **Stage Names** (`pipeline.py`, `checkpoint.py`)
   - `"audio_converted"`, `"audio_chunked"`, `"audio_transcribed"`
   - Used for checkpoint keys and logging

4. **File Format Strings** (`formatter.py`)
   - `"full"`, `"ic_only"`, `"ooc_only"`, `"json"`, `"srt_full"`
   - Output file naming

5. **Speaker IDs** (`diarizer.py`, `formatter.py`)
   - `"UNKNOWN"`, `"SPEAKER_00"`, etc.
   - Default speaker labels

### Example Issues

```python
# classifier.py:18
classification: str  # "IC", "OOC", or "MIXED"  <-- String in comment, not enforced

# classifier.py:414
if class_text in ["IC", "OOC", "MIXED"]:  <-- List of strings, typo-prone
    classification = class_text

# pipeline.py:282
completed_stages.add("audio_converted")  <-- String literal, could typo

# status_tracker.py
status: "running"  <-- Magic string

# formatter.py:103
if classif.classification == "OOC":  <-- String comparison
    continue
```

### Issues

1. **Typo Risk**: Easy to mistype strings
2. **No Autocomplete**: IDE can't suggest valid values
3. **No Type Checking**: Python can't catch invalid values
4. **Hard to Refactor**: Renaming requires find-and-replace
5. **Documentation Gap**: Valid values not clear
6. **Case Sensitivity**: "IC" vs "ic" bugs
7. **Magic Numbers**: Hard-coded values like `0.5` for default confidence

## Proposed Solution

### Design Overview

Create enums and constants for all magic strings and numbers:

```python
# src/constants.py - New file for all constants

from enum import Enum, auto


class Classification(str, Enum):
    """
    Segment classification types.

    Using str enum allows direct string comparison while providing type safety.
    """
    IN_CHARACTER = "IC"
    OUT_OF_CHARACTER = "OOC"
    MIXED = "MIXED"

    def __str__(self) -> str:
        """Return the string value for backward compatibility"""
        return self.value

    @property
    def display_name(self) -> str:
        """Get human-readable display name"""
        names = {
            Classification.IN_CHARACTER: "In-Character",
            Classification.OUT_OF_CHARACTER: "Out-of-Character",
            Classification.MIXED: "Mixed",
        }
        return names[self]


class ProcessingStatus(str, Enum):
    """Status of a processing stage or session"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal status (no more changes expected)"""
        return self in (
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.SKIPPED
        )


class PipelineStage(str, Enum):
    """Pipeline processing stages"""
    AUDIO_CONVERTED = "audio_converted"
    AUDIO_CHUNKED = "audio_chunked"
    AUDIO_TRANSCRIBED = "audio_transcribed"
    TRANSCRIPTION_MERGED = "transcription_merged"
    SPEAKER_DIARIZED = "speaker_diarized"
    SEGMENTS_CLASSIFIED = "segments_classified"
    OUTPUTS_GENERATED = "outputs_generated"
    AUDIO_SEGMENTS_EXPORTED = "audio_segments_exported"
    KNOWLEDGE_EXTRACTED = "knowledge_extracted"

    def __str__(self) -> str:
        return self.value

    @property
    def number(self) -> int:
        """Get stage number (1-9)"""
        stages = list(PipelineStage)
        return stages.index(self) + 1

    @property
    def display_name(self) -> str:
        """Get human-readable stage name"""
        names = {
            PipelineStage.AUDIO_CONVERTED: "Audio Conversion",
            PipelineStage.AUDIO_CHUNKED: "Audio Chunking",
            PipelineStage.AUDIO_TRANSCRIBED: "Transcription",
            PipelineStage.TRANSCRIPTION_MERGED: "Transcript Merging",
            PipelineStage.SPEAKER_DIARIZED: "Speaker Diarization",
            PipelineStage.SEGMENTS_CLASSIFIED: "IC/OOC Classification",
            PipelineStage.OUTPUTS_GENERATED: "Output Generation",
            PipelineStage.AUDIO_SEGMENTS_EXPORTED: "Audio Segment Export",
            PipelineStage.KNOWLEDGE_EXTRACTED: "Knowledge Extraction",
        }
        return names[self]


class OutputFormat(str, Enum):
    """Output file format types"""
    FULL = "full"
    IC_ONLY = "ic_only"
    OOC_ONLY = "ooc_only"
    JSON = "json"
    SRT_FULL = "srt_full"
    SRT_IC = "srt_ic"
    SRT_OOC = "srt_ooc"

    def __str__(self) -> str:
        return self.value

    def get_file_extension(self) -> str:
        """Get file extension for this format"""
        if self in (OutputFormat.JSON,):
            return "json"
        elif self.value.startswith("srt_"):
            return "srt"
        else:
            return "txt"


class SpeakerLabel:
    """Constants for speaker labels"""
    UNKNOWN = "UNKNOWN"
    DEFAULT_PREFIX = "SPEAKER_"

    @staticmethod
    def is_generic_label(speaker_id: str) -> bool:
        """Check if speaker ID is a generic label (not mapped to person)"""
        return speaker_id == SpeakerLabel.UNKNOWN or \
               speaker_id.startswith(SpeakerLabel.DEFAULT_PREFIX)

    @staticmethod
    def format_speaker_number(num: int) -> str:
        """Format speaker number as SPEAKER_XX"""
        return f"{SpeakerLabel.DEFAULT_PREFIX}{num:02d}"


class ConfidenceDefaults:
    """Default confidence values"""
    DEFAULT = 0.5
    HIGH = 0.9
    LOW = 0.3
    MINIMUM = 0.0
    MAXIMUM = 1.0

    @staticmethod
    def clamp(value: float) -> float:
        """Clamp confidence value to valid range"""
        return max(
            ConfidenceDefaults.MINIMUM,
            min(ConfidenceDefaults.MAXIMUM, value)
        )


class TimeConstants:
    """Time-related constants"""
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    MILLISECONDS_PER_SECOND = 1000

    @staticmethod
    def seconds_to_hms(seconds: float) -> tuple[int, int, int]:
        """Convert seconds to (hours, minutes, seconds)"""
        hours = int(seconds // TimeConstants.SECONDS_PER_HOUR)
        remaining = seconds % TimeConstants.SECONDS_PER_HOUR
        minutes = int(remaining // TimeConstants.SECONDS_PER_MINUTE)
        secs = int(remaining % TimeConstants.SECONDS_PER_MINUTE)
        return hours, minutes, secs
```

## Implementation Plan

### Phase 1: Create Constants Module (Low Risk)
**Duration**: 2-3 hours

1. **Create `src/constants.py`**
   - Add all enum definitions
   - Add all constant classes
   - Add helper methods
   - Add comprehensive docstrings

2. **Add unit tests**
   ```python
   # tests/test_constants.py
   def test_classification_enum():
       """Test Classification enum"""
       assert Classification.IN_CHARACTER.value == "IC"
       assert str(Classification.IN_CHARACTER) == "IC"
       assert Classification.IN_CHARACTER.display_name == "In-Character"

   def test_processing_status_is_terminal():
       """Test terminal status detection"""
       assert ProcessingStatus.COMPLETED.is_terminal()
       assert ProcessingStatus.FAILED.is_terminal()
       assert not ProcessingStatus.RUNNING.is_terminal()

   def test_pipeline_stage_number():
       """Test stage numbering"""
       assert PipelineStage.AUDIO_CONVERTED.number == 1
       assert PipelineStage.KNOWLEDGE_EXTRACTED.number == 9

   def test_speaker_label_is_generic():
       """Test generic speaker label detection"""
       assert SpeakerLabel.is_generic_label("UNKNOWN")
       assert SpeakerLabel.is_generic_label("SPEAKER_00")
       assert not SpeakerLabel.is_generic_label("Alice")

   def test_confidence_defaults_clamp():
       """Test confidence clamping"""
       assert ConfidenceDefaults.clamp(-0.5) == 0.0
       assert ConfidenceDefaults.clamp(1.5) == 1.0
       assert ConfidenceDefaults.clamp(0.7) == 0.7
   ```

### Phase 2: Update classifier.py (Medium Risk)
**Duration**: 2-3 hours

1. **Replace classification strings**
   ```python
   # OLD
   @dataclass
   class ClassificationResult:
       classification: str  # "IC", "OOC", or "MIXED"

   # NEW
   from src.constants import Classification

   @dataclass
   class ClassificationResult:
       classification: Classification
       # ... other fields

   # OLD
   if class_text in ["IC", "OOC", "MIXED"]:
       classification = class_text

   # NEW
   try:
       classification = Classification(class_text)
   except ValueError:
       self.logger.warning("Invalid classification: %s", class_text)
       classification = Classification.IN_CHARACTER

   # OLD
   if classif.classification == "IC":
       ...

   # NEW
   if classif.classification == Classification.IN_CHARACTER:
       ...
   ```

2. **Update tests**
   - Update all string comparisons
   - Test enum usage

### Phase 3: Update formatter.py (Medium Risk)
**Duration**: 2 hours

1. **Replace format strings**
   ```python
   # OLD
   if classif.classification == "OOC":
       continue

   # NEW
   if classif.classification == Classification.OUT_OF_CHARACTER:
       continue

   # OLD
   return {
       'full': output_dir / f"{session_name}_full.txt",
       'ic_only': output_dir / f"{session_name}_ic_only.txt",
       ...
   }

   # NEW
   return {
       OutputFormat.FULL: output_dir / f"{session_name}_full.txt",
       OutputFormat.IC_ONLY: output_dir / f"{session_name}_ic_only.txt",
       ...
   }
   ```

2. **Update tests**

### Phase 4: Update pipeline.py (High Risk - Most Changes)
**Duration**: 4-5 hours

1. **Replace stage strings**
   ```python
   # OLD
   completed_stages.add("audio_converted")
   if "audio_transcribed" in completed_stages:
       ...

   # NEW
   completed_stages.add(PipelineStage.AUDIO_CONVERTED)
   if PipelineStage.AUDIO_TRANSCRIBED in completed_stages:
       ...
   ```

2. **Update checkpoint keys**
   ```python
   # OLD
   self.checkpoint_manager.save("audio_converted", {...})

   # NEW
   self.checkpoint_manager.save(PipelineStage.AUDIO_CONVERTED, {...})
   ```

3. **Update status tracker calls**
   ```python
   # OLD
   StatusTracker.update_stage(self.session_id, 1, "running", "message")

   # NEW
   StatusTracker.update_stage(
       self.session_id,
       PipelineStage.AUDIO_CONVERTED.number,
       ProcessingStatus.RUNNING,
       "message"
   )
   ```

4. **Extensive testing required**

### Phase 5: Update Other Files (Medium Risk)
**Duration**: 3-4 hours

1. **Update `status_tracker.py`**
   - Use `ProcessingStatus` enum
   - Use `PipelineStage` enum

2. **Update `checkpoint.py`**
   - Accept enum keys
   - Convert to string for serialization

3. **Update `diarizer.py`**
   - Use `SpeakerLabel` constants

4. **Update UI files**
   - Update status indicators
   - Update display strings

### Phase 6: Testing (High Priority)
**Duration**: 4-5 hours

1. **Unit tests for all changes**
2. **Integration tests**
3. **Regression tests**
   - Ensure output files unchanged
   - Ensure behavior identical

### Phase 7: Documentation (Low Risk)
**Duration**: 2 hours

1. **Update documentation**
   - Document all enums
   - Add migration guide
   - Update code examples

2. **Update type hints**
   - Ensure all type hints use enums

## Testing Strategy

### Unit Tests

```python
class TestConstantsUsage(unittest.TestCase):
    """Test that constants are used correctly throughout codebase"""

    def test_classification_in_classifier(self):
        """Test Classification enum usage in classifier"""
        result = ClassificationResult(
            segment_index=0,
            classification=Classification.IN_CHARACTER,
            confidence=0.9,
            reasoning="Test"
        )
        assert result.classification == Classification.IN_CHARACTER

    def test_pipeline_stage_in_checkpoint(self):
        """Test PipelineStage enum in checkpoint manager"""
        manager = CheckpointManager("test", Path("test"))
        manager.save(PipelineStage.AUDIO_CONVERTED, {"data": "test"})
        # Verify it was saved correctly

    def test_processing_status_in_tracker(self):
        """Test ProcessingStatus enum in status tracker"""
        StatusTracker.update_stage(
            "test_session",
            1,
            ProcessingStatus.RUNNING,
            "test message"
        )
        # Verify status was set correctly
```

### Integration Tests

```python
@pytest.mark.integration
def test_full_pipeline_with_enums():
    """Test complete pipeline using enums"""
    processor = DDSessionProcessor(...)
    result = processor.process(...)

    # Verify classifications are enums
    assert all(
        isinstance(c.classification, Classification)
        for c in result['classifications']
    )

@pytest.mark.integration
def test_output_files_use_enum_keys():
    """Test that output files dict uses enum keys"""
    formatter = TranscriptFormatter()
    outputs = formatter.save_all_formats(...)

    assert OutputFormat.FULL in outputs
    assert OutputFormat.IC_ONLY in outputs
    assert OutputFormat.JSON in outputs
```

### Backward Compatibility Tests

```python
def test_enum_string_comparison():
    """Test that enums work in string comparisons"""
    classification = Classification.IN_CHARACTER

    # Should work with direct string comparison
    assert classification == "IC"
    assert str(classification) == "IC"

def test_checkpoint_deserialize_old_format():
    """Test loading old checkpoints with string keys"""
    # Old checkpoint uses string "audio_converted"
    old_checkpoint = {"stage": "audio_converted", "data": {...}}

    # Should still load correctly
    stage = PipelineStage(old_checkpoint["stage"])
    assert stage == PipelineStage.AUDIO_CONVERTED
```

## Risks and Mitigation

### Risk 1: Breaking Serialization
**Likelihood**: High
**Impact**: High
**Mitigation**:
- Use string enums (inheriting from str)
- Enums serialize as strings automatically
- Test checkpoint loading with old data
- Add migration path for old checkpoints

### Risk 2: String Comparison Failures
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Use `str` enum so comparisons work: `Classification.IC == "IC"`
- Add explicit `__str__()` methods
- Comprehensive tests for all comparison types
- Document enum usage

### Risk 3: Dictionary Key Issues
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Enums can be dict keys
- Test dict operations with enum keys
- Document serialization behavior
- Use `.value` for JSON serialization

### Risk 4: UI Display Issues
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Add `display_name` properties to enums
- Test UI rendering
- Update UI templates/components
- Document display conventions

## Expected Benefits

### Immediate Benefits
1. **Type Safety**: IDE catches invalid values
2. **Autocomplete**: IDE suggests valid options
3. **Refactoring**: Easy to rename enum values
4. **Documentation**: Enums self-document valid values
5. **Fewer Bugs**: Typos caught at development time

### Long-term Benefits
1. **Maintainability**: Clear intent for all constants
2. **Extensibility**: Easy to add new enum values
3. **Testing**: Easier to test all possible values
4. **Code Quality**: More professional, maintainable code
5. **Onboarding**: New developers understand valid values

### Code Quality Metrics
- **Type Coverage**: Increase from ~70% to ~90%
- **Magic Strings**: Reduce from ~100 to ~5 occurrences
- **IDE Warnings**: Eliminate string literal warnings
- **Documentation**: Self-documenting through enums

## Migration Path

### Backward Compatibility

1. **String Enums**: Use `str` as base class for automatic string conversion
   ```python
   class Classification(str, Enum):
       IN_CHARACTER = "IC"
   ```

2. **Serialization**: Enums serialize as strings automatically
   ```python
   json.dumps({"classification": Classification.IN_CHARACTER})
   # Output: '{"classification": "IC"}'
   ```

3. **Comparisons**: String comparisons still work
   ```python
   Classification.IN_CHARACTER == "IC"  # True
   ```

### Gradual Rollout

1. **Phase 1**: Add enums, don't enforce (current phase)
2. **Phase 2**: Use enums in new code, old code uses strings
3. **Phase 3**: Migrate existing code file-by-file
4. **Phase 4**: Deprecate string usage (future)

## Success Criteria

1. ✅ `constants.py` created with all enums
2. ✅ All classification strings replaced with `Classification` enum
3. ✅ All status strings replaced with `ProcessingStatus` enum
4. ✅ All stage strings replaced with `PipelineStage` enum
5. ✅ All output format strings replaced with `OutputFormat` enum
6. ✅ All tests passing (100% regression)
7. ✅ No serialization issues with enums
8. ✅ IDE autocomplete works for all enums
9. ✅ Documentation updated
10. ✅ Code review approved

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Create Constants | 2-3 hours | None |
| Phase 2: Update classifier.py | 2-3 hours | Phase 1 |
| Phase 3: Update formatter.py | 2 hours | Phase 1 |
| Phase 4: Update pipeline.py | 4-5 hours | Phase 1 |
| Phase 5: Update Other Files | 3-4 hours | Phase 1 |
| Phase 6: Testing | 4-5 hours | Phases 2-5 |
| Phase 7: Documentation | 2 hours | Phase 6 |
| **Total** | **19-24 hours** | |

## References

- Current usage: Multiple files throughout codebase
- Python enum documentation: https://docs.python.org/3/library/enum.html
- String enums: https://docs.python.org/3/library/enum.html#others
- Design pattern: Replace Magic Numbers with Symbolic Constants
- Related: Clean Code Chapter 17 (Smells and Heuristics)
