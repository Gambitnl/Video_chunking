# Google Colab Classification Setup

This guide shows you how to set up and test the Google Colab GPU-based classification for Stage 6 (IC/OOC classification).

## 🎯 Overview

Instead of running classification locally (which requires GPU/RAM), you can offload it to Google Colab's free GPU. The pipeline uploads jobs to Google Drive, Colab processes them, and results are downloaded automatically.

## 📋 One-Time Setup

### 1. Create Google Drive Folders

In your Google Drive, create this folder structure:

```
My Drive/
└── VideoChunking/
    ├── classification_pending/    (jobs uploaded here)
    └── classification_complete/   (results written here)
```

**Quick way:**
- Go to https://drive.google.com
- Create new folder: `VideoChunking`
- Inside it, create: `classification_pending` and `classification_complete`

### 2. Upload Colab Notebook

1. Upload `colab_classification_worker.ipynb` to your Google Drive
2. Right-click → Open with → Google Colaboratory
3. **Important**: Set runtime to GPU
   - Click: `Runtime → Change runtime type`
   - Hardware accelerator: **GPU**
   - GPU type: **T4 GPU** (free tier)
   - Click **Save**

### 3. Install Colab Extension (Optional)

If you want to run the notebook directly from VS Code:
1. Install "Google Colab" extension in VS Code
2. Open the `.ipynb` file
3. Select kernel → Colab
4. Sign in with your Google account

## 🚀 Testing the Integration

### Option 1: Quick Test with Checkpoint Data (Recommended)

Use existing diarization data to test just the classification step:

```bash
# Default test (20 segments from most recent checkpoint)
python test_colab_classifier.py

# Custom options
python test_colab_classifier.py --num-segments 50 --checkpoint-dir test_s6_nov12_1111am
```

**Steps:**

1. **Start Colab Worker**:
   - Open `colab_classification_worker.ipynb` in Colab
   - Run all cells (1→2→3→4→5)
   - Cell 5 will loop forever, watching for jobs
   - Keep this tab open!

2. **Run Test Script**:
   ```bash
   python test_colab_classifier.py
   ```

3. **Watch Output**:
   - Local: Shows upload, polling, and results
   - Colab: Shows job processing progress

### Option 2: Full Pipeline Test

To test with a real session:

1. Start Colab worker (as above)
2. In your app UI:
   - Go to "Process Session" tab
   - Upload a short audio file (~2-5 minutes)
   - **Advanced Options → Classification Backend: "colab"**
   - Click "Process Session"
3. Pipeline will automatically:
   - Process stages 1-5 locally
   - Upload job at Stage 6
   - Wait for Colab
   - Download results and continue

## 📊 What to Expect

### Timing

- **Job upload**: < 1 second
- **Colab processing**: ~2-5 seconds per segment
  - 20 segments ≈ 40-100 seconds
  - 100 segments ≈ 3-8 minutes
  - 5000 segments ≈ 2.5-7 hours

### Logs

**Local pipeline:**
```
Stage 6/9: IC/OOC classification...
Uploading classification job job_1699999999_abcd1234 to Google Drive...
Waiting for Colab to process job job_1699999999_abcd1234...
Polling every 10s for up to 1800s...
Still waiting... (30s elapsed)
Results ready after 45.3s
Stage 6/9 complete: 15 IC segments, 5 OOC segments
```

**Colab notebook:**
```
[14:32:15] Found 1 new job(s)
============================================================
Processing: job_1699999999_abcd1234.json
Job ID: job_1699999999_abcd1234
Segments to classify: 20
  Progress: 10/20 segments classified
  Progress: 20/20 segments classified
✓ Results written: job_1699999999_abcd1234_result.json
============================================================
```

## 🔧 Configuration

Customize in `.env` (create if missing):

```bash
# Default backend for classification
LLM_BACKEND=colab

# Google Drive paths (relative to "My Drive")
GDRIVE_CLASSIFICATION_PENDING=VideoChunking/classification_pending
GDRIVE_CLASSIFICATION_COMPLETE=VideoChunking/classification_complete

# Polling settings
COLAB_POLL_INTERVAL=10   # seconds between checks
COLAB_TIMEOUT=1800       # 30 minutes max wait
```

## ❓ Troubleshooting

### "No pending jobs found" - Worker Not Detecting Files

**Problem**: Colab worker shows "No pending jobs" but files exist in Google Drive.

