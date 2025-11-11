# Refactor Candidate #6: Extract Complex Logic from SpeakerDiarizer.diarize()

## Problem Statement

The `diarize()` method in `SpeakerDiarizer` class (lines 295-396) is 101 lines long and handles multiple responsibilities: diarization, audio loading with fallbacks, embedding extraction, and error handling. This complexity makes the method difficult to test, understand, and maintain.

## Current State Analysis

### Location
- **File**: `src/diarizer.py`
- **Class**: `SpeakerDiarizer`
- **Method**: `diarize()`
- **Lines**: 295-396
- **Size**: 101 lines

### Current Code Structure

```python
def diarize(self, audio_path: Path) -> Tuple[List[SpeakerSegment], Dict[str, np.ndarray]]:
    """
    Perform speaker diarization on audio file.

    Returns:
        A tuple containing:
        - A list of SpeakerSegment objects.
        - A dictionary mapping speaker IDs to their embeddings.
    """
    self._load_pipeline_if_needed()

    if self.pipeline is None:
        segments = self._create_fallback_diarization(audio_path)
        return segments, {}

    # Run diarization (lines 315-329)
    diarization_input = str(audio_path)
    try:
        import torchaudio
        waveform, sample_rate = torchaudio.load(str(audio_path))
        diarization_input = {
            "waveform": waveform,
            "sample_rate": sample_rate
        }
    except Exception as exc:
        self.logger.debug(...)

    diarization = self.pipeline(diarization_input)

    # Convert to our format (lines 332-339)
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(SpeakerSegment(...))

    # Extract speaker embeddings (lines 341-395)
    speaker_embeddings: Dict[str, np.ndarray] = {}
    if self.embedding_model is not None:
        try:
            from pydub import AudioSegment
        except Exception as exc:
            AudioSegment = None

        audio = None
        if AudioSegment is not None:
            try:
                audio = AudioSegment.from_wav(str(audio_path))
            except Exception as exc:
                self.logger.warning(...)

        if audio is None:
            self.logger.warning(...)
        else:
            for speaker_id in diarization.labels():
                # Extract segments for this speaker (lines 368-373)
                speaker_segments = diarization.label_timeline(speaker_id)
                speaker_audio = AudioSegment.empty()
                for segment in speaker_segments:
                    speaker_audio += audio[segment.start * 1000:segment.end * 1000]

                if len(speaker_audio) <= 0:
                    continue

                # Convert to tensor and extract embedding (lines 375-394)
                samples = np.array(...) / 32768.0
                samples_tensor = torch.from_numpy(samples).unsqueeze(0)
                try:
                    embedding = self.embedding_model(...)
                    speaker_embeddings[speaker_id] = self._embedding_to_numpy(embedding)
                except Exception as exc:
                    self.logger.warning(...)

    return segments, speaker_embeddings
```

### Issues

1. **Multiple Responsibilities**: Audio loading, diarization, embedding extraction
2. **Deep Nesting**: Multiple levels of try-except and if-else
3. **Poor Testability**: Hard to test individual parts
4. **Complex Control Flow**: Many branches and error paths
5. **Long Method**: 101 lines - hard to understand at a glance
6. **Mixed Concerns**: High-level and low-level operations mixed
7. **Error Handling Scattered**: Exception handling throughout
8. **Dependency Loading**: Dynamic imports mixed with business logic

## Proposed Solution

### Design Overview

Extract the method into smaller, focused methods:
1. **`_load_audio_for_diarization()`** - Handle audio loading with fallbacks
2. **`_run_diarization()`** - Execute diarization pipeline
3. **`_convert_diarization_to_segments()`** - Convert PyAnnote output to our format
4. **`_extract_speaker_embeddings()`** - Extract embeddings for all speakers
5. **`_extract_single_speaker_embedding()`** - Extract embedding for one speaker

### New Architecture

