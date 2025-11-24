import unittest
import threading
import time
from src.lock_manager import LockManager, LockTimeoutError

class TestLockManager(unittest.TestCase):
    def test_acquire_release(self):
        # Test basic acquire/release
        with LockManager.lock("test", "resource1"):
            # In RLock, same thread CAN acquire, so is_locked returns False (not locked for THIS thread)
            # To verify it IS locked for others, we need a separate thread

            result_holder = {"is_locked": False}
            def check_lock():
                result_holder["is_locked"] = LockManager.is_locked("test", "resource1")

            t = threading.Thread(target=check_lock)
            t.start()
            t.join()

            self.assertTrue(result_holder["is_locked"], "Resource should be locked for other threads")

        # Should be released now
        self.assertFalse(LockManager.is_locked("test", "resource1"))

    def test_reentrant(self):
        with LockManager.lock("test", "resource2"):
            with LockManager.lock("test", "resource2"):
                pass
        # Should not block

    def test_timeout(self):
        # Acquire lock in a separate thread and hold it
        def hold_lock():
            with LockManager.lock("test", "resource3"):
                time.sleep(2)

        t = threading.Thread(target=hold_lock)
        t.start()

        # Ensure thread has acquired lock
        time.sleep(0.5)

        # Try to acquire with short timeout
        with self.assertRaises(LockTimeoutError):
            with LockManager.lock("test", "resource3", timeout=0.1):
                pass

        t.join()

if __name__ == "__main__":
    unittest.main()
