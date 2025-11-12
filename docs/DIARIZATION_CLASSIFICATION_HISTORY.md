# Diarization & IC/OOC Classification Run Log

## Purpose

- Track the health of Stage 5 (speaker diarization) and Stage 6 (IC/OOC classification) so we can explain why the pipeline has not progressed to Stage 7/8.
- Capture historical issues, mitigations, and pending work with references back to `IMPLEMENTATION_PLANS.md` and `docs/BUG_HUNT_TODO.md`.
- Give operators a single place to review blockers before launching another long-running session.

## Terminology & Metric Labels

- `processing_time`: Wall-clock runtime for a pipeline stage. Example: Stage 1 finished in 18.00 seconds.
- `audio_length`: Total length of the input recording. Example: Stage 1 logged 13,315.8 seconds of source audio.
- Action item: rename the Stage 1 UI labels so `processing_time` (runtime) and `audio_length` (session length) are no longer both called "duration". Track this inside the UI logging backlog.

## Latest Pipeline Snapshot (Session 6 - 2025-11-12)

| Stage | Status | processing_time | Notes |
| --- | --- | --- | --- |
| Stage 1 - Audio Conversion | Completed | 18.00 s | Session length 13,315.8 s. Needs clearer label split (see above). |
| Stage 2 - Chunking | Completed | 176.00 s | Produced 23 chunks. |
| Stage 3 - Transcription | Completed | ~30 min | All 23 chunks transcribed. |
| Stage 4 - Merge Overlaps | Completed | < 2 s | Overlap reconciliation succeeded. |
| Stage 5 - Speaker Diarization | Completed with over-segmentation | ~9 min | Finished after PyAnnote initialization but still emitted 20 speaker labels and upgrade warnings. |
| Stage 6 - IC/OOC Classification | Blocked by Groq rate limits | < 1 min (before pause) | `llama-3.3-70b-versatile` hit the Groq daily token limit; classification is waiting for cooldown or fallback. |
| Stage 7 - Output Generation | Not reached | n/a | Downstream stages remain unverified on current branch. |
| Stage 8 - Audio Snippet Export | Not reached | n/a | Awaiting successful classification. |

## Timeline of Notable Events

| Date (UTC) | Stage | Event | Status | Reference |
| --- | --- | --- | --- | --- |
| 2025-11-03 | Stage 5 | P0-BUG-007 - Restored Hugging Face token handling and CUDA defaults so PyAnnote can initialize | [DONE] | `IMPLEMENTATION_PLANS.md` (P0-BUG-007) |
| 2025-11-07 | Stage 5 | P0-BUG-009 - Normalized embedding outputs (torch vs numpy) and hardened extraction loop | [DONE] | `IMPLEMENTATION_PLANS.md` (P0-BUG-009) |
| 2025-11-07 | Stage 6 | P0-BUG-010 - Added low-VRAM retries plus optional `OLLAMA_FALLBACK_MODEL` for memory errors | [DONE] | `IMPLEMENTATION_PLANS.md` (P0-BUG-010) |
| 2025-11-07 | Stage 5 | BUG-20251107-01 - `num_speakers` ignored, causing 20 detected speakers instead of 4 | [TODO] | `docs/BUG_HUNT_TODO.md` |
| 2025-11-07 | Stage 6 | BUG-20251107-02 - No progress logging during 5,726 segment classification runs | [TODO] | `docs/BUG_HUNT_TODO.md` |
| 2025-11-07 | Stage 6 | BUG-20251107-03 - Classification still 1 segment per LLM call; batching not implemented | [TODO] | `docs/BUG_HUNT_TODO.md` |
| 2025-11-12 | Stage 5 & 6 | P0-BUG-011 - Work in progress to tame PyAnnote warnings, add CUDA->CPU fallback, and throttle Groq API calls | [IN PROGRESS] | `IMPLEMENTATION_PLANS.md` (P0-BUG-011) |
| 2025-11-12 | Stage 5 | Session `test_s6_nov12_1111am` completed diarization but still produced 20 speaker labels (ignoring `num_speakers=4`) and repeated checkpoint upgrade warnings | [ACTIVE] | Session log (Stage 5) |
| 2025-11-12 | Stage 6 | Groq `llama-3.3-70b-versatile` returned immediate 429 TPD errors, so classification is stalled pending cooldown/fallback | [BLOCKED] | Session log (Stage 6) |

## Stage 5 - Speaker Diarization Details

- **Authentication + Device Defaults** `[DONE 2025-11-03]`
  - Hugging Face tokens now flow through `Config` into `SpeakerDiarizer`, and CUDA is preferred when available. Operators still need valid `HF_TOKEN` entries in `.env`.
- **Embedding Output Changes** `[DONE 2025-11-07]`
  - `_embedding_to_numpy` eliminates `'numpy.ndarray' object has no attribute 'numpy'` crashes by normalizing tensors, arrays, and `SlidingWindowFeature` objects and wrapping per-speaker extraction in `try/except`.
