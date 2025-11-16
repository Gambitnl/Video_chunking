# CLAUDE.md - AI Assistant Guide

> **Purpose**: Comprehensive guide for AI assistants (Claude, GPT, Gemini) working with this repository
> **Last Updated**: 2025-11-15
> **Repository**: D&D Session Transcription & Diarization System

---

## Quick Start for AI Assistants

**Read this FIRST if you're new to this repository.**

### Essential Reading Order (15 minutes)
1. **This file (CLAUDE.md)** - You are here
2. **[AGENT_ONBOARDING.md](AGENT_ONBOARDING.md)** - Structured onboarding path
3. **[AGENTS.md](AGENTS.md)** - Repository guidelines and Operator Workflow
4. **[ROADMAP.md](ROADMAP.md)** - Current priorities and planned features

### Repository At A Glance
- **Purpose**: Transform D&D session recordings into searchable transcripts with speaker diarization and IC/OOC classification
- **Stack**: Python 3.10+, faster-whisper, pyannote.audio, Ollama, Gradio
- **Main Interfaces**: CLI (`cli.py`) and Web UI (`app.py`)
- **Core Pipeline**: Audio -> Chunking -> Transcription -> Diarization -> Classification -> Output
- **Status**: Production-ready core pipeline, active feature development

---

## Repository Structure

```
Video_chunking/
+-- src/                          # Core Python modules
    +-- pipeline.py              # Main orchestration pipeline
    +-- audio_processor.py       # M4A -> WAV conversion
    +-- chunker.py               # VAD-based smart chunking
    +-- transcriber.py           # Multi-backend transcription
    +-- diarizer.py              # Speaker identification
    +-- classifier.py            # IC/OOC classification
    +-- formatter.py             # Output generation
    +-- party_config.py          # Party configuration management
    +-- checkpoint.py            # Resumable processing
    +-- knowledge_base.py        # Campaign knowledge extraction
    +-- story_notebook.py        # Narrative generation
    +-- config.py                # Configuration management
    +-- logger.py                # Logging utilities
    +-- ui/                      # UI components
    +-- prompts/                 # LLM prompts
    +-- realtime/                # Real-time processing (experimental)
+-- tests/                        # Pytest test suite
    +-- conftest.py              # Test fixtures and configuration
    +-- integration/             # Integration tests
    +-- system/                  # System-level tests
    +-- test_*.py                # Unit tests
+-- docs/                         # Documentation (ALL docs go here)
    +-- README.md                # Documentation index
    +-- SETUP.md                 # Installation guide
    +-- USAGE.md                 # Usage guide
    +-- QUICKREF.md              # Quick reference
    +-- CRITICAL_REVIEW_WORKFLOW.md  # Review process
+-- .claude/                      # Claude Code configuration
    +-- agents/                  # Agent definitions
        +-- critical-reviewer.md # Critical review agent
    +-- skills/                  # Reusable skills
        +-- campaign-analyzer/   # Campaign analysis skill
        +-- session-processor/   # Session processing skill
        +-- test-pipeline/       # Test running skill
        +-- diagnostics-runner/  # Diagnostics skill
+-- models/                       # Speaker profiles, knowledge base
    +-- knowledge/               # Campaign knowledge files
    +-- character_profiles/      # Character profile JSONs
+-- output/                       # Generated transcripts (timestamped)
+-- temp/                         # Temporary processing files
+-- cli.py                        # Command-line interface
+-- app.py                        # Gradio web interface
+-- app_manager.py                # Background process manager
+-- requirements.txt              # Python dependencies
+-- .env.example                  # Configuration template
+-- README.md                     # Project overview
+-- AGENTS.md                     # Repository guidelines
+-- ROADMAP.md                    # Feature roadmap
+-- IMPLEMENTATION_PLANS*.md      # Detailed implementation plans

DO NOT CREATE FILES OUTSIDE THIS STRUCTURE.
ALL NEW DOCUMENTATION MUST GO IN docs/.
```

---

## The Operator Workflow (CRITICAL)

**This is how ALL work is done in this repository. Follow this religiously.**

