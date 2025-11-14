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
    session_ids: List[str] = field(default_factory=list)
    narrative_paths: List[Path] = field(default_factory=list)

    @property
    def session_count(self) -> int:
        """Alias for sessions (backward compatibility)."""
        return self.sessions

    @property
    def narrative_count(self) -> int:
        """Alias for narratives (backward compatibility)."""
        return self.narratives

    @property
    def total_artifacts(self) -> int:
        """Total number of artifacts (sessions + narratives)."""
        return self.sessions + self.narratives

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "sessions": self.sessions,
            "narratives": self.narratives,
            "session_ids": self.session_ids,
            "narrative_paths": [str(p) for p in self.narrative_paths],
            "total_artifacts": self.total_artifacts,
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
        self._campaigns_cache: Optional[Tuple[List[str], datetime]] = None
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

            # Track session ID
            session_id = metadata.get("session_id", "unknown")
            counts.session_ids.append(session_id)

            # Count narratives in the session's narratives directory
            narratives_dir = data_path.parent / "narratives"
            if narratives_dir.exists() and narratives_dir.is_dir():
                try:
                    narrative_files = [
                        p for p in narratives_dir.glob("*.md")
                        if p.is_file()
                    ]
                    counts.narratives += len(narrative_files)
                    counts.narrative_paths.extend(narrative_files)
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
            campaign_id: If specified, clear only this campaign's counts cache.
                        Otherwise, clear all caches (counts and campaigns list).
        """
        with self._lock:
            if campaign_id:
                if campaign_id in self._cache:
                    del self._cache[campaign_id]
                    self.logger.debug(f"Cleared cache for campaign: {campaign_id}")
                # Also clear campaigns list cache since it may have changed
                self._campaigns_cache = None
                self.logger.debug("Cleared campaigns list cache")
            else:
                self._cache.clear()
                self._campaigns_cache = None
                self.logger.debug("Cleared all caches")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            return {
                "cached_campaigns": len(self._cache),
                "campaigns_list_cached": self._campaigns_cache is not None,
                "ttl_seconds": self.cache_ttl.total_seconds(),
                "campaigns": list(self._cache.keys())
            }

    def count_sessions(self, campaign_id: str, force_refresh: bool = False) -> int:
        """
        Get just the session count for a campaign (convenience method).

        Args:
            campaign_id: Campaign identifier
            force_refresh: If True, bypass cache and recount

        Returns:
            Number of sessions for the campaign
        """
        counts = self.count_artifacts(campaign_id, force_refresh=force_refresh)
        return counts.sessions

    def count_narratives(self, campaign_id: str, force_refresh: bool = False) -> int:
        """
        Get just the narrative count for a campaign (convenience method).

        Args:
            campaign_id: Campaign identifier
            force_refresh: If True, bypass cache and recount

        Returns:
            Number of narratives for the campaign
        """
        counts = self.count_artifacts(campaign_id, force_refresh=force_refresh)
        return counts.narratives

    def get_all_campaigns(self, use_cache: bool = True) -> List[str]:
        """
        Get list of all campaigns that have artifacts.

        Args:
            use_cache: Whether to use cached results (default: True)

        Returns:
            Sorted list of campaign IDs found in the output directory
        """
        # Check cache first (outside lock for fast path)
        if use_cache and self._campaigns_cache is not None:
            campaigns_list, cached_at = self._campaigns_cache
            age = datetime.now() - cached_at
            if age < self.cache_ttl:
                self.logger.debug(
                    f"Using cached campaign list (age: {age.total_seconds():.1f}s)"
                )
                return campaigns_list

        # Use lock to prevent cache stampede
        with self._lock:
            # Double-check cache inside lock
            if use_cache and self._campaigns_cache is not None:
                campaigns_list, cached_at = self._campaigns_cache
                age = datetime.now() - cached_at
                if age < self.cache_ttl:
                    self.logger.debug(
                        f"Using cached campaign list (age: {age.total_seconds():.1f}s) [lock-recheck]"
                    )
                    return campaigns_list

            # Perform discovery
            campaigns = set()

            if not self.output_dir.exists():
                self.logger.warning(f"Output directory not found: {self.output_dir}")
                return []

            try:
                data_files = list(self.output_dir.glob("**/*_data.json"))
            except Exception as e:
                self.logger.error(f"Failed to glob data files: {e}")
                return []

            for data_path in data_files:
                try:
                    payload = json.loads(data_path.read_text(encoding="utf-8"))
                    metadata = payload.get("metadata") or {}
                    campaign_id = metadata.get("campaign_id")
                    if campaign_id:
                        campaigns.add(campaign_id)
                except Exception as e:
                    self.logger.debug(f"Skipping {data_path.name}: {e}")
                    continue

            campaigns_list = sorted(campaigns)

            # Cache the result
            self._campaigns_cache = (campaigns_list, datetime.now())
            self.logger.debug(f"Cached campaign list with {len(campaigns_list)} campaigns")

            return campaigns_list

    def get_campaign_summary(self, campaign_id: str, force_refresh: bool = False) -> Dict:
        """
        Get detailed summary of campaign artifacts.

        Args:
            campaign_id: Campaign identifier
            force_refresh: If True, bypass cache and recount

        Returns:
            Dictionary with detailed counts, session IDs, and narrative paths
        """
        counts = self.count_artifacts(campaign_id, force_refresh=force_refresh)

        # Start with the base dictionary from to_dict()
        summary = counts.to_dict()

        # Add campaign_id and errors (not in base to_dict)
        summary["campaign_id"] = campaign_id
        summary["errors"] = counts.errors

        # Rename keys for consistency with existing API
        summary["session_count"] = summary.pop("sessions")
        summary["narrative_count"] = summary.pop("narratives")

        return summary
