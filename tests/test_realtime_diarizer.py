from __future__ import annotations

import asyncio

import numpy as np
import pytest

from src.realtime import (
    AudioStreamIngester,
    RealtimeDiarizer,
    RealtimeDiarizationResult,
)


def make_chunk(seconds: float, *, amplitude: float) -> np.ndarray:
    samples = int(seconds * 16000)
    return np.full(samples, amplitude, dtype=np.float32)


def test_process_chunk_merges_contiguous_segments():
    diarizer = RealtimeDiarizer(sample_rate=16000)

    first = diarizer.process_chunk(make_chunk(0.1, amplitude=0.01))
    assert first.segments == [], "No segment finalized until speaker changes"

    second = diarizer.process_chunk(make_chunk(0.1, amplitude=0.8))
    assert len(second.segments) == 1
    seg = second.segments[0]
    assert seg.speaker_id == "SPEAKER_00"
    assert pytest.approx(seg.start, 1e-6) == 0.0
    assert pytest.approx(seg.end, 1e-6) == 0.1

    third = diarizer.process_chunk(make_chunk(0.1, amplitude=0.02))
    assert len(third.segments) == 1
    seg2 = third.segments[0]
    assert seg2.speaker_id == "SPEAKER_01"
    assert pytest.approx(seg2.start, 1e-6) == 0.1


def test_flush_emits_active_segment():
    diarizer = RealtimeDiarizer(sample_rate=16000)
    diarizer.process_chunk(make_chunk(0.05, amplitude=0.2))
    result = asyncio.run(diarizer.flush())
    assert len(result.segments) == 1
    seg = result.segments[0]
    assert seg.speaker_id == "SPEAKER_01"
    assert pytest.approx(seg.end, 1e-6) == 0.05


def test_consume_chunk_integrates_with_ingester():
    diarizer = RealtimeDiarizer(sample_rate=16000)
    collected: list[RealtimeDiarizationResult] = []

    async def handler(result: RealtimeDiarizationResult):
        if result.segments:
            collected.append(result)

    diarizer.set_segment_handler(handler)
    ingester = AudioStreamIngester(sample_rate=16000, max_buffer_duration=0.05)
    ingester.set_consumer(diarizer.consume_chunk)

    async def runner():
        frame_low = make_chunk(0.05, amplitude=0.01).tobytes()
        frame_high = make_chunk(0.05, amplitude=0.2).tobytes()

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

        await ingester.ingest_async_iterable(Source([frame_low, frame_high]))
        await ingester.drain()
        await diarizer.flush()

    asyncio.run(runner())
    assert collected, "Expected handler to receive diarization results"
    assert collected[0].segments[0].speaker_id == "SPEAKER_00"
