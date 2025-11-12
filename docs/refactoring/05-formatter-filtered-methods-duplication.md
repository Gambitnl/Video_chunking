# Refactor Candidate #5: Consolidate Similar Formatting Methods in formatter.py

## Problem Statement

The `format_ic_only()` and `format_ooc_only()` methods in `TranscriptFormatter` (lines 84-119 and 121-153) have nearly identical implementations. The only difference is the filter condition (`classification == "IC"` vs `classification == "OOC"`). This code duplication violates DRY principles and creates maintenance overhead.

## Current State Analysis

### Location
- **File**: `src/formatter.py`
- **Class**: `TranscriptFormatter`
- **Duplicate Methods**:
  - `format_ic_only()` (lines 84-119)
  - `format_ooc_only()` (lines 121-153)
- **Lines of Duplication**: ~35 lines per method = 70 total lines

### Current Code Structure

```python
class TranscriptFormatter:
    def format_ic_only(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None
    ) -> str:
        """Format IC-only transcript (game narrative only)."""
        lines = []
        lines.append("=" * 80)
        lines.append("D&D SESSION TRANSCRIPT - IN-CHARACTER ONLY")
        lines.append("=" * 80)
        lines.append("")

        for seg, classif in zip(segments, classifications):
            # Skip OOC content
            if classif.classification == "OOC":  # <-- Only difference
                continue

            timestamp = self.format_timestamp(seg['start_time'])
            speaker = seg.get('speaker', 'UNKNOWN')

            if speaker_profiles and speaker in speaker_profiles:
                speaker = speaker_profiles[speaker]

            display_name = classif.character or speaker
            line = f"[{timestamp}] {display_name}: {seg['text']}"
            lines.append(line)

        return "\n".join(lines)

    def format_ooc_only(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None
    ) -> str:
        """Format OOC-only transcript (banter and meta-discussion)."""
        lines = []
        lines.append("=" * 80)
        lines.append("D&D SESSION TRANSCRIPT - OUT-OF-CHARACTER ONLY")
        lines.append("=" * 80)
        lines.append("")

        for seg, classif in zip(segments, classifications):
            # Skip IC content
            if classif.classification == "IC":  # <-- Only difference
                continue

            timestamp = self.format_timestamp(seg['start_time'])
            speaker = seg.get('speaker', 'UNKNOWN')

            if speaker_profiles and speaker in speaker_profiles:
                speaker = speaker_profiles[speaker]

            line = f"[{timestamp}] {speaker}: {seg['text']}"
            lines.append(line)

        return "\n".join(lines)
```

### Issues

1. **Code Duplication**: ~70 lines of nearly identical code
2. **Maintenance Burden**: Bug fixes must be applied twice
3. **Inconsistency Risk**: Methods could diverge over time
4. **Testing Overhead**: Same logic tested multiple times
5. **Limited Extensibility**: Hard to add new filter types (e.g., "MIXED")
6. **Hard-coded Headers**: Header text duplicated and hard-coded

## Proposed Solution

### Design Overview

Create a single `format_filtered()` method that accepts a filter strategy. This enables:
- Single implementation for all filter types
- Easy addition of new filter types
- Consistent formatting across all variants
- Better testing (test once, works for all)

### New Architecture

