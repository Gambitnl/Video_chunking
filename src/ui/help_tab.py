from __future__ import annotations

import gradio as gr
from src.ui.helpers import Placeholders, InfoText, StatusMessages, UIComponents
from src.ui.constants import StatusIndicators as SI


def create_help_tab() -> None:
    gr.Markdown("""
    ## How to Use

    ### First Time Setup

    1. **Install Dependencies**:
       ```bash
       pip install -r requirements.txt
       ```

    2. **Install FFmpeg**:
       - Download from https://ffmpeg.org
       - Add to system PATH

    3. **Setup Ollama** (for IC/OOC classification):
       ```bash
       # Install Ollama from https://ollama.ai
       ollama pull gpt-oss:20b
       ```

    4. **Setup PyAnnote** (for speaker diarization):
       - Visit https://huggingface.co/pyannote/speaker-diarization
       - Accept terms and create token
       - Add `HF_TOKEN=your_token` to `.env` file

    ### Processing a Session

    1. Upload your D&D session recording (M4A, MP3, WAV, etc.)
    2. Enter a unique session ID
    3. List your character and player names (helps with classification)
    4. Click `Process Session`

    ### Tips

    - Use party configurations to reuse character/player lists across sessions.
    - Check the Campaign Library tab after processing to review extracted knowledge.
    - Map speakers after diarization to improve future runs.
    - Use the Diagnostics tab to run targeted pytest suites while iterating.
    """)
