# Refactor Candidate #1: Extract Pipeline Process Method into Stages

## Problem Statement

The `DDSessionProcessor.process()` method in `pipeline.py` is 887 lines long (lines 149-1037), making it one of the largest methods in the codebase. This violates the Single Responsibility Principle and makes the code difficult to maintain, test, and understand.

## Current State Analysis

### Location
- **File**: `src/pipeline.py`
- **Method**: `DDSessionProcessor.process()`
- **Lines**: 149-1037
- **Size**: 887 lines

### Current Structure
The method handles all 9 processing stages sequentially:
1. Audio conversion (WAV format)
2. Audio chunking (with VAD)
3. Transcription
4. Transcript merging
5. Speaker diarization
6. IC/OOC classification
7. Output generation (multiple formats)
8. Audio segment export
9. Campaign knowledge extraction

### Issues
1. **Monolithic design**: Single method does everything
2. **Complex checkpoint logic**: Resume/checkpoint code intertwined with business logic
3. **Poor testability**: Cannot test individual stages in isolation
4. **High cognitive load**: Developers must understand entire pipeline to modify one stage
5. **Error handling complexity**: Try-catch blocks scattered throughout
6. **Difficult debugging**: Hard to identify which stage has issues
7. **Code duplication**: Checkpoint save/load patterns repeated 9 times

## Proposed Solution

### Architecture Overview
Extract each stage into a dedicated method with a consistent interface:

```python
class DDSessionProcessor:
    def process(self, input_file, output_dir=None, skip_diarization=False, ...):
        """Main orchestration method - simplified to stage coordination"""
        # Setup
        # For each stage: execute, checkpoint, handle errors
        # Teardown

    def _stage1_audio_conversion(self, input_file, completed_stages) -> StageResult:
        """Convert audio to WAV format"""

    def _stage2_audio_chunking(self, wav_file, completed_stages) -> StageResult:
        """Chunk audio with VAD"""

    def _stage3_transcription(self, chunks, completed_stages) -> StageResult:
        """Transcribe audio chunks"""

    # ... etc for all 9 stages
```

### Stage Result Pattern
Create a consistent return type for all stages:

```python
@dataclass
class StageResult:
    """Result from a pipeline stage"""
    stage_number: int
    stage_name: str
    data: Any  # Stage-specific output
    status: StageStatus
    checkpoint_data: Optional[Dict] = None
    error: Optional[Exception] = None

class StageStatus(Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    RESUMED = "resumed"
```

### Checkpoint Manager Integration
Create a `StageExecutor` helper class to handle common checkpoint logic:

```python
class StageExecutor:
    """Handles stage execution with checkpoint support"""

    def execute_stage(
        self,
        stage_number: int,
        stage_name: str,
        stage_func: Callable,
        checkpoint_manager: CheckpointManager,
        completed_stages: Set[str],
        skip_checkpoint: bool = False
    ) -> StageResult:
        """Execute a stage with automatic checkpoint handling"""
        # Check if resumable
        # Execute stage function
        # Save checkpoint
        # Update status tracker
        # Return result
```

## Implementation Plan

### Phase 1: Preparation (Low Risk)
**Duration**: 2-3 hours

1. **Create new data structures**
   - Create `StageResult` dataclass
   - Create `StageStatus` enum
   - Create `StageExecutor` helper class
   - Add comprehensive tests for these utilities

2. **Add type hints**
   - Add return type hints to existing method
   - Document expected data structures

3. **Create test fixtures**
   - Create test data for each stage
   - Create mocks for checkpoint manager
   - Create integration test baseline

### Phase 2: Extract Stages (Medium Risk)
**Duration**: 6-8 hours

Execute in this order (dependency order):

1. **Stage 1: Audio Conversion** (lines 246-299)
   ```python
   def _stage1_audio_conversion(
       self,
       input_file: Path,
       completed_stages: Set[str],
       checkpoint_metadata: Dict
   ) -> StageResult:
       """Convert audio to WAV format"""
   ```
   - Extract lines 246-299
   - Add checkpoint logic wrapper
   - Test independently

2. **Stage 2: Audio Chunking** (lines 301-401)
   ```python
   def _stage2_audio_chunking(
       self,
       wav_file: Path,
       duration: float,
       completed_stages: Set[str],
       checkpoint_metadata: Dict
   ) -> StageResult:
       """Chunk audio with VAD"""
   ```
   - Extract lines 301-401
   - Handle progress callbacks
   - Test with various audio lengths

3. **Stage 3: Transcription** (lines 403-496)
   ```python
   def _stage3_transcription(
       self,
       chunks: List[AudioChunk],
       completed_stages: Set[str],
       checkpoint_metadata: Dict
   ) -> StageResult:
       """Transcribe audio chunks"""
   ```
   - Extract lines 403-496
   - Handle large checkpoint data (blob storage)
   - Test with mock transcriber

4. **Continue for remaining stages** (4-9)
   - Follow same pattern
   - Test each independently
   - Ensure checkpoint compatibility

### Phase 3: Refactor Main Method (Medium Risk)
**Duration**: 3-4 hours

1. **Simplify orchestration**
   ```python
   def process(self, input_file, output_dir=None, ...):
       # Setup (lines 163-243)
       start_time = perf_counter()
       self._setup_session(...)

       # Execute stages sequentially
       results = {}
       results['stage1'] = self._execute_with_checkpoint(
           1, "audio_conversion",
           lambda: self._stage1_audio_conversion(...)
       )

       results['stage2'] = self._execute_with_checkpoint(
           2, "audio_chunking",
           lambda: self._stage2_audio_chunking(results['stage1'].data)
       )

       # ... etc

       # Teardown and return
       return self._build_result(results)
   ```

