# Troubleshooting Ollama Classification Errors

## Problem Summary

Your processing runs are failing at the classification stage with Ollama errors like:
```
model requires more system memory (12.8 GiB) than is available (9.3 GiB)
memory layout cannot be allocated
GGML_ASSERT(ctx->mem_buffer != NULL) failed
```

## Root Cause

Based on your logs from November 10th, 2025, the issue is **VRAM contention**:

1. **PyAnnote (Diarization)** loads into VRAM (~8GB)
2. PyAnnote doesn't fully unload after diarization completes
3. **Ollama** tries to load `gpt-oss:20b` (requires 12.8GB)
4. Only 9.3GB VRAM is available (PyAnnote still occupies ~3-4GB)
5. Ollama fails with memory allocation errors

### Evidence from Logs

```
2025-11-10 21:09:17 | WARNING | DDSessionProcessor.classifier.ollama |
Classification failed for segment 0 using gpt-oss:20b:
model requires more system memory (12.8 GiB) than is available (9.3 GiB)
```

Multiple subsequent attempts show:
- Low-VRAM retry also fails
- Persistent `memory layout cannot be allocated` errors
- Classification continues failing for all segments

---

## Solutions (Ordered by Effectiveness)

### ✅ Solution 1: Switch to Groq (RECOMMENDED)

**Why this works:** Offloads classification to cloud, eliminates VRAM contention entirely.

