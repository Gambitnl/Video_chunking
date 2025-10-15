# Quick Reference Guide

**One-page reference for common tasks.**

## Installation

```bash
pip install -r requirements.txt
# Install FFmpeg from https://ffmpeg.org
# Install Ollama from https://ollama.ai
ollama pull gpt-oss:20b
```

## Basic Usage

### Web UI
```bash
python app.py
# Open: http://127.0.0.1:7860
```

### CLI - Simple
```bash
python cli.py process recording.m4a
```

### CLI - Full Options
```bash
python cli.py process recording.m4a \
  --session-id "session1" \
  --characters "Thorin,Elara,Zyx" \
  --players "Alice,Bob,Charlie,DM" \
  --num-speakers 4
```

### CLI - With Party Config
```bash
# Use pre-configured party (easier!)
python cli.py process recording.m4a \
  --party default \
  --session-id "session1"
```

## Commands

```bash
# Process audio
python cli.py process <file>

# Process with party config
python cli.py process <file> --party default

# Party management
python cli.py list-parties                           # List all parties
python cli.py show-party default                     # Show party details
python cli.py export-party default my_party.json     # Export party
python cli.py import-party my_party.json             # Import party
python cli.py export-all-parties backup.json         # Backup all parties

# Character profiles
python cli.py list-characters                        # List all characters
python cli.py show-character "Name"                  # Show character overview
python cli.py export-character "Name" file.json      # Export character
python cli.py import-character file.json             # Import character

# Map speakers
python cli.py map-speaker <session> <speaker_id> <name>

# View speakers
python cli.py show-speakers <session>

# Check setup
python cli.py check-setup

# View config
python cli.py config
```

## File Outputs

After processing `session.m4a`, you get:

```
output/
├── session_full.txt       # Complete transcript
├── session_ic_only.txt    # Game narrative only
├── session_ooc_only.txt   # Banter only
└── session_data.json      # Structured data
```

**Future**: Session notebooks with perspective transformations (character POV, narrator POV)

## Configuration (.env)

```bash
# Backends
WHISPER_BACKEND=local      # or: groq, openai
LLM_BACKEND=ollama         # or: openai

# Models
WHISPER_MODEL=large-v3
OLLAMA_MODEL=gpt-oss:20b

# Processing
CHUNK_LENGTH_SECONDS=600
CHUNK_OVERLAP_SECONDS=10

# API Keys (optional)
GROQ_API_KEY=
OPENAI_API_KEY=
HF_TOKEN=                  # For PyAnnote
```

## Common Options

```bash
--skip-diarization        # Faster, no speaker labels
--skip-classification     # Faster, no IC/OOC separation
--num-speakers N          # Expected speaker count
--output-dir PATH         # Custom output location
```

## Processing Times

**4-hour session:**
- Local (CPU): ~8-12 hours
- Local (GPU): ~2-4 hours
- Groq API: ~30-60 minutes

## Troubleshooting

| Problem | Solution |
|---------|----------|
| FFmpeg not found | Install FFmpeg, add to PATH |
| Ollama error | Run `ollama serve` |
| PyAnnote error | Set HF_TOKEN in .env |
| Out of memory | Skip diarization/classification |
| Slow processing | Use Groq API or GPU |

## File Structure

```
VideoChunking/
├── src/               # Source code
├── cli.py             # Command-line interface
├── app.py             # Web interface
├── example.py         # Usage examples
├── output/            # Generated transcripts
├── temp/              # Temporary files
├── models/            # Speaker profiles
├── .env               # Your config (copy from .env.example)
└── requirements.txt   # Dependencies
```

## Example Workflow

```bash
# 1. Process
python cli.py process session1.m4a --session-id s1

# 2. Identify speakers from output
cat output/s1_full.txt | head

# 3. Map speakers
python cli.py map-speaker s1 SPEAKER_00 "DM"
python cli.py map-speaker s1 SPEAKER_01 "Alice"
python cli.py map-speaker s1 SPEAKER_02 "Bob"
python cli.py map-speaker s1 SPEAKER_03 "Charlie"

# 4. Verify
python cli.py show-speakers s1

# 5. Use outputs
cat output/s1_ic_only.txt  # Session notes!
```

## Python API

```python
from src.pipeline import DDSessionProcessor

# Option 1: Manual entry
processor = DDSessionProcessor(
    session_id="my_session",
    character_names=["Thorin", "Elara"],
    player_names=["Alice", "Bob", "DM"]
)

# Option 2: Use party config (recommended)
processor = DDSessionProcessor(
    session_id="my_session",
    party_id="default"
)

result = processor.process(
    input_file="session.m4a",
    output_dir="./output"
)

print(result['statistics'])
```

## Output Format Examples

### Full Transcript
```
[00:15:23] DM (IC): Je betreedt een donkere grot.
[00:15:45] Alice as Thorin (IC): Ik steek mijn fakkel aan.
[00:16:02] Bob (OOC): Haha, alweer een grot!
```

### IC-Only
```
[00:15:23] DM: Je betreedt een donkere grot.
[00:15:45] Thorin: Ik steek mijn fakkel aan.
```

### JSON
```json
{
  "segments": [{
    "text": "Je betreedt een donkere grot.",
    "speaker": "DM",
    "classification": "IC",
    "start_time": 923.45,
    "end_time": 928.12
  }]
}
```

## Documentation

- **[README.md](README.md)** - Overview
- **[SETUP.md](SETUP.md)** - Installation
- **[USAGE.md](USAGE.md)** - Detailed guide
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Technical details

---

**Quick help:** `python cli.py --help`
