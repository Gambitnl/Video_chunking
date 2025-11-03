# Setup Guide

Complete setup instructions for the D&D Session Transcription system.

## Prerequisites

- **Python 3.10 or higher**
- **FFmpeg** (for audio conversion)
- **8GB+ RAM** (16GB recommended for long sessions)
- **GPU** (optional but highly recommended for faster processing)

## Installation Steps

### 1. Install Python Dependencies

```bash
# Clone or download the repository
cd VideoChunking

# Install Python packages
pip install -r requirements.txt
```

### 2. Install FFmpeg

FFmpeg is required for audio file conversion.

**Windows**:
1. Download from https://www.gyan.dev/ffmpeg/builds/
2. Extract the zip file
3. Add the `bin` folder to your PATH
4. Verify: `ffmpeg -version`

**macOS**:
```bash
brew install ffmpeg
```

**Linux**:
```bash
sudo apt update
sudo apt install ffmpeg
```

### 3. Setup Ollama (for IC/OOC Classification)

Ollama runs the local LLM for classifying in-character vs out-of-character content.

1. **Install Ollama**:
   - Visit https://ollama.ai
   - Download and install for your platform

2. **Download the model**:
   ```bash
   ollama pull gpt-oss:20b
   ```

3. **Verify Ollama is running**:
   ```bash
   ollama list
   ```

### 4. Setup PyAnnote (for Speaker Diarization)

**Note**: This step is **optional** if you plan to use `--skip-diarization` (faster processing, but speakers labeled as "UNKNOWN").

PyAnnote uses gated models that require a HuggingFace token:

1. **Accept model terms** (required before creating token):
   - Visit https://huggingface.co/pyannote/speaker-diarization and accept terms
   - Visit https://huggingface.co/pyannote/segmentation and accept terms
   - Wait for approval (usually instant)