```python
from enum import Enum
from typing import Callable, Optional, List, Dict

class TranscriptFilter(Enum):
    """Filter types for transcript formatting"""
    ALL = "all"
    IC_ONLY = "ic_only"
    OOC_ONLY = "ooc_only"
    MIXED_ONLY = "mixed_only"

    def get_title(self) -> str:
        """Get human-readable title for this filter"""
        titles = {
            TranscriptFilter.ALL: "FULL VERSION",
            TranscriptFilter.IC_ONLY: "IN-CHARACTER ONLY",
            TranscriptFilter.OOC_ONLY: "OUT-OF-CHARACTER ONLY",
            TranscriptFilter.MIXED_ONLY: "MIXED SEGMENTS ONLY",
        }
        return titles[self]

    def should_include(self, classification: str) -> bool:
        """Determine if a segment should be included"""
        if self == TranscriptFilter.ALL:
            return True
        elif self == TranscriptFilter.IC_ONLY:
            return classification == "IC"
        elif self == TranscriptFilter.OOC_ONLY:
            return classification == "OOC"
        elif self == TranscriptFilter.MIXED_ONLY:
            return classification == "MIXED"
        return False


class TranscriptFormatter:
    """
    Formats transcription results into various output formats.

    Supports:
    1. Plain text with speaker labels and timestamps
    2. Filtered transcripts (IC-only, OOC-only, etc.)
    3. Full JSON with all metadata
    4. SRT subtitle format
    """

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """Format seconds as HH:MM:SS"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def format_filtered(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        filter_type: TranscriptFilter = TranscriptFilter.ALL,
        speaker_profiles: Optional[Dict[str, str]] = None,
        include_classification_marker: bool = False,
        use_character_names: bool = True,
    ) -> str:
        """
        Format transcript with optional filtering.

        Args:
            segments: Transcribed and diarized segments
            classifications: IC/OOC classifications
            filter_type: Which segments to include
            speaker_profiles: Optional speaker ID to name mapping
            include_classification_marker: Whether to show (IC/OOC) markers
            use_character_names: Whether to show character names for IC segments

        Returns:
            Formatted transcript string
        """
        lines = []

        # Add header
        lines.append("=" * 80)
        lines.append(f"D&D SESSION TRANSCRIPT - {filter_type.get_title()}")
        lines.append("=" * 80)
        lines.append("")

        # Format segments
        for seg, classif in zip(segments, classifications):
            # Apply filter
            if not filter_type.should_include(classif.classification):
                continue

            # Format timestamp
            timestamp = self.format_timestamp(seg['start_time'])

            # Resolve speaker name
            speaker = seg.get('speaker', 'UNKNOWN')
            if speaker_profiles and speaker in speaker_profiles:
                speaker = speaker_profiles[speaker]

            # Determine display name
            if use_character_names and classif.character and classif.classification == "IC":
                # Show character name for IC segments
                if filter_type == TranscriptFilter.ALL:
                    # For full transcript, show "Player as Character"
                    display_name = f"{speaker} as {classif.character}"
                else:
                    # For IC-only, just show character name
                    display_name = classif.character
            else:
                display_name = speaker

            # Add classification marker if requested
            marker = ""
            if include_classification_marker:
                marker = f" ({classif.classification})"

            # Build line
            line = f"[{timestamp}] {display_name}{marker}: {seg['text']}"
            lines.append(line)

        return "\n".join(lines)

    def format_full_transcript(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Format complete transcript with all information.

        Format:
        [HH:MM:SS] Speaker (IC/OOC): Text
        [HH:MM:SS] Speaker as Character (IC): Text
        """
        return self.format_filtered(
            segments,
            classifications,
            filter_type=TranscriptFilter.ALL,
            speaker_profiles=speaker_profiles,
            include_classification_marker=True,
            use_character_names=True,
        )

    def format_ic_only(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Format IC-only transcript (game narrative only).

        Format shows characters and DM narration, removes OOC banter.
        """
        return self.format_filtered(
            segments,
            classifications,
            filter_type=TranscriptFilter.IC_ONLY,
            speaker_profiles=speaker_profiles,
            include_classification_marker=False,
            use_character_names=True,
        )

    def format_ooc_only(
        self,
        segments: List[Dict],
        classifications: List[ClassificationResult],
        speaker_profiles: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Format OOC-only transcript (banter and meta-discussion).

        Useful for remembering jokes or strategy discussions.
        """
        return self.format_filtered(
            segments,
            classifications,
            filter_type=TranscriptFilter.OOC_ONLY,
            speaker_profiles=speaker_profiles,
            include_classification_marker=False,
            use_character_names=False,
        )

    # ... rest of methods unchanged
```

## Implementation Plan

### Phase 1: Create Infrastructure (Low Risk)
**Duration**: 2 hours

1. **Create `TranscriptFilter` enum**
   - Add all filter types
   - Implement `get_title()` method
   - Implement `should_include()` method

2. **Add unit tests for enum**
   ```python
   def test_transcript_filter_should_include_ic_only():
       filter_type = TranscriptFilter.IC_ONLY
       assert filter_type.should_include("IC") is True
       assert filter_type.should_include("OOC") is False
       assert filter_type.should_include("MIXED") is False

   def test_transcript_filter_should_include_all():
       filter_type = TranscriptFilter.ALL
       assert filter_type.should_include("IC") is True
       assert filter_type.should_include("OOC") is True
       assert filter_type.should_include("MIXED") is True

   def test_transcript_filter_get_title():
       assert "IN-CHARACTER" in TranscriptFilter.IC_ONLY.get_title()
       assert "OUT-OF-CHARACTER" in TranscriptFilter.OOC_ONLY.get_title()
   ```

### Phase 2: Implement `format_filtered()` (Medium Risk)
**Duration**: 3-4 hours

1. **Create method**
   - Extract common logic from existing methods
   - Add parameters for customization
   - Handle all filter types
   - Add comprehensive docstring