```
0. RECONCILE PLANNING ARTIFACTS
   |-> Cross-check ROADMAP.md, IMPLEMENTATION_PLANS*.md, and summaries
   |-> Ensure status, dates, and metrics are synchronized

1. START FROM THE PLAN
   |-> Read relevant section in ROADMAP.md or IMPLEMENTATION_PLANS*.md
   |-> Confirm subtasks you will execute
   |-> NEVER code without reading the plan first

2. WORK IN SMALL STEPS
   |-> Implement ONE subtask at a time
   |-> Update the plan IMMEDIATELY (status checkboxes, progress notes)
   |-> DO NOT leave documentation until the end

3. DOCUMENT REASONING
   |-> Add "Implementation Notes & Reasoning" as you work
   |-> Explain WHY decisions were made, not just WHAT was done
   |-> Record alternatives considered and trade-offs

4. VALIDATE CONTINUOUSLY
   |-> Run tests after each meaningful change (pytest -q)
   |-> Run targeted tests (pytest -k test_name) when appropriate
   |-> Note any test gaps or failures

5. REPORT WITH CONTEXT
   |-> Reference plan sections you advanced
   |-> List exact commands/tests executed
   |-> Point out follow-up actions or open questions

6. REQUEST CRITICAL REVIEW
   |-> After completing implementation, ask: "Is there truly no issues with [feature]?"
   |-> Invoke critical-reviewer agent when appropriate
   |-> Address findings and iterate

7. MERGE AFTER APPROVAL
   |-> Update all related documentation
   |-> Mark tasks as complete
   |-> Push to designated branch
   +-> Loop back to step 1 for next task
```

**Key Principles:**
- Plans are living documents - keep them synchronized
- Document reasoning as you go, not after
- Test continuously, not at the end
- Review skeptically, assume issues exist
- Small steps, frequent updates

---

## Critical Requirements

### 1. Character Encoding: ASCII-Only
**EXTREMELY IMPORTANT**: Use ASCII characters ONLY in all project files.

**Why**: Unicode characters break Windows cp1252 encoding and cause crashes when tools read/write files.

**Rules:**
- Use `->` instead of Unicode arrows
- Use `[x]` instead of emoji checkmarks
- Use `[DONE]`, `[TODO]`, `[BLOCKED]` instead of emoji status indicators
- Use `-`, `*`, or `1.` for bullets instead of decorative glyphs
- Use `WARNING:`, `NOTE:`, `INFO:` instead of emoji icons
- Before editing files, scan for non-ASCII characters and normalize them

**Allowed Exceptions:**
- User-facing UI text where Unicode is intentional
- Content that will never be programmatically processed
- Foreign language content requiring non-ASCII

**When in doubt, stick to ASCII. It works everywhere.**

### 2. Prompt & Changelog Formatting
Every status update or hand-off message must follow these rules:

- Begin with a **Date/Time line** in UTC with a short note:
  ```
  Date: 2025-11-15 14:30 UTC - Started P0-BUG-003 implementation
  ```
- Include a **Changelog** section grouping work by calendar date:
  ```
  ## Changelog
  - 2025-11-15: Fixed audio conversion memory leak in src/audio_processor.py
  - 2025-11-15: Added integration tests for checkpoint system
  ```

### 3. Documentation Organization
**ALL documentation files go in `/docs` directory.**

When adding/updating documentation:
1. Place file in `/docs` directory
2. Update `docs/README.md` index to reflect changes
3. Use ASCII-only characters
4. Follow existing naming conventions

### 4. File Creation Policy
**CRITICAL**: Only create files when absolutely necessary.

- **ALWAYS prefer editing** existing files over creating new ones
- **NEVER create** markdown files proactively (wait for user request)
- **NEVER create** README files unless explicitly asked
- When creating test files, follow `test_*.py` naming convention
- When creating new modules, add to appropriate `src/` subdirectory

---

## Development Standards

### Coding Style
- **Python Version**: 3.10+ with type hints
- **Indentation**: 4 spaces (no tabs)
- **Naming**:
  - Functions/modules: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- **Line Length**: ~100 characters (not strict)
