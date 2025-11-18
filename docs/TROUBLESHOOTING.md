# Troubleshooting Guide

This guide provides solutions to common problems you might encounter while using the D&D Session Processor.

---

## Table of Contents

1. [Installation & Setup Issues](#installation--setup-issues)
2. [Ollama Connection Issues](#ollama-connection-issues)
3. [API Key & Authentication Issues](#api-key--authentication-issues)
4. [Processing Errors](#processing-errors)
5. [GPU & Performance Issues](#gpu--performance-issues)
6. [Configuration Issues](#configuration-issues)
7. [Windows-Specific Issues](#windows-specific-issues)
8. [Testing Issues](#testing-issues)
9. [Git Workflow Issues](#git-workflow-issues)
10. [Advanced Troubleshooting](#advanced-troubleshooting)

---

## Installation & Setup Issues

### Error: "FFmpeg not found" or "ffmpeg: command not found"

**Problem:**
The pipeline fails immediately with an error indicating FFmpeg is not installed or not in PATH.

**Cause:**
FFmpeg is required for audio file conversion but is not installed or not accessible in your system PATH.

**Solution:**

**Windows:**
1. Download FFmpeg from https://www.gyan.dev/ffmpeg/builds/
2. Extract the zip file to a folder (e.g., `C:\ffmpeg`)
3. Add the `bin` folder to your PATH:
   - Search for "Environment Variables" in Windows search
   - Click "Environment Variables" button
   - Under "System variables", find and select "Path"
   - Click "Edit" -> "New"
   - Add `C:\ffmpeg\bin` (or your extraction path)
   - Click OK on all dialogs
4. Open a new command prompt and verify: `ffmpeg -version`

**macOS:**
```bash
brew install ffmpeg
ffmpeg -version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
ffmpeg -version
```

**Still not working?**
- Restart your terminal/IDE after adding to PATH
- Ensure you opened a NEW terminal window (old ones won't see PATH changes)
- Try the full path: `C:\ffmpeg\bin\ffmpeg.exe -version` (Windows)

---

### Error: "Python version 3.10 or higher required"

**Problem:**
The application fails to start or dependencies fail to install due to Python version mismatch.

**Cause:**
The project requires Python 3.10+ for type hints and modern features.

**Solution:**

1. **Check your Python version:**
   ```bash
   python --version
   # or
   python3 --version
   ```

2. **Install Python 3.10+:**
   - **Windows**: Download from https://www.python.org/downloads/
   - **macOS**: `brew install python@3.11`
   - **Linux**: `sudo apt install python3.11`

3. **Use the correct Python binary:**
   ```bash
   # If multiple versions are installed
   python3.11 -m venv .venv
   .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate  # Windows
   ```

---

### Error: "No module named 'faster_whisper'" or dependency import errors

**Problem:**
Import errors when running the application despite installing requirements.

**Cause:**
Dependencies not installed, wrong Python environment, or incomplete installation.

**Solution:**

1. **Verify you're in the virtual environment:**
   ```bash
   # Should show (.venv) prefix in terminal
   # If not, activate it:
   .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate  # Windows
   ```

2. **Reinstall dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Check for installation errors:**
   ```bash
   pip list | grep faster-whisper
   # Should show: faster-whisper x.x.x
   ```

4. **Nuclear option (fresh install):**
   ```bash
   # Delete virtual environment
   rm -rf .venv  # Linux/Mac
   rmdir /s .venv  # Windows

   # Recreate
   python3.11 -m venv .venv
   .venv/bin/activate
   pip install -r requirements.txt
   ```

---

## Ollama Connection Issues

### Error: "Failed to connect to Ollama at http://localhost:11434"

**Problem:**
The pipeline fails during IC/OOC classification with an `OllamaConnectionError`.

**Cause:**
Ollama server is not running, not installed, or running on a different port.

**Solution:**

1. **Check if Ollama is installed:**
   ```bash
   ollama --version
   ```

   If not installed, visit https://ollama.ai and download for your platform.

2. **Start Ollama server:**
   ```bash
   # Method 1: Start server explicitly
   ollama serve

   # Method 2: Start in background (macOS/Linux)
   nohup ollama serve > /dev/null 2>&1 &

   # Windows: Start from Start Menu or run as service
   ```

3. **Verify Ollama is running:**
   ```bash
   # Test connection
   curl http://localhost:11434/api/tags

   # Or list models
   ollama list
   ```

4. **Check custom port configuration:**
   If Ollama is running on a different port, update `.env`:
   ```bash
   OLLAMA_BASE_URL=http://localhost:YOUR_PORT
   ```

---

### Error: "Model 'qwen2.5:7b' not found" or model not available

**Problem:**
Ollama connects but the specified model is not available.

**Cause:**
The model has not been downloaded to your local machine.

**Solution:**

1. **Check available models:**
   ```bash
   ollama list
   ```

2. **Download the required model:**
   ```bash
   # Default recommended model
   ollama pull qwen2.5:7b

   # Or alternative models (see .env.example)
   ollama pull llama3.2:8b
   ollama pull llama3.2:3b
   ollama pull gpt-oss:20b  # Requires 16GB+ VRAM
   ```

3. **Verify download completed:**
   ```bash
   ollama list
   # Should show your model with size
   ```

4. **Update .env if using different model:**
   ```bash
   OLLAMA_MODEL=llama3.2:8b
   ```

**Memory Issues:**
If model download fails or Ollama crashes during loading:
- Use a smaller model: `llama3.2:3b` (2GB) instead of `qwen2.5:7b` (4.7GB)
- Configure fallback model in `.env`:
  ```bash
  OLLAMA_MODEL=qwen2.5:7b
  OLLAMA_FALLBACK_MODEL=llama3.2:3b
  ```

---

### Ollama server crashes or runs out of memory

**Problem:**
Ollama starts but crashes when processing or shows OOM (Out Of Memory) errors.

**Cause:**
Insufficient RAM or VRAM for the selected model.

**Solution:**

1. **Check your system resources:**
   - **qwen2.5:7b**: Requires 8GB RAM (minimum)
   - **llama3.2:8b**: Requires 8GB RAM
   - **llama3.2:3b**: Requires 4GB RAM
   - **gpt-oss:20b**: Requires 16GB+ RAM/VRAM

2. **Use a smaller model:**
   ```bash
   # In .env
   OLLAMA_MODEL=llama3.2:3b
   ```

3. **Configure Ollama memory limits:**
   ```bash
   # Set environment variable before starting Ollama
   export OLLAMA_MAX_LOADED_MODELS=1
   export OLLAMA_NUM_PARALLEL=1
   ```

4. **Close other applications:**
   Free up RAM by closing browsers, IDEs, and other memory-intensive apps.

---

## API Key & Authentication Issues

### Error: "Groq API key required. Set GROQ_API_KEY in .env"

**Problem:**
Processing fails when using Groq transcription backend.

**Cause:**
`WHISPER_BACKEND=groq` is set but no API key is configured.

**Solution:**

1. **Get a Groq API key:**
   - Visit https://console.groq.com
   - Sign up for an account
   - Generate an API key

2. **Add key to .env:**
   ```bash
   GROQ_API_KEY=gsk_your_api_key_here
   WHISPER_BACKEND=groq
   ```

3. **Or switch to local transcription:**
   ```bash
   WHISPER_BACKEND=local
   # No API key needed, uses local faster-whisper
   ```

---

### Error: "OpenAI API key required. Set OPENAI_API_KEY in .env"

**Problem:**
Similar to Groq error, but for OpenAI backend.

**Solution:**

1. **Get an OpenAI API key:**
   - Visit https://platform.openai.com/api-keys
   - Create an account
   - Generate an API key

2. **Add key to .env:**
   ```bash
   OPENAI_API_KEY=sk-your_api_key_here
   WHISPER_BACKEND=openai
   ```

3. **Or switch to local transcription:**
   ```bash
   WHISPER_BACKEND=local
   ```

---

### Error: "HuggingFace token invalid" or pyannote model access denied

**Problem:**
Diarization fails with authentication errors when accessing pyannote models.

**Cause:**
Missing or invalid HuggingFace token, or model access not granted.

**Solution:**

1. **Accept model terms (REQUIRED):**
   Visit these URLs and accept terms (you must be logged in):
   - https://huggingface.co/pyannote/speaker-diarization
   - https://huggingface.co/pyannote/segmentation
   - https://huggingface.co/pyannote/speaker-diarization-3.1

   Wait for approval (usually instant).

2. **Create HuggingFace token:**
   - Visit https://huggingface.co/settings/tokens
   - Click "Create new token"
   - **Token type**: Read (not Write)
   - **Permissions**: Enable "Read access to contents of all public gated repos you can access"
   - Copy the token (starts with `hf_`)

3. **Add token to .env:**
   ```bash
   HF_TOKEN=hf_your_token_here
   ```

4. **Verify token works:**
   ```bash
   # In Python
   from huggingface_hub import login
   login(token="hf_your_token_here")
   ```

**Alternative:**
Skip diarization entirely:
```bash
python cli.py process audio.m4a --skip-diarization
# Speakers will be labeled as "UNKNOWN"
```

---

## Processing Errors

### Error: "Audio chunking resulted in zero segments..."

**Problem:**
The processing pipeline fails with a `RuntimeError` and the message "Audio chunking resulted in zero segments. This can happen if the audio is completely silent, corrupt, or too short. Please check the input audio file."

**Cause:**
This error occurs when the audio chunking stage of the pipeline is unable to find any speech in the input audio file. This can be due to several reasons:

*   **The audio file is completely silent:** The VAD (Voice Activity Detection) system will not create any chunks if it doesn't detect any speech.
*   **The audio file is corrupt:** A corrupt audio file may not be readable by the audio processing library, resulting in no audio data being passed to the chunker.
*   **The audio file is too short:** If the audio file is very short (e.g., less than a few seconds), it may not contain enough speech for the chunker to create any segments.
*   **VAD threshold too strict:** The voice activity detection settings may be filtering out all audio.

**Solution:**

1. **Check your audio file:**
   - Play the file in a media player to verify it contains audio
   - Check duration: should be at least 30 seconds for meaningful processing
   - Check volume levels: audio should be clearly audible

2. **Verify file format:**
   ```bash
   # Use ffprobe to check audio properties
   ffprobe -i your_file.m4a

   # Look for:
   # - Duration: should be > 0:00:30
   # - Audio stream: should exist
   # - Sample rate: should be reasonable (44100 Hz, 48000 Hz, etc.)
   ```

3. **Test with a known-good file:**
   Try processing a different audio file to rule out systemic issues.

4. **Adjust VAD settings (Advanced):**
   If you're sure the audio is valid, you can adjust VAD threshold in `src/chunker.py`:
   ```python
   # Look for VAD configuration
   # Lower threshold = more sensitive (detects quieter speech)
   # Higher threshold = less sensitive (only loud speech)
   ```

   **Warning:** This is advanced and should only be attempted if you understand the codebase.

---

### Error: "Out of memory" or "CUDA out of memory"

**Problem:**
Processing fails with memory errors, especially on long sessions.

**Cause:**
Insufficient RAM or VRAM for the operation being performed.

**Solution:**

1. **Use streaming snippet export (recommended):**
   ```bash
   # In .env
   USE_STREAMING_SNIPPET_EXPORT=true
   ```
   This reduces memory usage by 90% (450MB -> 50MB for 4-hour sessions).

2. **Reduce chunk length:**
   ```bash
   # In .env
   CHUNK_LENGTH_SECONDS=300  # Default is 600 (10 min)
   ```

3. **Use smaller Whisper model:**
   ```bash
   # In .env
   WHISPER_MODEL=medium  # Instead of large-v3
   # or
   WHISPER_MODEL=small
   ```

4. **Use cloud transcription:**
   ```bash
   # In .env
   WHISPER_BACKEND=groq  # Offload to Groq API
   GROQ_API_KEY=your_key_here
   ```

5. **Close other applications:**
   Free up RAM before processing long sessions.

6. **Process in smaller chunks:**
   Split your audio file into smaller sections and process separately.

---

### Error: "Processing was cancelled by user" (unexpected)

**Problem:**
Processing stops with cancellation message when you didn't click cancel.

**Cause:**
A background process or cleanup routine may have triggered cancellation.

**Solution:**

1. **Check for multiple processes:**
   ```bash
   # Linux/Mac
   ps aux | grep "python.*app.py"

   # Windows
   tasklist | findstr python
   ```

   Kill duplicate processes and restart.

2. **Restart the application:**
   - Stop the web UI (`Ctrl+C`)
   - Clear any lock files: `rm temp/*.lock` (if safe)
   - Restart: `python app.py`

3. **Check logs for details:**
   ```bash
   # Check console logs
   tail -f logs/session_*.log

   # Check audit log
   tail -f logs/audit.log
   ```

---

## GPU & Performance Issues

### GPU not detected or "CUDA not available"

**Problem:**
The application doesn't use your GPU even though you have one.

**Cause:**
CUDA toolkit not installed, wrong PyTorch version, or driver issues.

**Solution:**

1. **Verify CUDA is available:**
   ```python
   import torch
   print(f"CUDA available: {torch.cuda.is_available()}")
   print(f"CUDA version: {torch.version.cuda}")
   print(f"GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
   ```

2. **Install CUDA toolkit:**
   - NVIDIA: https://developer.nvidia.com/cuda-downloads
   - Verify: `nvcc --version`

3. **Install correct PyTorch with CUDA:**
   ```bash
   # Check current PyTorch
   pip show torch

   # Reinstall with CUDA support (example for CUDA 11.8)
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

   # For CUDA 12.1
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

4. **Force GPU usage in .env:**
   ```bash
   INFERENCE_DEVICE=cuda
   ```

5. **Verify GPU drivers:**
   ```bash
   # NVIDIA
   nvidia-smi

   # Should show GPU info, memory, driver version
   ```

**Still not working?**
- Some operations (faster-whisper) may auto-detect and use GPU without explicit config
- Check your specific GPU's CUDA compatibility
- Try CPU processing first to ensure the pipeline works, then debug GPU issues

---

### Processing is very slow

**Problem:**
Processing takes hours for a 2-hour session.

**Cause:**
Using CPU instead of GPU, or inefficient model choices.

**Solution:**

1. **Enable GPU (if available):**
   ```bash
   # In .env
   INFERENCE_DEVICE=cuda
   ```

2. **Use cloud transcription:**
   ```bash
   # In .env
   WHISPER_BACKEND=groq
   GROQ_API_KEY=your_key_here
   ```

   **Speed comparison:**
   - CPU (local): 10-12 hours for 4-hour session
   - GPU (local): 1-2 hours for 4-hour session
   - Groq API: 20-30 minutes for 4-hour session

3. **Use smaller models:**
   ```bash
   # In .env
   WHISPER_MODEL=medium  # Instead of large-v3
   OLLAMA_MODEL=llama3.2:3b  # Instead of qwen2.5:7b
   ```

4. **Reduce processing overhead:**
   ```bash
   # In .env
   CHUNK_LENGTH_SECONDS=600  # Larger chunks = fewer transcription calls
   SAVE_INTERMEDIATE_OUTPUTS=false  # Skip JSON exports during processing
   ```

---

## Configuration Issues

### Error: "Invalid value for CHUNK_LENGTH_SECONDS" or type casting errors

**Problem:**
Application crashes on startup with configuration errors.

**Cause:**
Invalid values in `.env` file (non-numeric values for integer fields, etc.).

**Solution:**

1. **Validate your .env file:**
   Compare with `.env.example` to ensure all fields match expected format.

2. **Common issues:**
   ```bash
   # WRONG:
   CHUNK_LENGTH_SECONDS=ten
   AUDIO_SAMPLE_RATE=16k

   # CORRECT:
   CHUNK_LENGTH_SECONDS=600
   AUDIO_SAMPLE_RATE=16000
   ```

3. **Check boolean values:**
   ```bash
   # WRONG:
   CLEAN_STALE_CLIPS=yes
   AUDIT_LOG_ENABLED=1

   # CORRECT:
   CLEAN_STALE_CLIPS=true
   AUDIT_LOG_ENABLED=true
   ```

4. **Reset to defaults:**
   ```bash
   # Backup your .env
   cp .env .env.backup

   # Copy fresh example
   cp .env.example .env

   # Re-add your API keys only
   ```

---

### Error: "Unknown transcriber backend: xyz"

**Problem:**
Pipeline fails with invalid backend configuration.

**Cause:**
Typo or invalid value in `WHISPER_BACKEND` or `LLM_BACKEND`.

**Solution:**

Valid values:
```bash
# WHISPER_BACKEND options:
WHISPER_BACKEND=local   # Local faster-whisper (default)
WHISPER_BACKEND=groq    # Groq Cloud API
WHISPER_BACKEND=openai  # OpenAI Whisper API

# LLM_BACKEND options:
LLM_BACKEND=ollama   # Local Ollama (default)
LLM_BACKEND=openai   # OpenAI GPT API
LLM_BACKEND=groq     # Groq Cloud API
```

**Check for typos:**
```bash
# WRONG:
WHISPER_BACKEND=groq-cloud
WHISPER_BACKEND=Local  # Case-sensitive!

# CORRECT:
WHISPER_BACKEND=groq
WHISPER_BACKEND=local
```

---

## Windows-Specific Issues

### Unicode/cp1252 encoding errors

**Problem:**
Application crashes with `UnicodeDecodeError` or `UnicodeEncodeError` on Windows.

**Cause:**
Non-ASCII characters (emojis, Unicode arrows, special symbols) in files being read by Windows with cp1252 encoding.

**Solution:**

This is a known issue that has been largely fixed in the codebase. If you encounter it:

1. **Check for non-ASCII characters:**
   Look for:
   - Emoji in filenames or content
   - Unicode arrows (`→`, `←`) instead of ASCII (`->`, `<-`)
   - Special bullets (`•`, `★`) instead of ASCII (`-`, `*`)
   - Status symbols (checkmarks, crosses) instead of `[DONE]`, `[TODO]`

2. **Temporary workaround:**
   ```bash
   # Set Python to use UTF-8 (add to .env or environment)
   set PYTHONUTF8=1

   # Or use environment variable
   $env:PYTHONUTF8=1  # PowerShell
   ```

3. **Report the issue:**
   If you find a file with Unicode characters that breaks on Windows, report it as a bug with the filename and line number.

---

### Path issues with spaces or special characters

**Problem:**
File operations fail with path errors when paths contain spaces.

**Cause:**
Windows paths with spaces need proper quoting or Path object usage.

**Solution:**

1. **Use paths without spaces (recommended):**
   ```bash
   # BETTER:
   C:\projects\dnd-processor\

   # AVOID:
   C:\My Documents\D&D Sessions\
   ```

2. **Use quotes when necessary:**
   ```bash
   python cli.py process "C:\My Documents\session.m4a"
   ```

3. **Use forward slashes (works on Windows):**
   ```bash
   python cli.py process "C:/My Documents/session.m4a"
   ```

---

## Testing Issues

### Error: "fixture not found" or import errors in tests

**Problem:**
Running `pytest` fails with fixture or import errors.

**Cause:**
Missing test dependencies, wrong working directory, or broken test fixtures.

**Solution:**

1. **Ensure you're in project root:**
   ```bash
   cd /path/to/Video_chunking
   pytest -q
   ```

2. **Check test dependencies:**
   ```bash
   pip install pytest pytest-cov
   ```

3. **Verify fixtures are defined:**
   Check `tests/conftest.py` for fixture definitions.

4. **Run specific test file:**
   ```bash
   # Instead of all tests
   pytest tests/test_pipeline.py -v
   ```

5. **Clear pytest cache:**
   ```bash
   pytest --cache-clear
   rm -rf .pytest_cache
   ```

---

### Tests pass locally but fail in CI

**Problem:**
Tests work on your machine but fail in continuous integration.

**Cause:**
Environment differences (paths, API keys, missing dependencies).

**Solution:**

1. **Check for hardcoded paths:**
   Tests should use `tmp_path` fixture or relative paths.

2. **Check for environment dependencies:**
   Tests should not require API keys or external services.

3. **Use pytest markers:**
   ```python
   @pytest.mark.slow
   def test_full_pipeline():
       # Skip in fast test runs
       pass
   ```

4. **Mock external services:**
   ```python
   @pytest.fixture
   def mock_ollama():
       with patch('src.llm_factory.ollama.Client') as mock:
           yield mock
   ```

---

## Git Workflow Issues

### Error: "Push failed with 403 Forbidden"

**Problem:**
Cannot push to remote repository with 403 HTTP error.

**Cause:**
Branch name doesn't match required session ID format.

**Solution:**

**CRITICAL:** All development branches must start with `claude/` and end with matching session ID.

1. **Check your branch name:**
   ```bash
   git branch --show-current
   # Should be: claude/operator-workflow-task-SESSIONID
   ```

2. **Rename branch if needed:**
   ```bash
   # If on wrong branch
   git branch -m claude/operator-workflow-task-SESSIONID
   ```

3. **Push with correct format:**
   ```bash
   git push -u origin claude/operator-workflow-task-SESSIONID
   ```

4. **Retry with exponential backoff on network errors:**
   If push fails due to network issues (not 403), retry:
   - Wait 2s, retry
   - Wait 4s, retry
   - Wait 8s, retry
   - Wait 16s, final retry

---

### Git operations very slow or hanging

**Problem:**
Git fetch/pull/push operations take a very long time or appear to hang.

**Cause:**
Large repository, slow network, or git trying to compress large files.

**Solution:**

1. **Fetch specific branches only:**
   ```bash
   # Instead of:
   git fetch origin

   # Use:
   git fetch origin your-branch-name
   ```

2. **Shallow clone for initial setup:**
   ```bash
   git clone --depth 1 https://github.com/user/repo.git
   ```

3. **Check .gitignore:**
   Ensure large files are ignored:
   ```
   # Should be in .gitignore:
   models/
   output/
   temp/
   .venv/
   *.wav
   ```

4. **Increase buffer size:**
   ```bash
   git config --global http.postBuffer 524288000
   ```

---

## Advanced Troubleshooting

### Enable debug logging

**Problem:**
Need more detailed logs to diagnose issues.

**Solution:**

1. **Enable debug logging in .env:**
   ```bash
   LOG_LEVEL_CONSOLE=DEBUG
   LOG_LEVEL_FILE=DEBUG
   ```

2. **Check log files:**
   ```bash
   # Session logs (timestamped)
   ls -lt logs/session_*.log
   tail -f logs/session_20250118_143000.log

   # Audit log (all operations)
   tail -f logs/audit.log
   ```

3. **Enable classifier audit mode:**
   ```bash
   # In .env
   CLASSIFIER_AUDIT_MODE=1
   ```
   This logs all LLM prompts and responses for debugging classification issues.

---

### Preflight checks failing

**Problem:**
Pipeline fails immediately with preflight check errors.

**Cause:**
Missing dependencies, services not running, or configuration issues.

**Solution:**

1. **Run preflight checks manually:**
   ```bash
   python cli.py check-setup
   ```

2. **Review each failure:**
   The preflight checker will report:
   - Missing dependencies
   - Ollama connection status
   - Model availability
   - API key validity
   - FFmpeg installation

3. **Fix issues one by one:**
   Follow the specific error messages and solutions in earlier sections.

---

### Clear stale data and start fresh

**Problem:**
Corrupted state, stale checkpoints, or mysterious errors.

**Solution:**

**WARNING:** This will delete all temporary data and processing state.

```bash
# Backup important data first
cp -r output/ output_backup/
cp -r models/knowledge/ models/knowledge_backup/

# Clear temporary files
rm -rf temp/*

# Clear checkpoints
rm -rf temp/checkpoints/*

# Clear logs (optional)
rm -rf logs/*

# Restart application
python app.py
```

---

### Performance profiling

**Problem:**
Need to identify bottlenecks in processing pipeline.

**Solution:**

1. **Enable timing information:**
   The pipeline already logs stage timings. Check logs for:
   ```
   [INFO] Stage: TRANSCRIPTION completed in 125.34s
   [INFO] Stage: DIARIZATION completed in 87.21s
   ```

2. **Use Python profiler:**
   ```bash
   python -m cProfile -o profile.stats cli.py process audio.m4a

   # Analyze results
   python -m pstats profile.stats
   # Then: sort cumulative, stats 20
   ```

3. **Memory profiling:**
   ```bash
   pip install memory_profiler
   python -m memory_profiler cli.py process audio.m4a
   ```

---

### Contact & Support

If you're still experiencing issues after trying these solutions:

1. **Check documentation:**
   - [USAGE.md](./USAGE.md) - Detailed usage guide
   - [SETUP.md](./SETUP.md) - Complete setup instructions
   - [QUICKREF.md](./QUICKREF.md) - Quick reference guide

2. **Search existing issues:**
   Check if your issue has been reported at https://github.com/Gambitnl/Video_chunking/issues

3. **Report a bug:**
   Create a new issue with:
   - Error message (full traceback)
   - Steps to reproduce
   - Your environment (OS, Python version, GPU info)
   - Relevant log files
   - Configuration (sanitize API keys!)

---

**Last Updated:** 2025-11-18