**Root Cause**: Path type mismatch (PosixPath vs WindowsPath) when running notebook in WSL/container.

**Solution**:
1. **Restart kernel and run cells in order**:
   - Stop Cell 5 (worker)
   - `Kernel → Restart Kernel`
   - Run Cell 1, then Cell 3, then Cell 4, then Cell 5
2. **Verify Cell 1 output shows STRING paths** (not PosixPath):
   ```
   ✓ GOOD: G:\My Drive\VideoChunking\classification_pending
   ✗ BAD:  G:\My Drive/VideoChunking/classification_pending (mixed separators)
   ```
3. **Check debug output in Cell 5**:
   - Should show: `os.listdir() returned: ['job_12345.json']`
   - If empty list, Cell 1 needs to be re-run

### "Google Drive pending directory not found"

**Problem**: Pipeline can't find Google Drive folders.

**Solutions**:
1. **Check Google Drive Desktop is installed and running**
   - Windows: Usually mounts at `G:/My Drive` or `C:/Users/YourName/Google Drive`
2. **Verify folders exist**:
   - Open File Explorer → Google Drive → Check for `VideoChunking/` folders
3. **Create folders manually** if they don't exist:
   ```bash
   # Windows PowerShell
   mkdir "G:\My Drive\VideoChunking\classification_pending"
   mkdir "G:\My Drive\VideoChunking\classification_complete"
   ```
4. **Manual path override**:
   ```python
   # In test_colab_classifier.py or your code:
   classifier = ClassifierFactory.create(
       backend="colab",
       gdrive_mount_root="G:/My Drive"  # Your actual path
   )
   ```

### "Timeout waiting for Colab results"

**Problem**: Colab notebook isn't processing jobs.

**Checklist**:
- [ ] Is Colab notebook still running? (Check browser tab)
- [ ] Is Cell 5 (worker loop) running? (Should see "No pending jobs" logs)
- [ ] Did Google Drive disconnect? (Colab auto-disconnects after 12 hours)
- [ ] Check Colab output for errors

**Fix**: Restart Colab notebook (re-run all cells)

### "Model loading takes forever"

**Problem**: Cell 3 hangs when loading the model.

**Solutions**:
- **First run**: Takes 2-5 minutes (downloading model)
- **Subsequent runs**: < 30 seconds (cached)
- **If stuck**: `Runtime → Restart runtime` and try again
- **Smaller model**: Change in Cell 3:
  ```python
  MODEL_NAME = "meta-llama/Llama-3.2-1B-Instruct"  # Smaller, faster
  ```

### "CUDA out of memory"

**Problem**: Model doesn't fit on GPU.

**Solutions**:
1. Check GPU type: Should be **T4** (free tier)
2. Reduce batch size or use smaller model
3. Restart runtime: `Runtime → Restart runtime`

## 💡 Tips

1. **Keep Colab alive**: Colab disconnects after ~12 hours of inactivity
   - Restart notebook before long processing sessions

2. **Check quota**: Free tier has usage limits
   - If you hit limits, wait a few hours or upgrade to Colab Pro

3. **Monitor progress**: Both terminals show real-time progress
   - Local: "Still waiting..." messages every 30s
   - Colab: "Progress: X/Y segments" updates

4. **Process multiple sessions**: Colab worker handles queue automatically
   - Multiple pipelines can submit jobs
   - Processed in order

5. **Running locally (not in Colab)**:
   - The notebook works locally too (no GPU needed for small jobs)
   - Install dependencies: `pip install transformers torch`
   - Uses smaller model (Qwen2.5-1.5B) that runs on CPU
   - Slower than Colab GPU but useful for testing

6. **Manual job creation from existing output**:
   - If you have Stage 5 output already, create a job manually:
   ```bash
   python create_colab_job.py
   ```
   - Move the generated `job_*.json` to Google Drive pending folder
   - Worker will process it and write results to complete folder

## 📚 Next Steps

Once testing works:
1. Set `LLM_BACKEND=colab` as default in `.env`
2. Always start Colab worker before processing sessions
3. Can run multiple sessions while Colab processes queue

## 🆘 Still Having Issues?

1. Check logs in `logs/` directory
2. Verify Google Drive Desktop app is running
3. Ensure Colab has GPU enabled
4. Try the test script first before full pipeline

---

**Need Help?** Check the main [README.md](README.md) or open an issue on GitHub.
