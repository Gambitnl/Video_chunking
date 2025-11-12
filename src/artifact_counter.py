"""
Campaign artifact counter with caching and error handling.

This module provides functionality to count various artifacts for a campaign,
including processed sessions and narrative files, with proper error handling
and result caching.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ArtifactCounts:
    """Container for campaign artifact counts."""

    sessions: int = 0
    narratives: int = 0
    errors: List[str] = field(default_factory=list)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "sessions": self.sessions,
            "narratives": self.narratives,
            "error_count": len(self.errors),
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }

    def to_tuple(self) -> Tuple[int, int]:
        """Convert to tuple (sessions, narratives) for backward compatibility."""
        return (self.sessions, self.narratives)


class CampaignArtifactCounter:
    """
    Counts artifacts for a campaign with caching and error handling.

    Features:
    - Result caching with configurable TTL
    - Detailed error reporting and logging
    - No silent exception swallowing
    - Full observability

    Usage:
        counter = CampaignArtifactCounter(output_dir, cache_ttl_seconds=300)
        counts = counter.count_artifacts("campaign_123")
        print(f"Found {counts.sessions} sessions, {counts.narratives} narratives")
    """

    def __init__(
        self,
        output_dir: Path,
        cache_ttl_seconds: int = 300,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the artifact counter.

        Args:
            output_dir: Path to the output directory containing session data
            cache_ttl_seconds: How long to cache results (default: 5 minutes)
            logger: Optional logger instance
        """
        self.output_dir = Path(output_dir)
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.logger = logger or logging.getLogger(__name__)
        self._cache: Dict[str, Tuple[ArtifactCounts, datetime]] = {}
        self._lock = threading.Lock()

    def count_artifacts(
        self,
        campaign_id: str,
        force_refresh: bool = False
    ) -> ArtifactCounts:
        """
        Count all artifacts for a campaign.

        Args:
            campaign_id: Campaign identifier to count artifacts for
            force_refresh: If True, bypass cache and recount

        Returns:
            ArtifactCounts object with counts and metadata
        """
        if not campaign_id:
            self.logger.warning("count_artifacts called with empty campaign_id")
            return ArtifactCounts(last_updated=datetime.now())

        # Check cache (first check, no lock for fast path)
        if not force_refresh and campaign_id in self._cache:
            counts, cached_at = self._cache[campaign_id]
            age = datetime.now() - cached_at
            if age < self.cache_ttl:
                self.logger.debug(
                    f"Using cached counts for campaign '{campaign_id}' "
                    f"(age: {age.total_seconds():.1f}s)"
                )
                return counts

        # Use double-checked locking to prevent cache stampede
        with self._lock:
            # Double-check cache inside lock
            if not force_refresh and campaign_id in self._cache:
                counts, cached_at = self._cache[campaign_id]
                age = datetime.now() - cached_at
                if age < self.cache_ttl:
                    self.logger.debug(
                        f"Using cached counts for campaign '{campaign_id}' "
                        f"(age: {age.total_seconds():.1f}s) [lock-recheck]"
                    )
                    return counts

            # Perform count
            self.logger.info(f"Counting artifacts for campaign: {campaign_id}")
            start_time = time.time()

            counts = self._count_all_artifacts(campaign_id)
            counts.last_updated = datetime.now()

            elapsed = time.time() - start_time
            self.logger.info(
                f"Counted {counts.sessions} sessions, {counts.narratives} narratives "
                f"for campaign '{campaign_id}' in {elapsed:.2f}s"
            )

            if counts.errors:
                self.logger.warning(
                    f"Encountered {len(counts.errors)} errors during counting "
                    f"for campaign '{campaign_id}'"
                )
                for error in counts.errors:
                    self.logger.debug(f"  - {error}")

            # Update cache
            self._cache[campaign_id] = (counts, counts.last_updated)

            return counts

    def _count_all_artifacts(self, campaign_id: str) -> ArtifactCounts:
        """Internal method to count all artifact types for a campaign."""
        counts = ArtifactCounts()

        # Check if output directory exists
        if not self.output_dir.exists():
            error_msg = f"Output directory not found: {self.output_dir}"
            counts.errors.append(error_msg)
            self.logger.warning(error_msg)
            return counts

        if not self.output_dir.is_dir():
            error_msg = f"Output path is not a directory: {self.output_dir}"
            counts.errors.append(error_msg)
            self.logger.error(error_msg)
            return counts

        # Find all *_data.json files
        try:
            data_files = list(self.output_dir.glob("**/*_data.json"))
        except Exception as e:
            error_msg = f"Failed to glob data files in {self.output_dir}: {e}"
            counts.errors.append(error_msg)
            self.logger.error(error_msg)
            return counts

        # Process each data file
        for data_path in data_files:
            try:
                self._count_session_artifacts(data_path, campaign_id, counts)
            except Exception as e:
                error_msg = f"Error processing {data_path.name}: {e}"
                counts.errors.append(error_msg)
                self.logger.error(error_msg, exc_info=True)

        return counts

    def _count_session_artifacts(
        self,
        data_path: Path,
        campaign_id: str,
        counts: ArtifactCounts
    ) -> None:
        """Count artifacts from a single session data file."""
        try:
            # Read and parse the JSON file
            try:
                payload = json.loads(data_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in {data_path.name}: {e}"
                counts.errors.append(error_msg)
                self.logger.warning(error_msg)
                return
            except UnicodeDecodeError as e:
                error_msg = f"Encoding error in {data_path.name}: {e}"
                counts.errors.append(error_msg)
                self.logger.warning(error_msg)
                return
            except PermissionError as e:
                error_msg = f"Permission denied reading {data_path.name}: {e}"
                counts.errors.append(error_msg)
                self.logger.warning(error_msg)
                return

            # Check if this session belongs to the target campaign
            metadata = payload.get("metadata") or {}
            session_campaign_id = metadata.get("campaign_id")

            if session_campaign_id != campaign_id:
                # This session belongs to a different campaign
                return

            # Count this session
            counts.sessions += 1

            # Count narratives in the session's narratives directory
            narratives_dir = data_path.parent / "narratives"
            if narratives_dir.exists() and narratives_dir.is_dir():
                try:
                    narrative_files = [
                        p for p in narratives_dir.glob("*.md")
                        if p.is_file()
                    ]
                    counts.narratives += len(narrative_files)
                except Exception as e:
                    error_msg = f"Error counting narratives in {narratives_dir.name}: {e}"
                    counts.errors.append(error_msg)
                    self.logger.warning(error_msg)

        except Exception as e:
            # Catch any unexpected errors
            error_msg = f"Unexpected error processing {data_path.name}: {e}"
            counts.errors.append(error_msg)
            self.logger.error(error_msg, exc_info=True)

    def clear_cache(self, campaign_id: Optional[str] = None) -> None:
        """
        Clear the cache.

        Args:
            campaign_id: If specified, clear only this campaign. Otherwise, clear all.
        """
        with self._lock:
            if campaign_id:
                if campaign_id in self._cache:
                    del self._cache[campaign_id]
                    self.logger.debug(f"Cleared cache for campaign: {campaign_id}")
            else:
                self._cache.clear()
                self.logger.debug("Cleared all cache")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            return {
                "cached_campaigns": len(self._cache),
                "ttl_seconds": self.cache_ttl.total_seconds(),
                "campaigns": list(self._cache.keys())
            }
