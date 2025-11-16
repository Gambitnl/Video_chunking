# Known Issues - Comprehensive Bug Report

**Generated**: 2025-11-16
**Session**: claude/find-list-bugs-01V9zTY4AXrt5Gta9yEQkFsq
**Total Issues**: 25 bugs identified across codebase

This document tracks all known bugs and issues in the Video Chunking pipeline. Bugs are categorized by severity and include detailed information about location, impact, and suggested fixes.

---

## Table of Contents

1. [Critical Severity (Security & Data Loss)](#critical-severity-security--data-loss)
2. [High Severity (Crashes & Race Conditions)](#high-severity-crashes--race-conditions)
3. [Medium Severity (Logic Errors & Resource Leaks)](#medium-severity-logic-errors--resource-leaks)
4. [Low Severity (Edge Cases & Inconsistencies)](#low-severity-edge-cases--inconsistencies)
5. [Summary by Category](#summary-by-category)
6. [Recommended Fix Priority](#recommended-fix-priority)

---

## Critical Severity (Security & Data Loss)

### BUG #1: Path Traversal Vulnerability in Session Directory Handling

**Severity**: CRITICAL
**Location**: `src/session_manager.py:135`
**Category**: Security Vulnerability

**Description**:
Session IDs are not sanitized before being used in path construction. A malicious session ID containing path separators like `"../../../tmp"` could escape the output directory and create files in unauthorized locations on the filesystem.

**Code**:
```python
output_path = output_dir / "_checkpoints" / session_id  # Unsafe
```

**Impact**:
- Security vulnerability allowing unauthorized file system access
- Potential for arbitrary file creation/overwrite
- Could compromise system integrity

**Suggested Fix**:
```python
# Sanitize session_id before path construction
safe_id = sanitize_filename(session_id)  # Remove path separators
output_path = output_dir / "_checkpoints" / safe_id
```

**Priority**: IMMEDIATE

---

### BUG #2: Path Traversal in Audio Processing

**Severity**: CRITICAL
**Location**: `src/audio_processor.py:57-65`
**Category**: Security Vulnerability

**Description**:
Input path coercion doesn't validate for path traversal sequences (`../`) or absolute paths outside the intended directory. This could allow access to files outside the session directory.

**Impact**:
- Could access files outside session directory
- Potential security issue in multi-user environments
- Risk of unauthorized file access

**Suggested Fix**:
```python
def _coerce_path(input_path):
    path = Path(input_path)
    # Validate path safety
    if ".." in str(path) or path.is_absolute():
        raise ValueError("Path traversal detected")
    return path.resolve()
```

**Priority**: IMMEDIATE

---

### BUG #3: Silent Configuration Data Loss

**Severity**: CRITICAL
**Location**: `src/party_config.py:48-60`
**Category**: Data Loss

**Description**:
Corrupted JSON files return an empty dict silently without alerting users. Users are unaware their party configuration was corrupted and data was lost.

**Code**:
```python
except json.JSONDecodeError as e:
    logger.warning(f"Could not parse parties.json: {e}")  # Too lenient
    return {}
```

**Impact**:
- Silent data loss
- Users unaware their party config is corrupted
- Processing continues with invalid/empty configuration

**Suggested Fix**:
```python
except json.JSONDecodeError as e:
    logger.error(f"Corrupted parties.json: {e}")
    logger.error("Party configuration is unreadable and will be reset")
    # Optionally: backup corrupted file before resetting
    return {}
```

**Priority**: HIGH

---

## High Severity (Crashes & Race Conditions)

### BUG #4: Race Condition in Manifest Writing

**Severity**: HIGH
**Location**: `src/snipper.py:64-75`
**Category**: Concurrency Issue

**Description**:
Manifest lock is acquired but write operations may happen outside the lock scope in some code paths. This can lead to manifest corruption with concurrent access.

**Impact**:
- Manifest corruption with concurrent access
- Lost segment data
- Inconsistent snippet metadata

**Suggested Fix**:
```python
with self._manifest_lock:
    # Ensure ALL file operations complete inside lock
    self._clear_session_directory()
    # Write manifest here, inside lock
    manifest_file.write(json.dumps(manifest))
```

**Priority**: HIGH

---

### BUG #5: Missing Null Check in Speaker Profile Mapping

**Severity**: HIGH
**Location**: `src/diarizer.py:557-564`
**Category**: Error Handling

**Description**:
If diarization fails and returns None, calling `.labels()` on it raises an AttributeError. The pipeline crashes instead of gracefully degrading.

**Code**:
```python
for label in diarization.labels():  # Crashes if diarization is None
    ...
```

**Impact**:
- Pipeline crashes instead of graceful degradation
- No fallback mechanism
- Loss of processing progress

**Suggested Fix**:
```python
if diarization is None:
    logger.warning("Diarization failed, returning empty profile mapping")
    return {}

for label in diarization.labels():
    ...
```

**Priority**: HIGH

---

### BUG #6: Index Out of Bounds in Snipper Export

**Severity**: HIGH
**Location**: `src/pipeline.py:1151-1164`
**Category**: Array Access

**Description**:
Classifications array bounds are not checked before indexing. If the classifications list is shorter than segments, accessing `classifications[i]` throws IndexError.

**Impact**:
- Audio snippet export fails with IndexError
- Partial output, missing snippets
- Processing interruption

**Suggested Fix**:
```python
classification = classifications[i] if i < len(classifications) else None
if classification is None:
    logger.warning(f"Missing classification for segment {i}")
    continue
```

**Priority**: HIGH

---

### BUG #7: Unhandled Network Errors in Colab Classifier

**Severity**: HIGH
**Location**: `src/classifier.py:773-825`
**Category**: Error Handling

**Description**:
Network errors and Google Drive write failures have no fallback handling. If Google Drive write fails, the session processing fails completely without a recovery mechanism.

**Impact**:
- Complete session processing failure without recovery
- No fallback to local processing
- Lost work if network is unstable

**Suggested Fix**:
```python
try:
    job_file.write(json.dumps(job_data))
except Exception as e:
    logger.error(f"Google Drive write failed: {e}")
    logger.info("Falling back to local classification")
    return self._classify_locally(segments)
```

**Priority**: HIGH

---

## Medium Severity (Logic Errors & Resource Leaks)

### BUG #8: Potential Division by Zero

**Severity**: MEDIUM
**Location**: `src/ui/process_session_helpers.py:662`
**Category**: Logic Error

**Description**:
ZeroDivisionError is caught but the condition causing it isn't prevented. If `total_duration` becomes 0, percentage calculations will fail silently.

**Impact**:
- Silent failures in progress calculations
- Inaccurate statistics displayed to user
- Misleading progress indicators

**Suggested Fix**:
```python
if total_duration > 0:
    percentage = (current / total_duration) * 100
else:
    percentage = 0
    logger.warning("Total duration is zero, cannot calculate percentage")
```

**Priority**: MEDIUM

---

### BUG #9: Missing Checkpoint Data Validation

**Severity**: MEDIUM
**Location**: `src/pipeline.py:1651-1664`
**Category**: Data Validation

**Description**:
WAV file existence is checked, but corrupted/incomplete checkpoints may be accepted without validating all required data fields.

**Impact**:
- Pipeline may fail silently on resume
- Confusing error messages
- Incomplete checkpoint recovery

**Suggested Fix**:
```python
required_fields = ['wav_path', 'duration', 'sample_rate']
if not all([checkpoint_data.get(key) for key in required_fields]):
    logger.warning("Checkpoint missing required fields, discarding")
    discard_checkpoint()
    return None
```

**Priority**: MEDIUM

---

### BUG #10: Missing Bounds Checking in Segment Classification

**Severity**: MEDIUM
**Location**: `src/classifier.py:274-287`
**Category**: Array Access

**Description**:
Array indexing assumes segments are adjacent with no gaps. If segments are non-contiguous or filtered, `segments[i-1]` and `segments[i+1]` may reference wrong indices.

**Impact**:
- Incorrect context passed to classifier
- Wrong IC/OOC decisions
- Misclassified segments

**Suggested Fix**:
```python
prev_text = segments[i-1]['text'] if i > 0 else ""
next_text = segments[i+1]['text'] if i < len(segments)-1 else ""
```

**Priority**: MEDIUM

---

### BUG #11: Missing Configuration Value Validation

**Severity**: MEDIUM
**Location**: `src/config.py:81-83`
**Category**: Input Validation

**Description**:
Integer configuration values aren't validated for reasonable ranges. Values like `CHUNK_LENGTH_SECONDS=-1` or `CHUNK_OVERLAP_SECONDS=9999` would be accepted.

**Impact**:
- Invalid processing parameters causing silent failures
- Resource exhaustion with extreme values
- Unpredictable behavior

**Suggested Fix**:
```python
# Add validation in Config class
if not 10 <= CHUNK_LENGTH_SECONDS <= 3600:
    raise ValueError(f"Invalid CHUNK_LENGTH_SECONDS: {CHUNK_LENGTH_SECONDS}")
if not 0 <= CHUNK_OVERLAP_SECONDS <= 60:
    raise ValueError(f"Invalid CHUNK_OVERLAP_SECONDS: {CHUNK_OVERLAP_SECONDS}")
```

**Priority**: MEDIUM

---

### BUG #12: Resource Leak in Audio Loading

**Severity**: MEDIUM
**Location**: `src/audio_processor.py:155-161`
**Category**: Resource Management

**Description**:
AudioSegment.from_file() doesn't use context managers. Resources may not be freed on exception, leading to file handle leaks.

**Impact**:
- Memory leaks with large audio files
- File handle exhaustion
- "Too many open files" errors with repeated operations

**Suggested Fix**:
```python
# Use try-finally to ensure cleanup
audio_segment = None
try:
    audio_segment = AudioSegment.from_file(path)
    # ... process ...
finally:
    if audio_segment:
        del audio_segment  # Force cleanup
```

**Priority**: MEDIUM

---

### BUG #13: File Handle Not Closed in Error Case

**Severity**: MEDIUM
**Location**: `src/diarizer.py:729`
**Category**: Resource Management

**Description**:
AudioSegment.from_file() in fallback method doesn't close file handle properly in error paths.

**Impact**:
- File handle leaks during diarization failures
- Could prevent retries
- Resource accumulation over time

**Suggested Fix**:
```python
# Ensure proper cleanup in all code paths
try:
    audio_segment = AudioSegment.from_file(path)
    # ... process ...
finally:
    # Explicit cleanup
    pass
```

**Priority**: MEDIUM

---

### BUG #14: Hardcoded Model Names

**Severity**: MEDIUM
**Location**: `src/transcriber.py:398`
**Category**: Configuration Management

**Description**:
Model name `"whisper-large-v3-turbo"` is hardcoded in Groq transcriber, ignoring configuration settings. Users can't change the model without modifying source code.

**Impact**:
- Configuration ignored
- Users can't optimize for speed/cost tradeoff
- Inconsistent with other transcribers

**Suggested Fix**:
```python
model = Config.GROQ_WHISPER_MODEL or "whisper-large-v3-turbo"
```

**Priority**: MEDIUM

---

### BUG #15: Timeout Value Not Validated

**Severity**: MEDIUM
**Location**: `src/classifier.py:788-793`
**Category**: Input Validation

**Description**:
Colab classifier timeout is hardcoded to 1800s with no validation. If `COLAB_TIMEOUT=0` or negative, could cause infinite wait or immediate timeout.

**Impact**:
- Processing hangs indefinitely
- Or fails immediately with timeout
- Unpredictable behavior

**Suggested Fix**:
```python
if self.timeout <= 0:
    logger.warning(f"Invalid timeout {self.timeout}, using default")
    self.timeout = 1800  # default 30 minutes
```

**Priority**: MEDIUM

---

## Low Severity (Edge Cases & Inconsistencies)

### BUG #16: Type Inconsistency in Merger Return

**Severity**: LOW
**Location**: `src/merger.py:45-49`
**Category**: Type Safety

**Description**:
Single transcription chunk returns segments without consistent type wrapping. May return raw objects instead of expected TranscriptionSegment instances.

**Impact**:
- Potential type errors in downstream code
- Inconsistent object interfaces
- Type checking failures

**Suggested Fix**:
```python
# Add type hints and ensure consistent return types
def merge(self, transcriptions: List[ChunkTranscription]) -> List[TranscriptionSegment]:
    if len(transcriptions) == 1:
        return list(transcriptions[0].segments)  # Already correct
    # ... rest of method
```

**Priority**: LOW

---

### BUG #17: Floating-Point Precision in Timestamps

**Severity**: LOW
**Location**: `src/formatter.py:250-251`
**Category**: Precision Issue

**Description**:
Duration calculation doesn't account for floating-point precision. Rounding errors in segment duration: `end - start` may not equal stated duration.

**Impact**:
- Minor inconsistencies in transcript timing data
- Confusing for users expecting exact values
- Accumulation of rounding errors

**Suggested Fix**:
```python
duration = round(seg['end_time'] - seg['start_time'], 3)
```

**Priority**: LOW

---

### BUG #18: Missing ChromaDB Settings Validation

**Severity**: LOW
**Location**: `src/langchain/vector_store.py:36-41`
**Category**: Error Handling

**Description**:
ChromaDB initialization doesn't validate Settings() config validity. Invalid config could silently fail or cause database corruption.

**Impact**:
- Vector store may be non-functional
- No clear error message
- Difficult to diagnose issues

**Suggested Fix**:
```python
try:
    self.client = chromadb.Client(Settings(...))
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB: {e}")
    raise ValueError("Invalid ChromaDB configuration") from e
```

**Priority**: LOW

---

### BUG #19: Missing None Check in Diarizer Preflight

**Severity**: LOW
**Location**: `src/diarizer.py:687-695`
**Category**: Error Handling

**Description**:
API response attributes are accessed without confirming response is not None. If API call returns None/empty, accessing attributes fails.

**Impact**:
- Preflight check fails ungracefully
- AttributeError instead of clear error message
- Difficult to diagnose API issues

**Suggested Fix**:
```python
if response and hasattr(response, 'status_code'):
    # Access response attributes safely
    ...
else:
    logger.error("API response is invalid or None")
    return ["API connection failed"]
```

**Priority**: LOW

---

### BUG #20: Off-by-One Error in Vector Store IDs

**Severity**: LOW
**Location**: `src/langchain/vector_store.py:89`
**Category**: Logic Error

**Description**:
Batch index in IDs uses `batch_start + i` but should account for total offset across multiple batches. This can cause ID collisions.

**Impact**:
- Duplicate entries in vector store
- Search returns wrong segments
- Inconsistent retrieval results

**Suggested Fix**:
```python
# Use absolute index instead of batch-relative
absolute_index = batch_start + i
segment_id = f"{session_id}_seg_{absolute_index}"
```

**Priority**: LOW

---

### BUG #21: Inconsistent Return Types in Error Paths

**Severity**: LOW
**Location**: `src/diarizer.py:544-546`
**Category**: Type Safety

**Description**:
Function returns empty dict on model unavailability, but sometimes returns implicit None. Inconsistent return types cause AttributeError when code doesn't check type.

**Impact**:
- AttributeError when using return value
- Inconsistent API contract
- Difficult to handle errors

**Suggested Fix**:
```python
# Ensure consistent return type
if model_unavailable:
    return {}  # Explicit empty dict, not None
```

**Priority**: LOW

---

### BUG #22: Unsafe JSON Serialization of Numpy Arrays

**Severity**: LOW
**Location**: `src/diarizer.py:853`
**Category**: Data Serialization

**Description**:
Converting numpy array to list via `.tolist()` works, but embedding shapes aren't validated. Non-serializable numpy types could bypass JSON serialization if array conversion fails.

**Impact**:
- Checkpoint save fails
- Session can't be resumed
- Cryptic serialization errors

**Suggested Fix**:
```python
if not isinstance(embedding, np.ndarray):
    raise TypeError(f"Expected numpy array, got {type(embedding)}")
embedding_list = embedding.tolist()
```

**Priority**: LOW

---

### BUG #23: Missing Input Length Validation

**Severity**: LOW
**Location**: `src/formatter.py:41`
**Category**: Input Validation

**Description**:
Regex substitution doesn't validate input length before processing. Very large session IDs (>1000 chars) could cause regex performance issues.

**Impact**:
- Performance degradation with unusual inputs
- Potential ReDoS (regex denial of service)
- Slow processing for edge cases

**Suggested Fix**:
```python
if len(name) > 255:
    raise ValueError("Session ID too long (max 255 characters)")
```

**Priority**: LOW

---

### BUG #24: Missing Collection Creation Validation

**Severity**: LOW
**Location**: `src/langchain/vector_store.py:43-52`
**Category**: Error Handling

**Description**:
Collections are created with get_or_create but no validation that creation was successful. If collection creation fails silently, downstream operations use uninitialized collections.

**Impact**:
- Vector search fails with unclear error messages
- Difficult to diagnose initialization issues
- Silent failures

**Suggested Fix**:
```python
self.transcript_collection = self.client.get_or_create_collection("transcripts")
assert self.transcript_collection is not None, "Failed to create transcript collection"
```

**Priority**: LOW

---

### BUG #25: Mutable Default Arguments Pattern Risk

**Severity**: LOW
**Location**: `src/intermediate_output.py:85-90`
**Category**: Code Quality

**Description**:
While correctly using dataclass field(default_factory=...), pattern inconsistency exists elsewhere in the codebase. Could allow shared default lists across function calls.

**Impact**:
- Potential state leakage between calls
- Subtle bugs with mutable defaults
- Unexpected behavior in edge cases

**Suggested Fix**:
```python
# Continue using field(default_factory=...) pattern throughout
@dataclass
class Example:
    items: List[str] = field(default_factory=list)  # Correct
```

**Priority**: LOW

---

## Summary by Category

### By Severity
- **Critical**: 3 bugs (Security & Data Loss)
- **High**: 4 bugs (Crashes & Race Conditions)
- **Medium**: 7 bugs (Logic Errors & Resource Leaks)
- **Low**: 11 bugs (Edge Cases & Inconsistencies)

### By Type
- **Security Issues**: 2 (path traversal vulnerabilities)
- **Crash/Stability Issues**: 5 (race conditions, null checks, index bounds)
- **Logic Errors**: 6 (validation, checkpoint handling, configuration)
- **Resource Leaks**: 3 (file handles, memory)
- **Type/Consistency Issues**: 5 (return types, serialization, timestamps)
- **Edge Cases**: 4 (input validation, error handling)

### By Component
- **Audio Processing**: 2 bugs
- **Diarization**: 5 bugs
- **Classification**: 3 bugs
- **Configuration**: 2 bugs
- **Vector Store**: 3 bugs
- **Pipeline**: 3 bugs
- **Formatting**: 2 bugs
- **Other**: 5 bugs

---

## Recommended Fix Priority

### Phase 1: Immediate (Critical Security Issues)
1. **BUG #1** - Path traversal in session directory handling
2. **BUG #2** - Path traversal in audio processing
3. **BUG #3** - Silent configuration data loss

**Estimated Effort**: 4-6 hours
**Impact**: Prevents security vulnerabilities and data loss

---

### Phase 2: High Priority (Stability & Crashes)
4. **BUG #4** - Race condition in manifest writing
5. **BUG #5** - Missing null check in speaker profile mapping
6. **BUG #6** - Index out of bounds in snipper export
7. **BUG #7** - Unhandled network errors in Colab classifier

**Estimated Effort**: 8-12 hours
**Impact**: Prevents crashes and data corruption

---

### Phase 3: Medium Priority (Logic & Resources)
8. **BUG #8** - Potential division by zero
9. **BUG #9** - Missing checkpoint data validation
10. **BUG #10** - Missing bounds checking in segment classification
11. **BUG #11** - Missing configuration value validation
12. **BUG #12** - Resource leak in audio loading
13. **BUG #13** - File handle not closed in error case
14. **BUG #14** - Hardcoded model names
15. **BUG #15** - Timeout value not validated

**Estimated Effort**: 12-16 hours
**Impact**: Improves reliability and prevents resource leaks

---

### Phase 4: Low Priority (Polish & Edge Cases)
16. **BUG #16** through **BUG #25** - Various edge cases and type safety issues

**Estimated Effort**: 10-12 hours
**Impact**: Code quality improvements and edge case handling

---

## Total Estimated Effort
- **Phase 1-3 (Critical through Medium)**: 24-34 hours
- **Phase 4 (Low priority)**: 10-12 hours
- **Total**: 34-46 hours for complete bug resolution

---

## Testing Recommendations

After fixing each bug, add corresponding tests:

1. **Security Tests**: Path traversal attempts, malicious inputs
2. **Concurrency Tests**: Multiple threads accessing shared resources
3. **Error Handling Tests**: Network failures, corrupted data, missing files
4. **Edge Case Tests**: Zero values, empty inputs, extreme values
5. **Integration Tests**: Full pipeline with various configurations

**Test Coverage Goal**: >85% branch coverage

---

## Notes

- All bugs have been verified with specific file locations and line numbers
- Suggested fixes are implementation guidelines, not final code
- Some bugs may have cascading effects when fixed (update tests accordingly)
- Consider adding pre-commit hooks to catch similar issues in the future

**Last Updated**: 2025-11-16
**Maintained By**: Development Team
