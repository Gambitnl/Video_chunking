# 🎲 D&D Session Transcription & Diarization System

> **Transform your D&D session recordings into searchable, organized transcripts with automatic speaker identification and in-character/out-of-character separation.**

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start web interface
python app.py

# Or use CLI
python cli.py process your_session.m4a
```

**See [SETUP.md](SETUP.md) for detailed installation instructions.**

## ✨ Features

- **🎤 Multi-Speaker Diarization**: Automatically identify who is speaking
- **🗣️ Dutch Language Support**: Optimized for Dutch D&D sessions
- **🎭 IC/OOC Classification**: Separate in-character dialogue from meta-discussion
- **📊 Multiple Output Formats**: Plain text, IC-only, OOC-only, and JSON
- **🎯 Party Configuration**: Save and reuse character/player setups
- **👤 Character Profiles**: Track character development, actions, inventory, and relationships
- **📖 Session Notebooks** _(Planned)_: Transform transcripts into narrative perspectives
- **💰 Zero Budget Compatible**: 100% free with local models
- **⚡ Fast Processing**: Optional cloud APIs for speed
- **🔄 Learning System**: Speaker profiles improve over time
- **🖥️ Dual Interface**: Web UI and CLI

## 📋 What It Does

### Input
- **4-hour D&D session** recorded on Google Recorder (M4A format)
- **Single room microphone** (not ideally placed)
- **4 speakers**: 3 players + 1 DM
- **All in Dutch**

### Output (4 files)

1. **Full Transcript** - Everything with speaker labels and IC/OOC markers
2. **IC-Only** - Game narrative only (perfect for session notes!)
3. **OOC-Only** - Banter and meta-discussion
4. **JSON** - Complete data for further processing

**Optional:** Enable audio snippet export to save per-segment WAV clips plus a `manifest.json` under `output/segments/<session_id>/`.

### Example Output

```
[00:15:23] DM (IC): Je betreedt een donkere grot. De muren druipen van het vocht.
[00:15:45] Alice as Thorin (IC): Ik steek mijn fakkel aan en kijk om me heen.
[00:16:02] Bob (OOC): Haha, alweer een grot! Hoeveel grotten zijn dit nu al?
[00:16:30] DM (IC): Je ziet in het licht van de fakkel oude runen op de muur.
```

## 📖 Documentation

### Getting Started
- **[SETUP.md](SETUP.md)** - Installation and configuration
- **[FIRST_TIME_SETUP.md](FIRST_TIME_SETUP.md)** - Quick setup guide for new users
- **[USAGE.md](USAGE.md)** - Detailed usage guide with examples
- **[QUICKREF.md](QUICKREF.md)** - One-page command reference
- **[FULL_TEST_ENVIRONMENT.md](FULL_TEST_ENVIRONMENT.md)** - Run the complete pipeline locally for end-to-end validation

### Features
- **[PARTY_CONFIG.md](PARTY_CONFIG.md)** - Party configuration system guide
- **[CHARACTER_PROFILES.md](CHARACTER_PROFILES.md)** - Character profiling and overview generation
- **[SESSION_NOTEBOOK.md](SESSION_NOTEBOOK.md)** - Session notebook and perspective transformations _(planned)_

### Technical
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Technical implementation details

## 🏗️ Architecture Overview

```
M4A Recording
    ↓
Audio Conversion (16kHz mono WAV)
    ↓
Smart Chunking (10-min chunks with 10s overlap)
    ↓
Transcription (Whisper - Dutch optimized)
    ↓
Overlap Merging (LCS algorithm)
    ↓
Speaker Diarization (PyAnnote.audio)
    ↓
IC/OOC Classification (Ollama + Llama 3.1)
    ↓