2. **Extract helper methods**
   - `_setup_session()` - lines 163-243
   - `_execute_with_checkpoint()` - wrapper for stage execution
   - `_build_result()` - construct final output dict

### Phase 4: Testing (High Priority)
**Duration**: 4-5 hours

1. **Unit tests for each stage**
   - Test with valid inputs
   - Test with edge cases
   - Test checkpoint resume
   - Test error handling

2. **Integration tests**
   - Test full pipeline with new structure
   - Test checkpoint resume at each stage
   - Test error recovery
   - Compare outputs with baseline

3. **Performance tests**
   - Ensure no performance regression
   - Verify checkpoint overhead is minimal

### Phase 5: Documentation (Low Risk)
**Duration**: 2 hours

1. **Update docstrings**
   - Document each stage method
   - Document stage dependencies
   - Document checkpoint data format

2. **Update architecture docs**
   - Update pipeline flow diagram
   - Document stage interfaces
   - Add troubleshooting guide

## Testing Strategy

### Unit Tests

```python
class TestPipelineStages(unittest.TestCase):
    def test_stage1_audio_conversion_success(self):
        """Test successful audio conversion"""
        processor = DDSessionProcessor(...)
        result = processor._stage1_audio_conversion(
            input_file=Path("test.mp3"),
            completed_stages=set(),
            checkpoint_metadata={}
        )
        assert result.status == StageStatus.COMPLETED
        assert result.data['wav_file'].exists()
        assert result.data['duration'] > 0

    def test_stage1_checkpoint_resume(self):
        """Test resuming from checkpoint"""
        # Setup checkpoint
        # Execute stage
        # Verify checkpoint was used

    def test_stage2_progress_callback(self):
        """Test chunk progress reporting"""
        # Mock progress callback
        # Execute stage
        # Verify callback was called with correct data
```

### Integration Tests

```python
def test_full_pipeline_refactored():
    """Ensure refactored pipeline produces same output as original"""
    # Run baseline version
    # Run refactored version
    # Compare all outputs
    # Verify checksums match
```

### Regression Tests

```python
def test_checkpoint_compatibility():
    """Ensure new code can resume from old checkpoints"""
    # Create checkpoint with old code
    # Resume with new code
    # Verify success
```

## Risks and Mitigation

### Risk 1: Breaking Checkpoint Compatibility
**Likelihood**: High
**Impact**: High
**Mitigation**:
- Write checkpoint migration script
- Support both old and new checkpoint formats temporarily
- Add version number to checkpoint format
- Test extensively with existing checkpoints

### Risk 2: Performance Regression
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Benchmark before and after
- Profile method call overhead
- Ensure no data copying between stages
- Use lazy evaluation where possible

### Risk 3: Introducing Bugs in Complex Logic
**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Extract one stage at a time
- Comprehensive test coverage
- Code review each stage extraction
- Keep original code temporarily for comparison

### Risk 4: Stage Dependencies Not Clear
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Explicitly document inputs/outputs
- Use type hints extensively
- Create dependency diagram
- Validate inputs at stage entry

## Expected Benefits

### Immediate Benefits
1. **Improved testability**: Each stage can be tested independently
2. **Better error messages**: Know exactly which stage failed
3. **Easier debugging**: Set breakpoints in specific stages
4. **Code clarity**: Each stage is self-contained and documented

### Long-term Benefits
1. **Maintainability**: Changes to one stage don't affect others
2. **Extensibility**: Easy to add new stages or modify existing ones
3. **Parallel processing**: Potential to run independent stages in parallel
4. **Monitoring**: Can track metrics per stage
5. **Reusability**: Stages can be used in different pipelines

### Metrics
- **Cyclomatic complexity**: Reduce from ~45 to ~5 per method
- **Method size**: Reduce from 887 lines to <100 lines per method
- **Test coverage**: Increase from ~70% to >90%
- **Code duplication**: Reduce checkpoint handling code by 60%

## Migration Path

### Backward Compatibility
1. Keep old method as `process_legacy()` for 2 releases
2. Add deprecation warning
3. Provide migration guide for custom integrations
4. Remove legacy method in version 3.0

### Feature Flag
```python
# config.py
FEATURE_FLAGS = {
    'use_refactored_pipeline': True  # Toggle for gradual rollout
}
```

## Success Criteria

1. ✅ All existing tests pass
2. ✅ New unit tests for each stage (>90% coverage)
3. ✅ Integration tests verify same output as baseline
4. ✅ Checkpoint resume works at every stage
5. ✅ Performance within 5% of baseline
6. ✅ Code review approved by 2+ developers
7. ✅ Documentation updated
8. ✅ No regression in production for 2 weeks

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Preparation | 2-3 hours | None |
| Phase 2: Extract Stages | 6-8 hours | Phase 1 |
| Phase 3: Refactor Main | 3-4 hours | Phase 2 |
| Phase 4: Testing | 4-5 hours | Phase 3 |
| Phase 5: Documentation | 2 hours | Phase 4 |
| **Total** | **17-22 hours** | |

## References

- Current implementation: `src/pipeline.py:149-1037`
- Checkpoint manager: `src/checkpoint.py`
- Status tracker: `src/status_tracker.py`
- Similar refactoring: [Clean Code](https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882) Chapter 3