- **Function Size**: Keep under ~50 lines by extracting helpers
- **Imports**: Group by standard lib, third-party, local
- **Type Hints**: Required for all new functions
- **Docstrings**: Required for all public functions and classes

### Code Patterns
- Use `pathlib.Path` over raw strings for file paths
- Use `src/logger.py` for all logging (never `print()`)
- Load settings via `Config.from_env()` not direct `.env` reads
- Surface errors through `StageResult` dataclass with proper status
- Use dataclasses for structured data
- Prefer composition over inheritance

### Example Code Style
```python
"""Module docstring explaining purpose."""
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from .logger import get_logger
from .config import Config

logger = get_logger(__name__)


@dataclass
class ProcessingResult:
    """Result from processing operation."""
    success: bool
    data: Optional[dict] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def process_audio_file(input_path: Path, config: Config) -> ProcessingResult:
    """
    Process audio file with configuration.

    Args:
        input_path: Path to input audio file
        config: Configuration object

    Returns:
        ProcessingResult with success status and data

    Raises:
        ValueError: If input_path does not exist
    """
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        raise ValueError(f"File not found: {input_path}")

    logger.info(f"Processing audio file: {input_path}")
    # Implementation here
    return ProcessingResult(success=True)
```

---

## Testing Standards

### Test Organization
```
tests/
+-- conftest.py              # Fixtures and configuration
+-- test_*.py                # Unit tests (mirror src/ structure)
+-- integration/             # Integration tests
    +-- test_integration_*.py
+-- system/                  # System-level tests
    +-- test_system_*.py
```

### Test Markers
Use pytest markers to categorize tests:
```python
import pytest

@pytest.mark.fast
def test_quick_operation():
    """Fast unit test."""
    pass

@pytest.mark.slow
def test_long_running_operation():
    """Slow integration test."""
    pass

@pytest.mark.requires_api
def test_api_integration():
    """Requires external API."""
    pass
```

### Running Tests
```bash
# Run all tests
pytest -q

# Run fast tests only
pytest -m fast

# Run specific test
pytest -k test_audio_processor

# Run with coverage
pytest --cov=src --cov-report=html

# Run integration tests
pytest tests/integration/
```

### Test Guidelines
- Write tests beside related functionality: `tests/test_<module>.py`
- Mock external services (APIs, file I/O when appropriate)
- Use small WAV fixtures for audio tests
- Aim for >85% branch coverage on new/modified modules
- Test both happy-path and failure modes
- Add smoke tests for pipeline changes
- Keep tests fast (use mocks, small fixtures)

---

## Git Workflow

### Branch Strategy
**CRITICAL**: All development and commits go to your designated feature branch.

Branch naming convention: `claude/<session-id>` (automatically assigned by Claude Code)

### Commit Guidelines
Follow Conventional Commits format:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `docs:` - Documentation changes
- `chore:` - Build/tooling changes
- `style:` - Code style changes (formatting)

**Examples:**
```bash
git commit -m "feat: Add checkpoint system for resumable processing"
git commit -m "fix: Resolve memory leak in audio processor"
git commit -m "test: Add integration tests for diarization"
git commit -m "docs: Update QUICKREF with party config commands"
```

### Commit Best Practices
- Keep commits focused on single concerns
- Include context in commit body for behavior changes
- Reference issue numbers when applicable
- Never commit secrets or API keys
- Clean up `temp/` before committing
- Exclude generated audio segments

### Push Protocol
```bash
# Always use -u flag for new branches
git push -u origin <your-feature-branch>

# If push fails due to network errors, retry up to 4 times with backoff:
# Wait 2s, retry -> Wait 4s, retry -> Wait 8s, retry -> Wait 16s, final retry
```

### Creating Pull Requests
When creating a PR:
1. Provide concise summary of changes
2. List test evidence (`pytest -q` output)
3. Link related issues from ROADMAP.md
4. Include before/after snippets for transcript/log changes
5. Screenshot UI updates from `app.py`
6. Document new env variables in `.env.example`

---

## Available Skills

Skills are specialized agents for specific tasks. Invoke with: `/skill-name`

