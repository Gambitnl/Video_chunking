# Refactor Candidate #8: Extract Campaign Artifact Counting Logic

## Problem Statement

The `_count_campaign_artifacts()` function in `app.py` (lines 150-173) contains complex nested loops with exception swallowing for counting sessions and narratives. This makes it difficult to test, understand, and maintain. The function also has performance concerns for campaigns with many sessions.

## Current State Analysis

### Location
- **File**: `app.py`
- **Function**: `_count_campaign_artifacts()`
- **Lines**: 150-173
- **Size**: 24 lines

### Current Code Structure

```python
def _count_campaign_artifacts(campaign_id: str) -> Tuple[int, int]:
    """Count processed sessions and narratives for a campaign."""
    if not campaign_id:
        return 0, 0

    session_count = 0
    narrative_count = 0
    output_dir = Config.OUTPUT_DIR
    if not output_dir.exists():
        return 0, 0

    for data_path in output_dir.glob("**/*_data.json"):
        try:
            payload = json.loads(data_path.read_text(encoding="utf-8"))
        except Exception:
            continue  # Silently skip invalid files
        metadata = payload.get("metadata") or {}
        if metadata.get("campaign_id") != campaign_id:
            continue
        session_count += 1
        narratives_dir = data_path.parent / "narratives"
        if narratives_dir.exists():
            narrative_count += len([p for p in narratives_dir.glob("*.md") if p.is_file()])
    return session_count, narrative_count
```

### Issues

1. **Exception Swallowing**: Silent `except Exception` hides real errors
2. **Nested Logic**: Multiple levels of loops and conditionals
3. **Performance**: Reads all JSON files in output directory
4. **Not Testable**: Hard to mock filesystem operations
5. **Single Responsibility**: Counts two different things
6. **No Caching**: Recomputes on every call
7. **No Logging**: Can't debug counting issues
8. **Tightly Coupled**: Directly reads filesystem structure

## Proposed Solution

### Design Overview

Create a `CampaignArtifactCounter` class that:
- Separates session and narrative counting
- Adds proper error handling and logging
- Implements caching for performance
- Makes testing easier with dependency injection
- Provides detailed error reporting

### New Architecture

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from functools import lru_cache
from datetime import datetime, timedelta

from src.config import Config
from src.logger import get_logger


@dataclass
class ArtifactCounts:
    """Counts of campaign artifacts"""
    session_count: int
    narrative_count: int
    sessions: List[str]  # Session IDs
    narratives: List[Path]  # Narrative file paths

    @property
    def total_artifacts(self) -> int:
        """Total number of artifacts"""
        return self.session_count + self.narrative_count


@dataclass
class SessionInfo:
    """Information about a processed session"""
    session_id: str
    campaign_id: str
    data_path: Path
    narratives_dir: Optional[Path] = None
    narrative_count: int = 0

    @classmethod
    def from_data_file(cls, data_path: Path) -> Optional['SessionInfo']:
        """
        Create SessionInfo from a data.json file.

        Args:
            data_path: Path to *_data.json file

        Returns:
            SessionInfo object or None if file is invalid
        """
        try:
            payload = json.loads(data_path.read_text(encoding="utf-8"))
            metadata = payload.get("metadata") or {}

            session_id = metadata.get("session_id", "unknown")
            campaign_id = metadata.get("campaign_id", "")

            # Check for narratives directory
            narratives_dir = data_path.parent / "narratives"
            narrative_count = 0
            if narratives_dir.exists():
                narrative_count = len([
                    p for p in narratives_dir.glob("*.md")
                    if p.is_file()
                ])

            return cls(
                session_id=session_id,
                campaign_id=campaign_id,
                data_path=data_path,
                narratives_dir=narratives_dir if narratives_dir.exists() else None,
                narrative_count=narrative_count,
            )
        except Exception as exc:
            # Return None for invalid files, but log the error
            logger = get_logger("artifact_counter")
            logger.warning(
                "Failed to read session data from %s: %s",
                data_path, exc
            )
            return None


