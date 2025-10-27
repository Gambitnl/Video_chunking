from __future__ import annotations

import gradio as gr

from src.config import Config
from src.ui.helpers import Placeholders, InfoText, StatusMessages, UIComponents
from src.ui.constants import StatusIndicators as SI


def create_configuration_tab() -> None:
    try:
        import torch

        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_name = torch.cuda.get_device_name(0)
            gpu_count = torch.cuda.device_count()
            cuda_version = torch.version.cuda
            gpu_status = f"[SUCCESS] **{gpu_name}** (CUDA {cuda_version})"
            if gpu_count > 1:
                gpu_status += f" | {gpu_count} GPUs detected"
        else:
            pytorch_version = torch.__version__
            if "+cpu" in pytorch_version:
                gpu_status = "[INFO] **CPU-only PyTorch installed** - No GPU acceleration"
            else:
                gpu_status = "[INFO] **No GPU detected** - Using CPU"
    except Exception as exc:
        gpu_status = f"[ERROR] **Error checking GPU**: {exc}"

    gr.Markdown(f"""
    ### Current Configuration

    - **Whisper Model**: {Config.WHISPER_MODEL}
    - **Whisper Backend**: {Config.WHISPER_BACKEND}
    - **LLM Backend**: {Config.LLM_BACKEND}
    - **Chunk Length**: {Config.CHUNK_LENGTH_SECONDS}s
    - **Chunk Overlap**: {Config.CHUNK_OVERLAP_SECONDS}s
    - **Sample Rate**: {Config.AUDIO_SAMPLE_RATE} Hz
    - **Output Directory**: {Config.OUTPUT_DIR}

    ### GPU Status

    - **GPU Acceleration**: {gpu_status}

    To change settings, edit the `.env` file in the project root.

    **What this tab tells you**
    - Confirms which transcription and LLM backends are active before you launch a run.
    - Shows chunking parameters so you can double-check overlap and duration when troubleshooting alignment issues.
    - Mirrors the effective output and temp directories, useful when you are processing from an alternate drive.

    **When GPU data matters**
    - If GPU acceleration reads as CPU-only, install CUDA-enabled PyTorch or ensure the right Python environment is active.
    - Multi-GPU rigs display the primary device name; switch devices via `CUDA_VISIBLE_DEVICES` if you want to target another card.

    **Next steps**
    - Need to tweak defaults? Update `.env`, then reload this tab (or restart the app) to verify the new values.
    - After changing hardware drivers, revisit this tab to confirm the runtime still detects your GPU.
    """)