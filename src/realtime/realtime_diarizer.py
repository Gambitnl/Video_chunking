"""Realtime-friendly diarization scaffolding."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

import numpy as np

from ..logger import get_logger


@dataclass
class RealtimeSpeakerSegment:
    """Represents a speaker-labelled time span."""

    speaker_id: str
    start: float
    end: float
    confidence: Optional[float] = None


@dataclass
class RealtimeDiarizationResult:
    """Container describing diarization output for a processed chunk."""

    chunk_start: float
    chunk_end: float
    segments: List[RealtimeSpeakerSegment] = field(default_factory=list)


SegmentHandler = Callable[[RealtimeDiarizationResult], Awaitable[None]]


class EnergyBasedSpeakerClassifier:
    """Very lightweight speaker classifier using mean absolute amplitude."""

    def __init__(
        self,
        *,
        threshold: float = 0.05,
        low_speaker: str = "SPEAKER_00",
        high_speaker: str = "SPEAKER_01",
    ) -> None:
        self.threshold = threshold
        self.low_speaker = low_speaker
        self.high_speaker = high_speaker

    def predict(self, chunk: np.ndarray) -> tuple[str, float]:
        """Return speaker label and confidence score."""
        if chunk.size == 0:
            return self.low_speaker, 0.0

        amplitude = float(np.mean(np.abs(chunk)))
        if amplitude >= self.threshold:
            score = min(1.0, amplitude / max(self.threshold, 1e-6))
            return self.high_speaker, score
        score = 1.0 - min(1.0, amplitude / max(self.threshold, 1e-6))
        return self.low_speaker, score


class RealtimeDiarizer:
    """Incremental diarization tracker that works alongside the realtime transcriber."""

    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        speaker_classifier: Optional[EnergyBasedSpeakerClassifier] = None,
        segment_handler: Optional[SegmentHandler] = None,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        self.sample_rate = sample_rate
        self._classifier = speaker_classifier or EnergyBasedSpeakerClassifier()
        self._segment_handler = segment_handler
        self._processed_duration = 0.0
        self._active_segment: Optional[RealtimeSpeakerSegment] = None
        self._logger = get_logger("realtime.diarizer")

    def set_segment_handler(self, handler: SegmentHandler) -> None:
        """Register coroutine invoked when new diarization result is ready."""
        self._segment_handler = handler

    async def consume_chunk(self, chunk: np.ndarray) -> RealtimeDiarizationResult:
        """Async adapter mirroring the ingestion/transcriber interface."""
        result = self.process_chunk(chunk)
        if self._segment_handler is not None:
            await self._segment_handler(result)
        return result

    def process_chunk(self, chunk: np.ndarray) -> RealtimeDiarizationResult:
        """Process a mono float32 chunk and update speaker assignments."""
        mono = np.asarray(chunk, dtype=np.float32).reshape(-1)
        chunk_duration = mono.size / float(self.sample_rate) if mono.size else 0.0
        chunk_start = self._processed_duration
        chunk_end = chunk_start + chunk_duration

        new_segments: List[RealtimeSpeakerSegment] = []

        if mono.size:
            speaker_id, confidence = self._classifier.predict(mono)
            if (
                self._active_segment
                and self._active_segment.speaker_id == speaker_id
            ):
                self._active_segment.end = chunk_end
                self._active_segment.confidence = (
                    self._active_segment.confidence or confidence
                )
            else:
                if self._active_segment is not None:
                    new_segments.append(self._active_segment)
                self._active_segment = RealtimeSpeakerSegment(
                    speaker_id=speaker_id,
                    start=chunk_start,
                    end=chunk_end,
                    confidence=confidence,
                )
        else:
            if self._active_segment is not None:
                new_segments.append(self._active_segment)
                self._active_segment = None

        self._processed_duration = chunk_end

        result = RealtimeDiarizationResult(
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            segments=list(new_segments),
        )
        return result

    async def flush(self) -> RealtimeDiarizationResult:
        """Flush any active segment to downstream handlers."""
        if self._active_segment is None:
            return RealtimeDiarizationResult(
                chunk_start=self._processed_duration,
                chunk_end=self._processed_duration,
                segments=[],
            )

        segment = self._active_segment
        self._active_segment = None
        result = RealtimeDiarizationResult(
            chunk_start=segment.start,
            chunk_end=segment.end,
            segments=[segment],
        )

        if self._segment_handler is not None:
            await self._segment_handler(result)
        return result
