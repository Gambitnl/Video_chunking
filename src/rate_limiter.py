"""Simple rate limiter utilities."""
from __future__ import annotations

from collections import deque
from typing import Callable, Deque, Optional
import time


class RateLimiter:
    """Token bucket style limiter that caps API call throughput."""

    def __init__(
        self,
        max_calls: int,
        period: float,
        burst_size: Optional[int] = None,
        clock: Optional[Callable[[], float]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
    ):
        if max_calls <= 0:
            raise ValueError("max_calls must be > 0")
        self._period = max(period, 0.001)
        self.max_calls = max_calls
        self.burst_size = max(burst_size or max_calls, 1)
        self._clock = clock or time.monotonic
        self._sleep = sleeper or time.sleep
        self._timestamps: Deque[float] = deque()

    @property
    def period(self) -> float:
        return self._period

    def acquire(self) -> None:
        """Block until a new call fits within the configured window."""
        now = self._clock()
        self._prune(now)
        if len(self._timestamps) >= self.max_calls:
            sleep_time = self._period - (now - self._timestamps[0])
            if sleep_time > 0:
                self._sleep(sleep_time)
                now = self._clock()
                self._prune(now)
        self._timestamps.append(now)

    def penalize(self, extra_delay: Optional[float] = None) -> None:
        """Sleep for an additional delay (defaults to one period)."""
        delay = extra_delay if extra_delay is not None else self._period
        if delay > 0:
            self._sleep(delay)

    def _prune(self, now: float) -> None:
        boundary = now - self._period
        while self._timestamps and self._timestamps[0] <= boundary:
            self._timestamps.popleft()

