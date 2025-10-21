---
skill_name: video-chunk
description: Process a D&D session video through the chunking pipeline
---

# Video Chunking Skill

Process a D&D session video file through the complete chunking pipeline.

## What This Skill Does

This skill orchestrates the complete video processing workflow:

1. **Extract Audio**: Uses FFmpeg to extract audio from the video file
2. **Transcribe**: Uses Whisper to transcribe the audio to text
3. **Analyze**: Uses Ollama to analyze the transcription for topics and keywords
4. **Chunk**: Splits the video into topic-based segments
5. **Generate Outputs**: Creates snippet files and metadata

## Prerequisites

Before running this skill, ensure:
- FFmpeg is available at `f:/Repos/VideoChunking/ffmpeg/bin/ffmpeg.exe`
- Ollama is running locally
- Input video file path is provided
- Sufficient disk space for processing

## Usage

When invoked, this skill will:
1. Verify all dependencies are available
2. Run the processing pipeline via `python app.py` or the appropriate module
3. Monitor progress and report status
4. Handle errors gracefully and provide diagnostic information

## Example Invocation

User: "Process the session video at videos/session_001.mp4"

The skill will then execute the pipeline and provide status updates throughout.

## Error Handling

Common issues and solutions:
- **FFmpeg not found**: Verify FFmpeg path in settings
- **Ollama connection failed**: Ensure Ollama is running (`ollama serve`)
- **Out of memory**: Process shorter videos or adjust chunk parameters
- **Transcription errors**: Check audio quality and Whisper model

## Output

The skill produces:
- Transcription files (`.txt` or `.json`)
- Video chunks (separate video files)
- Metadata files with timestamps and topics
- Processing logs in the configured log directory
