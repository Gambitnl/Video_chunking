# Ollama & OpenAI OSS Model Setup

## Step 1: Install Ollama

### Manual Installation Required

The Ollama installer has been downloaded to:
```
f:\Repos\VideoChunking\ollama_setup.exe
```

**Please run this installer now:**
1. Double-click `ollama_setup.exe`
2. Follow the installation wizard
3. Ollama will install and start automatically

**Note**: The installer is 1.1GB and has been added to `.gitignore`.

## Step 2: Choose Your Model

Once Ollama is installed, you can use OpenAI's open-source models or other options:

### OpenAI OSS Models Available via Ollama

Recent options (as of October 2025):
- **gpt-oss** (20B, 8B) - OpenAI's open-weight series
- **llama3.2** (3B, 1B) - Latest Meta Llama, fast and efficient
- **llama3.1** (8B, 70B) - Previous Meta Llama version
- **qwen2.5** (0.5B-72B) - Alibaba's Qwen models, excellent multilingual
- **mistral** (7B) - Mistral AI's open model
- **phi3** (3.8B) - Microsoft's efficient model

**Note**: OpenAI now provides `gpt-oss` as an open-weight model family that can run locally through Ollama. If your hardware cannot handle the 20B model, fall back to one of the smaller alternatives listed above.

### Recommended Models for D&D Transcription

For your Dutch D&D IC/OOC classification:

1. **gpt-oss:20b** (Default - Highest quality)
   - Size: ~12.8GB download
   - Speed: Moderate (GPU strongly recommended)
   - Quality: Best reasoning, narrative coherence
   - Excellent Dutch + contextual understanding

2. **llama3.2:3b** (Fallback - Fastest)
   - Size: ~2GB
   - Speed: Very fast
   - Quality: Solid for quick classification
   - Good Dutch support

3. **qwen2.5:7b** (Balanced multilingual)
   - Size: ~4.7GB
   - Speed: Fast
   - Quality: Excellent multilingual output
   - Great Dutch comprehension

## Step 3: Pull the Model

After Ollama is installed, open a **new terminal** (to refresh PATH) and run:

### Option A: GPT-OSS 20B (Default)
```bash
ollama pull gpt-oss:20b
```

### Option B: Llama 3.2 (Fast fallback)
```bash
ollama pull llama3.2:3b
```

### Option C: Qwen 2.5 (Multilingual fallback)
```bash
ollama pull qwen2.5:7b
```

## Step 4: Verify Installation

Test that everything works:

```bash
# Check Ollama is running
ollama list

# Test the model (replace with your chosen model)
ollama run gpt-oss:20b "Classify this as IC or OOC: Ik rol voor initiatief"
```

Expected output: Should recognize this as OOC (game mechanics).

## Step 5: Update Configuration

Edit `.env` file (copy from `.env.example` if needed):

```bash
# Default: GPT-OSS 20B (best quality)
OLLAMA_MODEL=gpt-oss:20b

# Fallback: Llama 3.2 (fast & small)
OLLAMA_MODEL=llama3.2:3b

# Fallback: Qwen 2.5 (multilingual)
OLLAMA_MODEL=qwen2.5:7b

# Ollama server URL (default)
OLLAMA_BASE_URL=http://localhost:11434
```

## Step 6: Test in Your App

```bash
# Test via CLI
cd f:/Repos/VideoChunking
python cli.py check-setup

# Or test directly
python -c "from src.classifier import OllamaClassifier; c = OllamaClassifier(); print('Ollama OK!')"
```

## Model Comparison

| Model | Size | Speed | Dutch Quality | RAM Usage | Best For |
|-------|------|-------|---------------|-----------|----------|
| gpt-oss:20b | 12.8GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | 16GB+ | Premium storytelling & reasoning |
| llama3.2:3b | 2GB | ⚡⚡⚡ | ⭐⭐⭐ | 4GB | Fast processing |
| qwen2.5:7b | 4.7GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | 8GB | Best multilingual |

## Recommendation

For your use case (4-hour D&D sessions in Dutch):

**Default: `gpt-oss:20b`**  
- ✅ Best reasoning for IC/OOC, narrative rewrites, and persona work  
- ✅ Strong Dutch comprehension  
- ⚠ Requires ~12.8GB download and 16GB+ RAM (or capable GPU)

**Use `llama3.2:3b` if**  
- You need the quickest setup  
- Running on limited hardware (≤8GB RAM)  
- You’re okay with slightly less nuance

**Use `qwen2.5:7b` if**  
- You want a middle ground between speed and multilingual nuance  
- You have 8GB+ RAM and good CPU/GPU  
- You prefer stronger Dutch handling than 3B models

## Troubleshooting

### Ollama not found after installation
- Close and reopen your terminal
- Windows: Log out and back in
- Verify: `ollama --version`

### Model download fails
- Check internet connection
- Try again: `ollama pull <model>`
- Check disk space (need 2-5GB free)

### Connection refused
- Ollama service may not be running
- Windows: Check system tray for Ollama icon
- Restart: Close Ollama and reopen

### Out of memory during inference
- Close other applications
- Try smaller model (llama3.2:3b)
- Reduce batch processing

---

## Next Steps After Installation

1. Run installer: `ollama_setup.exe`
2. Pull model: `ollama pull gpt-oss:20b`
3. Update `.env`: `OLLAMA_MODEL=gpt-oss:20b`
4. Test: `python cli.py check-setup`
5. Process your first session! 🎉