```python
from typing import Tuple, List, Dict, Optional, Any
from pathlib import Path
import numpy as np

class SpeakerDiarizer(BaseDiarizer):
    """
    Speaker diarization using PyAnnote.audio.
    """

    def diarize(self, audio_path: Path) -> Tuple[List[SpeakerSegment], Dict[str, np.ndarray]]:
        """
        Perform speaker diarization on audio file.

        This is the main entry point that orchestrates the diarization process.

        Args:
            audio_path: Path to WAV file

        Returns:
            A tuple containing:
            - A list of SpeakerSegment objects
            - A dictionary mapping speaker IDs to their embeddings

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RuntimeError: If diarization fails critically
        """
        # Ensure pipeline is loaded
        self._load_pipeline_if_needed()

        # Fallback if pipeline unavailable
        if self.pipeline is None:
            segments = self._create_fallback_diarization(audio_path)
            return segments, {}

        # Load audio with appropriate format
        diarization_input = self._load_audio_for_diarization(audio_path)

        # Run diarization
        diarization = self._run_diarization(diarization_input)

        # Convert results to our format
        segments = self._convert_diarization_to_segments(diarization)

        # Extract speaker embeddings (optional, requires embedding model)
        speaker_embeddings = self._extract_speaker_embeddings(
            diarization, audio_path
        )

        return segments, speaker_embeddings

    def _load_audio_for_diarization(self, audio_path: Path) -> Any:
        """
        Load audio in the format required by PyAnnote.

        Attempts to load as tensor (preferred) with fallback to file path.

        Args:
            audio_path: Path to audio file

        Returns:
            Either a dict with waveform/sample_rate or a path string
        """
        # Try loading as tensor (preferred by PyAnnote 3.x)
        try:
            import torchaudio

            waveform, sample_rate = torchaudio.load(str(audio_path))
            self.logger.debug(
                "Loaded audio as tensor: %d samples at %d Hz",
                waveform.shape[1], sample_rate
            )
            return {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
        except Exception as exc:
            # Fallback to file path (supported by PyAnnote 2.x)
            self.logger.debug(
                "Falling back to on-disk audio loading for diarization: %s",
                exc
            )
            return str(audio_path)

    def _run_diarization(self, diarization_input: Any) -> Any:
        """
        Execute the PyAnnote diarization pipeline.

        Args:
            diarization_input: Either tensor dict or file path

        Returns:
            PyAnnote Annotation object

        Raises:
            RuntimeError: If pipeline execution fails
        """
        try:
            return self.pipeline(diarization_input)
        except Exception as exc:
            raise RuntimeError(
                f"Diarization pipeline failed: {exc}"
            ) from exc

    def _convert_diarization_to_segments(
        self,
        diarization: Any
    ) -> List[SpeakerSegment]:
        """
        Convert PyAnnote diarization output to our SpeakerSegment format.

        Args:
            diarization: PyAnnote Annotation object

        Returns:
            List of SpeakerSegment objects
        """
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(SpeakerSegment(
                speaker_id=speaker,
                start_time=turn.start,
                end_time=turn.end
            ))

        self.logger.info(
            "Converted %d diarization segments to SpeakerSegment format",
            len(segments)
        )
        return segments

    def _extract_speaker_embeddings(
        self,
        diarization: Any,
        audio_path: Path
    ) -> Dict[str, np.ndarray]:
        """
        Extract voice embeddings for all speakers.

        This is used for speaker identification across sessions.

        Args:
            diarization: PyAnnote Annotation object
            audio_path: Path to audio file

        Returns:
            Dictionary mapping speaker IDs to embeddings
        """
        speaker_embeddings: Dict[str, np.ndarray] = {}

        # Check if embedding model is available
        if self.embedding_model is None:
            self.logger.debug("No embedding model available, skipping extraction")
            return speaker_embeddings

        # Load audio for embedding extraction
        audio = self._load_audio_for_embeddings(audio_path)
        if audio is None:
            self.logger.warning(
                "Could not load audio for embedding extraction"
            )
            return speaker_embeddings

        # Extract embedding for each speaker
        for speaker_id in diarization.labels():
            try:
                embedding = self._extract_single_speaker_embedding(
                    speaker_id, diarization, audio
                )
                if embedding is not None:
                    speaker_embeddings[speaker_id] = embedding
            except Exception as exc:
                self.logger.warning(
                    "Failed to extract embedding for %s: %s",
                    speaker_id, exc
                )

        self.logger.info(
            "Extracted embeddings for %d/%d speakers",
            len(speaker_embeddings),
            len(diarization.labels())
        )

        return speaker_embeddings

    def _load_audio_for_embeddings(
        self,
        audio_path: Path
    ) -> Optional[Any]:
        """
        Load audio file for embedding extraction.

        Uses pydub for audio manipulation.

        Args:
            audio_path: Path to audio file

        Returns:
            AudioSegment object or None if loading fails
        """
        try:
            from pydub import AudioSegment
        except ImportError as exc:
            self.logger.warning(
                "Unable to import pydub for embedding extraction: %s",
                exc
            )
            return None

        try:
            audio = AudioSegment.from_wav(str(audio_path))
            self.logger.debug(
                "Loaded audio for embeddings: %.1fs duration",
                len(audio) / 1000.0
            )
            return audio
        except Exception as exc:
            self.logger.warning(
                "Unable to load %s for speaker embeddings: %s",
                audio_path, exc
            )
            return None

    def _extract_single_speaker_embedding(
        self,
        speaker_id: str,
        diarization: Any,
        audio: Any
    ) -> Optional[np.ndarray]:
        """
        Extract voice embedding for a single speaker.

        Combines all segments for the speaker and extracts a single embedding.

        Args:
            speaker_id: ID of speaker to extract
            diarization: PyAnnote Annotation object
            audio: pydub AudioSegment

        Returns:
            Numpy array with embedding or None if extraction fails

        Raises:
            Exception: If embedding extraction fails
        """
        from pydub import AudioSegment

        # Get all segments for this speaker
        speaker_segments = diarization.label_timeline(speaker_id)

        # Combine audio from all segments
        speaker_audio = AudioSegment.empty()
        for segment in speaker_segments:
            start_ms = int(segment.start * 1000)
            end_ms = int(segment.end * 1000)
            speaker_audio += audio[start_ms:end_ms]

        # Check if we have enough audio
        if len(speaker_audio) <= 0:
            self.logger.debug(
                "Speaker %s has no audio segments, skipping embedding",
                speaker_id
            )
            return None

        # Convert to tensor
        samples = np.array(
            speaker_audio.get_array_of_samples(),
            dtype=np.float32
        ) / 32768.0

        samples_tensor = torch.from_numpy(samples).unsqueeze(0)

        # Extract embedding
        embedding = self.embedding_model({
            "waveform": samples_tensor,
            "sample_rate": audio.frame_rate
        })

        return self._embedding_to_numpy(embedding)

    # ... rest of methods unchanged
```

