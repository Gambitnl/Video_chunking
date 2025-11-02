from __future__ import annotations

import asyncio
from types import SimpleNamespace

import numpy as np
import pytest

from src.realtime import (
    AudioStreamIngester,
    RealtimeTranscriber,
    RealtimeTranscriptionResult,
)


class StubSegment:
    def __init__(self, text: str, start: float, end: float, confidence: float = 0.9):
        self.text = text
        self.start = start
        self.end = end
        self.confidence = confidence


class StubWhisperModel:
    def __init__(self, *, language: str = "en"):
        self.language = language
        self.calls = 0

    def transcribe(self, audio: np.ndarray, **kwargs):
        duration = audio.size / 16000.0
        text = f"chunk-{self.calls}"
        segment = StubSegment(text=text, start=0.0, end=duration)
        self.calls += 1
        info = SimpleNamespace(language=self.language)
        return [segment], info


def make_chunk(seconds: float, *, amplitude: float = 0.01) -> np.ndarray:
    samples = int(seconds * 16000)
    return np.full(samples, amplitude, dtype=np.float32)


def test_transcribe_chunk_tracks_timestamps():
    model = StubWhisperModel()
    transcriber = RealtimeTranscriber(model, sample_rate=16000, history_window=10.0)

    first = transcriber.transcribe_chunk(make_chunk(0.1))
    second = transcriber.transcribe_chunk(make_chunk(0.2))

    assert pytest.approx(first.chunk_start, 1e-6) == 0.0
    assert pytest.approx(first.chunk_end, 1e-6) == 0.1
    assert first.segments[0].text == "chunk-0"
    assert pytest.approx(first.segments[0].end, 1e-6) == 0.1

    assert pytest.approx(second.chunk_start, 1e-6) == 0.1
    assert pytest.approx(second.segments[0].start, 1e-6) == 0.1
    assert second.segments[0].text == "chunk-1"

    context = transcriber.get_context_prompt()
    assert "chunk-0" in context and "chunk-1" in context


def test_context_window_prunes_old_segments():
    model = StubWhisperModel()
    transcriber = RealtimeTranscriber(model, sample_rate=16000, history_window=0.05)

    transcriber.transcribe_chunk(make_chunk(0.1))  # chunk-0
    transcriber.transcribe_chunk(make_chunk(0.1))  # chunk-1

    context = transcriber.get_context_prompt()
    assert "chunk-1" in context
    assert "chunk-0" not in context


def test_consume_chunk_invokes_result_handler():
    model = StubWhisperModel()
    collected: list[RealtimeTranscriptionResult] = []

    async def handler(result: RealtimeTranscriptionResult):
        collected.append(result)

    transcriber = RealtimeTranscriber(
        model,
        sample_rate=16000,
        history_window=5.0,
        result_handler=handler,
    )

    ingester = AudioStreamIngester(sample_rate=16000, max_buffer_duration=0.05)
    ingester.set_consumer(transcriber.consume_chunk)

    async def runner():
        frame = make_chunk(0.03).tobytes()

        class Source:
            def __init__(self, messages):
                self._messages = iter(messages)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self._messages)
                except StopIteration:
                    raise StopAsyncIteration

        await ingester.ingest_async_iterable(Source([frame, frame]))
        await ingester.drain()
        await asyncio.sleep(0)  # Allow handler to run

    asyncio.run(runner())

    assert len(collected) >= 1
    assert collected[0].segments[0].text == "chunk-0"