### Operational Skills
- **session-processor** - End-to-end processing of D&D session videos
- **video-chunk** - Process videos through complete chunking pipeline
- **diagnostics-runner** - Run system diagnostics and health checks
- **test-pipeline** - Run pytest suite with coverage analysis

### Analysis Skills
- **campaign-analyzer** - Extract/summarize campaign knowledge (NPCs, quests, locations)
- **party-validator** - Validate party configuration files

### Debugging Skills
- **debug-ffmpeg** - Debug FFmpeg integration and video/audio processing issues

**Usage Example:**
```
User: "Process the latest session recording"
Assistant: [Invokes session-processor skill]
```

---

## Common Tasks Reference

### Setup & Configuration
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Check setup
python cli.py check-setup
```

### Processing Sessions
```bash
# Web UI (recommended for first-time users)
python app.py

# CLI - Simple
python cli.py process recording.m4a

# CLI - With party config
python cli.py process recording.m4a --party default --session-id "session1"

# CLI - Full options
python cli.py process recording.m4a \
  --session-id "session1" \
  --characters "Thorin,Elara,Zyx" \
  --players "Alice,Bob,Charlie,DM" \
  --num-speakers 4
```

### Party Management
```bash
# List parties
python cli.py list-parties

# Show party details
python cli.py show-party default

# Export/Import
python cli.py export-party default party.json
python cli.py import-party party.json
```

### Character Management
```bash
# List characters
python cli.py list-characters

# Show character
python cli.py show-character "Thorin"

# Export/Import
python cli.py export-character "Thorin" thorin.json
python cli.py import-character thorin.json
```

### Testing
```bash
# Run all tests
pytest -q

# Run fast tests only
pytest -m fast -q

# Run specific test file
pytest tests/test_pipeline.py -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run single test
pytest -k test_audio_conversion
```

### Code Quality
```bash
# Type checking (if mypy configured)
mypy src/

# Linting (if flake8 configured)
flake8 src/

