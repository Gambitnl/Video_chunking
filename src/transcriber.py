"""Transcription with multiple backend support"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np
from .config import Config
from .chunker import AudioChunk
from .logger import get_logger


@dataclass
class TranscriptionSegment:
    """A segment of transcribed text with timing and metadata"""
    text: str
    start_time: float  # seconds from audio start
    end_time: float
    confidence: Optional[float] = None
    words: Optional[List[Dict]] = None  # Word-level timestamps if available


@dataclass
class ChunkTranscription:
    """Transcription result for a single chunk"""
    chunk_index: int
    chunk_start: float  # Original position in full audio
    chunk_end: float
    segments: List[TranscriptionSegment]
    language: str


class BaseTranscriber(ABC):
    """Abstract base class for transcription backends"""

    @abstractmethod
    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: str = "nl"
    ) -> ChunkTranscription:
        """
        Transcribe a single audio chunk.

        Args:
            chunk: AudioChunk to transcribe
            language: Language code (ISO 639-1)

        Returns:
            ChunkTranscription with segments
        """
        pass


class FasterWhisperTranscriber(BaseTranscriber):
    """
    Local Whisper transcription using faster-whisper.

    Pros:
    - Completely free
    - 4x faster than original Whisper
    - Excellent Dutch support
    - Runs locally (privacy)

    Cons:
    - Requires GPU for best performance
    - Large model download (~3GB)
    """

    def __init__(self, model_name: str = None, device: str = "auto"):
        self.model_name = model_name or Config.WHISPER_MODEL
        self.logger = get_logger('transcriber.faster_whisper')
        self.device = device
        self.model = None  # Defer model loading

    def _load_model_if_needed(self):
        """Load the Whisper model on first use."""
        if self.model is not None:
            return

        from faster_whisper import WhisperModel
        
        # Auto-detect device if not specified
        if self.device == "auto":
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.logger.info("Loading Whisper model '%s' on %s...", self.model_name, self.device)
        self.model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type="float16" if self.device == "cuda" else "int8"
        )
        self.logger.info("Whisper model loaded.")

    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: str = "nl"
    ) -> ChunkTranscription:
        """Transcribe using local faster-whisper"""
        self._load_model_if_needed()

        self.logger.debug(
            "Transcribing chunk %d (start=%.2fs, end=%.2fs, duration=%.2fs)",
            chunk.chunk_index,
            chunk.start_time,
            chunk.end_time,
            chunk.end_time - chunk.start_time
        )

        segments, info = self.model.transcribe(
            chunk.audio,
            language=language,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,  # Built-in VAD for better accuracy
            vad_parameters=dict(
                min_silence_duration_ms=500
            )
        )

        # Convert segments to our format
        transcription_segments = []
        for segment in segments:
            # Adjust timestamps relative to full audio (not just chunk)
            absolute_start = chunk.start_time + segment.start
            absolute_end = chunk.start_time + segment.end

            # Extract word-level data if available
            words = None
            if hasattr(segment, 'words') and segment.words:
                words = [
                    {
                        'word': w.word,
                        'start': chunk.start_time + w.start,
                        'end': chunk.start_time + w.end,
                        'probability': w.probability
                    }
                    for w in segment.words
                ]

            transcription_segments.append(TranscriptionSegment(
                text=segment.text.strip(),
                start_time=absolute_start,
                end_time=absolute_end,
                confidence=getattr(segment, 'avg_logprob', None),
                words=words
            ))

        return ChunkTranscription(
            chunk_index=chunk.chunk_index,
            chunk_start=chunk.start_time,
            chunk_end=chunk.end_time,
            segments=transcription_segments,
            language=info.language
        )


class GroqTranscriber(BaseTranscriber):
    """
    Groq API transcription - fast cloud-based Whisper.

    Pros:
    - Very fast (hardware accelerated)
    - Generous free tier
    - No local GPU needed

    Cons:
    - Requires API key
    - Internet connection required
    - Rate limits
    """

    def __init__(self, api_key: str = None):
        from groq import Groq
        import tempfile

        self.api_key = api_key or Config.GROQ_API_KEY
        if not self.api_key:
            raise ValueError("Groq API key required. Set GROQ_API_KEY in .env")

        self.client = Groq(api_key=self.api_key)
        self.temp_dir = Path(tempfile.gettempdir())
        self.logger = get_logger("transcriber.groq")

    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: str = "nl"
    ) -> ChunkTranscription:
        """Transcribe using Groq API"""
        import soundfile as sf

        # Groq requires a file path, so save chunk temporarily
        temp_path = self.temp_dir / f"chunk_{chunk.chunk_index}.wav"
        sf.write(str(temp_path), chunk.audio, chunk.sample_rate)
        self.logger.debug("Submitting chunk %d to Groq (temp file: %s)", chunk.chunk_index, temp_path)

        try:
            # Call Groq API
            with open(temp_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment", "word"]
                )

            # Parse response
            segments = []
            response_words = getattr(response, "words", None)
            for seg in response.segments:
                # Adjust timestamps to absolute time
                absolute_start = chunk.start_time + seg['start']
                absolute_end = chunk.start_time + seg['end']

                words = None
                if response_words:
                    words = [
                        {
                            'word': w['word'],
                            'start': chunk.start_time + w['start'],
                            'end': chunk.start_time + w['end'],
                            'probability': w.get('probability', 1.0)
                        }
                        for w in response_words
                        if seg['start'] <= w['start'] <= seg['end']
                    ]

                segments.append(TranscriptionSegment(
                    text=seg['text'].strip(),
                    start_time=absolute_start,
                    end_time=absolute_end,
                    words=words
                ))

            return ChunkTranscription(
                chunk_index=chunk.chunk_index,
                chunk_start=chunk.start_time,
                chunk_end=chunk.end_time,
                segments=segments,
                language=response.language
            )

        finally:
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
                self.logger.debug("Cleaned temporary chunk file %s", temp_path)


class TranscriberFactory:
    """Factory to create appropriate transcriber based on config"""

    @staticmethod
    def create(backend: str = None) -> BaseTranscriber:
        """
        Create transcriber instance.

        Args:
            backend: 'local', 'groq', or 'openai' (defaults to config)

        Returns:
            Appropriate transcriber instance
        """
        backend = backend or Config.WHISPER_BACKEND

        if backend == "local":
            return FasterWhisperTranscriber()
        elif backend == "groq":
            return GroqTranscriber()
        elif backend == "openai":
            # TODO: Implement OpenAI transcriber if needed
            raise NotImplementedError("OpenAI transcriber not yet implemented")
        else:
            raise ValueError(f"Unknown transcriber backend: {backend}")
