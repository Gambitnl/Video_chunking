"""A simple retry decorator with exponential backoff."""
import time
import random
from functools import wraps
from .logger import get_logger

logger = get_logger("retry")

def retry_with_backoff(retries=5, backoff_in_seconds=1, retry_on_exceptions=(Exception,)):
    """
    A decorator to retry a function with an exponential backoff.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            _retries, _delay = retries, backoff_in_seconds
            while _retries > 1:
                try:
                    return f(*args, **kwargs)
                except retry_on_exceptions as e:
                    logger.warning(f"Caught retryable exception: {e}. Retrying in {_delay} seconds...")
                    time.sleep(_delay + random.uniform(0, 1))
                    _retries -= 1
                    _delay *= 2
            return f(*args, **kwargs)
        return wrapper
    return decorator