- **Ignored `num_speakers`** `[TODO]`
  - PyAnnote still estimates speakers automatically because `num_speakers` is never passed to `pipeline(...)`. The 2025-11-12 run produced 20 speaker IDs even though the UI was configured for four, confirming the regression. Fix requires wiring the parameter through `pipeline.py` and `SpeakerDiarizer`.
- **CUDA Illegal Memory Access** `[IN PROGRESS]`
  - P0-BUG-011 tracks the CPU fallback path after the first CUDA `illegal memory access` plus migration of PyAnnote checkpoints to silence Lightning warnings. Need validation run once the fallback lands.
- **Operational Noise & Checkpoint Upgrades**
  - Deprecated `torchaudio` backend setters, `torch.load(weights_only=False)` future warnings, and Lightning upgrade notices still spam the console. The latest run surfaced `loss_func.W` mismatch messages plus a recommendation to run `python -m pytorch_lightning.utilities.upgrade_checkpoint ...`. P0-BUG-011 adds targeted warning filters so diarization logs stay readable, but we still need to perform (or script) the checkpoint upgrade or switch loads to `weights_only=True`.
- **Alternative Execution Paths**
  - `docs/COLAB_OFFLOAD_PLAN.md` describes running Stages 1-5 inside Colab to leverage a clean GPU environment. This is useful while local CUDA issues persist, though it still requires the fixes above.

## Stage 6 - IC/OOC Classification Details

- **Ollama Memory Exhaustion** `[DONE 2025-11-07]`
  - Low-VRAM retry plus optional `OLLAMA_FALLBACK_MODEL` protect against `memory layout cannot be allocated (500)` errors when using `gpt-oss:20b`. A preflight warning now surfaces when RAM is below the model requirement.
- **Groq Rate Limits** `[IN PROGRESS]`
  - P0-BUG-011 adds a token-bucket `RateLimiter` gated by `GROQ_MAX_CALLS_PER_SECOND` and `GROQ_BURST_SIZE`. The 2025-11-12 session hit Groq's daily token quota (100k TPD) immediately, and the classifier began backing off in 1-8 second increments while waiting ~5 minutes for quota to reset. Until the limiter and a fallback path are in place, Groq runs may stall mid-stage.
- **Zero Progress Visibility** `[TODO]`
  - BUG-20251107-02 specifies periodic log and UI updates every 50 segments, ETA calculation, and `StatusTracker` wiring. Without this, operators cannot tell whether Stage 6 is alive during multi-hour runs.
- **Sequential Request Model** `[TODO]`
  - BUG-20251107-03 tracks batched classification. The current one-call-per-segment approach yields 5,726 Ollama or Groq requests for Session 6 (~3 hours). Batching (10-20 segments) plus prompt templates should reduce cost and runtime by roughly 90 percent.
- **Stage Completion Gap**
  - No recent pipeline run has reached Stage 7, so we still lack evidence that classification outputs integrate with manifests and snippet exporters. Keep `--skip-classification` available for debugging runs, but resume end-to-end validation once the above blockers clear.

## Alternative Strategies & Considerations

- **Device & Backend Overrides**: `INFERENCE_DEVICE`, `--skip-diarization`, and `--skip-classification` flags remain viable for partial runs, but they hide bugs. Document the reason here whenever they are used.
- **Remote Execution**: The Colab offload path (Stages 1-5) plus local Stage 6 isolates whether diarization failures stem from environment drift or code regressions.
- **Model Choices**: Operators can swap between local Ollama (`gpt-oss:20b`, `llama3.1:8b`) and Groq/OpenAI classifiers. Record the selected model pair for each session before launching a long job.

## Open Actions

1. Wire `num_speakers` through `SpeakerDiarizer` and `pipeline.py`, then re-run Session 6 to confirm exactly four speakers. (Refs: BUG-20251107-01)
2. Land and validate the CUDA->CPU fallback plus warning filters from P0-BUG-011; capture before/after log samples.
3. Implement Stage 6 progress logging and ETA reporting so the UI no longer appears frozen. (Refs: BUG-20251107-02)
4. Add batched classification with configurable batch size and regression tests. (Refs: BUG-20251107-03)
5. Complete the Groq rate limiter work, add a guard for daily token quotas, then schedule classification runs using Groq and (if quota exhausted) Ollama low-VRAM settings to compare throughput.
6. Rename Stage 1 duration labels in the UI/logs to `processing_time` vs `audio_length` for clarity, then update this document with the new wording.
7. Run the PyTorch Lightning checkpoint upgrade (or load with `weights_only=True`) for cached PyAnnote models so diarization logs stop emitting upgrade warnings each run.

## References

- `IMPLEMENTATION_PLANS.md` - P0-BUG-007, P0-BUG-009, P0-BUG-010, P0-BUG-011.
- `docs/BUG_HUNT_TODO.md` - Stage 5/6 bug backlog (num_speakers, progress logging, batching).
- `docs/COLAB_OFFLOAD_PLAN.md` - Remote execution plan for Stages 1-5.
- `docs/USAGE.md` - Flags for skipping diarization/classification during focused debugging runs.
