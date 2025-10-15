# First Time Setup Guide

Quick guide to get your D&D Session Processor up and running.

## 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install all required Python packages including PyTorch, faster-whisper, pyannote.audio, and more.

## 2. Install FFmpeg

FFmpeg is already installed locally in this project at `ffmpeg/bin/ffmpeg.exe`. The system will auto-detect it.

To verify:
```bash
python -c "from src.audio_processor import AudioProcessor; print('FFmpeg OK')"
```

## 3. Install and Configure Ollama

### Install Ollama
Run the installer that was downloaded:
```bash
ollama_setup.exe
```

### Pull the gpt-oss Model
After installation, pull the OpenAI OSS model (12.8GB download):
```bash
ollama pull gpt-oss:20b
```

**Note**: This model requires at least 16GB of RAM. See `INSTALL_GPT_OSS.md` for alternative models.

## 4. Setup PyAnnote for Speaker Diarization

1. Visit https://huggingface.co/pyannote/speaker-diarization-3.1
2. Accept the terms and conditions
3. Create a HuggingFace account if needed
4. Generate an access token at https://huggingface.co/settings/tokens
5. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
6. Add your token to `.env`:
   ```
   HF_TOKEN=hf_xxxxxxxxxxxxx
   ```

## 5. Configure Your Party (Optional but Recommended)

The system includes a default party "The Broken Seekers" with your campaign characters. To customize:

### Option 1: Use the Example Template
```bash
# Copy the example file to create your config
cp models/parties.json.example models/parties.json

# Edit models/parties.json with your character details
```

### Option 2: The Default Party Will Be Created Automatically
When you first run the system, it will automatically create `models/parties.json` with "The Broken Seekers" party. You can then edit this file to match your actual campaign.

### Party Configuration Fields

Edit `models/parties.json` and update:
- **party_name**: Your party's name
- **dm_name**: The DM's name
- **campaign**: Campaign name
- **characters**: List of all characters
  - **name**: Full character name
  - **player**: Player name (use "Player1", "Player2", etc., or actual names)
  - **race**: Character race
  - **class_name**: Character class
  - **description**: Detailed character description (helps IC/OOC classification)
  - **aliases**: Alternative names/nicknames for the character

Example:
```json
{
  "default": {
    "party_name": "My Party Name",
    "dm_name": "John",
    "campaign": "My Campaign",
    "characters": [
      {
        "name": "Character Full Name",
        "player": "Alice",
        "race": "Human",
        "class_name": "Fighter",
        "description": "Description of the character",
        "aliases": ["Nickname", "Short Name"]
      }
    ]
  }
}
```

## 6. Verify Setup

Run the setup checker:
```bash
python cli.py check-setup
```

You should see:
- ✓ FFmpeg: Installed
- ✓ PyTorch: Installed (with CUDA or CPU)
- ✓ faster-whisper: Installed
- ✓ pyannote.audio: Installed
- ✓ Ollama: Running at http://localhost:11434

## 7. Test with Web UI

Start the web interface:
```bash
python app.py
```

Open your browser to: http://127.0.0.1:7860

Try processing a short audio clip (1-2 minutes) to verify everything works.

## 8. Optional: Configure API Keys

If you want to use cloud services for faster processing:

### Groq API (for faster transcription)
1. Get API key from https://console.groq.com
2. Add to `.env`:
   ```
   GROQ_API_KEY=gsk_xxxxxxxxxxxxx
   WHISPER_BACKEND=groq
   ```

### OpenAI API (for classification)
1. Get API key from https://platform.openai.com
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-xxxxxxxxxxxxx
   LLM_BACKEND=openai
   ```

## Troubleshooting

### FFmpeg not found
The system should auto-detect FFmpeg in the `ffmpeg/` directory. If not, check that `ffmpeg/bin/ffmpeg.exe` exists.

### Ollama connection failed
Make sure Ollama is running:
```bash
ollama serve
```

### PyAnnote error: "Unauthorized"
Your HuggingFace token is missing or invalid. Check:
1. You accepted the terms at https://huggingface.co/pyannote/speaker-diarization-3.1
2. Your token is correctly set in `.env`
3. Token has read permissions

### Out of memory
Try:
- Using a smaller model: `qwen2.5:7b` or `llama3.2:3b`
- Skip diarization: `--skip-diarization`
- Skip classification: `--skip-classification`
- Process shorter clips first

### Model download is slow
Models are large:
- gpt-oss:20b: 12.8GB
- faster-whisper large-v3: ~3GB
- pyannote models: ~300MB

Use a stable internet connection for first-time setup.

## Next Steps

Once setup is complete:
1. Read [USAGE.md](USAGE.md) for detailed usage instructions
2. Read [PARTY_CONFIG.md](PARTY_CONFIG.md) to understand party configurations
3. Process your first session!

```bash
# Using CLI
python cli.py process recording.m4a --party default --session-id session1

# Or use the Web UI
python app.py
```

---

For more help, see:
- [SETUP.md](SETUP.md) - Detailed installation guide
- [USAGE.md](USAGE.md) - How to use the system
- [QUICKREF.md](QUICKREF.md) - Quick reference
