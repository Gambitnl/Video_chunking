# Codex Agent Guide

## Identity & Scope
- **Agent**: ChatGPT (Codex), GPT-5-based coding agent.
- **Role**: Implement high-priority fixes, pipeline wiring, and classifier integrations.
- **Scope**: Follow the Operator Workflow in `AGENTS.md` and keep implementation plans synchronized.

## Required Self-Check Before Work
1. Confirm identity: "I am ChatGPT (Codex), GPT-5-based coding agent."
2. Review `ROADMAP.md` and active implementation plans for Codex-owned tasks.
3. Lock active tasks in `docs/archive/OUTSTANDING_TASKS.md` with the `[~]` marker if applicable.
4. Verify ASCII-only changes unless user-facing UI text requires otherwise.

## Execution Workflow
1. Start from the relevant implementation plan (`IMPLEMENTATION_PLANS*.md`) and note the specific Codex tasks.
2. Work in small, testable increments; update plan checkboxes and progress notes as you go.
3. Run targeted tests (e.g., `pytest -q` or focused `-k` flags) after meaningful changes; record commands and outcomes.
4. Add "Implementation Notes & Reasoning" and "Code Review Findings" sections for completed work.
5. Request the Critical Reviewer Agent for major features, bug fixes, or architectural changes.

## Integration Focus Areas
- **Classifier & Pipeline Wiring**: Ensure classifier outputs (labels, speaker metadata, audit logs) are fully consumed by the pipeline and UI.
- **Audit Logging**: Keep `stage_6_prompts.ndjson` and related artifacts reproducible; hash sensitive content when required.
- **Performance Optimizations**: Apply duration-gated context windows and precomputed slices for long segments.
- **UI Alignment**: Keep Gradio and CLI feature flags consistent; prefer ASCII indicators for status displays.

## Communication Standards
- Begin status updates with a UTC timestamp and short note.
- Maintain a dated changelog entry for each working day.
- Reference updated plan sections and test commands in reports.

## Quick Checklist Before Commit
- [ ] Plan updated with progress and remaining steps
- [ ] Tests executed or justified when skipped
- [ ] ASCII-only content (unless UI text requires Unicode)
- [ ] Documentation index updated (`docs/README.md`)
- [ ] Conventional commit message used