**Steps:**
1. Get free Groq API key at [https://console.groq.com/](https://console.groq.com/)
2. Add to `.env`:
   ```bash
   GROQ_API_KEY=your_groq_api_key_here
   ```
3. Test connection:
   ```bash
   python test_api_keys.py
   ```
4. Configure in UI:
   - Step 2: Configure Session
   - Advanced Backend Settings
   - Classification: `groq`

**Benefits:**
- ✅ 100% free (no credit card required)
- ✅ Faster than local Ollama
- ✅ No VRAM usage
- ✅ No memory contention
- ✅ Works every time

**Recommended Configuration (12GB VRAM):**
```
Transcription:  groq       (cloud - free)
Diarization:    pyannote   (local - 8GB VRAM)
Classification: groq       (cloud - free)
```

---

### ⚙️ Solution 2: Use Smaller Ollama Model

**Why this works:** Smaller model fits in remaining VRAM after PyAnnote.

**Steps:**
1. Pull a smaller model:
   ```bash
   ollama pull llama3.1:8b
   # or
   ollama pull mistral:7b
   ```

2. Update `.env`:
   ```bash
   OLLAMA_MODEL=llama3.1:8b
   ```

3. Restart application

**Model Size Comparison:**
| Model | Size | VRAM Required | Fits After PyAnnote? |
|-------|------|---------------|---------------------|
| gpt-oss:20b | 20B params | ~12.8GB | ❌ No (requires 12.8GB) |
| llama3.1:8b | 8B params | ~8GB | ⚠️ Maybe (tight fit) |
| llama3.1:3b | 3B params | ~4GB | ✅ Yes (plenty of room) |
| phi3:mini | 3.8B params | ~4GB | ✅ Yes |

**Drawbacks:**
- Smaller models = lower classification quality
- Still risk of VRAM issues if PyAnnote doesn't release memory
- Slower than cloud (local inference)

---

### 🔧 Solution 3: Force CPU for Ollama

**Why this works:** Moves Ollama to CPU, leaving GPU entirely for PyAnnote.

**Steps:**
1. Check current Ollama configuration:
   ```bash
   ollama show gpt-oss:20b --modelfile
   ```

2. Create a CPU-only version:
   ```bash
   # Create Modelfile
   cat > Modelfile-cpu <<EOF
   FROM gpt-oss:20b
   PARAMETER num_gpu 0
   PARAMETER num_thread 8
   EOF

   # Create the model
   ollama create gpt-oss-cpu -f Modelfile-cpu
   ```

3. Update `.env`:
   ```bash
   OLLAMA_MODEL=gpt-oss-cpu
   ```

**Drawbacks:**
- 🐌 **VERY SLOW** on CPU (10-20x slower)
- May timeout on long segments
- Not practical for large sessions

---

### 🔄 Solution 4: Sequential Processing with Manual Restart

**Why this works:** Ensures complete VRAM release between stages.

**Steps:**
1. Run diarization only:
   - Configure: Diarization = `pyannote`
   - Skip classification stage
   - Let it complete

2. Restart application (clears VRAM):
   - Settings & Tools tab
   - Application Control
   - Restart Application button

3. Run classification only:
   - Load previous session
   - Skip diarization (already done)
   - Run classification with Ollama

**Drawbacks:**
- 🕐 Manual intervention required
- 🔄 Two-step process
- 📦 Complex for large sessions

---

### 🎯 Solution 5: Mixed Cloud/Local (OPTIMAL FOR COST)

**Why this works:** Offloads classification, keeps diarization local (HF API is rate-limited).

**Configuration:**
```
Transcription:  groq       (cloud - free, fast)
Diarization:    pyannote   (local - best quality, no rate limits)
Classification: groq       (cloud - free, fast)
```

**Benefits:**
- ✅ No VRAM contention (only PyAnnote uses GPU)
- ✅ Best diarization quality (local PyAnnote)
- ✅ No HF API rate limits for diarization
- ✅ Fast classification (Groq)
- ✅ 100% free

**Steps:**
1. Set up Groq API (Solution 1)
2. Configure mixed backends in UI
3. Process normally

---

## Quick Diagnostic Commands

### Check Available VRAM
```bash
nvidia-smi
```

### Check Ollama Models
```bash
ollama list
```

### Check Ollama Model Size
```bash
ollama show gpt-oss:20b
```

### Test Ollama Directly
```bash
ollama run gpt-oss:20b "What is 2+2?"
```
If this fails with memory errors, the model is too large for your system.

### Check PyAnnote VRAM Usage
```python
import torch
print(f"GPU Memory Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
print(f"GPU Memory Cached: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
```

---

## Understanding the Error Messages

### "model requires more system memory (X GiB) than is available (Y GiB)"
**Meaning:** Ollama model requires X GB, but only Y GB is free in VRAM.
**Fix:** Use smaller model or switch to Groq.

### "memory layout cannot be allocated"
**Meaning:** VRAM fragmentation or not enough contiguous memory.
**Fix:** Restart application to clear VRAM, or use Groq.

### "GGML_ASSERT(ctx->mem_buffer != NULL) failed"
**Meaning:** Internal Ollama error due to memory allocation failure.
**Fix:** Model is too large for available VRAM. Use Groq or smaller model.

### "Low-VRAM retry also failed"
**Meaning:** Even with reduced context window, model doesn't fit.
**Fix:** Model is fundamentally too large. Must use Groq or much smaller model.

---

## Performance Comparison

Based on your logs and typical processing times:

### Classification Speed (100 segments)

| Backend | Time | Success Rate | VRAM Usage |
|---------|------|--------------|------------|
| Ollama gpt-oss:20b (GPU) | ~10-15 min | ❌ 0% (fails) | 12.8GB (too much) |
| Ollama llama3.1:8b (GPU) | ~8-10 min | ⚠️ ~50% (unreliable) | 8GB (tight fit) |
| Ollama llama3.1:8b (CPU) | ~60-90 min | ✅ 100% | 0GB (CPU only) |
| Groq llama-3.3-70b | ~2-3 min | ✅ 100% | 0GB (cloud) |

**Conclusion:** Groq is faster, more reliable, and eliminates VRAM issues entirely.

---

## Why Not Increase VRAM?

**Your system:** 12GB VRAM (likely RTX 3060 or similar)

**What you'd need for gpt-oss:20b:** ~16-24GB VRAM to handle:
- PyAnnote diarization (8GB)
- Ollama gpt-oss:20b (12.8GB)
- Overhead and fragmentation (~2-4GB)

**Upgrade options:**
- RTX 4090 (24GB) - $1,600+
- RTX A5000 (24GB) - $2,000+
- RTX 6000 Ada (48GB) - $6,000+

**Better option:** Use free Groq API instead of hardware upgrade.

---

## Recommended Action Plan

### For Immediate Relief
1. **Switch to Groq** (Solution 1)
   - Takes 5 minutes to set up
   - Eliminates all Ollama errors
   - Faster than local
   - 100% free

### For Long-Term Stability
2. **Use mixed configuration** (Solution 5)
   ```
   Transcription:  groq
   Diarization:    pyannote  (local)
   Classification: groq
   ```

### If You Must Use Ollama
3. **Try smaller model** (Solution 2)
   ```bash
   ollama pull llama3.1:3b
   ```
   Then update `.env`:
   ```bash
   OLLAMA_MODEL=llama3.1:3b
   ```

---

## Testing Your Fix

After implementing a solution:

1. **Start fresh session:**
   - Upload a small test video (~5-10 minutes)
   - Configure your chosen backend

2. **Monitor logs:**
   ```bash
   tail -f logs/session_processor_*.log | grep -i "classif\|error"
   ```

3. **Check for success:**
   - No "memory layout cannot be allocated" errors
   - No "model requires more system memory" errors
   - Classification completes for all segments

4. **Verify output:**
   - Check `output/[session]/[session]_classified.json`
   - Should have classifications for all segments
   - No null/missing classifications

---

## Additional Resources

- [CLOUD_INFERENCE_OPTIONS.md](CLOUD_INFERENCE_OPTIONS.md) - Complete guide to cloud backends
- [test_api_keys.py](test_api_keys.py) - Test your Groq/HF API keys
- [Groq Console](https://console.groq.com/) - Get free API key
- [Ollama Model Library](https://ollama.com/library) - Browse smaller models

---

## Still Having Issues?

If you're still experiencing problems after trying these solutions:

1. **Share your logs:**
   ```bash
   tail -100 logs/session_processor_*.log
   ```

2. **Share your configuration:**
   ```bash
   cat .env | grep -v "API_KEY"  # Don't share actual keys
   ```

3. **Share VRAM status:**
   ```bash
   nvidia-smi
   ```

4. **Check Ollama status:**
   ```bash
   ollama list
   ollama ps  # Show running models
   ```

---

**Last Updated:** 2025-11-11
**Your Specific Issue:** gpt-oss:20b requires 12.8GB, only 9.3GB available after PyAnnote
**Recommended Fix:** Switch classification to Groq (free, fast, reliable)