4 Output Formats (TXT + JSON)
```

## 🛠️ Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Audio Conversion | FFmpeg | Universal format support |
| Voice Detection | Silero VAD | Best free VAD |
| Transcription | faster-whisper | 4x faster, excellent Dutch |
| Diarization | PyAnnote.audio 3.1 | State-of-the-art |
| Classification | Ollama (Llama 3.1) | Free, local, Dutch support |
| UI | Gradio + Click + Rich | User-friendly interfaces |

## 📦 Project Overview

A production-ready system for processing long-form Dutch D&D session recordings with intelligent speaker diarization, character distinction, and in-character/out-of-character (IC/OOC) content separation.

## The Challenge

### Input Characteristics
- **Source**: Google Recorder app (M4A format, convertible to WAV)
- **Duration**: ~4 hours per session
- **Audio Quality**: Single room microphone, not ideally placed
- **Language**: Dutch
- **Speakers**: 3 players + 1 DM (+ rare passersby)

### Complexity Factors
1. **Multi-layered Speaker Identity**
   - Each player has their own voice (persona)
   - Each player voices their character(s) (in-character)
   - DM voices themselves + multiple NPCs
   - Need to distinguish: Player A → Character X vs Player A → OOC

2. **Content Classification**
   - In-character dialogue (game narrative)
   - Out-of-character banter (meta-discussion, jokes, breaks)
   - DM narration vs DM as NPC

3. **Technical Constraints**
   - Zero budget (free APIs/local models only)
   - Dutch language support required
   - Single-mic recording (overlapping speech possible)

## Proposed Architecture

### Phase 1: Audio Processing & Chunking
```
M4A Input → Audio Conversion → VAD Segmentation → Chunks
```

**Tools**:
- **FFmpeg**: Convert M4A to WAV (free, local)
- **Silero VAD** (Voice Activity Detection): Detect speech segments and silence
- **PyAnnote.audio** or **Resemblyzer**: Create speaker embeddings

**Chunking Strategy** (based on research & best practices):
- **Hybrid Approach**: Combine silence detection with fixed-length chunking
  - Primary: Use VAD to detect natural speech pauses
  - Fallback: 10-minute (600 second) maximum chunks if no suitable pause found
- **Overlap**: 10-second overlap between chunks to prevent word splitting
  - Only 1.67% overhead with 10-min chunks
  - Prevents context loss at boundaries
- **Audio Format**: Convert to 16kHz mono WAV/FLAC for optimal Whisper performance
- **Merge Strategy**: Use longest common subsequence (LCS) algorithm to merge overlapping transcriptions without duplicates

**Why This Works**:
- Whisper was trained on 30s segments, but longer chunks (up to 10 min) provide better context
- Groq API and local Whisper both handle longer chunks well
- Overlap prevents cutting words mid-utterance
- Natural pauses (silence) create better semantic boundaries for D&D sessions

### Phase 2: Speaker Diarization
```
Audio Chunks → Speaker Embeddings → Clustering → Speaker Labels
```

**Tools**:
- **PyAnnote.audio** (free, local): State-of-the-art speaker diarization
  - Pre-trained models available
  - Can be fine-tuned with speaker samples
- **Alternative**: Resemblyzer + UMAP/HDBSCAN clustering

**Process**:
1. Extract speaker embeddings from audio
2. Cluster embeddings to identify unique speakers
3. Build speaker profiles over time (learning across sessions)
4. Manual labeling in first session → auto-labeling in subsequent sessions

### Phase 3: Transcription
```
Speaker-labeled Chunks → Whisper API/Local → Dutch Transcription
```

**Tools** (Multiple Options):

1. **Local Whisper** (Recommended for zero budget):
   - `faster-whisper`: Optimized version, 4x faster than original
   - Model: `large-v3` for best Dutch accuracy
   - Fully free, runs on your hardware
   - Supports `verbose_json` for detailed timestamps

2. **Groq API** (Alternative - fast & generous free tier):
   - Uses Whisper models with hardware acceleration
   - Much faster than local processing
   - Free tier: significant daily allowance
   - Good for testing/prototyping

3. **OpenAI Whisper API** (Fallback):
   - 25MB file size limit per request
   - Pay-per-use, but relatively cheap
   - Most reliable Dutch support

**Process**:
1. Transcribe each chunk with `language="nl"` parameter for faster/better results
2. Use `verbose_json` response format for detailed timestamps and word-level data
3. Implement retry logic for API rate limiting (if using Groq/OpenAI)
4. Merge overlapping chunk transcriptions using LCS alignment
5. Associate speaker labels from diarization with transcribed segments

### Phase 4: Character & Context Classification
```
Transcribed Text → LLM Analysis → IC/OOC Classification + Character Attribution
```

**Tools**:
- **Ollama** (free, local LLM): Run GPT-OSS 20B by default (fall back to Llama/Qwen if hardware-limited)
- **Alternative**: GPT-4o-mini API (has free tier)

**Process**:
1. **Semantic Analysis** of transcribed text (no audio cues available):
   - **IC Indicators**: Narrative language, character actions ("I do X"), dialogue in-world context, fantasy/game vocabulary
   - **OOC Indicators**: Meta-discussion about rules/mechanics, real-world topics (food, bathroom breaks), game strategy discussion, laughter/jokes about the game itself
   - **Context clues**: Character names being used vs player names, present tense action vs past tense discussion

2. **LLM Prompt Strategy**:
   - Use context window of surrounding segments (not just individual sentences)
   - Provide character names and player names as reference
   - Ask LLM to classify with confidence scores
   - Use few-shot examples from manually labeled early sessions

3. **Classification Output** for each segment:
   - Speaker: [Player Name | DM]
   - Character: [Character Name | NPC Name | OOC | Narration]
   - Type: [IC | OOC | MIXED]
   - Confidence: 0.0-1.0

4. **Iterative Learning**:
   - Build character voice profiles over sessions
   - Learn common OOC patterns specific to your group
   - User can manually correct classifications to improve future sessions

### Phase 5: Output Generation
```
Classified Segments → Formatting → Multiple Output Formats
```

**Output Formats**:

1. **Full Transcript** (plain text with markers)
```
[00:15:23] DM (Narration): Je betreedt de donkere grot...
[00:15:45] Player1 as CharacterA (IC): Ik steek mijn fakkel aan.
[00:16:02] Player2 (OOC): Haha, weer een grot!
```

2. **IC-Only Transcript** (game narrative only)
```
[00:15:23] DM: Je betreedt de donkere grot...
[00:15:45] CharacterA: Ik steek mijn fakkel aan.
```

3. **Structured JSON** (for further processing)
```json
{
  "segments": [
    {
      "timestamp": "00:15:23",
      "speaker": "DM",
      "character": null,
      "type": "narration",
      "text": "Je betreedt de donkere grot..."
    }
  ]
}
```

## Technology Stack

### Core Components
- **Python 3.10+**: Main language
- **FFmpeg**: Audio conversion
- **PyTorch**: ML framework for models

### Libraries
- `pyannote.audio`: Speaker diarization
- `faster-whisper`: Optimized Whisper transcription (recommended)
- `pydub`: Audio chunking and manipulation
- `silero-vad`: Voice activity detection for smart chunking
- `groq`: Optional API client for faster transcription
- `ollama-python`: Local LLM for IC/OOC classification
- `numpy`, `scipy`: Audio processing utilities

### UI Framework (for future phases)
- **Gradio**: Simple web UI for Python
- **Streamlit**: Alternative with more customization
- Or **Electron + Python backend**: For desktop app

## Development Phases

### MVP (Minimum Viable Product)
1. ✅ Audio conversion (M4A → WAV)
2. ✅ Basic chunking by silence detection
3. ✅ Whisper transcription with timestamps
4. ✅ Simple speaker diarization (PyAnnote)
5. ✅ Plain text output with speaker labels

### Phase 2 Enhancements
- Speaker profile learning across sessions
- IC/OOC classification using LLM
- Character attribution
- Multiple output formats

### Phase 3 Advanced Features
- Web UI for processing and review
- Manual correction interface
- Speaker profile management
- Batch processing multiple sessions

### Phase 4 Polish
- Character voice profile refinement
- Automatic OOC filtering improvement
- Session summary generation
- Search functionality across transcripts

## Success Metrics

- **Accuracy**: >85% speaker identification accuracy
- **Character Attribution**: >80% correct IC/OOC classification
- **Processing Time**: <1x real-time (4hr audio processed in <4hrs)
- **Usability**: Non-technical user can process sessions with <5 min setup

## Known Limitations & Mitigation

| Challenge | Impact | Mitigation |
|-----------|--------|------------|
| Single mic = overlapping speech | Harder to separate speakers | Use stricter VAD, accept some loss |
| DM voices multiple NPCs | Confusion in speaker ID | Use contextual LLM analysis |
| Dutch language support | Fewer pre-trained models | Whisper has excellent Dutch support |
| Zero budget | Limited API calls | Prioritize local models (Whisper, Ollama) |
| Voice similarity (same person, different characters) | Character attribution errors | Learn character patterns over time |
| Long-session audio exports | Per-segment clipping loads full WAV (~450 MB for 4hr) | Recommend 16 GB RAM (documented) or process sessions in smaller blocks |

## Implementation References

These guides informed the chunking and transcription approach:
- [Groq Community: Chunking Audio for Whisper](https://community.groq.com/t/chunking-longer-audio-files-for-whisper-models-on-groq/162) - 10-min chunks with overlap strategy
- [Murray Cole: Whisper Audio to Text](https://murraycole.com/posts/whisper-audio-to-text) - Practical implementation patterns

## Next Steps

1. Set up development environment (Python 3.10+, FFmpeg, dependencies)
2. Implement audio conversion (M4A → 16kHz mono WAV)
3. Implement hybrid chunking (VAD + 10-min max with 10s overlap)
4. Test Whisper transcription quality on sample chunk
5. Implement LCS merge algorithm for overlapping transcriptions
6. Evaluate PyAnnote diarization on sample
7. Build MVP command-line tool
8. Iterate on IC/OOC classification

## IC/OOC Classification Strategy

**Challenge**: There are **no explicit audio or verbal cues** when conversation shifts between in-character and out-of-character.

**Solution**: Post-transcription semantic analysis using LLM reasoning:

### Example Prompting Approach
```
Context: D&D session in Dutch with 3 players + 1 DM
Characters: [CharacterA, CharacterB, CharacterC]
Players: [Player1, Player2, Player3, DM]

