"""File locking utilities for preventing concurrent write conflicts.

This module provides thread-safe file locking for JSON configuration files
to prevent data corruption when multiple Gradio tabs attempt to modify
the same files concurrently.

Usage:
    from src.file_lock import get_file_lock

    lock = get_file_lock("campaigns.json")
    with lock:
        # Perform file operations safely
        data = json.load(file)
        # ... modify data ...
        json.dump(data, file)
"""

import threading
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger("DDSessionProcessor.file_lock")

# Global registry of locks, keyed by file path
_lock_registry: Dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()


def get_file_lock(file_path: Path | str) -> threading.Lock:
    """
    Get or create a thread lock for a specific file.

    This ensures that the same lock instance is used for a given file
    across the entire application, preventing race conditions when
    multiple threads/tabs try to write to the same JSON file.

    Args:
        file_path: Path to the file to lock (can be Path or string)

    Returns:
        A threading.Lock instance for the specified file

    Example:
        >>> lock = get_file_lock("models/campaigns.json")
        >>> with lock:
        ...     # Safe to write to campaigns.json
        ...     save_campaigns()
    """
    # Normalize path to string for consistent dict keys
    normalized_path = str(Path(file_path).resolve())

    with _registry_lock:
        if normalized_path not in _lock_registry:
            _lock_registry[normalized_path] = threading.Lock()
            logger.debug(f"Created new lock for file: {normalized_path}")

        return _lock_registry[normalized_path]


def clear_lock_registry():
    """
    Clear the lock registry.

    This is primarily useful for testing to reset the lock state
    between test runs. Should not be called in production code.
    """
    with _registry_lock:
        _lock_registry.clear()
        logger.debug("Cleared file lock registry")


class FileLockContext:
    """
    Context manager for file locking with additional safety features.

    Provides automatic lock acquisition/release with timeout support
    and better error handling.

    Example:
        >>> with FileLockContext("models/campaigns.json", timeout=5.0):
        ...     # File operations here
        ...     pass
    """

    def __init__(self, file_path: Path | str, timeout: float = 10.0):
        """
        Initialize file lock context.

        Args:
            file_path: Path to the file to lock
            timeout: Maximum time to wait for lock acquisition (seconds)
        """
        self.file_path = Path(file_path)
        self.timeout = timeout
        self.lock = get_file_lock(file_path)
        self._acquired = False

    def __enter__(self):
        """Acquire the lock."""
        # Try to acquire the lock with timeout
        self._acquired = self.lock.acquire(timeout=self.timeout)

        if not self._acquired:
            raise RuntimeError(
                f"Failed to acquire lock for {self.file_path} within {self.timeout}s. "
                "Another operation may be in progress."
            )

        logger.debug(f"Acquired lock for {self.file_path}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the lock."""
        if self._acquired:
            self.lock.release()
            logger.debug(f"Released lock for {self.file_path}")
            self._acquired = False

        # Don't suppress exceptions
        return False
