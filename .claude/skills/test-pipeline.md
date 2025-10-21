---
skill_name: test-pipeline
description: Run tests for the video processing pipeline
---

# Test Pipeline Skill

Run the test suite for the VideoChunking project.

## What This Skill Does

Executes the test suite and provides detailed feedback on:
- Test coverage
- Passing/failing tests
- Performance metrics
- Code quality issues

## Test Execution

This skill will:
1. Run pytest with appropriate flags
2. Display test results clearly
3. Identify failing tests and provide context
4. Suggest fixes for common test failures

## Usage

When invoked, runs:
```bash
python -m pytest tests/ -v
```

With options for:
- Specific test files
- Coverage reports
- Verbose output
- Marker-based filtering

## Test Categories

The project has tests for:
- **Audio Processing**: `tests/test_audio_processor.py`
- **Transcription**: `tests/test_transcriber.py`
- **Chunking Logic**: `tests/test_chunker.py`
- **Formatting**: `tests/test_formatter.py`
- **Merging**: `tests/test_merger.py`
- **Pipeline Integration**: End-to-end tests

## Output

Provides:
- Test results summary (passed/failed/skipped)
- Detailed failure messages
- Stack traces for errors
- Code coverage percentage (if enabled)
- Suggestions for fixing failures