Analyze this segment and classify as IC (in-character) or OOC (out-of-character):

Previous segment: "Ik steek mijn fakkel aan en loop de grot in."
Current segment: "Wacht, moet ik daar een perception check voor doen?"
Next segment: "Ja, gooi maar een d20."

Classification: OOC (discussing game mechanics)
Confidence: 0.95
Reason: Discussion about dice rolls and game rules
```

This approach relies on the LLM understanding:
- D&D game context and terminology
- Narrative vs meta-discussion patterns
- Dutch language nuances

---

## 🎯 Project Status

✅ **COMPLETE** - Full production system implemented!

All phases completed:
- ✅ Audio conversion and chunking
- ✅ Multi-backend transcription (local + Groq API)
- ✅ Overlap merging with LCS algorithm
- ✅ Speaker diarization with PyAnnote
- ✅ IC/OOC classification with Ollama
- ✅ Multiple output formats
- ✅ Web UI (Gradio)
- ✅ CLI (Click + Rich)
- ✅ Complete documentation

## 💡 Use Cases

- **Session Notes**: Automatic IC-only transcripts for campaign journal
- **Quote Mining**: Search for memorable moments and quotes
- **Analysis**: Track character speaking time and participation
- **Accessibility**: Make sessions accessible to deaf/hard-of-hearing players
- **Recap Creation**: Quick session recaps from IC-only output
- **Rules Reference**: Find when specific rules were discussed (OOC-only)

## 🔮 Future Enhancements

Planned features (see [SESSION_NOTEBOOK.md](SESSION_NOTEBOOK.md) for details):
- [ ] **Session Notebooks**: Transform IC transcripts into narrative formats
  - [ ] Character first-person POV
  - [ ] Third-person narrator style
  - [ ] Character journal/diary entries
- [ ] SRT subtitle export for video overlay
- [ ] Automatic session summary generation
- [ ] Character emotion/tone detection
- [ ] Combat encounter extraction
- [ ] Multi-session search and analysis
- [ ] Voice cloning for TTS playback

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

## 📝 License

This project is provided as-is for personal use. See individual library licenses for dependencies.

## 🙏 Acknowledgments

- OpenAI Whisper team for excellent multilingual transcription
- PyAnnote.audio team for state-of-the-art diarization
- Ollama team for making local LLMs accessible
- Research from Groq community and Murray Cole for chunking strategies

---

**Built with love for D&D players who want to preserve their campaign memories!** 🎲✨
