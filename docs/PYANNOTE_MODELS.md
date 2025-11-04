# Pyannote Gated Model Reference

This document records key information from the gated pyannote repositories used by the project. The goal is to expose setup steps, licensing, and performance context without requiring every teammate to authenticate against Hugging Face just to read the model cards.

## Access Requirements

- Install `pyannote.audio` (`pip install pyannote.audio`).
- Accept the user conditions for each gated repository before first use.
- Create a Hugging Face access token and store it locally (the project expects `.env` to provide `HF_TOKEN`).
- Provide the token to `Pipeline.from_pretrained` or `Model.from_pretrained` via the `token` or `use_auth_token` argument.
- The default embedding model is `pyannote/wespeaker-voxceleb-resnet34-LM`. Override it by setting `PYANNOTE_EMBEDDING_MODEL` in `.env` if you prefer a different checkpoint.

## pyannote/segmentation-3.0 ("Powerset" Speaker Segmentation)

- License: MIT.
- Input shape: 10 second mono chunks sampled at 16 kHz (stereo is downmixed automatically when pipelines load audio).
- Output: `(num_frames, 7)` powerset encoding covering non-speech, single speakers (1, 2, 3), and overlapping pairs (1+2, 1+3, 2+3).
- Training data: AISHELL, AliMeeting, AMI, AVA-AVD, DIHARD, Ego4D, MSDWild, REPERE, VoxConverse.
- Typical usage:

```python
from pyannote.audio import Model
model = Model.from_pretrained(
    "pyannote/segmentation-3.0",
    use_auth_token="YOUR_HF_TOKEN",
)
```

- Convert the powerset output to multilabel using `pyannote.audio.utils.powerset.Powerset`.
- Downstream pipelines:
  - Voice activity detection: `VoiceActivityDetection(segmentation=model)`
  - Overlapped speech detection: `OverlappedSpeechDetection(segmentation=model)`
- Note: This model processes short windows only; pair it with a diarization pipeline to stitch full recordings.

## pyannote/speaker-diarization-3.1

- License: MIT.
- Requires `pyannote.audio >= 3.1`; both segmentation and embedding stages run in PyTorch (no ONNX Runtime dependency).
- Function: End-to-end diarization that downmixes to mono and resamples to 16 kHz as needed.
- Usage:

```python
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token="YOUR_HF_TOKEN",
)
diarization = pipeline("audio.wav")
with open("audio.rttm", "w") as rttm:
    diarization.write_rttm(rttm)
```

- GPU support: `pipeline.to(torch.device("cuda"))`.
- Processing from memory: supply `{"waveform": waveform, "sample_rate": sample_rate}` after loading with `torchaudio`.
- Monitoring: wrap calls with `ProgressHook` to track pipeline progress.
- Speaker bounds: provide `num_speakers`, `min_speakers`, and `max_speakers` arguments to steer clustering when prior knowledge exists.
- Embedding: The pipeline pairs with the `pyannote/wespeaker-voxceleb-resnet34-LM` embedding by default (configurable via `PYANNOTE_EMBEDDING_MODEL`).
- Benchmarks: Evaluated with the "Full" diarization error rate settings (no forgiveness collar, overlap counted) on AISHELL-4, AliMeeting, AMI (IHM/SDM), AVA-AVD, CALLHOME, DIHARD 3, Ego4D, REPERE, VoxConverse, and more. Refer to the upstream README for full DER/FA/Miss/Conf breakdowns.

## pyannote/speaker-diarization-community-1

- License: CC-BY-4.0.
- Positioned as an improved community pipeline with better DER than the legacy 3.1 release, enhanced speaker counting, and exclusive diarization that simplifies transcript alignment.
- Usage mirrors the 3.1 pipeline:

```python
from pyannote.audio import Pipeline
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1",
    token="YOUR_HF_TOKEN",
)
output = pipeline("audio.wav")
for turn, speaker in output.speaker_diarization:
    print(f"{speaker} speaks between t={turn.start:.3f}s and t={turn.end:.3f}s")
```

- Offline mode: artifacts can be cached for later use without internet access.
- Benchmark snapshot (2025-09):
  - AISHELL-4: 11.7% DER vs. 12.2% for legacy 3.1.
  - AliMeeting: 20.3% vs. 24.5%.
  - AMI IHM: 17.0% vs. 18.8%.
  - AMI SDM: 19.9% vs. 22.7%.
  - AVA-AVD: 44.6% vs. 49.7%.
  - CALLHOME: 26.7% vs. 28.5%.
  - DIHARD 3: 29.9% vs. 33.7%.
  - Ego4D: 44.5% vs. 47.8%.
  - MSDWild: 52.6% vs. 57.7%.
  - REPERE: 27.6% vs. 31.5%.
  - VoxConverse: 5.1% vs. 5.9%.
- Premium `precision-2` (pyannoteAI) offers additional accuracy improvements where subscription access is available.
- Exclusive diarization: ensures non-overlapping turns, making it easier to align transcripts and feed downstream IC/OOC classification.
- Hosted option: `pyannote/speaker-diarization-community-1-cloud` provides managed inference on pyannoteAI.

## Operational Notes

- Handle access tokens securely; `.env` already contains `HF_TOKEN` and is ignored by Git. Load tokens through `Config.from_env` rather than hardcoding.
- Production planning: pyannote highlights pyannoteAI as a managed alternative with lower latency and support SLAs. Compare against self-hosted pipelines during deployment design.
- Maintenance: repeat this documentation capture when new community or precision releases appear so local docs remain aligned with upstream guidance.