2. **Create HuggingFace account** (if you don't have one):
   - Visit https://huggingface.co/join

3. **Create access token**:
   - Visit https://huggingface.co/settings/tokens
   - Click "Create new token"
   - **Token type**: Select "Read" (not Write or Fine-grained)
   - **Token name**: Enter any name (e.g., "dnd-processor")
   - **Permissions**: Enable "Read access to contents of all public gated repos you can access"
   - Copy the token (starts with `hf_`)

4. **Add token to environment**:
   - Copy `.env.example` to `.env` if you haven't already
   - Add your token: `HF_TOKEN=hf_xxxxxxxxxxxxx`
   - Optional: add `INFERENCE_DEVICE=cuda` to force GPU usage (falls back to CPU if CUDA is unavailable)

**Security note**: The token only needs Read access to download gated models.

### 5. Configure Settings (Optional)

Edit the `.env` file to customize:

```bash
# Copy example config
cp .env.example .env

# Edit with your preferred settings
# You can choose between local processing or API backends
```

**Key settings**:
- `WHISPER_BACKEND=local` - Use local Whisper (free, slower)
- `WHISPER_BACKEND=groq` - Use Groq API (free tier, faster)
- `LLM_BACKEND=ollama` - Use local Ollama (free)
- `INFERENCE_DEVICE=cuda` - Prefer GPU for Whisper and PyAnnote (auto-detects CPU if CUDA is not available)

### 6. Verify Setup

Run the setup checker:

```bash
python cli.py check-setup
```

This will verify:
- ✓ FFmpeg is installed
- ✓ PyTorch is available (with/without CUDA)
- ✓ faster-whisper is installed
- ✓ PyAnnote.audio is installed
- ✓ Ollama is running

## Quick Start

### Using the Web UI (Recommended)

```bash
python app.py
```

Then open http://127.0.0.1:7860 in your browser.

### Using the CLI

```bash
# Basic usage
python cli.py process path/to/session.m4a

# With character and player names
python cli.py process session.m4a \
  --session-id "Session_2024_01_15" \
  --characters "Thorin,Elara,Zyx" \
  --players "Alice,Bob,Charlie,DM"

# Skip optional processing for speed
python cli.py process session.m4a --skip-diarization --skip-classification
```

## Expected Processing Times

For a **4-hour D&D session**:

| Configuration | Time | Notes |
|--------------|------|-------|
| **Local (CPU only)** | ~8-12 hours | Slow but free |
| **Local (GPU)** | ~2-4 hours | Recommended |
| **Groq API** | ~30-60 min | Fast, uses free API |

First run will be slower due to model downloads.

## Troubleshooting

### FFmpeg not found

```
Error: FFmpeg not found
```

**Solution**: Install FFmpeg and add to PATH (see step 2 above)

### Ollama connection failed

```
Error: Could not connect to Ollama
```

**Solution**:
1. Make sure Ollama is installed
2. Start Ollama: `ollama serve` (or it may start automatically)
3. Verify: `ollama list`

### PyAnnote authentication error

```
Error: Cannot access pyannote/speaker-diarization
```

**Solution**:
1. Accept terms at https://huggingface.co/pyannote/speaker-diarization
2. Create token at https://huggingface.co/settings/tokens
3. Add to `.env`: `HF_TOKEN=your_token_here`

### Out of memory

```
Error: CUDA out of memory / RuntimeError: [...]
```

**Solution**:
1. Process shorter audio clips
2. Skip diarization: `--skip-diarization`
3. Use CPU instead of GPU
4. Close other applications

### CUDA not available (GPU not detected)

```
Warning: PyTorch installed (CPU only)
```

**Solution** (if you have an NVIDIA GPU):
1. Install CUDA toolkit from https://developer.nvidia.com/cuda-downloads
2. Reinstall PyTorch with CUDA support:
   ```bash
   pip uninstall torch torchaudio
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

### Transcription quality issues

If transcription has many errors:

1. **Check audio quality**: Single room mic should be as close to speakers as possible
2. **Try different model**: Edit `.env` and set `WHISPER_MODEL=large-v3`
3. **Reduce background noise**: Use audio editing software to clean before processing

## File Structure

After installation, your project should look like:

```
VideoChunking/
├── src/                    # Source code
│   ├── audio_processor.py  # Audio conversion
│   ├── chunker.py          # Audio chunking
│   ├── transcriber.py      # Transcription
│   ├── merger.py           # Overlap merging
│   ├── diarizer.py         # Speaker diarization
│   ├── classifier.py       # IC/OOC classification
│   ├── formatter.py        # Output formatting
│   ├── pipeline.py         # Main orchestration
│   └── config.py           # Configuration
├── output/                 # Generated transcripts (created automatically)
├── temp/                   # Temporary files (created automatically)
├── models/                 # Speaker profiles (created automatically)
├── cli.py                  # Command-line interface
├── app.py                  # Web interface
├── requirements.txt        # Python dependencies
├── .env                    # Your configuration (create from .env.example)
├── README.md              # Project overview
├── SETUP.md               # This file
└── DEVELOPMENT.md         # Development chronicle
```

## Next Steps

1. **Process your first session**: Try with a short clip (10-15 minutes) first
2. **Review outputs**: Check the generated transcripts in `output/`
3. **Map speakers**: Use the speaker management to label SPEAKER_00, etc.
4. **Iterate**: Adjust character names and settings for better results

## Getting Help

- Check the **Help** tab in the web UI for detailed usage instructions
- Review [README.md](README.md) for project overview
- See [DEVELOPMENT.md](DEVELOPMENT.md) for technical details

## Optional Enhancements

### Using Groq API (Faster Transcription)

1. Create account at https://console.groq.com
2. Get API key from dashboard
3. Add to `.env`: `GROQ_API_KEY=your_key_here`
4. Set: `WHISPER_BACKEND=groq`

### GPU Acceleration

For NVIDIA GPUs:

1. Install CUDA Toolkit 12.1+
2. Install PyTorch with CUDA:
   ```bash
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```
3. Verify: `python -c "import torch; print(torch.cuda.is_available())"`

This can speed up processing by 5-10x!

---

You're all set! Try processing your first D&D session.

## MCP Integrations (Preparation)
1. Install `graphviz` (system + Python) for flowchart tooling.
2. Optional: install `langchain`, `llama-index`, `openai`, `ollama` (pending integration).
3. Update `.env` with backend preferences once agent workflows land.

