# Colab Offload Plan

## Goal
Allow the heavy GPU stages of the D&D Session Processor (audio transcription + diarization) to run inside a Google Colab notebook while keeping the existing desktop UI/workflow intact. Operators should be able to spin up a notebook, run the pipeline against a session, and sync the generated artifacts back to their local `output/` folder with minimal manual steps.

## Scope & Assumptions
- Target stages: Stage 1–5 (audio convert, chunking, transcription, merging, diarization). IC/OOC classification and downstream steps may remain local if needed.
- Colab runtime: single GPU notebook (T4/L4/A100 depending on quota) with 35–50 GB disk.
- Storage: Google Drive mount is acceptable for round-tripping large files (>10 GB).
- Secrets: `.env` values (HF token, etc.) provided via Colab form inputs; no secrets embedded in notebooks.
- UI does not change in this iteration; we supply a CLI-based workflow plus manual sync instructions.

## Architecture Overview
1. **Preparation Script (Local)**  
   - Zips input audio + optional party config metadata.  
   - Uploads to Drive or exposes via temporary download link.
2. **Colab Notebook**  
   - Provision GPU runtime.  
   - Clone repo branch/tag.  
   - Install dependencies (pip install -r requirements + apt install ffmpeg).  
   - Mount Drive (optional) for faster file ingress/egress.  
   - Download session bundle, place in `input/`.  
   - Run `python cli.py process ... --resume` with the desired flags.  
   - Compress `output/<session>` + `_checkpoints/<session>` + `logs/session_processor_*.log`.  
   - Upload artifacts back to Drive/Cloud Storage.
3. **Post-processing (Local)**  
   - Download artifact bundle.  
   - Extract into local `output/` and `_checkpoints/`.  
   - Run `python cli.py resume ...` or open the UI to inspect results.

## Detailed Steps

### 1. Local Preparation
1. `python tools/prepare_session_bundle.py --input path/to/audio.m4a --session-id my_session --campaign campaign_001`
2. Script output:  
   - `bundles/my_session_upload.zip` containing audio + metadata JSON.  
   - MD5 checksum for integrity verification.  
3. Operator uploads the ZIP to Google Drive (e.g., `/MyDrive/video_chunking/sessions/`).

### 2. Colab Notebook Flow
Notebook sections:

1. **Runtime Setup**
   - Check GPU availability (`!nvidia-smi`).  
   - Install system deps: `!apt-get update && apt-get install -y ffmpeg`.  
   - Clone repo: `!git clone https://github.com/Gambitnl/Video_chunking.git`.  
   - `cd Video_chunking`.
2. **Environment**
   - Prompt user for `.env` secrets via `getpass` or text cells.  
   - Write `.env` and run `pip install -r requirements.txt`.
3. **Import Session Bundle**
   - Mount Drive (`from google.colab import drive; drive.mount('/content/drive')`).  
   - Copy `my_session_upload.zip` into `/content/Video_chunking/input/` and extract.  
   - Verify audio exists and is readable.
4. **Processing**
   - Run CLI:  
     ```
     !python cli.py process input/MySession.m4a \
         --session-id my_session \
         --party default \
         --skip-snippets False \
         --skip-knowledge False
     ```
   - Monitor logs; automatically tail `logs/session_processor_*.log`.
5. **Artifact Packaging**
   - `!zip -r /content/my_session_results.zip output/2025... _checkpoints/my_session logs/session_processor_*.log`
   - Move ZIP to Drive.
6. **Optional: Upload to Cloud Storage**
   - Provide gcloud instructions for teams that prefer a bucket instead of Drive.

### 3. Local Resume
1. Download `my_session_results.zip` to `F:\Repos\VideoChunking\colab_results\`.  
2. Extract contents into repo root, ensuring `output/` and `_checkpoints/` merge.  
3. Run `python cli.py resume my_session` (if additional stages needed) or open the Gradio UI to see the session in “Review Results”.

## Automation Enhancements
- **Colab Form Inputs**: Use `widgets` to capture session ID, command-line flags, and Drive paths.
- **Integrity Check**: Compare MD5 before and after transfer to ensure audio integrity.
- **Optional REST Hook**: Add a lightweight Flask server (ngrok) to report progress back to the desktop UI.

## Risks & Mitigations
- **Large Upload Times**: 3–4 hour sessions (~1–2 GB) may take minutes to upload. Mitigation: compress with FLAC or run Stage 1 locally before bundling.
- **Colab Timeouts**: Long diarization runs may exceed 12-hour limits. Mitigation: enable checkpointing and persist `_checkpoints` to Drive mid-run.
- **Dependency Drift**: Ensure Colab uses the same `requirements.txt` hash; pin versions or install via `pip install -r requirements-colab.txt`.
- **Secrets Exposure**: Never hard-code tokens. Use Colab forms plus `os.environ` and avoid saving `.env` to Drive unless encrypted.

## Next Steps
1. Implement `tools/prepare_session_bundle.py` and `tools/import_session_bundle.py`.
2. Create `notebooks/colab_pipeline.ipynb` with the outlined cells.
3. Document workflow in `docs/COLAB_OFFLOAD_PLAN.md` (this file) and update `docs/README.md`.
4. Add QA checklist to ensure artifacts rehydrate cleanly locally.
5. Optional: add CLI commands `python tools/colab_upload.py` / `colab_download.py`.
