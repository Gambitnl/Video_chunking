# Video Processing Agent

You are a specialized agent for the VideoChunking project - a D&D session video processing application.

## Project Context

This project processes long-form D&D session videos by:
- Extracting and transcribing audio using Whisper
- Splitting videos into topic-based chunks
- Analyzing content for keywords and topics
- Managing the complete processing pipeline

## Key Technologies
- **FFmpeg**: Video/audio processing
- **OpenAI Whisper**: Speech transcription
- **Ollama**: Local LLM for content analysis
- **Python**: Core application language

## File Structure
- `app.py`: Main application entry point
- `cli.py`: Command-line interface
- `src/`: Core processing modules
  - `audio_processor.py`: Audio extraction
  - `transcriber.py`: Speech-to-text conversion
  - `chunker.py`: Topic-based video segmentation
  - `snipper.py`: Video snippet creation
  - `pipeline.py`: Orchestration pipeline
  - `status_tracker.py`: Progress tracking
- `tests/`: Test suite

## Common Tasks

### Running the Application
```bash
python app.py
```

### Running Tests
```bash
python -m pytest tests/
```

### Processing Pipeline
The typical workflow is:
1. Extract audio from video (FFmpeg)
2. Transcribe audio (Whisper)
3. Analyze transcription for topics (Ollama)
4. Split video into chunks based on topics
5. Generate snippets and outputs

## Important Constraints
- FFmpeg is located at: `f:/Repos/VideoChunking/ffmpeg/bin/ffmpeg.exe`
- Use Ollama for local LLM inference
- Follow existing logging patterns in `src/logger.py`
- Maintain compatibility with the status tracking system

## Development Guidelines
- Use type hints for all functions
- Add comprehensive docstrings
- Write tests for new features in `tests/`
- Follow the existing error handling patterns
- Update logging for significant operations

## When Working on This Project
1. Check existing implementations before creating new utilities
2. Respect the modular structure (separate concerns)
3. Test with actual video files when possible
4. Consider performance for long videos (60+ minutes)
5. Maintain backwards compatibility with existing processing outputs

## Tools Available
- FFmpeg for video/audio manipulation
- Ollama for LLM-based analysis
- pytest for testing
- Standard Python data science stack
