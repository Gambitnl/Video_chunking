"""Tests for file locking utilities to prevent concurrent write conflicts."""

import pytest
import threading
import time
import json
from pathlib import Path
from src.file_lock import get_file_lock, clear_lock_registry, FileLockContext


class TestFileLock:
    """Test basic file locking functionality."""

    def test_get_file_lock_creates_lock(self):
        """Test that get_file_lock creates a lock for a file."""
        clear_lock_registry()
        lock = get_file_lock("test_file.json")
        assert lock is not None
        assert isinstance(lock, threading.Lock)

    def test_get_file_lock_returns_same_lock_for_same_file(self):
        """Test that the same file always gets the same lock instance."""
        clear_lock_registry()
        lock1 = get_file_lock("test_file.json")
        lock2 = get_file_lock("test_file.json")
        assert lock1 is lock2

    def test_get_file_lock_different_locks_for_different_files(self):
        """Test that different files get different lock instances."""
        clear_lock_registry()
        lock1 = get_file_lock("file1.json")
        lock2 = get_file_lock("file2.json")
        assert lock1 is not lock2

    def test_get_file_lock_normalizes_paths(self):
        """Test that path normalization works correctly."""
        clear_lock_registry()
        lock1 = get_file_lock("./models/campaigns.json")
        lock2 = get_file_lock("models/campaigns.json")
        # Should be the same lock after path normalization
        assert lock1 is lock2

    def test_clear_lock_registry(self):
        """Test that clear_lock_registry removes all locks."""
        clear_lock_registry()
        lock1 = get_file_lock("test1.json")
        lock2 = get_file_lock("test2.json")

        clear_lock_registry()

        # After clearing, should get new lock instances
        lock3 = get_file_lock("test1.json")
        lock4 = get_file_lock("test2.json")

        assert lock1 is not lock3
        assert lock2 is not lock4


class TestFileLockContext:
    """Test FileLockContext context manager."""

    def test_context_manager_acquires_and_releases_lock(self, tmp_path):
        """Test that FileLockContext properly acquires and releases locks."""
        clear_lock_registry()
        test_file = tmp_path / "test.json"

        with FileLockContext(test_file):
            # Lock should be acquired
            lock = get_file_lock(test_file)
            # Try to acquire it again (should fail immediately)
            acquired = lock.acquire(blocking=False)
            assert not acquired  # Lock is held by context manager

        # After exiting context, lock should be released
        acquired = lock.acquire(blocking=False)
        assert acquired  # Lock is now available
        lock.release()

    def test_context_manager_timeout(self, tmp_path):
        """Test that FileLockContext raises error on timeout."""
        clear_lock_registry()
        test_file = tmp_path / "test.json"

        lock = get_file_lock(test_file)
        lock.acquire()  # Manually acquire the lock

        try:
            # Try to acquire with short timeout
            with pytest.raises(RuntimeError, match="Failed to acquire lock"):
                with FileLockContext(test_file, timeout=0.1):
                    pass
        finally:
            lock.release()

    def test_context_manager_preserves_exceptions(self, tmp_path):
        """Test that exceptions inside context are not suppressed."""
        clear_lock_registry()
        test_file = tmp_path / "test.json"

        with pytest.raises(ValueError, match="test error"):
            with FileLockContext(test_file):
                raise ValueError("test error")


