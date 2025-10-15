# OpenAI GPT-OSS Model Setup

## About GPT-OSS

**OpenAI GPT-OSS-20B** is OpenAI's new open-weight model released in 2025:
- **21B parameters** (3.6B active)
- **Apache 2.0 license** - Can be used freely
- **Designed for**: Lower latency, local use, reasoning tasks
- **Perfect for**: IC/OOC classification, context understanding
- **Model size**: ~12.8 GB

This is OpenAI's first open-weight model, designed specifically for local deployment!

## Installation Steps

### Step 1: Install Ollama

Run the downloaded installer:
```
f:\Repos\VideoChunking\ollama_setup.exe
```

### Step 2: Pull GPT-OSS Model

After Ollama is installed, open a **new terminal** and run:

```bash
ollama pull gpt-oss:20b
```

**Download size**: ~12.8 GB
**Time**: 10-20 minutes depending on connection

### Step 3: Verify Installation

```bash
# Check model is installed
ollama list

# Test the model
ollama run gpt-oss:20b "Classify as IC or OOC: Ik rol voor initiatief"
```

Expected: Should identify this as OOC (game mechanics discussion)

### Step 4: Update Configuration

Create/edit `.env` file:

```bash
# Copy example if needed
cp .env.example .env

# Edit .env and set:
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_BASE_URL=http://localhost:11434
```

### Step 5: Test in Your App

```bash
cd f:/Repos/VideoChunking

# Check setup
python cli.py check-setup

# Or test directly
python -c "from src.classifier import OllamaClassifier; c = OllamaClassifier(); print('GPT-OSS OK!')"
```

## System Requirements

### Minimum
- **RAM**: 16GB (recommended 32GB)
- **Disk**: 15GB free space
- **OS**: Windows 10/11

### Recommended
- **RAM**: 32GB+
- **GPU**: NVIDIA with 8GB+ VRAM (for faster inference)
- **Disk**: SSD for better performance

## Performance Comparison

| Model | Size | RAM | Speed | Quality | Dutch | Best For |
|-------|------|-----|-------|---------|-------|----------|
| **gpt-oss:20b** ⭐ | 12.8GB | 16GB+ | ⚡⚡ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | OpenAI quality, reasoning |
| llama3.2:3b | 2GB | 4GB | ⚡⚡⚡ | ⭐⭐⭐ | ⭐⭐⭐ | Quick processing |
| qwen2.5:7b | 4.7GB | 8GB | ⚡⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Best multilingual |

## Why GPT-OSS for D&D Transcription?

### Advantages
✅ **OpenAI Quality** - Same architecture as GPT models
✅ **Reasoning Capability** - Better context understanding
✅ **Tool Use** - Can follow complex instructions
✅ **Free & Local** - No API costs, runs on your machine
✅ **Open Weights** - Apache 2.0 license

### Trade-offs
⚠️ **Large Download** - 12.8GB vs 2-5GB for other models
⚠️ **More RAM** - Needs 16GB+ vs 4-8GB
⚠️ **Slower** - Bigger model = more processing time

### For Your Use Case

**IC/OOC Classification** in Dutch D&D sessions:
- ✅ Excellent at understanding context
- ✅ Can handle Dutch well (multilingual training)
- ✅ Better reasoning for ambiguous cases
- ⚠️ Processing 4-hour sessions will take longer than smaller models

### Recommendation

**If you have 16GB+ RAM**: Use **gpt-oss:20b** for best quality
**If you have 8GB RAM**: Use **qwen2.5:7b** (best multilingual alternative)
**If you want speed**: Use **llama3.2:3b** (fastest option)

## Using GPT-OSS Features

### Configurable Reasoning Levels

GPT-OSS supports different reasoning modes:

```python
# In your .env, you can experiment with:
# (Note: Implementation may vary)
OLLAMA_MODEL=gpt-oss:20b
```

### Advanced Usage

The model supports:
- **Chain of Thought** - For complex classifications
- **Multi-turn Context** - Remembers previous segments
- **Tool Use** - Can be extended with function calling

## Troubleshooting

### Download Fails
```bash
# Retry with:
ollama pull gpt-oss:20b --insecure-skip-tls-verify
```

### Out of Memory
- Close other applications
- Increase virtual memory (Windows: Settings > System > About > Advanced System Settings)
- Consider using smaller model (qwen2.5:7b or llama3.2:3b)

### Slow Performance
- First run downloads model (~12.8GB)
- Subsequent runs are faster
- Consider GPU acceleration if available
- For 4-hour sessions, expect 2-3x longer processing than smaller models

### Model Not Found
```bash
# Verify installation
ollama list

# Should see: gpt-oss:20b
```

## Next Steps

1. ✅ Install Ollama: Run `ollama_setup.exe`
2. ✅ Pull model: `ollama pull gpt-oss:20b`
3. ✅ Update config: Set `OLLAMA_MODEL=gpt-oss:20b` in `.env`
4. ✅ Test: `python cli.py check-setup`
5. ✅ Process your first D&D session! 🎲

## Alternative Models

If GPT-OSS doesn't work for your system:

```bash
# Best multilingual (4.7GB, 8GB RAM)
ollama pull qwen2.5:7b

# Fastest (2GB, 4GB RAM)
ollama pull llama3.2:3b

# Balanced (4.7GB, 8GB RAM)
ollama pull llama3.1:8b
```

---

**Ready to install?** Run the Ollama installer, then: `ollama pull gpt-oss:20b`