# Format code (if black configured)
black src/
```

---

## Priority System

Features and bugs are prioritized P0-P4:

- **P0**: Critical/Immediate - Bugs, crashes, blocking issues
- **P1**: High Impact - Features that unlock major value
- **P2**: Important Enhancements - Significant improvements
- **P3**: Future Enhancements - Nice-to-have features
- **P4**: Infrastructure & Quality - Technical debt, refactoring

**Always start with P0 items** before moving to lower priorities.

See [ROADMAP.md](ROADMAP.md) for current priorities.

---

## Critical Review Process

### When to Request Critical Review
- After completing any P0-P4 feature
- After bug fixes (ensure completeness)
- After architectural decisions
- After refactoring work
- After API design changes

### How to Invoke Critical Review
**Method 1**: Explicit invocation
```
/critical-reviewer [feature-name]
```

**Method 2**: Challenge pattern (triggers deep analysis)
```
"Is there truly no issues with this solution?"
"Critically review the implementation of [feature]"
"Find issues with this code"
```

### Required Documentation for Review

**All implementations MUST include:**

1. **Implementation Notes & Reasoning** section:
   - Design decisions with justification
   - Alternatives considered
   - Trade-offs made
   - Open questions for reviewers

2. **Code Review Findings** section:
   - Issues identified (with severity levels)
   - Impact analysis and recommendations
   - Positive findings
   - Clear merge recommendation (Approved / Issues Found / Revisions Requested)

### Critical Review Philosophy
- **Skeptical by default**: Assume issues exist until proven otherwise
- **Socratic questioning**: Challenge assumptions, force deeper thinking
- **Systems thinking**: Consider broader impact, not just local fixes
- **Documented reasoning**: Preserve the "why" for future developers
- **Learning feedback loop**: Quality compounds over time

See [docs/CRITICAL_REVIEW_WORKFLOW.md](docs/CRITICAL_REVIEW_WORKFLOW.md) for detailed process.

---

## Environment Variables

Key configuration variables (see `.env.example` for full list):

### API Keys (optional, local-only by default)
```bash
GROQ_API_KEY=           # Groq Cloud API (fast transcription)
OPENAI_API_KEY=         # OpenAI API (alternative transcription)
HF_TOKEN=               # HuggingFace (for pyannote models)
```

### Model Configuration
```bash
LLM_BACKEND=ollama      # ollama, openai, groq
WHISPER_BACKEND=local   # local, groq, openai
WHISPER_MODEL=large-v3  # large-v3, medium, small
OLLAMA_MODEL=qwen2.5:7b # Recommended for Dutch
```

### Processing Settings
```bash
CHUNK_LENGTH_SECONDS=600      # 10 minutes
CHUNK_OVERLAP_SECONDS=10      # 10 seconds overlap
AUDIO_SAMPLE_RATE=16000       # 16kHz
CLEAN_STALE_CLIPS=true        # Remove old clips on reprocess
```

### Logging
```bash
LOG_LEVEL_CONSOLE=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_LEVEL_FILE=DEBUG    # More verbose for file logs
AUDIT_LOG_ENABLED=true  # Track all operations
```

---

## Common Pitfalls to Avoid

### DON'T Do This
1. [FAIL] Code without reading the plan -> You'll miss requirements
2. [FAIL] Leave documentation until the end -> Context is lost
3. [FAIL] Skip keeping plan synchronized -> Plan becomes stale
4. [FAIL] Skip tests -> Bugs slip through
5. [FAIL] Not request critical review -> Issues ship to production
6. [FAIL] Use Unicode characters in docs/code -> cp1252 crashes
7. [FAIL] Create files unnecessarily -> Clutters repository
8. [FAIL] Push to wrong branch -> Work gets lost
9. [FAIL] Commit secrets/API keys -> Security vulnerability
10. [FAIL] Use `print()` for logging -> Use `logger` instead

### DO This Instead
1. [DONE] Start from the plan -> Read before coding
2. [DONE] Document as you go -> Update plan after each subtask
3. [DONE] Keep plan synchronized -> Plan is single source of truth
4. [DONE] Write tests continuously -> Test as you implement
5. [DONE] Request skeptical review -> "Is there truly no issues?"
6. [DONE] Use ASCII only -> Works everywhere
7. [DONE] Edit existing files -> Prefer editing over creating
8. [DONE] Verify branch -> Check before pushing
9. [DONE] Use .env -> Never hardcode secrets
10. [DONE] Use logger -> Proper logging infrastructure

---

## Key Patterns & Idioms

### Pipeline Stage Pattern
All pipeline stages follow this pattern:
```python
from src.pipeline import StageResult
from src.constants import PipelineStage, ProcessingStatus

def _stage_name(self, context: Dict[str, Any]) -> StageResult:
    """Execute stage_name stage."""
    result = StageResult(
        stage=PipelineStage.STAGE_NAME,
        status=ProcessingStatus.RUNNING
    )
    result.start_time = datetime.now()

    try:
        # Do work
        result.data = {"key": "value"}
        result.status = ProcessingStatus.COMPLETED
    except Exception as e:
        logger.error(f"Stage failed: {e}")
        result.errors.append(str(e))
        result.status = ProcessingStatus.FAILED
    finally:
        result.end_time = datetime.now()

    return result
```

### Configuration Pattern
```python
from src.config import Config

# Always load config this way
config = Config.from_env()

# Access settings
sample_rate = config.audio_sample_rate
model_name = config.whisper_model
```

### Logging Pattern
```python
from src.logger import get_logger

logger = get_logger(__name__)

# Use appropriate log levels
logger.debug("Detailed debugging information")
logger.info("General information")
logger.warning("Warning but not critical")
logger.error("Error occurred")
logger.critical("Critical failure")
```

### Party Config Pattern
```python
from src.party_config import PartyConfigManager

manager = PartyConfigManager()

# Load party
party = manager.load_party("default")