## Implementation Plan

### Phase 1: Extract Audio Loading (Low Risk)
**Duration**: 2 hours

1. **Create `_load_audio_for_diarization()` method**
   - Extract lines 315-329
   - Add comprehensive error handling
   - Add logging
   - Add docstring

2. **Create unit tests**
   ```python
   def test_load_audio_for_diarization_tensor_success():
       """Test loading audio as tensor"""
       diarizer = SpeakerDiarizer()
       result = diarizer._load_audio_for_diarization(Path("test.wav"))
       assert isinstance(result, dict)
       assert "waveform" in result
       assert "sample_rate" in result

   def test_load_audio_for_diarization_fallback():
       """Test fallback to path string"""
       # Mock torchaudio to raise exception
       # Verify fallback works
   ```

3. **Update main method**
   - Replace inline code with method call
   - Verify behavior unchanged

### Phase 2: Extract Diarization Conversion (Low Risk)
**Duration**: 1 hour

1. **Create `_run_diarization()` method**
   - Simple wrapper around pipeline call
   - Add error handling

2. **Create `_convert_diarization_to_segments()` method**
   - Extract lines 332-339
   - Add logging
   - Add docstring

3. **Add tests**
   ```python
   def test_convert_diarization_to_segments():
       """Test conversion from PyAnnote format"""
       diarizer = SpeakerDiarizer()
       mock_diarization = create_mock_diarization()
       segments = diarizer._convert_diarization_to_segments(mock_diarization)
       assert len(segments) > 0
       assert all(isinstance(s, SpeakerSegment) for s in segments)
   ```