class TestConcurrentWrites:
    """Test concurrent write scenarios to ensure data integrity."""

    def test_concurrent_writes_to_same_file(self, tmp_path):
        """Test that concurrent writes to the same file are serialized."""
        clear_lock_registry()
        test_file = tmp_path / "concurrent.json"
        test_file.write_text("{}")

        results = []
        errors = []

        def write_data(thread_id: int, value: str):
            """Simulate writing to a JSON file."""
            try:
                lock = get_file_lock(test_file)
                with lock:
                    # Read current data
                    with open(test_file, 'r') as f:
                        data = json.load(f)

                    # Simulate some processing time
                    time.sleep(0.01)

                    # Update data
                    data[f"thread_{thread_id}"] = value

                    # Write back
                    with open(test_file, 'w') as f:
                        json.dump(data, f)

                    results.append((thread_id, value))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Start 10 threads writing concurrently
        threads = []
        for i in range(10):
            t = threading.Thread(target=write_data, args=(i, f"value_{i}"))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # No errors should have occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # All writes should have succeeded
        assert len(results) == 10

        # Final file should contain all 10 entries
        with open(test_file, 'r') as f:
            final_data = json.load(f)

        assert len(final_data) == 10
        for i in range(10):
            assert f"thread_{i}" in final_data
            assert final_data[f"thread_{i}"] == f"value_{i}"

    def test_concurrent_writes_to_different_files(self, tmp_path):
        """Test that concurrent writes to different files don't block each other."""
        clear_lock_registry()

        def write_to_file(file_path: Path, content: dict):
            """Write content to a file with locking."""
            lock = get_file_lock(file_path)
            with lock:
                time.sleep(0.05)  # Simulate work
                with open(file_path, 'w') as f:
                    json.dump(content, f)

        # Create multiple files
        files = [tmp_path / f"file_{i}.json" for i in range(5)]
        threads = []
        start_time = time.time()

        for i, file_path in enumerate(files):
            content = {"id": i, "data": f"content_{i}"}
            t = threading.Thread(target=write_to_file, args=(file_path, content))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        end_time = time.time()
        elapsed = end_time - start_time

        # With proper concurrent execution, should take ~0.05s (not 5 * 0.05s)
        # Allow some overhead, but should be much less than sequential
        assert elapsed < 0.3, f"Concurrent writes took too long: {elapsed}s"

        # Verify all files were written correctly
        for i, file_path in enumerate(files):
            with open(file_path, 'r') as f:
                data = json.load(f)
            assert data["id"] == i
            assert data["data"] == f"content_{i}"


class TestIntegrationWithManagers:
    """Test file locking integration with actual manager classes."""

    def test_concurrent_campaign_updates(self, tmp_path):
        """Test concurrent updates to CampaignManager."""
        from src.party_config import CampaignManager, Campaign, CampaignSettings

        clear_lock_registry()
        config_file = tmp_path / "campaigns.json"
        config_file.write_text("{}")

        manager = CampaignManager(config_file=config_file)
        errors = []

        def update_campaign(campaign_id: str, name: str):
            """Update a campaign."""
            try:
                campaign = Campaign(
                    name=name,
                    party_id="default",
                    settings=CampaignSettings()
                )
                manager.add_campaign(campaign_id, campaign)
            except Exception as e:
                errors.append((campaign_id, str(e)))

        # Concurrently create 20 campaigns
        threads = []
        for i in range(20):
            t = threading.Thread(
                target=update_campaign,
                args=(f"campaign_{i:03d}", f"Campaign {i}")
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0, f"Errors: {errors}"

        # Reload manager from file to verify persistence
        manager2 = CampaignManager(config_file=config_file)
        assert len(manager2.campaigns) == 20

        # All campaigns should be present
        for i in range(20):
            campaign_id = f"campaign_{i:03d}"
            assert campaign_id in manager2.campaigns
            assert manager2.campaigns[campaign_id].name == f"Campaign {i}"

    def test_concurrent_party_updates(self, tmp_path):
        """Test concurrent updates to PartyConfigManager."""
        from src.party_config import PartyConfigManager, Party, Character

        clear_lock_registry()
        config_file = tmp_path / "parties.json"
        config_file.write_text("{}")

        manager = PartyConfigManager(config_file=config_file)
        errors = []

        def update_party(party_id: str, party_name: str):
            """Update a party."""
            try:
                party = Party(
                    party_name=party_name,
                    dm_name="Test DM",
                    characters=[
                        Character(
                            name=f"Character {party_id}",
                            player="Player",
                            race="Human",
                            class_name="Fighter"
                        )
                    ]
                )
                manager.add_party(party_id, party)
            except Exception as e:
                errors.append((party_id, str(e)))

        # Concurrently create 15 parties
        threads = []
        for i in range(15):
            t = threading.Thread(
                target=update_party,
                args=(f"party_{i}", f"Party {i}")
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0, f"Errors: {errors}"

        # Reload and verify
        manager2 = PartyConfigManager(config_file=config_file)
        # Will have 15 custom parties + 1 default party
        assert len(manager2.parties) == 16  # 15 + default
