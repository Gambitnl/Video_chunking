import pytest

from src.rate_limiter import RateLimiter


def test_rate_limiter_sleeps_when_burst_exceeded():
    sleeps = []
    current_time = [0.0]

    def clock():
        return current_time[0]

    def sleeper(duration: float):
        sleeps.append(duration)
        current_time[0] += duration

    limiter = RateLimiter(max_calls=2, period=1.0, burst_size=2, clock=clock, sleeper=sleeper)

    limiter.acquire()
    limiter.acquire()
    limiter.acquire()

    assert sleeps == [1.0]
    assert pytest.approx(current_time[0]) == 1.0


def test_penalize_uses_period_by_default():
    sleeps = []

    limiter = RateLimiter(
        max_calls=1,
        period=0.5,
        burst_size=1,
        clock=lambda: 0.0,
        sleeper=lambda duration: sleeps.append(duration),
    )

    limiter.penalize()
    limiter.penalize(0.25)

    assert sleeps == [0.5, 0.25]


def test_rate_limiter_enforces_max_calls_not_burst():
    """Verify that max_calls is enforced even when burst_size is larger."""
    sleeps = []
    current_time = [0.0]

    def clock():
        return current_time[0]

    def sleeper(duration: float):
        sleeps.append(duration)
        current_time[0] += duration

    # max_calls=14, burst_size=20 (like Groq config)
    limiter = RateLimiter(max_calls=14, period=1.0, burst_size=20, clock=clock, sleeper=sleeper)

    # Should allow 14 calls without sleeping
    for _ in range(14):
        limiter.acquire()
    assert len(sleeps) == 0

    # 15th call should trigger sleep
    limiter.acquire()
    assert len(sleeps) == 1
    assert pytest.approx(sleeps[0]) == 1.0
