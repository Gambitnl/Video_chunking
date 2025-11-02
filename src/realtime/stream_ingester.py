"""Async audio stream ingestion utilities for real-time processing."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, AsyncIterable, Awaitable, Callable, Optional

import numpy as np


ChunkConsumer = Callable[[np.ndarray], Awaitable[None]]


class AudioBuffer:
    """Accumulate audio chunks until a duration threshold is reached."""

    def __init__(self, *, sample_rate: int = 16000, max_duration: float = 30.0) -> None:
        if max_duration <= 0:
            raise ValueError("max_duration must be positive")
        self.sample_rate = sample_rate
        self.max_duration = max_duration
        self._segments: list[np.ndarray] = []
        self._sample_count = 0

    @property
    def duration(self) -> float:
        """Current buffered duration in seconds."""
        if self.sample_rate <= 0:
            return 0.0
        return self._sample_count / float(self.sample_rate)

    def append(self, chunk: np.ndarray) -> None:
        """Append a new chunk to the buffer."""
        if chunk.size == 0:
            return
        mono = chunk.reshape(-1).astype(np.float32, copy=False)
        self._segments.append(mono)
        self._sample_count += mono.size

    def is_ready(self) -> bool:
        """Return True when buffered duration meets or exceeds the threshold."""
        return self.duration >= self.max_duration

    def pop(self) -> np.ndarray:
        """Return the buffered audio and clear the buffer."""
        if not self._segments:
            return np.empty(0, dtype=np.float32)
        combined = np.concatenate(self._segments).astype(np.float32, copy=False)
        self.clear()
        return combined

    def clear(self) -> None:
        """Clear the buffer contents."""
        self._segments.clear()
        self._sample_count = 0


class AudioStreamIngester:
    """Handle streaming audio input from WebSockets, async generators, or file tails."""

    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        max_buffer_duration: float = 5.0,
        consumer: Optional[ChunkConsumer] = None,
    ) -> None:
        self.buffer = AudioBuffer(sample_rate=sample_rate, max_duration=max_buffer_duration)
        self._consumer = consumer
        self._lock = asyncio.Lock()

    def set_consumer(self, consumer: ChunkConsumer) -> None:
        """Register the coroutine that receives flushed audio chunks."""
        self._consumer = consumer

    async def ingest_websocket(self, websocket: Any) -> None:
        """Consume audio frames from an async WebSocket object."""
        await self.ingest_async_iterable(websocket)

    async def ingest_async_iterable(self, source: AsyncIterable[Any]) -> None:
        """Consume audio frames from any async iterable (e.g., async generator)."""
        async for message in source:
            array = self._to_array(message)
            if array.size == 0:
                continue
            self.buffer.append(array)
            if self.buffer.is_ready():
                await self.flush()

    async def ingest_file_tail(
        self,
        file_path: Path,
        *,
        chunk_size: int = 4096,
        poll_interval: float = 0.25,
        stop_event: Optional[asyncio.Event] = None,
        start_at_end: bool = True,
    ) -> None:
        """Tail a file and ingest newly appended bytes as float32 frames."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(path)

        loop = asyncio.get_running_loop()

        def read_chunk(handle) -> bytes:
            return handle.read(chunk_size)

        with path.open("rb") as handle:
            if start_at_end:
                handle.seek(0, 2)
            while True:
                if stop_event and stop_event.is_set():
                    break
                data = await loop.run_in_executor(None, read_chunk, handle)
                if data:
                    array = self._to_array(data)
                    if array.size:
                        self.buffer.append(array)
                        if self.buffer.is_ready():
                            await self.flush()
                else:
                    await asyncio.sleep(poll_interval)

    async def flush(self) -> None:
        """Flush buffered audio to the registered consumer."""
        async with self._lock:
            chunk = self.buffer.pop()
            if chunk.size == 0:
                return
            if self._consumer is not None:
                await self._consumer(chunk)

    async def drain(self) -> None:
        """Flush any remaining samples even if the buffer is below threshold."""
        await self.flush()

    @staticmethod
    def _to_array(message: Any) -> np.ndarray:
        """Convert an incoming message to a float32 numpy array."""
        if message is None:
            return np.empty(0, dtype=np.float32)

        if isinstance(message, np.ndarray):
            return message.astype(np.float32, copy=False)

        if isinstance(message, (bytes, bytearray, memoryview)):
            buffer = np.frombuffer(message, dtype=np.float32)
            return buffer.astype(np.float32, copy=False)

        if isinstance(message, list):
            return np.asarray(message, dtype=np.float32)

        if hasattr(message, "buffer"):
            return np.frombuffer(message.buffer, dtype=np.float32).astype(np.float32, copy=False)

        raise TypeError(f"Unsupported audio message type: {type(message)}")