# Access party data
characters = party.characters
players = party.players
dm_name = party.dm_name
```

---

## Troubleshooting

### Common Issues

**Issue**: Pipeline fails at chunking with "0 chunks generated"
- **Cause**: Audio file too short or VAD settings too strict
- **Fix**: Check audio duration, adjust VAD threshold, use smaller test file

**Issue**: Unicode errors when running on Windows
- **Cause**: Non-ASCII characters in source files
- **Fix**: Replace all Unicode with ASCII equivalents

**Issue**: Out of memory during transcription
- **Cause**: Large audio files with local Whisper
- **Fix**: Use smaller chunk size, use cloud API, or add more RAM

**Issue**: Ollama connection refused
- **Cause**: Ollama not running
- **Fix**: Start Ollama (`ollama serve`) and pull model

**Issue**: Tests failing with "fixture not found"
- **Cause**: Missing test fixtures or incorrect test structure
- **Fix**: Check `tests/conftest.py` for fixture definitions

**Issue**: Git push fails with 403
- **Cause**: Branch name doesn't match session ID format
- **Fix**: Ensure branch starts with `claude/` and matches session ID

---

## Architecture Deep Dive

### Processing Pipeline Flow
```
User Input (M4A/MP3/WAV file)
    |
    v
[1] AUDIO_CONVERSION (src/audio_processor.py)
    - Convert to 16kHz mono WAV via FFmpeg
    - Validate audio properties
    |
    v
[2] CHUNKING (src/chunker.py)
    - VAD-based silence detection (Silero)
    - 10-minute max chunks with 10s overlap
    - Prevent word splitting at boundaries
    |
    v
[3] TRANSCRIPTION (src/transcriber.py)
    - faster-whisper (local) OR Groq/OpenAI (cloud)
    - Dutch language optimization
    - Word-level timestamps
    |
    v
[4] OVERLAP_MERGING (src/merger.py)
    - LCS algorithm to merge overlaps
    - Remove duplicates at chunk boundaries
    - Preserve timestamps
    |
    v
[5] DIARIZATION (src/diarizer.py)
    - pyannote.audio speaker embeddings
    - Cluster speakers (SPEAKER_00, SPEAKER_01, ...)
    - Map to party config (Alice, Bob, DM, ...)
    |
    v
[6] IC_OOC_CLASSIFICATION (src/classifier.py)
    - Ollama LLM analysis
    - Semantic understanding (no audio cues)
    - Confidence scoring
    |
    v
[7] OUTPUT_GENERATION (src/formatter.py)
    - Full transcript (IC + OOC)
    - IC-only transcript
    - OOC-only transcript
    - JSON data
    - SRT subtitles (optional)
    |
    v
Output Directory: output/YYYYMMDD_HHMMSS_<session_id>/
    - session_id_full.txt
    - session_id_ic_only.txt
    - session_id_ooc_only.txt
    - session_id_data.json
    - session_id_full.srt
```

### Key Components

**AudioProcessor** (`src/audio_processor.py`)
- FFmpeg wrapper for format conversion
- Audio validation and normalization
- Handles M4A, MP3, WAV, FLAC inputs

**HybridChunker** (`src/chunker.py`)
- Silero VAD for voice activity detection
- Smart chunk splitting at natural pauses
- 10-minute max with 10-second overlap
- Prevents word splitting

**TranscriberFactory** (`src/transcriber.py`)
- Multi-backend support (local, Groq, OpenAI)
- faster-whisper for local processing
- Dutch language optimization
- Rate limiting for APIs

**TranscriptionMerger** (`src/merger.py`)
- LCS (Longest Common Subsequence) algorithm
- Merges overlapping transcriptions
- Removes duplicates
- Preserves accurate timestamps

**DiarizerFactory** (`src/diarizer.py`)
- pyannote.audio integration
- Speaker embedding extraction
- Clustering for speaker identification
- Profile learning across sessions

**ClassifierFactory** (`src/classifier.py`)
- Ollama LLM integration
- IC/OOC semantic analysis
- Context-aware classification
- Confidence scoring

**TranscriptFormatter** (`src/formatter.py`)
- Multiple output format generation
- SRT subtitle export
- Statistics calculation
- Filename sanitization

**CheckpointManager** (`src/checkpoint.py`)
- Save/resume pipeline state
- Prevents data loss on long sessions
- Compressed checkpoint storage

---

## Quick Decision Tree

**Starting a new task?**
```
Have you read ROADMAP.md? -> NO -> Read it first
                           -> YES -> Continue