class CampaignArtifactCounter:
    """
    Counts and indexes campaign artifacts (sessions and narratives).

    Provides efficient counting with caching and detailed error reporting.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the counter.

        Args:
            output_dir: Directory containing processed sessions
                       (defaults to Config.OUTPUT_DIR)
        """
        self.output_dir = output_dir or Config.OUTPUT_DIR
        self.logger = get_logger("artifact_counter")
        self._cache: Dict[str, Tuple[ArtifactCounts, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache for 5 minutes

    def count_artifacts(
        self,
        campaign_id: str,
        use_cache: bool = True
    ) -> ArtifactCounts:
        """
        Count all artifacts for a campaign.

        Args:
            campaign_id: Campaign identifier
            use_cache: Whether to use cached results

        Returns:
            ArtifactCounts object with session and narrative counts
        """
        if not campaign_id:
            return ArtifactCounts(
                session_count=0,
                narrative_count=0,
                sessions=[],
                narratives=[]
            )

        # Check cache
        if use_cache and campaign_id in self._cache:
            counts, cached_at = self._cache[campaign_id]
            if datetime.now() - cached_at < self._cache_ttl:
                self.logger.debug(
                    "Using cached counts for campaign %s", campaign_id
                )
                return counts

        # Check if output directory exists
        if not self.output_dir.exists():
            self.logger.warning(
                "Output directory does not exist: %s", self.output_dir
            )
            return ArtifactCounts(
                session_count=0,
                narrative_count=0,
                sessions=[],
                narratives=[]
            )

        # Find all sessions
        sessions = self._find_sessions()

        # Filter for this campaign
        campaign_sessions = [
            s for s in sessions
            if s.campaign_id == campaign_id
        ]

        # Build counts
        session_ids = [s.session_id for s in campaign_sessions]
        session_count = len(campaign_sessions)

        narrative_paths = []
        narrative_count = 0
        for session in campaign_sessions:
            narrative_count += session.narrative_count
            if session.narratives_dir:
                narrative_paths.extend(
                    session.narratives_dir.glob("*.md")
                )

        counts = ArtifactCounts(
            session_count=session_count,
            narrative_count=narrative_count,
            sessions=session_ids,
            narratives=narrative_paths,
        )

        # Cache results
        self._cache[campaign_id] = (counts, datetime.now())

        self.logger.info(
            "Campaign %s: %d sessions, %d narratives",
            campaign_id, session_count, narrative_count
        )

        return counts

    def count_sessions(self, campaign_id: str) -> int:
        """Get just the session count (convenience method)"""
        return self.count_artifacts(campaign_id).session_count

    def count_narratives(self, campaign_id: str) -> int:
        """Get just the narrative count (convenience method)"""
        return self.count_artifacts(campaign_id).narrative_count

    def _find_sessions(self) -> List[SessionInfo]:
        """
        Find all processed sessions in the output directory.

        Returns:
            List of SessionInfo objects
        """
        sessions = []

        # Find all *_data.json files
        data_files = list(self.output_dir.glob("**/*_data.json"))
        self.logger.debug("Found %d data files in output directory", len(data_files))

        for data_path in data_files:
            session_info = SessionInfo.from_data_file(data_path)
            if session_info:
                sessions.append(session_info)

        return sessions

    def clear_cache(self, campaign_id: Optional[str] = None):
        """
        Clear the cache.

        Args:
            campaign_id: If provided, clear only this campaign.
                        If None, clear all cache.
        """
        if campaign_id:
            self._cache.pop(campaign_id, None)
            self.logger.debug("Cleared cache for campaign %s", campaign_id)
        else:
            self._cache.clear()
            self.logger.debug("Cleared all cache")

    def get_all_campaigns(self) -> List[str]:
        """
        Get list of all campaigns that have artifacts.

        Returns:
            List of campaign IDs
        """
        sessions = self._find_sessions()
        campaigns = {s.campaign_id for s in sessions if s.campaign_id}
        return sorted(campaigns)

    def get_campaign_summary(self, campaign_id: str) -> Dict:
        """
        Get detailed summary of campaign artifacts.

        Returns:
            Dictionary with detailed counts and paths
        """
        counts = self.count_artifacts(campaign_id)

        return {
            "campaign_id": campaign_id,
            "session_count": counts.session_count,
            "narrative_count": counts.narrative_count,
            "total_artifacts": counts.total_artifacts,
            "sessions": counts.sessions,
            "narrative_paths": [str(p) for p in counts.narratives],
        }


# Backward compatible function for existing code
def _count_campaign_artifacts(campaign_id: str) -> Tuple[int, int]:
    """
    Count processed sessions and narratives for a campaign.

    This is a compatibility wrapper around CampaignArtifactCounter.

    Args:
        campaign_id: Campaign identifier

    Returns:
        Tuple of (session_count, narrative_count)
    """
    counter = CampaignArtifactCounter()
    counts = counter.count_artifacts(campaign_id)
    return counts.session_count, counts.narrative_count
```

## Implementation Plan

### Phase 1: Create Data Classes (Low Risk)
**Duration**: 1-2 hours

1. **Create `SessionInfo` dataclass**
   - Implement `from_data_file()` classmethod
   - Add error handling
   - Add logging

2. **Create `ArtifactCounts` dataclass**
   - Add computed properties
   - Add validation

3. **Add unit tests**
   ```python
   def test_session_info_from_valid_file():
       """Test creating SessionInfo from valid data file"""
       data_path = create_test_data_file(
           campaign_id="test_campaign",
           session_id="test_session"
       )
       info = SessionInfo.from_data_file(data_path)
       assert info is not None
       assert info.campaign_id == "test_campaign"
       assert info.session_id == "test_session"

   def test_session_info_from_invalid_file():
       """Test handling of invalid data file"""
       data_path = Path("invalid.json")
       data_path.write_text("invalid json")
       info = SessionInfo.from_data_file(data_path)
       assert info is None  # Should handle gracefully

   def test_artifact_counts_total():
       """Test computed total_artifacts property"""
       counts = ArtifactCounts(
           session_count=5,
           narrative_count=10,
           sessions=[],
           narratives=[]
       )
       assert counts.total_artifacts == 15
   ```

### Phase 2: Implement Counter Class (Medium Risk)
**Duration**: 3-4 hours

1. **Create `CampaignArtifactCounter` class**
   - Implement `__init__()`
   - Implement `count_artifacts()`
   - Implement `_find_sessions()`
   - Add caching logic
   - Add logging

2. **Add unit tests**
   ```python
   class TestCampaignArtifactCounter(unittest.TestCase):
       def setUp(self):
           self.temp_dir = create_temp_output_dir()
           self.counter = CampaignArtifactCounter(self.temp_dir)

       def test_count_artifacts_empty_campaign(self):
           """Test counting for campaign with no artifacts"""
           counts = self.counter.count_artifacts("nonexistent")
           assert counts.session_count == 0
           assert counts.narrative_count == 0

       def test_count_artifacts_with_sessions(self):
           """Test counting with multiple sessions"""
           create_test_session(
               self.temp_dir,
               campaign_id="test",
               session_id="session1"
           )
           create_test_session(
               self.temp_dir,
               campaign_id="test",
               session_id="session2"
           )

           counts = self.counter.count_artifacts("test")
           assert counts.session_count == 2

       def test_count_artifacts_with_narratives(self):
           """Test counting narratives"""
           session_dir = create_test_session(
               self.temp_dir,
               campaign_id="test",
               session_id="session1"
           )
           narratives_dir = session_dir / "narratives"
           narratives_dir.mkdir()
           (narratives_dir / "narrative1.md").write_text("# Test")
           (narratives_dir / "narrative2.md").write_text("# Test 2")

           counts = self.counter.count_artifacts("test")
           assert counts.session_count == 1
           assert counts.narrative_count == 2

       def test_caching(self):
           """Test that results are cached"""
           create_test_session(self.temp_dir, "test", "session1")

           # First call
           counts1 = self.counter.count_artifacts("test")

           # Add another session (shouldn't be counted due to cache)
           create_test_session(self.temp_dir, "test", "session2")

           # Second call (should use cache)
           counts2 = self.counter.count_artifacts("test", use_cache=True)
           assert counts2.session_count == counts1.session_count

           # Third call (bypass cache)
           counts3 = self.counter.count_artifacts("test", use_cache=False)
           assert counts3.session_count == 2

       def test_clear_cache(self):
           """Test cache clearing"""
           self.counter.count_artifacts("test")
           assert "test" in self.counter._cache

           self.counter.clear_cache("test")
           assert "test" not in self.counter._cache

       def test_get_all_campaigns(self):
           """Test getting all campaigns"""
           create_test_session(self.temp_dir, "campaign1", "s1")
           create_test_session(self.temp_dir, "campaign2", "s2")
           create_test_session(self.temp_dir, "campaign1", "s3")

           campaigns = self.counter.get_all_campaigns()
           assert set(campaigns) == {"campaign1", "campaign2"}

       def test_get_campaign_summary(self):
           """Test detailed summary"""
           create_test_session(self.temp_dir, "test", "session1")

           summary = self.counter.get_campaign_summary("test")
           assert summary["campaign_id"] == "test"
           assert summary["session_count"] == 1
           assert "sessions" in summary
           assert "narrative_paths" in summary
   ```

### Phase 3: Add Convenience Methods (Low Risk)
**Duration**: 1 hour

1. **Add helper methods**
   - `count_sessions()`
   - `count_narratives()`
   - `get_all_campaigns()`
   - `get_campaign_summary()`

2. **Add tests for helpers**

### Phase 4: Update app.py (Low Risk)
**Duration**: 1-2 hours

1. **Replace function calls**
   ```python
   # OLD
   session_count, narrative_count = _count_campaign_artifacts(campaign_id)

   # NEW
   counter = CampaignArtifactCounter()
   counts = counter.count_artifacts(campaign_id)
   session_count = counts.session_count
   narrative_count = counts.narrative_count

   # Or use convenience methods
   session_count = counter.count_sessions(campaign_id)
   narrative_count = counter.count_narratives(campaign_id)

   # Or keep backward compatible wrapper
   session_count, narrative_count = _count_campaign_artifacts(campaign_id)
   ```

2. **Consider creating global counter instance**
   ```python
   # At module level
   artifact_counter = CampaignArtifactCounter()

   # In functions
   counts = artifact_counter.count_artifacts(campaign_id)
   ```

### Phase 5: Testing (High Priority)
**Duration**: 2-3 hours

1. **Integration tests**
   ```python
   @pytest.mark.integration
   def test_counter_with_real_sessions():
       """Test counter with actual processed sessions"""
       # Process a real session
       # Count artifacts
       # Verify counts match expected
   ```

2. **Performance tests**
   ```python
   def test_counter_performance():
       """Test performance with many sessions"""
       # Create 100+ test sessions
       # Time the counting operation
       # Should complete in < 1 second
   ```

3. **Error handling tests**
   ```python
   def test_counter_handles_corrupt_files():
       """Test graceful handling of corrupt data files"""
       # Create corrupt JSON file
       # Verify counting continues
       # Verify error is logged
   ```

### Phase 6: Documentation (Low Risk)
**Duration**: 1 hour

1. **Add docstrings**
2. **Update architecture docs**
3. **Add usage examples**

## Testing Strategy

### Unit Tests

All unit tests listed in Phase 1 and Phase 2 implementation plan.

### Integration Tests

```python
@pytest.mark.integration
class TestArtifactCounterIntegration(unittest.TestCase):
    """Integration tests with real filesystem"""

    def test_count_real_campaign(self):
        """Test counting a real processed campaign"""
        counter = CampaignArtifactCounter()
        counts = counter.count_artifacts("real_campaign_id")
        # Verify against known values

    def test_count_after_processing_session(self):
        """Test counting after processing a new session"""
        # Count before
        before = counter.count_artifacts("test")

        # Process session
        processor.process(...)

        # Count after (bypass cache)
        after = counter.count_artifacts("test", use_cache=False)

        # Verify increase
        assert after.session_count == before.session_count + 1
```

### Performance Tests

```python
def test_counter_performance_many_sessions():
    """Test performance with 1000+ sessions"""
    import time

    # Create 1000 test sessions
    for i in range(1000):
        create_test_session(output_dir, "test", f"session_{i}")

    counter = CampaignArtifactCounter(output_dir)

    start = time.time()
    counts = counter.count_artifacts("test", use_cache=False)
    elapsed = time.time() - start

    assert counts.session_count == 1000
    assert elapsed < 2.0  # Should complete in under 2 seconds
```

## Risks and Mitigation

### Risk 1: Cache Invalidation Issues
**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Short TTL (5 minutes)
- Provide `use_cache=False` option
- Clear cache after processing sessions
- Document caching behavior

### Risk 2: Performance Regression
**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Add caching (actually improves performance)
- Benchmark before/after
- Optimize glob patterns if needed
- Consider indexing for large datasets

### Risk 3: Breaking Existing Code
**Likelihood**: Low
**Impact**: Low
**Mitigation**:
- Keep backward compatible wrapper function
- Gradual migration
- Comprehensive tests
- No API changes for callers

## Expected Benefits

### Immediate Benefits
1. **Better Error Handling**: Logs errors instead of swallowing
2. **Testability**: Easy to test with temp directories
3. **Performance**: Caching improves repeated calls
4. **Clarity**: Clear separation of concerns
5. **Debugging**: Detailed logging of counting process

### Long-term Benefits
1. **Extensibility**: Easy to add new artifact types
2. **Maintainability**: Clear class structure
3. **Reusability**: Can use counter in multiple places
4. **Features**: Can build UI features on detailed counts
5. **Monitoring**: Can track artifact growth over time

### Metrics
- **Test Coverage**: Increase from ~0% to >90% for counting logic
- **Performance**: 50% faster with caching
- **Error Visibility**: 100% of errors logged (vs 0% currently)
- **Code Clarity**: Reduce cyclomatic complexity from ~8 to ~3

## Success Criteria

1. ✅ `CampaignArtifactCounter` class created
2. ✅ All data classes created and tested
3. ✅ Unit tests for all methods (>90% coverage)
4. ✅ Integration tests pass
5. ✅ Performance tests show improvement
6. ✅ Backward compatible wrapper works
7. ✅ All error cases handled and logged
8. ✅ Documentation updated
9. ✅ Code review approved

## Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Create Data Classes | 1-2 hours | None |
| Phase 2: Implement Counter | 3-4 hours | Phase 1 |
| Phase 3: Add Convenience Methods | 1 hour | Phase 2 |
| Phase 4: Update app.py | 1-2 hours | Phase 2 |
| Phase 5: Testing | 2-3 hours | Phase 4 |
| Phase 6: Documentation | 1 hour | Phase 5 |
| **Total** | **9-13 hours** | |

## References

- Current implementation: `app.py:150-173`
- Related function: `_status_tracker_summary()` (app.py:176-200)
- Config: `src/config.py`
- Design pattern: Repository Pattern (for artifact access)
