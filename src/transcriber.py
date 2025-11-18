"""Transcription with multiple backend support"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np
from .config import Config
from .chunker import AudioChunk
from .logger import get_logger
from .preflight import PreflightIssue
from .retry import retry_with_backoff


@dataclass
class TranscriptionSegment:
    """A segment of transcribed text with timing and metadata"""
    text: str
    start_time: float  # seconds from audio start
    end_time: float
    confidence: Optional[float] = None
    words: Optional[List[Dict]] = None  # Word-level timestamps if available

    def to_dict(self) -> dict:
        """Converts the TranscriptionSegment to a dictionary for serialization."""
        return {
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "confidence": self.confidence,
            "words": self.words,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TranscriptionSegment":
        """Creates a TranscriptionSegment from a dictionary."""
        return cls(
            text=data["text"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            confidence=data.get("confidence"),
            words=data.get("words"),
        )


@dataclass
class ChunkTranscription:
    """Transcription result for a single chunk"""
    chunk_index: int
    chunk_start: float  # Original position in full audio
    chunk_end: float
    segments: List[TranscriptionSegment]
    language: str

    def preview_text(self, max_chars: int = 200) -> str:
        """Return a short text preview for UI status updates."""
        combined = " ".join(
            segment.text.strip()
            for segment in self.segments
            if segment.text and segment.text.strip()
        ).strip()
        if not combined:
            return ""
        if len(combined) <= max_chars:
            return combined
        return f"{combined[:max_chars].rstrip()}..."

    def to_dict(self) -> dict:
        """Converts the ChunkTranscription to a dictionary for serialization."""
        return {
            "chunk_index": self.chunk_index,
            "chunk_start": self.chunk_start,
            "chunk_end": self.chunk_end,
            "segments": [s.to_dict() for s in self.segments],
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChunkTranscription":
        """Creates a ChunkTranscription from a dictionary."""
        return cls(
            chunk_index=data["chunk_index"],
            chunk_start=data["chunk_start"],
            chunk_end=data["chunk_end"],
            segments=[TranscriptionSegment.from_dict(s) for s in data["segments"]],
            language=data["language"],
        )


class BaseTranscriber(ABC):
    """Abstract base class for transcription backends"""

    @retry_with_backoff()
    def _make_api_call(self, audio_file, language):
        return self.client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            language=language,
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"]
        )

    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: str = Config.WHISPER_LANGUAGE
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

    def preflight_check(self):
        """Return an iterable of PreflightIssue objects."""
        return []


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

    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or Config.WHISPER_MODEL
        self.logger = get_logger('transcriber.faster_whisper')
        self.device = (device or Config.get_inference_device()).lower()
        self.model = None  # Defer model loading

    def _load_model_if_needed(self):
        """Load the Whisper model on first use."""
        if self.model is not None:
            return

        from faster_whisper import WhisperModel

        resolved_device = self.device
        if resolved_device not in {"cpu", "cuda"}:
            resolved_device = Config.get_inference_device()

        if resolved_device == "cuda":
            try:
                import torch  # type: ignore
                if not torch.cuda.is_available():
                    self.logger.warning(
                        "CUDA requested for Whisper but no GPU detected. Falling back to CPU."
                    )
                    resolved_device = "cpu"
            except Exception:
                self.logger.warning(
                    "Could not verify CUDA availability. Falling back to CPU."
                )
                resolved_device = "cpu"

        compute_type = "float16" if resolved_device == "cuda" else "int8"
        self.logger.info(
            "Loading Whisper model '%s' on %s (compute_type=%s)...",
            self.model_name,
            resolved_device,
            compute_type
        )
        self.device = resolved_device
        self.model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=compute_type
        )
        self.logger.info("Whisper model loaded.")

    def preflight_check(self):
        issues = []
        target_device = Config.get_inference_device()
        if target_device == "cuda":
            try:
                import torch  # type: ignore
                if not torch.cuda.is_available():
                    issues.append(
                        PreflightIssue(
                            component="transcriber",
                            message="CUDA requested but no GPU is available; transcription will fall back to CPU.",
                            severity="warning",
                        )
                    )
            except Exception as exc:
                issues.append(
                    PreflightIssue(
                        component="transcriber",
                        message=f"Could not verify CUDA availability: {exc}",
                        severity="warning",
                    )
                )
        return issues

    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: str = Config.WHISPER_LANGUAGE
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
        language: str = Config.WHISPER_LANGUAGE
    ) -> ChunkTranscription:
        """Transcribe using Groq API"""
        import soundfile as sf

        # Groq requires a file path, so save chunk temporarily
        temp_path = self.temp_dir / f"chunk_{chunk.chunk_index}.wav"
        sf.write(str(temp_path), chunk.audio, chunk.sample_rate)
        self.logger.debug("Submitting chunk %d to Groq (temp file: %s)", chunk.chunk_index, temp_path)

        try:
            # Call Groq API
            with open(str(temp_path), "rb") as audio_file:
                response = self._make_api_call(audio_file, language)

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

    def preflight_check(self):
        """Check Groq API availability and authentication."""
        issues = []

        if not self.api_key:
            issues.append(
                PreflightIssue(
                    component="transcriber.groq",
                    message="Groq API key not configured. Set GROQ_API_KEY in .env file.",
                    severity="error",
                )
            )
            return issues

        try:
            # Test API with minimal request
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": "test"}],
                model="llama-3.3-70b-versatile",
                max_tokens=1,
            )
            self.logger.debug("Groq API preflight check passed")
        except Exception as e:
            issues.append(
                PreflightIssue(
                    component="transcriber.groq",
                    message=f"Groq API test failed: {str(e)}. Check API key and internet connection.",
                    severity="error",
                )
            )

        return issues

    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    def _make_api_call(self, audio_file, language):
        """Make API call with retry logic."""
        return self.client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3-turbo",
            language=language if language != "auto" else None,
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"]
        )


class OpenAITranscriber(BaseTranscriber):
    """
    OpenAI Whisper API transcription - cloud-based Whisper.

    Pros:
    - Very fast (cloud-accelerated)
    - High quality results
    - No local GPU needed
    - Official OpenAI implementation

    Cons:
    - Requires API key
    - Internet connection required
    - Pay-per-use pricing
    """

    def __init__(self, api_key: str = None):
        from openai import OpenAI
        import tempfile

        self.api_key = api_key or Config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY in .env")

        self.client = OpenAI(api_key=self.api_key)
        self.temp_dir = Path(tempfile.gettempdir())
        self.logger = get_logger("transcriber.openai")

    def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: str = Config.WHISPER_LANGUAGE
    ) -> ChunkTranscription:
        """Transcribe using OpenAI Whisper API"""
        import soundfile as sf

        # OpenAI requires a file path, so save chunk temporarily
        temp_path = self.temp_dir / f"chunk_{chunk.chunk_index}.wav"
        sf.write(str(temp_path), chunk.audio, chunk.sample_rate)
        self.logger.debug("Submitting chunk %d to OpenAI (temp file: %s)", chunk.chunk_index, temp_path)

        try:
            # Call OpenAI API
            with open(str(temp_path), "rb") as audio_file:
                response = self._make_api_call(audio_file, language)

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

    def preflight_check(self):
        """Check OpenAI API availability and authentication."""
        issues = []

        if not self.api_key:
            issues.append(
                PreflightIssue(
                    component="transcriber.openai",
                    message="OpenAI API key not configured. Set OPENAI_API_KEY in .env file.",
                    severity="error",
                )
            )
            return issues

        try:
            # Test API with minimal request
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": "test"}],
                model="gpt-3.5-turbo",
                max_tokens=1,
            )
            self.logger.debug("OpenAI API preflight check passed")
        except Exception as e:
            issues.append(
                PreflightIssue(
                    component="transcriber.openai",
                    message=f"OpenAI API test failed: {str(e)}. Check API key and internet connection.",
                    severity="error",
                )
            )

        return issues

    @retry_with_backoff(retries=3, backoff_in_seconds=1)
    def _make_api_call(self, audio_file, language):
        """Make API call with retry logic."""
        return self.client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            language=language if language != "auto" else None,
            response_format="verbose_json",
            timestamp_granularities=["segment", "word"]
        )


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

        if backend in ("local", "whisper"):
            return FasterWhisperTranscriber()
        elif backend == "groq":
            return GroqTranscriber()
        elif backend == "openai":
            return OpenAITranscriber()
        else:
            raise ValueError(f"Unknown transcriber backend: {backend}")
