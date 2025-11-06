# Testing Documentation

> **Last Updated**: 2025-10-24
> **Test Suite Size**: 98 tests
> **Test Framework**: pytest

## Table of Contents

- [Component Test Coverage Map](#component-test-coverage-map)
- [Test Execution Guide](#test-execution-guide)
- [Smoke Testing Checklist](#smoke-testing-checklist)
- [Pipeline Health Check](#pipeline-health-check)
- [Test Categories](#test-categories)
- [Adding New Tests](#adding-new-tests)
- [Troubleshooting](#troubleshooting)

---

## Component Test Coverage Map

### ✅ Components With Tests

| Component | Test File | Test Count | Coverage Notes |
|-----------|-----------|------------|----------------|
| `src/config.py` | `tests/test_config_env.py` | 19 | ✅ Comprehensive - Config helpers, edge cases |
| `src/snipper.py` | `tests/test_snipper.py` | 5 | ✅ Good - Clip export, cleanup, sanitization |
| `src/transcriber.py` | `tests/test_transcriber.py` | 7 | ✅ Good - Factory, backends, lazy loading |
| `src/classifier.py` | `tests/test_classifier.py` | 12 | ✅ Good - Factory, parsing, prompt building |
| `src/diarizer.py` | `tests/test_diarizer.py` | 14 | ✅ Good - Overlap calc, speaker assignment, profiles |
| `src/merger.py` | `tests/test_merger.py` | 1 | ⚠️ Minimal - Only overlap removal tested |
| `src/formatter.py` | `tests/test_formatter.py` | 1 | ⚠️ Minimal - Only filename sanitization tested |
| `src/knowledge_base.py` | `tests/test_knowledge_base.py` | 6 | ✅ Good - Extract, merge, save/load, search |
| `src/analyzer.py` | `tests/test_analyzer.py` | 5 | ✅ Good - OOC keyword analysis |
| `src/audio_processor.py` | `tests/test_audio_processor.py` | 10 | ✅ Good - FFmpeg, conversion, normalization |
| `src/campaign_dashboard.py` | `tests/test_campaign_dashboard.py` | 7 | ✅ Good - Health checks, party config, KB status |
| `src/checkpoint.py` | `tests/test_checkpoint_manager.py` | 2 | ⚠️ Minimal - Save/load, clear |

**Total Covered**: 12 components with 89 unit tests

### ❌ Components Without Tests

| Component | Type | Priority | Risk Level |
|-----------|------|----------|------------|
| `src/pipeline.py` | Orchestrator | **P0** | 🔴 High - Core orchestration logic |
| `src/chunker.py` | Audio Processing | **P0** | 🔴 High - VAD chunking, overlap logic |
| `src/srt_exporter.py` | Output Formatter | P1 | 🟡 Medium - SRT subtitle generation |
| `src/profile_extractor.py` | AI Feature | P1 | 🟡 Medium - Character profile extraction |
| `src/story_generator.py` | AI Feature | P2 | 🟢 Low - Narrative generation |
| `src/character_profile.py` | Data Manager | P1 | 🟡 Medium - Profile CRUD, migration |
| `src/party_config.py` | Data Manager | P2 | 🟢 Low - Party configuration |
| `src/status_tracker.py` | Monitoring | P2 | 🟢 Low - Status JSON tracking |
| `src/logger.py` | Utility | P3 | 🟢 Low - Logging setup |
| `src/google_drive_auth.py` | Integration | P2 | 🟡 Medium - OAuth flow |
| `app.py` | UI | P1 | 🟡 Medium - Gradio interface |
| `app_manager.py` | UI | P2 | 🟢 Low - Status viewer UI |
| `cli.py` | CLI | P2 | 🟢 Low - Command-line interface |

**Total Uncovered**: 13 components (52% coverage by file count)

### 🧪 System & Integration Tests

| Test File | Purpose | Duration | Status |
|-----------|---------|----------|--------|
| `tests/system/test_system.py` | Environment verification | ~30s | ✅ Passing |
| `tests/integration/test_sample.py` | End-to-end pipeline | ~5-10 min | ✅ Passing (marked slow) |

---

## Test Execution Guide

### Quick Reference Commands

```bash
# Fast unit tests only (< 3 seconds)
pytest tests/ -v

# Exclude slow integration tests
pytest -m "not slow" -v

# Run only slow integration tests
pytest -m slow -v

# Run specific component tests
pytest tests/test_config_env.py -v
pytest tests/test_snipper.py -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=html

# System verification (checks dependencies)
python tests/system/test_system.py

# Skip Whisper model loading (faster system check)
python tests/system/test_system.py --skip-whisper
```

### Test Markers

```python
@pytest.mark.slow  # Integration tests that take >1 minute
```

**Note**: Register custom markers by creating `pytest.ini`:

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

---

## Smoke Testing Checklist

### Pre-Release Smoke Test Checklist

**Test Date**: _____________
**Tester**: _____________
**Version/Branch**: _____________

#### ✅ Core Pipeline Tests

| Test | Command | Pass Criteria | Fail Criteria | Status | Notes |
|------|---------|---------------|---------------|--------|-------|
| **Config Loading** | `pytest tests/test_config_env.py -v` | All 19 tests pass | Any test fails | ☐ | |
| **Audio Conversion** | `pytest tests/test_audio_processor.py -v` | All 10 tests pass | Any test fails | ☐ | |
| **Transcription** | `pytest tests/test_transcriber.py -v` | All 7 tests pass | Any test fails | ☐ | |
| **Diarization** | `pytest tests/test_diarizer.py -v` | All 14 tests pass | Any test fails | ☐ | |
| **Classification** | `pytest tests/test_classifier.py -v` | All 12 tests pass | Any test fails | ☐ | |
| **Snippet Export** | `pytest tests/test_snipper.py -v` | All 5 tests pass | Any test fails | ☐ | |

#### ✅ System Verification

| Test | Command | Pass Criteria | Fail Criteria | Status | Notes |
|------|---------|---------------|---------------|--------|-------|
| **Dependencies** | `python tests/system/test_system.py --skip-whisper` | All checks pass, no import errors | Import errors, missing deps | ☐ | |
| **FFmpeg Available** | `python tests/system/test_system.py` | FFmpeg found in PATH or bundle | FFmpeg not found | ☐ | |
| **Ollama Running** | `python tests/system/test_system.py` | Ollama responds on localhost:11434 | Connection refused | ☐ | |
| **Directories** | `python tests/system/test_system.py` | output/, temp/, models/ exist | Dirs missing or not writable | ☐ | |

#### ✅ Integration Tests (Optional - Long Running)

| Test | Command | Pass Criteria | Fail Criteria | Status | Notes |
|------|---------|---------------|---------------|--------|-------|
| **Sample Processing** | `pytest tests/integration/test_sample.py::test_sample_quick -v` | Completes without errors, outputs created | Pipeline crash, missing outputs | ☐ | ~5 min |
| **Full Sample** | `pytest tests/integration/test_sample.py::test_sample_file -v` | Full pipeline with diarization completes | Any stage fails | ☐ | ~10 min |

#### ✅ Manual UI Smoke Tests

| Test | Steps | Pass Criteria | Fail Criteria | Status | Notes |
|------|-------|---------------|---------------|--------|-------|
| **Web UI Launch** | `python app_manager.py` then visit http://localhost:7861 | UI loads, no console errors | UI crashes, 500 errors | ☐ | |
| **CLI Help** | `python cli.py --help` | Help text displays all commands | Command not found, import error | ☐ | |
| **File Upload** | Upload sample audio in Web UI | File accepted, processing starts | Upload rejected, crash | ☐ | |
| **Party Config** | Load party config in UI | Config loads, displays correctly | JSON parse error, blank display | ☐ | |

#### ✅ Critical User Flows

| Flow | Steps | Pass Criteria | Fail Criteria | Status | Notes |
|------|-------|---------------|---------------|--------|-------|
| **Process Session** | 1. Upload audio<br>2. Set options<br>3. Start processing<br>4. View outputs | All stages complete, 4 output files created | Stage fails, no outputs | ☐ | |
| **Resume Checkpoint** | 1. Start processing<br>2. Cancel mid-stage<br>3. Resume from checkpoint | Resumes from correct stage, completes | Restart from beginning, corruption | ☐ | |
| **Speaker Mapping** | 1. Process with diarization<br>2. Map speakers<br>3. Reprocess | Speaker labels applied correctly | Labels ignored, crashes | ☐ | |

---

### New Failure Mode Documentation

**When tests fail in unexpected ways, document them here:**

| Date | Test | Failure Description | Root Cause | Fix Applied | Ticket |
|------|------|---------------------|------------|-------------|--------|
| 2025-10-24 | test_stale_clip_cleanup | Fails on Windows with UnicodeDecodeError | Windows cp1252 encoding doesn't support emoji | Replaced emoji with ASCII | P0-BUG-001 |
| 2025-10-22 | test_invalid_int_env_value_falls_back | No warning logged for empty string | Empty string check missing in bool helper | Added empty string check | P0-BUG-002 |
| | | | | | |

**Instructions**: Add new rows whenever you discover a failure mode not covered by existing tests.

---

## Pipeline Health Check

**IMPORTANT - Cloud/Web-Based Agents:**
- If you are a **cloud-based or web-based AI agent** (e.g., Claude via web interface, ChatGPT, etc.): **SKIP this entire section**
- Cloud agents cannot access local system tools (FFmpeg, Ollama, pip commands)
- Proceed directly to your assigned tasks
- Note in your status: "Health checks skipped - cloud-based agent"

---

### Health Check Components (Local Agents Only)

The `mcp__videochunking-dev__check_pipeline_health()` function verifies all required dependencies and tools are available.

**Implementation**: `mcp_server.py:114-169`

| Component | Check Method | Pass Criteria | Fail Criteria |
|-----------|--------------|---------------|---------------|
| **FFmpeg** | `ffmpeg -version` | Exit code 0 | Command fails or not found |
| **Ollama** | `ollama list` | Exit code 0, lists models | Command fails or not found |
| **faster-whisper** | `pip show faster-whisper` | Package installed | Package not found |
| **pyannote.audio** | `pip show pyannote.audio` | Package installed | Package not found |
| **pydub** | `pip show pydub` | Package installed | Package not found |
| **gradio** | `pip show gradio` | Package installed | Package not found |
| **click** | `pip show click` | Package installed | Package not found |
| **rich** | `pip show rich` | Package installed | Package not found |
| **torch** | `pip show torch` | Package installed | Package not found |
| **groq** | `pip show groq` | Package installed | Package not found |

**Total Checks**: 10 components (1 external tool, 1 AI service, 8 Python packages)

### Health Check Results - Individual Component Logs

**Instructions**:
- Run health check: `mcp__videochunking-dev__check_pipeline_health()`
- Log results for each component below
- **SUCCESS**: Log timestamp only
- **FAILURE**: Log timestamp + failure description + remedy applied

---

#### 1. FFmpeg

| Date/Time (UTC) | Status | Notes / Failure & Remedy |
|-----------------|--------|--------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS |                          |

---

#### 2. Ollama

| Date/Time (UTC) | Status | Available Models / Failure & Remedy |
|-----------------|--------|--------------------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | gpt-oss:20b                            |

---

#### 3. faster-whisper

| Date/Time (UTC) | Status | Version / Failure & Remedy |
|-----------------|--------|----------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 1.2.0                      |

---

#### 4. pyannote.audio

| Date/Time (UTC) | Status | Version / Failure & Remedy |
|-----------------|--------|----------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 3.1.1                      |
| 2025-11-04 07:20 | SUCCESS | v4.0.1 - All 15 diarizer tests passing |

---

#### 5. pydub

| Date/Time (UTC) | Status | Version / Failure & Remedy |
|-----------------|--------|----------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 0.25.1                     |

---

#### 6. gradio

| Date/Time (UTC) | Status | Version / Failure & Remedy |
|-----------------|--------|----------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 5.49.1                     |

---

#### 7. click

| Date/Time (UTC) | Status | Version / Failure & Remedy |
|-----------------|--------|----------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 8.3.0                      |

---

#### 8. rich

| Date/Time (UTC) | Status | Version / Failure & Remedy |
|-----------------|--------|----------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 14.2.0                     |

---

#### 9. torch

| Date/Time (UTC) | Status | Version / Failure & Remedy |
|-----------------|--------|----------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 2.5.1+cu121                |

---

#### 10. groq

| Date/Time (UTC) | Status | Version / Failure & Remedy |
|-----------------|--------|----------------------------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 0.32.0                     |

---

### Summary Log (Overall Health Check Runs)

**Purpose**: Track overall health check execution to avoid unnecessary re-runs.

**Usage** (Local Agents Only):
- **Cloud/web-based agents**: Skip entirely
- **Local agents**: Before running health checks, check this table:
  - If last run was **<24 hours ago** and **status = SUCCESS**: Skip health check
  - If last run was **>24 hours ago** OR **status = FAILURE**: Run health check

| Date/Time (UTC) | Status | Passed | Failed | Duration | Notes |
|-----------------|--------|--------|--------|----------|-------|
| 2025-11-06 12:05:09 UTC | SUCCESS | 10 | 0 | ~20s | Manual health check by agent. |
| 2025-11-04 07:15 | PARTIAL | 2 | 8 | ~5s | FFmpeg + Ollama OK, Python deps check failed (MCP server env issue, packages verified manually) |

**Status Values**:
- `SUCCESS` = All 10 components passed
- `FAILURE` = One or more components failed (see individual component logs)

**Common Remedies**:

| Component | Common Failure | Remedy |
|-----------|----------------|--------|
| FFmpeg | Command not found | Install FFmpeg: `winget install FFmpeg` or download from https://ffmpeg.org/download.html |
| FFmpeg | Not in PATH | Add FFmpeg bin directory to system PATH or place in project root under `ffmpeg/bin/` |
| Ollama | Connection refused | Start Ollama service: `ollama serve` |
| Ollama | Command not found | Install Ollama from https://ollama.ai/download |
| Python packages | Package not found | Run `pip install -r requirements.txt` |
| Python packages | Version mismatch | Reinstall with `pip install --upgrade <package>` |
| torch | CUDA errors | Verify GPU drivers or install CPU-only version: `pip install torch --index-url https://download.pytorch.org/whl/cpu` |

---

## Test Categories

### Unit Tests (Fast - < 3 seconds total)

Located in `tests/test_*.py`

**Purpose**: Test individual functions and classes in isolation
**Speed**: ~0.1-0.5s per file
**Run Command**: `pytest tests/ -v`

**Coverage by Module**:
- Config: 19 tests
- Audio Processing: 10 tests
- Transcription: 7 tests
- Diarization: 14 tests
- Classification: 12 tests
- Other: 27 tests

**Total**: 89 unit tests

### Integration Tests (Slow - 5-10 minutes)

Located in `tests/integration/test_sample.py`

**Purpose**: Test full pipeline with real audio files
**Speed**: 5-10 minutes
**Run Command**: `pytest -m slow -v`

**Tests**:
1. `test_sample_file` - Full pipeline with diarization (~10 min)
2. `test_sample_quick` - Fast pipeline without diarization (~5 min)

### System Tests (Medium - 30 seconds)

Located in `tests/system/test_system.py`

**Purpose**: Verify environment setup and dependencies
**Speed**: ~30s with Whisper, ~5s without
**Run Command**: `python tests/system/test_system.py [--skip-whisper]`

**Checks**:
- Python imports
- FFmpeg availability
- Ollama connection
- Sample file existence
- Directory creation
- Config loading
- Whisper model loading (optional)

---

## Test Pass/Fail Criteria

### ✅ PASS Criteria

**Unit Tests**:
- All assertions pass
- No exceptions raised
- Output matches expected values
- Mock interactions verified
- Cleanup completed (temp files removed)

**Integration Tests**:
- Pipeline completes without errors
- All output files created:
  - `*_full.txt`
  - `*_ic_only.txt`
  - `*_ooc_only.txt`
  - `*_structured.json`
- Output files contain expected structure
- Timestamps are valid
- Speaker labels applied (if diarization enabled)

**System Tests**:
- All dependencies importable
- External tools available (FFmpeg, Ollama)
- Directories writable
- No connection errors

### ❌ FAIL Criteria

**Unit Tests**:
- AssertionError raised
- Unexpected exception
- Mock not called as expected
- Memory leak (temp files not cleaned)
- Timeout (>30s for single test)

**Integration Tests**:
- Pipeline crashes with exception
- Output files missing
- Output format invalid (malformed JSON)
- Timestamps negative or out of order
- Transcription empty when audio contains speech

**System Tests**:
- ImportError for core modules
- FFmpeg not found
- Ollama not running
- Directories not writable
- Sample files missing

**Document New Failure Modes**:
- When a test fails for a reason not listed above, add it to the [New Failure Mode Documentation](#new-failure-mode-documentation) table

---

## Adding New Tests

### Test File Naming Convention

```
tests/test_{component_name}.py
tests/integration/test_{feature_name}.py
tests/system/test_{verification_type}.py
```

### Example Unit Test Template

```python
# tests/test_new_component.py
import pytest
from src.new_component import NewComponent


class TestNewComponent:
    """Unit tests for NewComponent."""

    def test_basic_functionality(self):
        """Test basic operation."""
        component = NewComponent()
        result = component.do_something()
        assert result == expected_value

    def test_error_handling(self, monkeypatch):
        """Test error handling."""
        component = NewComponent()
        with pytest.raises(ValueError):
            component.do_invalid_thing()

    def test_edge_case(self, tmp_path):
        """Test edge case with temp directory."""
        component = NewComponent(output_dir=tmp_path)
        result = component.process_empty_input()
        assert result is None
```

### Example Integration Test Template

```python
# tests/integration/test_new_feature.py
import pytest
from pathlib import Path


@pytest.mark.slow
def test_new_feature_end_to_end(tmp_path):
    """Test new feature from input to output."""
    # Setup
    input_file = Path("tests/fixtures/sample.wav")
    output_dir = tmp_path / "output"

    # Execute
    result = run_new_feature(input_file, output_dir)

    # Verify
    assert output_dir.exists()
    assert (output_dir / "expected_output.json").exists()
    assert result["status"] == "success"
```

### Marking Tests

```python
# Mark slow tests
@pytest.mark.slow
def test_long_running():
    pass

# Parametrize tests
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_with_params(input, expected):
    assert double(input) == expected
```

---

## Test Priority Recommendations

### Priority 0 (Urgent - Missing Critical Coverage)

1. **`src/pipeline.py`** - Full pipeline orchestration
   - Test each stage execution
   - Test stage failure handling
   - Test checkpoint integration
   - **Estimated Effort**: 2-3 days

2. **`src/chunker.py`** - VAD-based chunking
   - Test VAD silence detection
   - Test overlap calculation
   - Test chunk boundary selection
   - **Estimated Effort**: 1 day

### Priority 1 (High - Important Components)

3. **`src/srt_exporter.py`** - Subtitle generation
   - Test SRT formatting
   - Test timestamp precision
   - Test multi-format output
   - **Estimated Effort**: 0.5 days

4. **`src/character_profile.py`** - Profile management
   - Test CRUD operations
   - Test migration from old format
   - Test file I/O edge cases
   - **Estimated Effort**: 1 day

5. **`src/profile_extractor.py`** - AI extraction
   - Test extraction with mock LLM
   - Test parsing and validation
   - **Estimated Effort**: 1 day

### Priority 2 (Medium - Nice to Have)

6. **`app.py`** - Web UI
   - Test file upload handling
   - Test progress updates
   - Test error display
   - **Estimated Effort**: 2 days

7. **`src/google_drive_auth.py`** - OAuth integration
   - Test auth flow with mocked OAuth
   - Test token refresh
   - **Estimated Effort**: 1 day

---

## Troubleshooting

### Common Test Failures

#### "ModuleNotFoundError: No module named 'src'"

**Solution**: Run tests from project root, not from tests/ directory

```bash
# ✅ Correct
cd F:\Repos\VideoChunking
pytest tests/

# ❌ Wrong
cd F:\Repos\VideoChunking\tests
pytest .
```

#### "Unknown pytest.mark.slow"

**Solution**: Create `pytest.ini` to register markers

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

#### Test hangs during Whisper loading

**Solution**: Use `--skip-whisper` flag for system tests

```bash
python tests/system/test_system.py --skip-whisper
```

#### "FFmpeg not found"

**Solution**: Ensure FFmpeg is installed and in PATH

```bash
# Check FFmpeg
ffmpeg -version

# Or place in project root under ffmpeg/bin/
```

#### Cleanup errors (temp files not deleted)

**Solution**: Use `tmp_path` fixture instead of manual cleanup

```python
def test_with_temp(tmp_path):
    # pytest automatically cleans up tmp_path
    output = tmp_path / "output.txt"
    output.write_text("test")
```

---

## CI/CD Integration (Planned)

**Status**: Not yet implemented (see P4-INFRA-002 in IMPLEMENTATION_PLANS_PART4.md)

**Planned GitHub Actions Workflow**:

```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -m "not slow" -v
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3
```

---

## Test Metrics

**Last Run**: 2025-11-04
**Total Tests**: 98
**Passing**: 98
**Failing**: 0
**Skipped**: 0
**Duration**: ~3s (unit tests), ~10min (with integration)

**Recent Test Runs**:
- 2025-11-04: Diarizer tests (15 tests) - All passing in 8.71s
- 2025-10-24: Full suite - 98 tests passing

**Coverage** (estimated):
- By Component: 52% (12/23 files have tests)
- By Lines: Unknown (run `pytest --cov=src` to measure)
- Target: >85% line coverage

---

## Related Documents

- **DEVELOPMENT.md** - Development history with test evolution
- **IMPLEMENTATION_PLANS_PART4.md** - P4-INFRA-001 comprehensive test suite plan
- **CRITICAL_REVIEW_WORKFLOW.md** - Code review process including test requirements

---

**Document Version**: 1.0
**Maintained By**: Development Team
**Next Review**: After Sprint 1 (when pipeline tests are added)
