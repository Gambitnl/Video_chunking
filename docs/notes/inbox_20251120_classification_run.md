# Inbox Notes - 2025-11-20 Classification Run

Context: Captured TODOs from the 2025-11-20 app log while a test session run was in progress. This is a parking lot to avoid conflicts with pending TODO list changes; merge into the main backlog after syncing remote PRs. Each item includes action, rationale (log evidence), and a quick verification note.

- [TODO] Classification logging (Stage 6)
  - Action: In `src/classifier.py` (or stage 6 runner), log model/endpoint/parameters at start; emit periodic progress (segments done/total, elapsed/ETA) per batch; add final summary with duration, total/class breakdown, unknown-label counts, and any fallbacks.
  - Rationale: Stage 6 currently silent until warnings; no progress visibility. Evidence: 20:22:21 start -> only warnings at 21:26/21:26/22:17.
  - Verify: Run a small session and confirm Stage 6 logs start config, periodic progress lines, and a final summary.

- [TODO] Unknown label handling (`DM_NARRATION`)
  - Action: Map `DM_NARRATION` to a valid class or tighten the prompt/validation; log the first few offending labels and a count before defaulting to IC.
  - Rationale: Warnings for segments 572, 593, 2325 defaulted to IC. Evidence: warnings at 21:26:06, 21:26:43, 22:17:12.
  - Verify: Classification run shows zero unhandled label warnings, and mapping logic is covered by a unit test.

- [TODO] Model availability guardrail
  - Action: At Stage 6 start, check Ollama/model availability and fail fast with guidance if none; allow fallback chain if configured.
  - Rationale: Ollama connected with zero models; warnings that `qwen2.5:7b` may not be available. Evidence: 20:21:56 and 20:22:21 logs.
  - Verify: With no models installed, pipeline surfaces a clear error and does not silently proceed; with a valid model, Stage 6 starts normally.

- [TODO] Session list hygiene (UI)
  - Action: Filter `_checkpoints` and dirs missing `data.json` before feeding dropdown choices.
  - Rationale: Dropdown warning about `_checkpoints` and repeated “No data.json” warnings during index build.
  - Verify: UI dropdown shows only valid sessions; log is free of `_checkpoints` and missing `data.json` warnings during index build.

- [TODO] Missing artifacts handling
  - Action: Either regenerate `data.json` for incomplete runs or hide those dirs during index/build; add a single summary warning with counts.
  - Rationale: Multiple “No data.json” warnings for dated session folders; noisy and possibly broken entries.
  - Verify: Index build reports a concise summary (e.g., skipped N sessions missing data.json) and proceeds without repeated per-dir warnings.

- [TODO] Diarization stack version warnings
  - Action: Decide on accepted versions or document remediation for PyAnnote/Lightning/Torch mismatch warnings during Stage 5 initialization.
  - Rationale: Warnings about checkpoint upgrades and version skew were emitted; potential stability/perf risk.
  - Verify: Documented matrix in troubleshooting or a code-side guard that logs a concise “known mismatch accepted” line; no unexpected crashes in Stage 5 init.
