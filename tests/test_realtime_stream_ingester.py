import asyncio
from pathlib import Path

import numpy as np
import pytest

from src.realtime import AudioBuffer, AudioStreamIngester


def test_audio_buffer_basic():
    buffer = AudioBuffer(sample_rate=16000, max_duration=0.1)
    chunk = np.ones(800, dtype=np.float32)  # 0.05 seconds at 16kHz
    buffer.append(chunk)
    assert pytest.approx(buffer.duration, 0.0001) == 0.05
    buffer.append(chunk)
    assert buffer.is_ready()
    combined = buffer.pop()
    assert combined.shape[0] == 1600
    assert buffer.duration == 0.0


def test_ingest_async_iterable_triggers_consumer():
    async def runner():
        collected = []

        async def consumer(chunk: np.ndarray):
            collected.append(chunk)

        ingester = AudioStreamIngester(sample_rate=16000, max_buffer_duration=0.05, consumer=consumer)

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

        frame = np.ones(800, dtype=np.float32).tobytes()
        await ingester.ingest_async_iterable(Source([frame, frame]))
        await ingester.drain()

        assert collected, "Expected consumer to be invoked"
        assert collected[0].dtype == np.float32

    asyncio.run(runner())


def test_ingest_file_tail(tmp_path: Path):
    async def runner():
        data_path = tmp_path / "stream.f32"
        data_path.write_bytes(b"")

        collected = []

        async def consumer(chunk: np.ndarray):
            collected.append(chunk.copy())

        stop_event = asyncio.Event()
        ingester = AudioStreamIngester(sample_rate=16000, max_buffer_duration=0.01, consumer=consumer)

        async def writer():
            await asyncio.sleep(0.05)
            with data_path.open("ab") as handle:
                handle.write(np.ones(320, dtype=np.float32).tobytes())
                handle.flush()
            await asyncio.sleep(0.1)
            stop_event.set()

        task = asyncio.create_task(
            ingester.ingest_file_tail(
                data_path,
                chunk_size=320 * 4,
                poll_interval=0.01,
                stop_event=stop_event,
                start_at_end=False,
            )
        )
        await asyncio.gather(writer(), task)

        assert collected, "Expected data to be ingested from file tail"
        assert collected[0].shape[0] == 320

    asyncio.run(runner())