2. **Add unit tests**
   ```python
   class TestTranscriptFormatterFiltered(unittest.TestCase):
       def setUp(self):
           self.formatter = TranscriptFormatter()
           self.segments = [
               {'text': 'IC text', 'speaker': 'S1', 'start_time': 0, 'end_time': 1},
               {'text': 'OOC text', 'speaker': 'S2', 'start_time': 1, 'end_time': 2},
           ]
           self.classifications = [
               ClassificationResult(0, "IC", 0.9, "IC reasoning", "Hero"),
               ClassificationResult(1, "OOC", 0.8, "OOC reasoning", None),
           ]

       def test_format_filtered_all(self):
           result = self.formatter.format_filtered(
               self.segments,
               self.classifications,
               TranscriptFilter.ALL
           )
           assert "IC text" in result
           assert "OOC text" in result

       def test_format_filtered_ic_only(self):
           result = self.formatter.format_filtered(
               self.segments,
               self.classifications,
               TranscriptFilter.IC_ONLY
           )
           assert "IC text" in result
           assert "OOC text" not in result

       def test_format_filtered_ooc_only(self):
           result = self.formatter.format_filtered(
               self.segments,
               self.classifications,
               TranscriptFilter.OOC_ONLY
           )
           assert "IC text" not in result
           assert "OOC text" in result

       def test_format_filtered_with_character_names(self):
           result = self.formatter.format_filtered(
               self.segments,
               self.classifications,
               TranscriptFilter.IC_ONLY,
               use_character_names=True
           )
           assert "Hero" in result  # Character name shown

       def test_format_filtered_with_classification_markers(self):
           result = self.formatter.format_filtered(
               self.segments,
               self.classifications,
               TranscriptFilter.ALL,
               include_classification_marker=True
           )
           assert "(IC)" in result
           assert "(OOC)" in result

       def test_format_filtered_with_speaker_profiles(self):
           profiles = {'S1': 'Alice', 'S2': 'Bob'}
           result = self.formatter.format_filtered(
               self.segments,
               self.classifications,
               TranscriptFilter.OOC_ONLY,
               speaker_profiles=profiles
           )
           assert "Bob" in result  # Mapped name shown
   ```

### Phase 3: Refactor Existing Methods (Low Risk)
**Duration**: 1-2 hours

1. **Update `format_full_transcript()`**
   - Call `format_filtered()` with appropriate parameters
   - Keep same public API
   - Add deprecation notice if needed

2. **Update `format_ic_only()`**
   - Call `format_filtered()` with `TranscriptFilter.IC_ONLY`
   - Keep same signature and behavior

3. **Update `format_ooc_only()`**
   - Call `format_filtered()` with `TranscriptFilter.OOC_ONLY`
   - Keep same signature and behavior

### Phase 4: Testing (High Priority)
**Duration**: 2-3 hours

1. **Regression tests**
   ```python
   def test_format_ic_only_behavior_unchanged():
       """Ensure format_ic_only produces same output as before"""
       formatter = TranscriptFormatter()
       # Use test data from before refactoring
       old_output = load_baseline_output("ic_only")
       new_output = formatter.format_ic_only(segments, classifications)
       assert old_output == new_output

   def test_format_ooc_only_behavior_unchanged():
       """Ensure format_ooc_only produces same output as before"""
       # Similar test
   ```

2. **Integration tests**
   - Test with real session data
   - Verify output files are identical
   - Test with various edge cases

3. **Edge case tests**
   ```python
   def test_format_filtered_empty_segments():
       """Test with no segments"""
       result = formatter.format_filtered([], [], TranscriptFilter.ALL)
       assert "D&D SESSION TRANSCRIPT" in result  # Header still present

   def test_format_filtered_all_filtered_out():
       """Test when filter excludes all segments"""
       # All IC segments, filtering for OOC only
       result = formatter.format_filtered(
           ic_segments,
           ic_classifications,
           TranscriptFilter.OOC_ONLY
       )
       # Should have header but no content

   def test_format_filtered_mixed_segments():
       """Test with MIXED classification"""
       # Test MIXED filter type
   ```

### Phase 5: Documentation (Low Risk)
**Duration**: 1 hour

1. **Update docstrings**
   - Document `format_filtered()` thoroughly
   - Update class docstring
   - Add examples

2. **Update user documentation**
   - Document new filter capabilities
   - Update formatter usage guide

## Testing Strategy

### Unit Tests

All tests should verify:
1. Correct filtering behavior
2. Proper header generation
3. Speaker name resolution
4. Character name display
5. Classification marker display
6. Timestamp formatting
7. Empty segment handling

### Integration Tests