Is there an implementation plan? -> NO -> Create one or ask for clarification
                                 -> YES -> Read it thoroughly

Is the plan up to date? -> NO -> Update it first
                        -> YES -> Start implementation

Are you following Operator Workflow? -> NO -> Go back and follow it
                                     -> YES -> Proceed

Have you written tests? -> NO -> Write tests
                        -> YES -> Continue

Have you documented reasoning? -> NO -> Add Implementation Notes
                               -> YES -> Continue

Ready for review? -> Request critical review
```

**Unsure about something?**
```
Is it a coding style question? -> Check AGENTS.md
Is it a test question? -> Check tests/conftest.py examples
Is it a feature priority? -> Check ROADMAP.md
Is it a workflow question? -> Check AGENT_ONBOARDING.md
Is it a technical question? -> Check docs/ directory
Still unsure? -> Ask the user
```

---

## Resources & References

### Documentation
- **Full Documentation Index**: [docs/README.md](docs/README.md)
- **Setup Guide**: [docs/SETUP.md](docs/SETUP.md)
- **Usage Guide**: [docs/USAGE.md](docs/USAGE.md)
- **Quick Reference**: [docs/QUICKREF.md](docs/QUICKREF.md)
- **Critical Review Workflow**: [docs/CRITICAL_REVIEW_WORKFLOW.md](docs/CRITICAL_REVIEW_WORKFLOW.md)

### Planning & Roadmap
- **Feature Roadmap**: [ROADMAP.md](ROADMAP.md)
- **Implementation Plans**: Look for `IMPLEMENTATION_PLANS*.md` in root

### Development
- **Repository Guidelines**: [AGENTS.md](AGENTS.md)
- **Onboarding Guide**: [AGENT_ONBOARDING.md](AGENT_ONBOARDING.md)
- **Project Summary**: [docs/PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)

### External Resources
- **Whisper Models**: https://github.com/openai/whisper
- **pyannote.audio**: https://github.com/pyannote/pyannote-audio
- **Ollama**: https://ollama.ai
- **Gradio**: https://gradio.app
- **FFmpeg**: https://ffmpeg.org

---

## Success Checklist

Before considering any task complete, verify:

- [ ] Code follows repository coding style
- [ ] All functions have type hints and docstrings
- [ ] Tests are written and passing (`pytest -q`)
- [ ] Implementation plan is updated with progress
- [ ] "Implementation Notes & Reasoning" section is complete
- [ ] ASCII-only characters used (no Unicode)
- [ ] Changes committed with proper commit message
- [ ] Documentation updated (if applicable)
- [ ] Critical review requested
- [ ] Review findings addressed
- [ ] Changes pushed to correct branch

---

## Final Reminders

1. **Plans are living documents** - Keep them synchronized as you work
2. **Document reasoning as you go** - Don't wait until the end
3. **Test continuously** - After each meaningful change
4. **Review skeptically** - Assume issues exist until proven otherwise
5. **ASCII only** - Prevents encoding issues
6. **Edit, don't create** - Prefer editing existing files
7. **Small steps** - One subtask at a time
8. **Ask when unsure** - Better to clarify than assume

---

## Meta: About This File

**Purpose**: Comprehensive guide for AI assistants working with this codebase

**Maintenance**: Update this file when:
- Major architectural changes occur
- New workflows are established
- New skills/tools are added
- Common pitfalls are discovered
- Best practices evolve

**Target Audience**: Claude, GPT, Gemini, and other AI assistants

**Scope**: Everything an AI assistant needs to work effectively in this repository

---

**Welcome! You're now equipped to contribute effectively to this project.**

**Next Steps:**
1. Read [AGENT_ONBOARDING.md](AGENT_ONBOARDING.md) for structured onboarding
2. Review [ROADMAP.md](ROADMAP.md) to pick your first task
3. Follow the Operator Workflow religiously
4. Ask questions when unsure
5. Request critical review when ready

**Remember**: Quality emerges from dialogue, not perfection on first try.
