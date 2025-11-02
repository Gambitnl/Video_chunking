"""Low-latency transcription helpers for streaming audio pipelines."""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Deque, Iterable, List, Optional, Protocol

import numpy as np

from ..config import Config
from ..logger import get_logger


class WhisperLikeModel(Protocol):
    """Protocol describing the faster-whisper style interface used by the transcriber."""

    def transcribe(self, audio: np.ndarray, **kwargs) -> tuple[Iterable, SimpleNamespace]:
        ...


@dataclass
class RealtimeTranscriptSegment:
    """Single transcript segment emitted during streaming transcription."""

    text: str
    start: float
    end: float
    confidence: Optional[float] = None
    words: Optional[List[dict]] = None


@dataclass
class RealtimeTranscriptionResult:
    """Container describing the result of a streaming transcription chunk."""

    chunk_start: float
    chunk_end: float
    language: str
    segments: List[RealtimeTranscriptSegment] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.chunk_end - self.chunk_start)


ResultHandler = Callable[[RealtimeTranscriptionResult], Awaitable[None]]


class RealtimeTranscriber:
    """Perform incremental transcription against streaming audio chunks."""

    def __init__(
        self,
        model: WhisperLikeModel,
        *,
        sample_rate: int = 16000,
        history_window: float = 30.0,
        language: Optional[str] = None,
        beam_size: int = 1,
        best_of: int = 1,
        temperature: float = 0.0,
        result_handler: Optional[ResultHandler] = None,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if history_window < 0:
            raise ValueError("history_window must be non-negative")

        self._model = model
        self.sample_rate = sample_rate
        self.history_window = history_window
        default_language = getattr(Config, "WHISPER_LANGUAGE", "en")
        self.language = language or default_language
        self.beam_size = beam_size
        self.best_of = best_of
        self.temperature = temperature
        self._result_handler = result_handler
        self._history: Deque[RealtimeTranscriptSegment] = deque()
        self._processed_duration = 0.0
        self._logger = get_logger("realtime.transcriber")

    def set_result_handler(self, handler: ResultHandler) -> None:
        """Register a callback invoked whenever a chunk is processed."""
        self._result_handler = handler

    async def consume_chunk(self, chunk: np.ndarray) -> RealtimeTranscriptionResult:
        """Async adapter for `AudioStreamIngester` consumers."""
        if chunk.size == 0:
            return RealtimeTranscriptionResult(
                chunk_start=self._processed_duration,
                chunk_end=self._processed_duration,
                language=self.language,
                segments=[],
            )

        result = await asyncio.to_thread(self.transcribe_chunk, chunk)
        if self._result_handler is not None:
            await self._result_handler(result)
        return result

    def transcribe_chunk(self, chunk: np.ndarray) -> RealtimeTranscriptionResult:
        """Transcribe a streaming chunk synchronously."""
        if chunk.size == 0:
            return RealtimeTranscriptionResult(
                chunk_start=self._processed_duration,
                chunk_end=self._processed_duration,
                language=self.language,
                segments=[],
            )

        mono = np.asarray(chunk, dtype=np.float32).reshape(-1)
        chunk_duration = mono.size / float(self.sample_rate)
        chunk_start = self._processed_duration
        chunk_end = chunk_start + chunk_duration

        try:
            segments, info = self._model.transcribe(
                mono,
                beam_size=self.beam_size,
                best_of=self.best_of,
                temperature=self.temperature,
                language=self.language,
                initial_prompt=self._build_context_prompt(),
                vad_filter=False,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            self._logger.exception("Realtime transcription failed: %s", exc)
            self._processed_duration = chunk_end
            return RealtimeTranscriptionResult(
                chunk_start=chunk_start,
                chunk_end=chunk_end,
                language=self.language,
                segments=[],
            )

        result_segments: List[RealtimeTranscriptSegment] = []
        for raw_segment in segments or []:
            segment = self._normalize_segment(raw_segment, chunk_start, chunk_end)
            if segment is not None:
                result_segments.append(segment)

        result = RealtimeTranscriptionResult(
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            language=getattr(info, "language", self.language),
            segments=result_segments,
        )

        self._processed_duration = chunk_end
        self._append_history(result_segments)
        self._trim_history(chunk_end)

        return result

    def _normalize_segment(
        self,
        raw_segment: Any,
        chunk_start: float,
        chunk_end: float,
    ) -> Optional[RealtimeTranscriptSegment]:
        text = self._extract_attr(raw_segment, "text")
        if not text:
            return None

        rel_start = float(self._extract_attr(raw_segment, "start", 0.0))
        rel_end = float(self._extract_attr(raw_segment, "end", rel_start))

        start_time = chunk_start + max(0.0, rel_start)
        end_time = chunk_start + max(rel_start, rel_end)
        if end_time < start_time:
            end_time = start_time

        confidence = self._extract_attr(raw_segment, "confidence")
        words = self._extract_attr(raw_segment, "words")

        if words:
            normalized_words = []
            for word in words:
                if not isinstance(word, dict):
                    continue
                normalized_words.append(
                    {
                        "word": word.get("word", ""),
                        "start": chunk_start + float(word.get("start", rel_start)),
                        "end": chunk_start + float(word.get("end", rel_start)),
                        "probability": word.get("probability"),
                    }
                )
            words = normalized_words

        return RealtimeTranscriptSegment(
            text=text.strip(),
            start=start_time,
            end=min(end_time, chunk_end),
            confidence=confidence,
            words=words,
        )

    @staticmethod
    def _extract_attr(obj: Any, key: str, default: Any = None) -> Any:
        if hasattr(obj, key):
            return getattr(obj, key)
        if isinstance(obj, dict):
            return obj.get(key, default)
        return default

    def _append_history(self, segments: Iterable[RealtimeTranscriptSegment]) -> None:
        for segment in segments:
            self._history.append(segment)

    def _trim_history(self, current_time: float) -> None:
        if self.history_window == 0:
            self._history.clear()
            return

        threshold = max(0.0, current_time - self.history_window)
        while self._history and self._history[0].end < threshold:
            self._history.popleft()

    def _build_context_prompt(self) -> str:
        if not self._history:
            return ""
        return " ".join(segment.text for segment in self._history if segment.text)

    def get_context_prompt(self) -> str:
        """Expose the current context prompt (useful for testing/monitoring)."""
        return self._build_context_prompt()