### Phase 3: Extract Embedding Extraction (Medium Risk)
**Duration**: 3-4 hours

1. **Create `_load_audio_for_embeddings()` method**
   - Extract audio loading logic for embeddings
   - Handle pydub import
   - Add error handling

2. **Create `_extract_speaker_embeddings()` method**
   - Extract main embedding loop (lines 341-395)
   - Call `_extract_single_speaker_embedding()` for each speaker
   - Add progress logging

3. **Create `_extract_single_speaker_embedding()` method**
   - Extract single speaker embedding logic
   - Handle audio concatenation
   - Handle tensor conversion
   - Call embedding model

4. **Add comprehensive tests**
   ```python
   def test_extract_speaker_embeddings_success():
       """Test successful embedding extraction"""
       diarizer = SpeakerDiarizer()
       diarizer.embedding_model = Mock()
       mock_diarization = create_mock_diarization()
       embeddings = diarizer._extract_speaker_embeddings(
           mock_diarization,
           Path("test.wav")
       )
       assert len(embeddings) > 0
       assert all(isinstance(v, np.ndarray) for v in embeddings.values())

   def test_extract_speaker_embeddings_no_model():
       """Test when embedding model not available"""
       diarizer = SpeakerDiarizer()
       diarizer.embedding_model = None
       embeddings = diarizer._extract_speaker_embeddings(
           create_mock_diarization(),
           Path("test.wav")
       )
       assert embeddings == {}

   def test_extract_single_speaker_embedding():
       """Test single speaker embedding extraction"""
       diarizer = SpeakerDiarizer()
       diarizer.embedding_model = Mock()
       embedding = diarizer._extract_single_speaker_embedding(
           "SPEAKER_00",
           mock_diarization,
           mock_audio
       )
       assert isinstance(embedding, np.ndarray)
   ```

### Phase 4: Refactor Main Method (Low Risk)
**Duration**: 1 hour

1. **Simplify `diarize()` method**
   - Replace all extracted code with method calls
   - Keep same return signature
   - Add high-level comments
   - Improve overall readability

2. **Verify behavior**
   - Run all tests
   - Manual testing with sample audio

### Phase 5: Testing (High Priority)
**Duration**: 2-3 hours

1. **Integration tests**
   ```python
   @pytest.mark.integration
   def test_diarize_full_workflow():
       """Test complete diarization workflow"""
       diarizer = SpeakerDiarizer()
       segments, embeddings = diarizer.diarize(Path("test_audio.wav"))

       assert len(segments) > 0
       assert all(isinstance(s, SpeakerSegment) for s in segments)
       assert isinstance(embeddings, dict)
   ```

2. **Error handling tests**
   ```python
   def test_diarize_invalid_audio_path():
       """Test error handling for invalid path"""
       diarizer = SpeakerDiarizer()
       with pytest.raises(Exception):
           diarizer.diarize(Path("nonexistent.wav"))

   def test_diarize_pipeline_failure():
       """Test handling of pipeline failures"""
       # Mock pipeline to raise exception
       # Verify graceful handling
   ```

3. **Performance tests**
   - Benchmark before/after
   - Ensure no regression

### Phase 6: Documentation (Low Risk)
**Duration**: 1 hour

1. **Update docstrings**
   - Document all new methods
   - Add examples
   - Document error conditions

