# Live Review Implementation Plan (Maximal)
> Drafted: 2025-11-20 | Scope: Real-time transcription/diarization/classification visibility with operator steering and partial reruns.

## Guiding Principles
- Stream early, never block pipeline progress on UI.
- Edits apply to completed chunks only; override store is append-only with audit.
- Downstream consumers read merged view (base data + overrides) without full restarts.
- Transport first (events), then minimal read-only UI, then edits, then reruns.

## Sequenced Plan
1) **Preflight decisions**
   - Lock transport choice: WebSocket primary, SSE fallback.
   - Define allowed override fields: speaker_id, character_tag, ic_ooc, text, confidence_flag.
   - Choose storage: `output/<session>/overrides/overrides.jsonl` (append-only) plus `overrides_index.json` for quick reads.
   - Pick batching: emit events per chunk with up to 20 segments per payload.

2) **Event schema and emitters (pipeline)**
   - Add shared dataclass/schema for live events (stage, chunk_id, segment_id, timings, speaker, ic_ooc, confidences, text, model, status).
   - Instrument Stage 3/4/5/6 to emit batch events after each chunk and a stage-start/complete summary.
   - File targets: `src/pipeline.py`, `src/transcriber.py`, `src/diarizer.py`, `src/classifier.py`; keep emissions behind a feature flag (e.g., `LIVE_STREAM_ENABLED`).
   - Tests: unit for serializer and a noop transport stub that records emissions.

3) **Server transport layer**
   - Add lightweight WS/SSE broadcaster that accepts event objects and fans out to subscribers.
   - Handle backpressure (queue with drop policy -> summary) and client disconnects.
   - File targets: `src/server/live_stream.py` (new) + wiring hook in `app.py`.
   - Tests: integration with fake subscriber; ensure pipeline runs if broadcaster is absent.

4) **Client data model + cache**
   - Define client-side models keyed by session_id + segment_id; store in memory and IndexedDB/localStorage for refresh resilience.
   - Implement coalescing and throttling (e.g., render every 250ms).
   - File targets: `src/ui/live_session_tab.py` or new `src/ui/live_review_store.py`.
   - Tests: JS/py unit (depending on UI layer) for merge and dedupe.

5) **UI v1 (read-only stream)**
   - Live timeline with status badges (Transcribed, Diarized, Classified, Needs Attention).
   - Detail grid: time, speaker, IC/OOC, character, text, confidences; filters for low confidence, unknown speaker, OOC.
   - Mini waveform for current chunk; basic playback controls.
   - File targets: `app.py` (Gradio layout) + new `src/ui/live_review_components.py`.
   - Tests: UI smoke for component construction; snapshot of empty and sample data states.

6) **Override input + persistence**
   - Enable edits on completed chunks: speaker reassignment dropdown, IC/OOC toggle, character autocomplete, text inline edit, “mark uncertain.”
   - Write overrides to JSONL with audit fields (user, timestamp, reason); update in-memory state immediately.
   - File targets: new `src/overrides/store.py`, UI hooks in live review components.
   - Tests: store append/read, conflict resolution (last write wins), audit fields present.

7) **Applying overrides to pipeline view**
   - Merge overrides when building artifacts for downstream stages (classification, knowledge, snippets).
   - Guard so live run consumes overrides in-memory; resume path loads `overrides.jsonl`.
   - File targets: `src/pipeline.py` merge utilities; `src/formatter.py` or stage readers.
   - Tests: unit for merge logic; ensure unchanged segments passthrough.

8) **Partial rerun/replay**
   - Add APIs to queue reclassify/re-diarize subsets (by chunk or segment range) using current overrides/prompt.
   - Update intermediates (stage 5/6) and emit events for rerun results; maintain history per rerun.
   - File targets: `src/pipeline.py` (rerun entrypoints), `src/classifier.py` and `src/diarizer.py` hooks; UI actions to trigger rerun and display results.
   - Tests: rerun on small fixture; ensure only targeted segments change and history is recorded.

9) **Role and safety controls**
   - Add viewer vs editor flag; block edits if read-only.
   - Confirmation modal for batch apply; undo last apply.
   - File targets: UI components + overrides store (undo buffer).
   - Tests: role enforcement and undo behavior.

10) **Observability and resilience**
    - Metrics: event throughput, drop counts, rerun counts, override counts.
    - Logging: concise banners for degraded mode or missing models mid-run.
    - Tests: simulate backpressure; ensure pipeline continues if live channel fails.

11) **Rollout milestone gates**
- M1: Events + transport + read-only UI (phases 2-5).
- M2: Overrides write + merge into downstream view (phase 6-7).
- M3: Partial rerun + history (phase 8).
- M4: Roles, undo, resilience polish (phase 9-10).

## Parallelizable Workstreams
- Transport layer (phase 3) can proceed in parallel with the event schema work (phase 2) once the shared schema is defined.
- Client data model/cache (phase 4) and read-only UI (phase 5) can move in parallel after a sample event payload is agreed.
- Override store/persistence (phase 6) can start while UI edit surfaces are built, as long as the append-only format is fixed.
- Pipeline override merge (phase 7) can proceed in parallel with rerun plumbing (phase 8) after the override format is frozen.
- Role/safety UX (phase 9) and observability (phase 10) can be handled by separate owners once the base UI and transport are stable (post-M1).

## Open Questions
- Multi-operator support now or later? (Concurrency and conflict UI not in M1/M2.)
- Prompt/model variant flips exposed in UI, or fixed in config?
- Throughput expectations to size queues and default throttle intervals.
