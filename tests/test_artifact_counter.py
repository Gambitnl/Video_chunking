"""Tests for CampaignArtifactCounter."""

import json
import pytest
import time
from pathlib import Path
from datetime import datetime

try:
    from freezegun import freeze_time
    FREEZEGUN_AVAILABLE = True
except ImportError:
    FREEZEGUN_AVAILABLE = False

from src.artifact_counter import CampaignArtifactCounter, ArtifactCounts


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory structure with test data."""
    output = tmp_path / "output"
    output.mkdir()

    # Create session 1 for campaign_123
    session1 = output / "session_001"
    session1.mkdir()
    data1 = session1 / "session_001_data.json"
    data1.write_text(json.dumps({
        "metadata": {
            "campaign_id": "campaign_123",
            "session_id": "session_001"
        }
    }))

    # Create narratives for session 1
    narratives1 = session1 / "narratives"
    narratives1.mkdir()
    (narratives1 / "narrative_01.md").write_text("# Narrative 1")
    (narratives1 / "narrative_02.md").write_text("# Narrative 2")

    # Create session 2 for campaign_123
    session2 = output / "session_002"
    session2.mkdir()
    data2 = session2 / "session_002_data.json"
    data2.write_text(json.dumps({
        "metadata": {
            "campaign_id": "campaign_123",
            "session_id": "session_002"
        }
    }))

    # Create narratives for session 2
    narratives2 = session2 / "narratives"
    narratives2.mkdir()
    (narratives2 / "narrative_01.md").write_text("# Narrative 1")

    # Create session 3 for different campaign
    session3 = output / "session_003"
    session3.mkdir()
    data3 = session3 / "session_003_data.json"
    data3.write_text(json.dumps({
        "metadata": {
            "campaign_id": "campaign_456",
            "session_id": "session_003"
        }
    }))

    # Create session 4 with no campaign_id
    session4 = output / "session_004"
    session4.mkdir()
    data4 = session4 / "session_004_data.json"
    data4.write_text(json.dumps({
        "metadata": {
            "session_id": "session_004"
        }
    }))

    return output


class TestArtifactCounts:
    """Test the ArtifactCounts dataclass."""

    def test_default_values(self):
        """Test default initialization."""
        counts = ArtifactCounts()
        assert counts.sessions == 0
        assert counts.narratives == 0
        assert counts.errors == []
        assert counts.last_updated is None

    def test_to_dict(self):
        """Test conversion to dictionary."""
        counts = ArtifactCounts(sessions=5, narratives=10)
        d = counts.to_dict()

        assert d["sessions"] == 5
        assert d["narratives"] == 10
        assert d["error_count"] == 0
        assert "last_updated" in d

    def test_to_dict_with_timestamp(self):
        """Test dictionary conversion with timestamp."""
        now = datetime.now()
        counts = ArtifactCounts(sessions=3, last_updated=now)
        d = counts.to_dict()

        assert d["sessions"] == 3
        assert d["last_updated"] == now.isoformat()

    def test_to_tuple(self):
        """Test conversion to tuple for backward compatibility."""
        counts = ArtifactCounts(sessions=7, narratives=14)
        tup = counts.to_tuple()

        assert tup == (7, 14)
        assert isinstance(tup, tuple)


class TestCampaignArtifactCounter:
    """Test the CampaignArtifactCounter class."""

    @pytest.fixture
    def counter(self, temp_output_dir):
        """Create a counter instance with test data."""
        return CampaignArtifactCounter(
            output_dir=temp_output_dir,
            cache_ttl_seconds=60
        )

    def test_initialization(self, temp_output_dir):
        """Test counter initialization."""
        counter = CampaignArtifactCounter(temp_output_dir, cache_ttl_seconds=120)

        assert counter.output_dir == temp_output_dir
        assert counter.cache_ttl.total_seconds() == 120
        assert counter._cache == {}

    def test_count_artifacts_basic(self, counter):
        """Test basic artifact counting."""
        counts = counter.count_artifacts("campaign_123")

        assert counts.sessions == 2
        assert counts.narratives == 3  # 2 from session_001, 1 from session_002
        assert len(counts.errors) == 0
        assert counts.last_updated is not None

    def test_count_artifacts_different_campaign(self, counter):
        """Test counting for a different campaign."""
        counts = counter.count_artifacts("campaign_456")

        assert counts.sessions == 1
        assert counts.narratives == 0  # No narratives dir for session_003
        assert len(counts.errors) == 0

    def test_count_artifacts_empty_campaign_id(self, counter):
        """Test counting with empty campaign ID."""
        counts = counter.count_artifacts("")

        assert counts.sessions == 0
        assert counts.narratives == 0

    def test_count_artifacts_nonexistent_campaign(self, counter):
        """Test counting for non-existent campaign."""
        counts = counter.count_artifacts("campaign_999")

        assert counts.sessions == 0
        assert counts.narratives == 0
        assert len(counts.errors) == 0

    def test_caching(self, counter, temp_output_dir):
        """Test that results are cached."""
        # First call
        counts1 = counter.count_artifacts("campaign_123")
        assert counts1.sessions == 2

        # Add a new session for the same campaign
        new_session = temp_output_dir / "session_999"
        new_session.mkdir()
        data_new = new_session / "session_999_data.json"
        data_new.write_text(json.dumps({
            "metadata": {
                "campaign_id": "campaign_123",
                "session_id": "session_999"
            }
        }))

        # Second call should return cached result
        counts2 = counter.count_artifacts("campaign_123")
        assert counts2.sessions == 2  # Still 2, not 3

        # Force refresh should see new session
        counts3 = counter.count_artifacts("campaign_123", force_refresh=True)
        assert counts3.sessions == 3

    @pytest.mark.skipif(not FREEZEGUN_AVAILABLE, reason="freezegun not installed")
    def test_cache_expiration_with_freezegun(self, temp_output_dir):
        """Test that cache expires after TTL using freezegun for deterministic timing."""
        counter = CampaignArtifactCounter(temp_output_dir, cache_ttl_seconds=60)

        with freeze_time("2023-01-01 12:00:00") as freezer:
            # First count
            counts1 = counter.count_artifacts("campaign_123")
            assert counts1.sessions == 2

            # Add new session
            new_session = temp_output_dir / "session_999"
            new_session.mkdir()
            data_new = new_session / "session_999_data.json"
            data_new.write_text(json.dumps({
                "metadata": {
                    "campaign_id": "campaign_123",
                    "session_id": "session_999"
                }
            }))

            # Second call within TTL should be cached
            freezer.tick(30)  # 30 seconds elapsed
            counts2 = counter.count_artifacts("campaign_123")
            assert counts2.sessions == 2, "Should use cache within TTL"

            # Third call after TTL should recount
            freezer.tick(35)  # Total 65 seconds elapsed, > 60s TTL
            counts3 = counter.count_artifacts("campaign_123")
            assert counts3.sessions == 3, "Should recount after TTL expired"

    def test_cache_expiration_with_sleep(self, temp_output_dir):
        """Test that cache expires after TTL (fallback test using sleep)."""
        counter = CampaignArtifactCounter(temp_output_dir, cache_ttl_seconds=1)

        # First count
        counts1 = counter.count_artifacts("campaign_123")
        assert counts1.sessions == 2

        # Wait for cache to expire
        time.sleep(1.1)

        # Add new session
        new_session = temp_output_dir / "session_999"
        new_session.mkdir()
        data_new = new_session / "session_999_data.json"
        data_new.write_text(json.dumps({
            "metadata": {
                "campaign_id": "campaign_123",
                "session_id": "session_999"
            }
        }))

        # Should recount and see new session
        counts2 = counter.count_artifacts("campaign_123")
        assert counts2.sessions == 3

    def test_clear_cache_specific(self, counter, temp_output_dir):
        """Test clearing cache for specific campaign."""
        counts1 = counter.count_artifacts("campaign_123")
        assert counts1.sessions == 2

        counter.clear_cache("campaign_123")

        # Add new session
        new_session = temp_output_dir / "session_999"
        new_session.mkdir()
        data_new = new_session / "session_999_data.json"
        data_new.write_text(json.dumps({
            "metadata": {
                "campaign_id": "campaign_123",
                "session_id": "session_999"
            }
        }))

        # Should recount
        counts2 = counter.count_artifacts("campaign_123")
        assert counts2.sessions == 3

    def test_clear_cache_all(self, counter):
        """Test clearing all cache."""
        counter.count_artifacts("campaign_123")
        counter.count_artifacts("campaign_456")

        assert len(counter._cache) == 2

        counter.clear_cache()

        stats = counter.get_cache_stats()
        assert stats["cached_campaigns"] == 0

    def test_error_handling_invalid_json(self, counter, temp_output_dir):
        """Test error handling when JSON is invalid."""
        # Create session with invalid JSON
        bad_session = temp_output_dir / "session_bad"
        bad_session.mkdir()
        bad_data = bad_session / "session_bad_data.json"
        bad_data.write_text("{ invalid json }")

        counts = counter.count_artifacts("campaign_123")

        # Should still complete but with errors
        assert len(counts.errors) > 0
        assert any("Invalid JSON" in err for err in counts.errors)

    def test_error_handling_missing_output_dir(self, tmp_path):
        """Test error handling when output directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"
        counter = CampaignArtifactCounter(nonexistent)

        counts = counter.count_artifacts("campaign_123")

        assert counts.sessions == 0
        assert len(counts.errors) > 0
        assert any("not found" in err for err in counts.errors)

    def test_error_handling_output_dir_is_file(self, tmp_path):
        """Test error handling when output path is a file, not directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")

        counter = CampaignArtifactCounter(file_path)
        counts = counter.count_artifacts("campaign_123")

        assert counts.sessions == 0
        assert len(counts.errors) > 0
        assert any("not a directory" in err for err in counts.errors)

    def test_session_without_metadata(self, counter, temp_output_dir):
        """Test handling session data without metadata."""
        no_meta_session = temp_output_dir / "session_no_meta"
        no_meta_session.mkdir()
        data = no_meta_session / "session_no_meta_data.json"
        data.write_text(json.dumps({
            "some_field": "some_value"
        }))

        counts = counter.count_artifacts("campaign_123")

        # Should not crash, just not count this session
        assert counts.sessions == 2  # Still only the valid ones

    def test_get_cache_stats(self, counter):
        """Test cache statistics."""
        counter.count_artifacts("campaign_123")
        counter.count_artifacts("campaign_456")

        stats = counter.get_cache_stats()

        assert stats["cached_campaigns"] == 2
        assert stats["ttl_seconds"] == 60
        assert "campaign_123" in stats["campaigns"]
        assert "campaign_456" in stats["campaigns"]

    def test_nested_session_directories(self, tmp_path):
        """Test handling of nested directory structures."""
        output = tmp_path / "output_nested"
        output.mkdir()

        # Create nested structure
        nested = output / "year_2024" / "month_01"
        nested.mkdir(parents=True)
        data = nested / "session_nested_data.json"
        data.write_text(json.dumps({
            "metadata": {
                "campaign_id": "campaign_123",
                "session_id": "session_nested"
            }
        }))

        counter = CampaignArtifactCounter(output, cache_ttl_seconds=60)
        counts = counter.count_artifacts("campaign_123")

        # Should find nested sessions
        assert counts.sessions == 1

    def test_backward_compatibility_tuple(self, counter):
        """Test backward compatibility with tuple return."""
        counts = counter.count_artifacts("campaign_123")
        session_count, narrative_count = counts.to_tuple()

        assert session_count == 2
        assert narrative_count == 3

    def test_cache_handles_multiple_campaigns(self, counter):
        """Test that cache correctly handles multiple different campaigns."""
        counts1 = counter.count_artifacts("campaign_123")
        counts2 = counter.count_artifacts("campaign_456")
        counts3 = counter.count_artifacts("campaign_123")  # Should be cached

        assert counts1.sessions == 2
        assert counts2.sessions == 1
        assert counts3.sessions == 2  # From cache
        # Note: Cache returns same object for performance, which is acceptable
        # since ArtifactCounts is immutable after creation

    def test_thread_safety(self, counter):
        """Test that counter is thread-safe with concurrent access."""
        import threading
        results = []
        errors = []

        def count_artifacts(campaign_id):
            try:
                counts = counter.count_artifacts(campaign_id)
                results.append((campaign_id, counts.sessions, counts.narratives))
            except Exception as e:
                errors.append(e)

        # Create multiple threads that access the counter concurrently
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=count_artifacts, args=("campaign_123",)))
            threads.append(threading.Thread(target=count_artifacts, args=("campaign_456",)))

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all results are consistent
        campaign_123_results = [r for r in results if r[0] == "campaign_123"]
        campaign_456_results = [r for r in results if r[0] == "campaign_456"]

        # All results for campaign_123 should be identical
        assert all(r == (2, 3) for _, s, n in campaign_123_results for r in [(s, n)])

        # All results for campaign_456 should be identical
        assert all(r == (1, 0) for _, s, n in campaign_456_results for r in [(s, n)])