2. **Update architecture docs**
   - Document diarization flow
   - Add sequence diagram

## Testing Strategy

### Unit Tests

```python
class TestSpeakerDiarizerRefactored(unittest.TestCase):
    """Test suite for refactored SpeakerDiarizer"""

    def setUp(self):
        self.diarizer = SpeakerDiarizer()

    def test_load_audio_for_diarization(self):
        """Test audio loading"""
        pass

    def test_run_diarization(self):
        """Test diarization execution"""
        pass

    def test_convert_diarization_to_segments(self):
        """Test format conversion"""
        pass

    def test_extract_speaker_embeddings(self):
        """Test embedding extraction"""
        pass

    def test_extract_single_speaker_embedding(self):
        """Test single speaker embedding"""
        pass

    def test_load_audio_for_embeddings(self):
        """Test audio loading for embeddings"""
        pass
```

### Integration Tests

```python
@pytest.mark.integration
class TestDiarizationIntegration(unittest.TestCase):
    """Integration tests for complete diarization pipeline"""

    def test_diarize_real_audio(self):
        """Test with real audio file"""
        pass

    def test_diarize_various_speaker_counts(self):
        """Test with 1, 2, 3, 4+ speakers"""
        pass

    def test_diarize_with_embeddings(self):
        """Test embedding extraction with real audio"""
        pass
```

## Risks and Mitigation

### Risk 1: Breaking Diarization Behavior
**Likelihood**: Low
**Impact**: High
**Mitigation**:
- Keep exact same logic
- Comprehensive regression tests
- Test with production audio samples
- Compare outputs byte-for-byte

### Risk 2: Embedding Extraction Failures
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Extensive error handling
- Graceful degradation (continue without embeddings)
- Log all failures with context
- Test edge cases thoroughly

### Risk 3: Performance Regression
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Benchmark before/after
- Profile method calls
- Ensure no unnecessary data copying
- Optimize hot paths if needed

## Expected Benefits

### Immediate Benefits
1. **Improved Readability**: Each method does one thing
2. **Better Testability**: Test each component independently
3. **Easier Debugging**: Isolate issues to specific methods
4. **Clearer Flow**: High-level method is now easy to understand
5. **Better Error Messages**: More specific error locations

### Long-term Benefits
1. **Maintainability**: Easier to modify individual parts
2. **Reusability**: Extracted methods can be reused
3. **Extensibility**: Easy to add new embedding models
4. **Documentation**: Self-documenting code structure
5. **Performance**: Easier to optimize specific parts

### Metrics
- **Method Size**: Reduce from 101 lines to ~30 lines (main method)
- **Cyclomatic Complexity**: Reduce from ~12 to ~4 (main method)
- **Test Coverage**: Increase to >90%
- **Number of Methods**: Increase from 1 to 6 (better separation)

## Success Criteria

1. ✅ All extracted methods created and tested
2. ✅ Main `diarize()` method simplified to ~30 lines
3. ✅ All existing tests pass
4. ✅ New unit tests for each extracted method (>90% coverage)
5. ✅ Integration tests verify same behavior
6. ✅ No performance regression (<5% difference)
7. ✅ Documentation updated
8. ✅ Code review approved

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Extract Audio Loading | 2 hours | None |
| Phase 2: Extract Conversion | 1 hour | Phase 1 |
| Phase 3: Extract Embeddings | 3-4 hours | Phase 2 |
| Phase 4: Refactor Main Method | 1 hour | Phase 3 |
| Phase 5: Testing | 2-3 hours | Phase 4 |
| Phase 6: Documentation | 1 hour | Phase 5 |
| **Total** | **10-12 hours** | |

## References

- Current implementation: `src/diarizer.py:295-396`
- Class: `SpeakerDiarizer`
- Related: `HuggingFaceApiDiarizer.diarize()` (lines 127-168)
- Design principle: Single Responsibility Principle
- Refactoring technique: Extract Method
