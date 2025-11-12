# Cloud Inference Options for D&D Session Processing

## Overview

This document outlines 100% free cloud API options for offloading compute-intensive tasks in the D&D Session Processor. These are particularly useful if local inference (Ollama, Whisper, PyAnnote) encounters issues or if you want to leverage cloud resources.

---

## 🎯 Recommended: Groq (100% FREE)

**Best for:** Transcription, Classification (IC/OOC)
**Cost:** Completely free with registration (no credit card required)
**Speed:** Fastest inference available (up to 1000 tokens/second)

### Setup
1. Visit [https://console.groq.com/](https://console.groq.com/)
2. Register for a free account (no payment method needed)
3. Generate an API key
4. Add to your `.env` file:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

### Supported Models
- **LLaMA 3.3 70B Versatile** (`llama-3.3-70b-versatile`) - **DEFAULT** for classification/transcription
- **LLaMA 3.1 8B Instant** (`llama-3.1-8b-instant`) - Fast, efficient alternative
- **Mixtral 8x7B** (`mixtral-8x7b-32768`) - Large context window
- **Whisper Large V3** (`whisper-large-v3`) - Speech-to-text transcription

**Note:** Older models like `llama3-8b-8192` and `llama-3.2-1b-preview` have been decommissioned.

### Configuration in UI
1. Navigate to **Step 2: Configure Session**
2. Expand **Advanced Backend Settings** accordion
3. Select backends:
   - **Transcription:** `groq`
   - **Classification:** `groq`

### Testing
Run the API validation script:
```bash
python test_api_keys.py
```

---

## 🤗 HuggingFace Inference API (FREE TIER)

**Best for:** Diarization (speaker identification)
**Cost:** Free tier with rate limits
**Limitations:** ~1000 requests/day on free tier

### Setup
1. Visit [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Create a new token with **"Make calls to Inference Providers"** permission
3. Add to your `.env` file:
   ```
   HUGGING_FACE_API_KEY=your_hf_token_here
   ```

### Supported Models
- **PyAnnote Audio 3.1** - Speaker diarization (who is speaking when)
- **Whisper** - Speech recognition
- **Custom fine-tuned models** - Upload your own

### Configuration in UI
1. Navigate to **Step 2: Configure Session**
2. Expand **Advanced Backend Settings** accordion
3. Select backends:
   - **Diarization:** `hf_api`

### Testing
Run the API validation script:
```bash
python test_api_keys.py
```

---

## 🆓 Alternative Free Options

### Deepgram
**Best for:** Real-time transcription
**Cost:** $200 free credits (no credit card for trial)
**Speed:** Extremely fast real-time processing
**Website:** [https://deepgram.com/](https://deepgram.com/)

**Pros:**
- Superior accuracy
- Real-time streaming
- Multiple languages

**Cons:**
- Not implemented in this project yet
- Credits expire after trial period

---

### Gladia
**Best for:** Podcast/interview transcription
**Cost:** 10 hours/month free
**Website:** [https://www.gladia.io/](https://www.gladia.io/)

**Pros:**
- Speaker diarization included
- Multi-language support
- Webhook callbacks

**Cons:**
- Not implemented in this project yet
- Limited free tier hours

---

### Cohere
**Best for:** Text classification
**Cost:** Free tier with rate limits
**Website:** [https://cohere.com/](https://cohere.com/)

**Pros:**
- Excellent for classification tasks
- Good documentation
- Simple API

**Cons:**
- Not implemented in this project yet
- Primarily focused on text (not audio)

---

### Google AI Studio (Gemini)
**Best for:** Multi-modal classification
**Cost:** Free tier (60 requests/minute)
**Website:** [https://ai.google.dev/](https://ai.google.dev/)

**Pros:**
- Multi-modal (text, image, audio)
- Generous free tier
- Fast inference

**Cons:**
- Not implemented in this project yet

---

## 💻 Local vs Cloud: Quick Comparison

| Task | Local Backend | Cloud Backend | Free Cloud Option |
|------|--------------|---------------|-------------------|
| **Transcription** | Whisper (GPU/CPU) | Groq Whisper | ✅ Groq (unlimited) |
| **Diarization** | PyAnnote (GPU) | HF Inference | ✅ HuggingFace (~1000/day) |
| **Classification** | Ollama (CPU/GPU) | Groq LLaMA | ✅ Groq (unlimited) |

### Hardware Requirements

**Local Processing (12GB VRAM):**
- ✅ Whisper Large V3 (~10GB VRAM)
- ✅ PyAnnote Audio (~8GB VRAM)
- ⚠️ Ollama LLaMA 3.1 8B (~8GB VRAM) - May conflict with other models

**Cloud Processing:**
- ✅ No VRAM required
- ✅ No local compute
- ✅ Scales automatically

---

## 🔍 Troubleshooting

### Issue: Ollama classification errors during local processing

**Symptoms:**
- Processing fails at classification stage
- Errors like: `model requires more system memory (12.8 GiB) than is available (9.3 GiB)`
- Errors like: `memory layout cannot be allocated`
- CUDA out of memory errors
- Ollama timeouts

**Root Cause:**
VRAM contention between PyAnnote (diarization) and Ollama (classification). PyAnnote occupies ~8GB VRAM and doesn't fully release it before Ollama tries to load large models.

**Quick Fix:**
Switch classification to Groq (100% free, no VRAM usage):
```
Classification Backend: groq
```

**Detailed Troubleshooting:**
See [TROUBLESHOOTING_OLLAMA.md](TROUBLESHOOTING_OLLAMA.md) for:
- Complete root cause analysis with log examples
- 5 different solution approaches
- Model size comparisons
- Performance benchmarks
- Step-by-step diagnostic commands

---

## 🚀 Recommended Configuration for 12GB VRAM

**Best setup to avoid Ollama errors:**

```
Transcription:  groq       (cloud - free, fast)
Diarization:    pyannote   (local - uses 8GB VRAM)
Classification: groq       (cloud - free, fast)
```

**Why this works:**
- Groq handles transcription (no local VRAM usage)
- PyAnnote runs on GPU with 8GB VRAM (plenty of headroom)
- Groq handles classification (no local VRAM usage)
- No VRAM contention = no Ollama errors

**Alternative (all local, but risky with 12GB VRAM):**
```
Transcription:  whisper    (local - ~10GB VRAM)
Diarization:    pyannote   (local - ~8GB VRAM, runs after Whisper)
Classification: ollama     (local - ~8GB VRAM, runs after PyAnnote)
```
⚠️ This may cause VRAM errors if models don't unload properly.

---

## 📊 Performance Comparison

### Transcription (60-minute video)
- **Local Whisper (GPU):** ~15-20 minutes
- **Groq Whisper:** ~5-10 minutes
- **Deepgram:** ~2-3 minutes (real-time)

### Diarization (60-minute video)
- **Local PyAnnote (GPU):** ~10-15 minutes
- **HF Inference API:** ~15-20 minutes (due to queue)

### Classification (100 chunks)
- **Local Ollama (GPU):** ~5-10 minutes
- **Groq LLaMA:** ~2-3 minutes
- **Cohere:** ~1-2 minutes

---

## 🔐 Security Considerations

### API Keys
- Store in `.env` file (never commit to git)
- Use environment variables
- Rotate keys regularly
- Use read-only tokens when possible (HuggingFace)

### Data Privacy
- Groq: Data not used for training (check Terms of Service)
- HuggingFace: Inference API doesn't store audio
- Local: 100% private (no data leaves your machine)

**For sensitive campaigns:**
- Use local backends only
- Or review cloud provider privacy policies carefully

---

## 📚 Additional Resources

- [Groq Console](https://console.groq.com/)
- [HuggingFace Inference API](https://huggingface.co/docs/api-inference/)
- [Deepgram API Docs](https://developers.deepgram.com/)
- [Gladia API Docs](https://docs.gladia.io/)
- [Cohere API Docs](https://docs.cohere.com/)
- [Google AI Studio](https://ai.google.dev/)

---

## 🎮 Quick Start: Switching from Ollama to Groq

If your local Ollama keeps erroring out:

1. **Get Groq API Key:**
   ```bash
   # Visit https://console.groq.com/
   # Sign up (free, no credit card)
   # Copy your API key
   ```

2. **Add to .env:**
   ```bash
   echo "GROQ_API_KEY=your_key_here" >> .env
   ```

3. **Test the connection:**
   ```bash
   python test_api_keys.py
   ```

4. **Configure in UI:**
   - Open the Gradio app
   - Go to Step 2: Configure Session
   - Expand Advanced Backend Settings
   - Set Classification to: `groq`

5. **Process your session:**
   - Should complete without Ollama errors
   - Cloud classification is often faster
   - Completely free, no limits

---

## ✅ Validation Checklist

Before processing a session with cloud backends:

- [ ] API keys added to `.env` file
- [ ] Ran `python test_api_keys.py` successfully
- [ ] Selected cloud backends in UI (Step 2)
- [ ] Internet connection is stable
- [ ] (Optional) Set up local fallback if cloud fails

---

**Last Updated:** 2025-11-11
**Version:** 1.0
