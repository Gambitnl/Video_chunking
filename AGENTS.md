# Repository Guidelines

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
