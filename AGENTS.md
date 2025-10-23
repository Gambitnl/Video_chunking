# Repository Guidelines

> **New to this repository?** Start with [`AGENT_ONBOARDING.md`](./AGENT_ONBOARDING.md) for a structured onboarding path with step-by-step reading order.

---

## Project Structure & Module Organization
Core Python modules live in `src/`, with `pipeline.py` orchestrating the audio conversion, chunking, transcription, diarization, and IC/OOC classification stages. Supporting components such as `audio_processor.py`, `chunker.py`, `transcriber.py`, and `formatter.py` each focus on a single responsibility; touch only the module that aligns with your change. The Click CLI in `cli.py` and the Gradio app in `app.py` expose the same pipeline, while configuration helpers sit in `src/config.py` and logging utilities in `src/logger.py`. Tests reside in `tests/`; generated artifacts land in `output/`, intermediates in `temp/`, and reusable speaker data in `models/`.

## Build, Test, and Development Commands
- `python -m venv .venv && .venv\Scripts\activate`: set up a local environment.
- `pip install -r requirements.txt`: install runtime and test dependencies.
- `python cli.py process sample.m4a --session-id demo --party default`: run the full pipeline headlessly.
- `python app.py`: launch the Gradio UI for manual runs.
- `pytest -q`: execute the fast unit test suite; add `-k name` for focused runs.

## Coding Style & Naming Conventions
Use Python 3.10+ with 4-space indentation, `snake_case` for functions and modules, and `PascalCase` for classes. Mirror the existing type-hinted, docstring-heavy style (see `src/pipeline.py`) and keep functions under ~50 lines by extracting helpers. Prefer `pathlib.Path` over raw strings, surface logs through `src/logger.py`, and load settings via `Config.from_env` rather than reading `.env` directly. Keep CLI options declarative in `cli.py`, and gate experimental features behind clearly named flags.

## Testing Guidelines
Write unit tests beside related functionality in `tests/test_*.py`, mocking external services and using small WAV fixtures. Aim for meaningful coverage on new logic (roughly >85% branch coverage on touched modules) and assert both happy-path results and failure modes. Run `pytest -q` before committing; when altering the pipeline, add smoke tests for `DDSessionProcessor` that validate generated artifacts end up under `output/`.

## Commit & Pull Request Guidelines
Follow the existing Conventional Commit format (`feat:`, `fix:`, `chore:`, `refactor:`). Keep commits focused on a single concern and include context in the body when behavior changes. For pull requests, provide a concise summary, list test evidence (e.g., ``pytest -q``), link related issues, and attach before/after snippets of transcript output or logs when relevant. Screenshot UI updates from `app.py`, and document env variable additions in `.env.example` within the same PR.

## Environment & Assets
Copy `.env.example` to `.env` and fill in API keys only if you enable external transcription backends; never commit secrets. Large assets such as Whisper models live under `models/` and are ignored by Git. The bundled `ffmpeg/` binaries stay untouched; if you upgrade them, note the source and version in the PR. Clean up `temp/` after debugging, and exclude generated audio segments before sharing branches.

## Documentation Guidelines
To keep the root directory clean, all documentation files should be placed in the `/docs` directory.

When adding a new documentation file or updating an existing one, the index file at `docs/README.md` must also be updated to reflect the changes. This index serves as a table of contents for the project's documentation.

### Character Encoding: ASCII-Only
**IMPORTANT**: Keep all shared project files (markdown, code, configs) ASCII-only unless there's a specific technical requirement for Unicode.

**Why**: Unicode characters (arrows, emojis, special symbols) break Windows cp1252 encoding and cause issues when tools read/write files programmatically.

**Rules**:
- Use ASCII equivalents: write `->` instead of Unicode arrows, `[x]` instead of emoji checkmarks, `[ ]` instead of decorative boxes
- Avoid emojis in documentation: use text labels instead (e.g., `WARNING:` rather than emoji icons)
- Bullets: use `-`, `*`, or `1.` instead of decorative bullet glyphs
- Status indicators: prefer `[DONE]`, `[TODO]`, `[BLOCKED]` instead of emoji checkmarks/crosses
- Arrows in diagrams: use `->`, `<-`, `|`, `v` for flowcharts

**Allowed exceptions**:
- User-facing UI text where Unicode is intentional
- Content that will never be programmatically processed
- Foreign language content that requires non-ASCII characters

**When in doubt**: Stick to ASCII. It works everywhere.

## Operator Workflow

To stay aligned with the repository's planning cadence, follow this loop whenever you pick up work:

1. **Start from the plan** - read the relevant section in `IMPLEMENTATION_PLANS*.md` (or ROADMAP) before touching code and confirm the subtasks you are executing.
2. **Work in small steps** - implement one subtask at a time and update the plan immediately (status checkboxes, progress notes, new decisions). Do not leave documentation until the end.
3. **Document reasoning** - add or append the "Implementation Notes & Reasoning" block as you make decisions so future reviewers see the "why", not just the "what".
4. **Validate continuously** - run targeted tests (unit, integration, or `pytest -k`) after each meaningful change, capture the exact command, and note any gaps.
5. **Report with context** - when responding to the user, reference the plan section(s) you advanced, list tests executed, and point to any follow-up actions or open questions.

This keep-the-plan-in-sync workflow is required for both human contributors and AI agents; it ensures that implementation documents remain the single source of truth and that critical review can proceed without guesswork.

## AI Agent Workflows

### Critical Reviewer Agent

**Location**: `.claude/agents/critical-reviewer.md`

This project uses a **Critical Reviewer Agent** methodology for rigorous code review. The agent applies skeptical analysis and Socratic questioning to find issues before they reach production.

#### When to Use

Invoke the Critical Reviewer agent for:
- Completed implementations (any P0-P4 feature)
- Bug fixes (ensure completeness, prevent regression)
- Architectural decisions (validate design choices)
- Refactoring work (confirm improvements don't introduce issues)
- API design (review public interfaces)

#### How to Invoke

**Explicit invocation**:
```
/critical-reviewer [feature-name]
```

**Challenge pattern** (triggers deep analysis):
```
"Is there truly no issues with this solution?"
"Critically review the implementation of [feature]"
"Find issues with this code"
```

#### Required Documentation

**IMPORTANT**: All implementations must include:

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

See `IMPLEMENTATION_PLANS.md` for complete templates and examples.

#### Philosophy

The Critical Reviewer methodology embodies:
- **Skeptical by default**: Assume issues exist until proven otherwise
- **Socratic questioning**: Challenge assumptions, force deeper thinking
- **Systems thinking**: Consider broader impact, not just local fixes
- **Documented reasoning**: Preserve the "why" for future developers

This creates a **learning feedback loop** where quality compounds over time.

#### Example Reviews

See implementation plans for real examples:
- **P0-BUG-001**: Clean implementation ([DONE] Approved)
- **P0-BUG-002**: Issues found ([LOOP] Revisions Requested - 6 issues documented)

For detailed workflow, see: **[docs/CRITICAL_REVIEW_WORKFLOW.md](./docs/CRITICAL_REVIEW_WORKFLOW.md)**