```python
@pytest.mark.integration
def test_formatter_with_real_session():
    """Test formatter with actual processed session data"""
    # Load real session data
    session_data = load_test_session("test_session_01")

    formatter = TranscriptFormatter()

    # Test all filter types
    full = formatter.format_full_transcript(
        session_data['segments'],
        session_data['classifications'],
        session_data['speaker_profiles']
    )
    assert len(full) > 0

    ic_only = formatter.format_ic_only(
        session_data['segments'],
        session_data['classifications'],
        session_data['speaker_profiles']
    )
    assert len(ic_only) < len(full)  # Should be shorter

    ooc_only = formatter.format_ooc_only(
        session_data['segments'],
        session_data['classifications'],
        session_data['speaker_profiles']
    )
    assert len(ooc_only) < len(full)  # Should be shorter
```

### Regression Tests

```python
def test_regression_format_outputs():
    """Ensure new implementation produces identical output"""
    # Use saved baseline outputs
    baselines = {
        'full': Path('tests/fixtures/baseline_full.txt').read_text(),
        'ic': Path('tests/fixtures/baseline_ic.txt').read_text(),
        'ooc': Path('tests/fixtures/baseline_ooc.txt').read_text(),
    }

    formatter = TranscriptFormatter()
    test_data = load_test_data()

    # Test each format
    assert formatter.format_full_transcript(**test_data) == baselines['full']
    assert formatter.format_ic_only(**test_data) == baselines['ic']
    assert formatter.format_ooc_only(**test_data) == baselines['ooc']
```

## Risks and Mitigation

### Risk 1: Breaking Output Format
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Keep exact same output format
- Regression tests with baseline outputs
- Character-by-character comparison
- Manual review of sample outputs

### Risk 2: Performance Regression
**Likelihood**: Low
**Impact**: Low
**Mitigation**:
- Benchmark before/after
- Profile method execution
- Optimize hot paths if needed
- Use generators for large transcripts

### Risk 3: Edge Cases Not Covered
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Comprehensive edge case tests
- Test with production data samples
- Test with empty/null values
- Test with Unicode characters

## Expected Benefits

### Immediate Benefits
1. **Reduced Code**: Eliminate ~70 lines of duplication
2. **Single Source of Truth**: One implementation for all filters
3. **Easier Maintenance**: Changes applied once
4. **Better Testing**: Test filtering logic once
5. **Consistency**: Guaranteed identical formatting

### Long-term Benefits
1. **Extensibility**: Easy to add new filter types (MIXED, DM-only, etc.)
2. **Flexibility**: Customizable formatting options
3. **Reusability**: Can use `format_filtered()` directly
4. **Documentation**: Self-documenting with enum
5. **Type Safety**: Enum prevents typos

### Future Enhancements
1. **Add MIXED filter**: Show only mixed segments
2. **Add speaker filters**: Filter by specific speaker
3. **Add time range filters**: Show specific time ranges
4. **Add combined filters**: IC AND speaker X
5. **Add custom filter functions**: User-defined filters

### Metrics
- **Lines of Code**: Reduce by ~70 lines (20% of formatter.py)
- **Code Duplication**: Eliminate 100% of formatting duplication
- **Test Coverage**: Increase to 100% for formatting methods
- **Cyclomatic Complexity**: Reduce from ~8 to ~4 per method

## Migration Path

### Backward Compatibility
- All existing public methods remain with same signatures
- Old methods now call `format_filtered()` internally
- No breaking changes for users
- Output format remains identical

### Deprecation (Not Needed)
- No deprecation needed - old methods stay for convenience
- They act as convenience wrappers around `format_filtered()`

## Success Criteria

1. ✅ `TranscriptFilter` enum created and tested
2. ✅ `format_filtered()` method implemented
3. ✅ All existing format methods refactored to use `format_filtered()`
4. ✅ All existing tests pass
5. ✅ Regression tests verify identical output
6. ✅ New tests for `format_filtered()` (100% coverage)
7. ✅ No performance regression
8. ✅ Documentation updated

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Create Infrastructure | 2 hours | None |
| Phase 2: Implement format_filtered | 3-4 hours | Phase 1 |
| Phase 3: Refactor Existing Methods | 1-2 hours | Phase 2 |
| Phase 4: Testing | 2-3 hours | Phase 3 |
| Phase 5: Documentation | 1 hour | Phase 4 |
| **Total** | **9-12 hours** | |

## References

- Current implementation: `src/formatter.py:84-153`
- Class: `TranscriptFormatter`
- Related: `save_all_formats()` method (lines 200-290)
- Design pattern: Strategy Pattern (filter strategy)
- Similar pattern: Python's `filter()` built-in function
