# Full Test Environment Setup

This guide walks through spinning up the **complete** D&D Session Processor environment using the same dependencies and runtime components that power production runs. Follow these steps when you want to validate the full transcription/diarisation/classification flow rather than a mocked demo.

## 1. Prerequisites

- **Python 3.10+**
- **FFmpeg** available on your `PATH`
- (Optional) **CUDA/cuDNN** if you plan to leverage GPU acceleration for Whisper or PyAnnote models

## 2. Create an isolated Python environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 3. Install project dependencies

Install the full dependency set used by the pipeline:

```bash
pip install -r requirements.txt
```

> **Tip:** If you encounter PyTorch/CUDA mismatches, consult [INSTALL_GPT_OSS.md](INSTALL_GPT_OSS.md) or [INSTALL_OLLAMA.txt](INSTALL_OLLAMA.txt) for GPU-specific notes.

## 4. Launch the Gradio preview UI

Start the web UI with the standard configuration:

```bash
python app.py
```

By default Gradio binds to `http://127.0.0.1:7860/`. Upload a test `.m4a`, `.mp3`, or `.wav` file to run the complete pipeline end-to-end. Outputs will be written under `output/<session_id>/` alongside IC-only/OOC-only/JSON exports.

If you prefer a headless run or are operating from a remote server, add `--server.port <PORT>` or `--server.name 0.0.0.0` flags via the `GRADIO_SERVER_PORT` and `GRADIO_SERVER_NAME` environment variables supported by Gradio.

## 5. Alternative: Run via CLI

To process audio without the UI, use the CLI entry point:

```bash
python cli.py process path/to/your_session.m4a \
    --session-id session_2024_01_15 \
    --num-speakers 4
```

Additional options are documented in [USAGE.md](USAGE.md) and [QUICKREF.md](QUICKREF.md).

## 6. Verifying the run

After the job completes, inspect the `output/<session_id>/` directory. You should see:

- `full_transcript.txt`
- `ic_only.txt`
- `ooc_only.txt`
- `transcript.json`
- (Optional) `segments/` folder if snippet export is enabled

Review the console logs for timing information from the chunker, transcriber, diariser, and classifier. Any errors or missing dependencies will surface there for quick troubleshooting.

## 7. Shutting down

Press `Ctrl+C` in the terminal running Gradio or the CLI process once processing is complete. Deactivate the virtual environment with:

```bash
deactivate
```

You're now back to your base shell.
