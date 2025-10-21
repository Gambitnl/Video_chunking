# Web App Testing Guide

## Current Status

The Gradio web application is running on **http://127.0.0.1:7860**

## Accessing the Web App

### In VS Code:
1. Look for port forward notification (bottom-right)
2. Or use the PORTS panel (bottom panel, next to Terminal)
3. Click the globe icon next to port 7860

### In Browser:
- Direct URL: http://127.0.0.1:7860

## Testing with Your 5-Minute Sample

### Step 1: Prepare Your Sample File
- Make sure your 5-minute D&D session sample is accessible
- Supported formats: MP4, M4A, MP3, WAV, AVI, etc.

### Step 2: Upload and Process
1. Go to the "Process Session" tab
2. Click "Upload Audio File(s)" and select your sample
3. Enter a Session ID (e.g., "test_5min")
4. Configure settings:
   - **Party Configuration**: Select "default" or "Manual Entry"
   - **Number of Speakers**: Set to match your session (usually 3-5)
   - **Optional Flags**:
     - Skip Speaker Diarization: Faster, but no speaker labels
     - Skip IC/OOC Classification: Faster, but no content separation
     - Skip Audio Snippets: Skip per-segment audio export

5. Click "🚀 Process Session"

### Step 3: Monitor Progress
- Watch the Status field for updates
- Check logs in the "Logs" tab if issues occur
- Log file location: `F:\Repos\VideoChunking\logs\`

### Step 4: View Results
After processing completes, view:
- **Full Transcript**: Complete transcription with speaker labels
- **In-Character Only**: Game narrative and roleplay
- **Out-of-Character Only**: Player banter and meta discussion
- **Statistics**: Duration breakdown, character appearances, segment counts

## Troubleshooting

### Common Issues:

**1. Processing Fails Immediately**
- Check if Ollama is running: `ollama list`
- Verify FFmpeg path in Configuration tab
- Check logs for specific error messages

**2. "FFmpeg not found"**
- The app expects FFmpeg at: `f:/Repos/VideoChunking/ffmpeg/bin/ffmpeg.exe`
- Verify the file exists
- Or install system-wide FFmpeg

**3. "Ollama connection failed"**
- Start Ollama: `ollama serve` (in another terminal)
- Or skip classification with the checkbox

**4. "PyAnnote error / HF_TOKEN"**
- Create `.env` file in project root
- Add: `HF_TOKEN=your_huggingface_token`
- Get token from: https://huggingface.co/settings/tokens
- Or skip diarization with the checkbox

**5. Out of Memory**
- Try skipping snippets
- Process shorter clips first
- Close other applications

### Quick Test (Minimal Processing):
For fastest results to test the app:
1. Upload your sample file
2. ✅ Check "Skip Speaker Diarization"
3. ✅ Check "Skip IC/OOC Classification"
4. ✅ Check "Skip Audio Snippets"
5. Process

This will just transcribe the audio without extra processing.

## App Features

### Process Session Tab
- Upload and process D&D recordings
- Full transcription with optional speaker identification
- IC/OOC content separation
- Audio snippet export

### Party Management Tab
- Import/export party configurations
- Define characters, players, and campaign info
- Reuse configurations across sessions

### Character Profiles Tab
- Track character development over time
- Export/import character data
- Automatic profile extraction from transcripts
- View character overviews with stats and history

### Speaker Management Tab
- Map speaker IDs (SPEAKER_00) to real names
- Persistent mappings across sessions
- View speaker profiles per session

### Document Viewer Tab
- View public Google Docs
- Useful for campaign notes or session summaries

### Logs Tab
- View application logs
- Filter for errors/warnings
- Clear old logs

### Social Insights Tab
- Analyze OOC banter keywords
- Generate "Topic Nebula" word cloud
- Discover conversation themes

### Diagnostics Tab
- Discover and run pytest tests
- Useful for development and debugging

### Configuration Tab
- View current settings
- Check GPU status
- See model configurations

### Help Tab
- Setup instructions
- Usage guide
- Troubleshooting tips

## Next Steps

1. **Test with your sample file** to verify the pipeline works
2. **Report any errors** - check the logs for details
3. **Optimize settings** based on your hardware (GPU/CPU)
4. **Configure party settings** for better character tracking

## Stopping the App

To stop the Gradio server:
- In VS Code: Find the terminal running `python app.py` and press Ctrl+C
- Or: `taskkill /F /PID <process_id>` (find PID with `netstat -ano | findstr 7860`)
