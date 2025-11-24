"""
Global Lock Manager for coordinating access to shared resources.

This module provides a centralized locking mechanism to prevent race conditions
across different UI tabs and background processes. It supports locking logical
resources (e.g., "campaign:123", "session:abc") rather than just physical files.

Usage:
    from src.lock_manager import LockManager, LockTimeoutError

    # Acquire a lock
    try:
        with LockManager.lock("campaign", "campaign_001"):
            # Critical section
            pass
    except LockTimeoutError:
        print("Could not acquire lock")
"""

import threading
import time
import logging
from typing import Dict, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class LockTimeoutError(Exception):
    """Raised when a lock cannot be acquired within the specified timeout."""
    pass

class LockManager:
    """
    Centralized manager for resource locks.

    Uses threading.RLock to allow re-entrant locking within the same thread,
    while preventing concurrent access from different threads (users).
    """

    _locks: Dict[str, threading.RLock] = {}
    _lock_registry_lock = threading.Lock()

    # Track who holds the lock for debugging/status (optional, basic impl)
    _lock_owners: Dict[str, str] = {}

    @staticmethod
    def _get_lock_key(resource_type: str, resource_id: str) -> str:
        """Generate a unique key for the resource."""
        return f"{resource_type}:{resource_id}"

    @classmethod
    def get_lock_object(cls, resource_type: str, resource_id: str) -> threading.RLock:
        """Get or create the RLock object for a resource."""
        key = cls._get_lock_key(resource_type, resource_id)
        with cls._lock_registry_lock:
            if key not in cls._locks:
                cls._locks[key] = threading.RLock()
            return cls._locks[key]

    @classmethod
    def is_locked(cls, resource_type: str, resource_id: str) -> bool:
        """
        Check if a resource is currently locked.

        Note: RLock doesn't easily expose 'is_locked()' in a thread-safe way
        that returns True if *another* thread holds it.
        This method is an approximation or requires tracking owners.
        """
        # RLock doesn't have a locked() method that works across threads reliably for query
        # without internal hacks.
        # However, we can try to acquire non-blocking.
        key = cls._get_lock_key(resource_type, resource_id)
        with cls._lock_registry_lock:
            if key not in cls._locks:
                return False
            lock = cls._locks[key]

        # Try to acquire without blocking
        acquired = lock.acquire(blocking=False)
        if acquired:
            lock.release()
            return False # We could acquire it, so it wasn't locked by someone else
        return True # Could not acquire, so it is locked

    @classmethod
    @contextmanager
    def lock(cls, resource_type: str, resource_id: str, timeout: float = 5.0, owner_id: str = "unknown"):
        """
        Context manager to acquire a lock for a resource.

        Args:
            resource_type: Type of resource (e.g., 'campaign', 'session')
            resource_id: ID of the resource
            timeout: Max time to wait in seconds
            owner_id: Identifier for the requester (for logging)

        Raises:
            LockTimeoutError: If lock cannot be acquired
        """
        key = cls._get_lock_key(resource_type, resource_id)
        lock_obj = cls.get_lock_object(resource_type, resource_id)

        start_time = time.time()
        # RLock.acquire with timeout is available in Python 3.2+
        # But standard threading.Lock/RLock blocking=True, timeout=X is supported.

        # Note: threading.RLock.acquire does support timeout.
        acquired = lock_obj.acquire(timeout=timeout)

        if not acquired:
            logger.warning(f"Failed to acquire lock for {key} (requester: {owner_id}) after {timeout}s")
            raise LockTimeoutError(f"Resource {key} is currently busy. Please try again later.")

        try:
            logger.debug(f"Lock acquired for {key} by {owner_id}")
            yield
        finally:
            lock_obj.release()
            logger.debug(f"Lock released for {key} by {owner_id}")

    @classmethod
    def acquire(cls, resource_type: str, resource_id: str, timeout: float = 5.0) -> bool:
        """
        Manually acquire a lock. Must be released manually.

        Returns:
            True if acquired, False if timeout.
        """
        lock_obj = cls.get_lock_object(resource_type, resource_id)
        return lock_obj.acquire(timeout=timeout)

    @classmethod
    def release(cls, resource_type: str, resource_id: str):
        """Manually release a lock."""
        lock_obj = cls.get_lock_object(resource_type, resource_id)
        try:
            lock_obj.release()
        except RuntimeError:
            logger.error(f"Attempted to release unheld lock for {resource_type}:{resource_id}")
