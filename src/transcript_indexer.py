"""
Transcript Indexer - Build searchable index of all session transcripts.

This module provides functionality to scan the output directory for processed
session transcripts and build an in-memory searchable index with caching support.

Author: Claude (Sonnet 4.5)
Date: 2025-11-17
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

logger = logging.getLogger("DDSessionProcessor.transcript_indexer")


@dataclass
class TranscriptSegment:
    """
    A single segment from a transcript.

    Represents one line of dialogue or narration from a D&D session,
    including all metadata needed for searching and filtering.
    """

    session_id: str
    timestamp: float  # Seconds from start of session
    timestamp_str: str  # HH:MM:SS format for display
    speaker: str
    text: str
    ic_ooc: str  # "IC", "OOC", or "Unknown"
    segment_index: int  # Position in session (0-based)

    # Optional metadata
    session_date: Optional[str] = None  # YYYYMMDD_HHMMSS from directory name
    file_path: Optional[Path] = None  # Path to source JSON file


@dataclass
class TranscriptIndex:
    """
    Searchable index of all transcripts.

    Maintains an in-memory index of all transcript segments across all sessions,
    with metadata for efficient filtering and searching.
    """

    segments: List[TranscriptSegment] = field(default_factory=list)
    sessions: Dict[str, Dict] = field(default_factory=dict)  # session_id -> metadata
    speakers: Set[str] = field(default_factory=set)
    indexed_at: datetime = field(default_factory=datetime.now)

    def add_segment(self, segment: TranscriptSegment) -> None:
        """
        Add a segment to the index.

        Args:
            segment: TranscriptSegment to add
        """
        self.segments.append(segment)
        self.speakers.add(segment.speaker)

    def add_session_metadata(self, session_id: str, metadata: Dict) -> None:
        """
        Add session metadata to the index.

        Args:
            session_id: Unique session identifier
            metadata: Dictionary of session metadata
        """
        self.sessions[session_id] = metadata

    def get_total_segments(self) -> int:
        """
        Get total number of indexed segments.

        Returns:
            Count of all segments across all sessions
        """
        return len(self.segments)

    def get_session_count(self) -> int:
        """
        Get number of indexed sessions.

        Returns:
            Count of unique sessions
        """
        return len(self.sessions)


class TranscriptIndexer:
    """
    Build and maintain searchable index of transcript data.

    Features:
    - Indexes all transcripts in output directory
    - Caches index to disk for fast loading
    - Supports incremental updates
    - Extracts metadata from JSON data files

    The indexer scans session output directories (format: YYYYMMDD_HHMMSS_<session_id>)
    and parses the *_data.json files to build a searchable index.
    """

    def __init__(self, output_dir: Path, cache_dir: Path = None):
        """
        Initialize the indexer.

        Args:
            output_dir: Directory containing session output folders
            cache_dir: Directory for cache storage (defaults to output_dir/.cache)
        """
        self.output_dir = Path(output_dir)
        self.cache_dir = Path(cache_dir) if cache_dir else self.output_dir / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # FIX: Use JSON instead of pickle for security (prevents arbitrary code execution)
        self.cache_file = self.cache_dir / "transcript_index.json"
        self.index: Optional[TranscriptIndex] = None

    def build_index(self, force_rebuild: bool = False) -> TranscriptIndex:
        """
        Build or load the transcript index.

        Attempts to load from cache first unless force_rebuild is True.
        If cache doesn't exist or is invalid, builds a new index.

        Args:
            force_rebuild: Force rebuild even if cache exists

        Returns:
            TranscriptIndex with all indexed segments
        """
        # Try to load from cache if available
        if not force_rebuild and self.cache_file.exists():
            logger.info(f"Loading index from cache: {self.cache_file}")
            try:
                self.index = self._load_cache()
                logger.info(
                    f"Loaded index: {self.index.get_total_segments()} segments "
                    f"from {self.index.get_session_count()} sessions"
                )
                return self.index
            except Exception as e:
                logger.warning(f"Failed to load cache, rebuilding: {e}")

        # Build new index
        logger.info(f"Building transcript index from {self.output_dir}")
        self.index = TranscriptIndex()

        # Find all session directories
        if not self.output_dir.exists():
            logger.warning(f"Output directory does not exist: {self.output_dir}")
            return self.index

        session_dirs = [
            d for d in self.output_dir.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ]

        logger.info(f"Found {len(session_dirs)} session directories")

        for session_dir in sorted(session_dirs):
            try:
                self._index_session(session_dir)
            except Exception as e:
                logger.error(f"Error indexing session {session_dir.name}: {e}", exc_info=True)
                continue

        # Save to cache
        self._save_cache()

        logger.info(
            f"Index built: {self.index.get_total_segments()} segments "
            f"from {self.index.get_session_count()} sessions"
        )

        return self.index

    def _index_session(self, session_dir: Path) -> None:
        """
        Index a single session directory.

        Parses the directory name to extract session_id and date,
        then loads the JSON data file and indexes all segments.

        Args:
            session_dir: Path to session output directory
        """
        # Extract session_id from directory name
        # Format: YYYYMMDD_HHMMSS_<session_id>
        dir_name = session_dir.name
        parts = dir_name.split('_', 2)
        if len(parts) < 3:
            logger.warning(f"Invalid directory name format: {dir_name}")
            return

        session_date = f"{parts[0]}_{parts[1]}"
        session_id = parts[2]

        # Look for JSON data file
        # FIX: Sort to ensure deterministic behavior if multiple files exist
        json_files = sorted(list(session_dir.glob("*_data.json")))
        if not json_files:
            logger.warning(f"No data.json file found in {session_dir}")
            return

        # Warn if multiple JSON files found (should be rare)
        if len(json_files) > 1:
            logger.warning(
                f"Multiple data.json files found in {session_dir}, using {json_files[0]}"
            )

        data_file = json_files[0]

        # Load transcript data
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {data_file}: {e}")
            return

        # Extract session metadata
        session_metadata = {
            'session_id': session_id,
            'session_date': session_date,
            'directory': str(session_dir),
            'num_speakers': data.get('num_speakers', 0),
            'total_duration': data.get('total_duration', 0),
            'ic_percentage': data.get('ic_percentage', 0),
            'ooc_percentage': data.get('ooc_percentage', 0)
        }

        self.index.add_session_metadata(session_id, session_metadata)

        # Index segments
        segments = data.get('segments', [])
        for idx, segment in enumerate(segments):
            transcript_segment = TranscriptSegment(
                session_id=session_id,
                timestamp=segment.get('start', 0.0),
                timestamp_str=segment.get('timestamp', '00:00:00'),
                speaker=segment.get('speaker', 'Unknown'),
                text=segment.get('text', ''),
                ic_ooc=segment.get('classification', 'Unknown'),
                segment_index=idx,
                session_date=session_date,
                file_path=data_file
            )
            self.index.add_segment(transcript_segment)

        logger.debug(f"Indexed {len(segments)} segments from {session_id}")

    def _load_cache(self) -> TranscriptIndex:
        """
        Load index from JSON cache file.

        FIX: Use JSON instead of pickle for security (prevents arbitrary code execution).

        Returns:
            Loaded TranscriptIndex

        Raises:
            Exception if cache file is invalid or corrupted
        """
        with open(self.cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Reconstruct TranscriptIndex from JSON
        index = TranscriptIndex()

        # Deserialize segments
        for seg_data in data.get('segments', []):
            segment = TranscriptSegment(
                session_id=seg_data['session_id'],
                timestamp=seg_data['timestamp'],
                timestamp_str=seg_data['timestamp_str'],
                speaker=seg_data['speaker'],
                text=seg_data['text'],
                ic_ooc=seg_data['ic_ooc'],
                segment_index=seg_data['segment_index'],
                session_date=seg_data.get('session_date'),
                file_path=Path(seg_data['file_path']) if seg_data.get('file_path') else None,
            )
            index.add_segment(segment)

        # Restore sessions metadata
        index.sessions = data.get('sessions', {})

        # Restore indexed_at timestamp
        if 'indexed_at' in data:
            index.indexed_at = datetime.fromisoformat(data['indexed_at'])

        return index

    def _save_cache(self) -> None:
        """
        Save index to cache file using JSON.

        FIX: Use JSON instead of pickle for security (prevents arbitrary code execution).
        The cache file is stored in the cache directory and can be
        quickly loaded on subsequent runs to avoid re-indexing.
        """
        try:
            # Serialize index to JSON-compatible format
            data = {
                'indexed_at': self.index.indexed_at.isoformat(),
                'sessions': self.index.sessions,
                'segments': [
                    {
                        'session_id': seg.session_id,
                        'timestamp': seg.timestamp,
                        'timestamp_str': seg.timestamp_str,
                        'speaker': seg.speaker,
                        'text': seg.text,
                        'ic_ooc': seg.ic_ooc,
                        'segment_index': seg.segment_index,
                        'session_date': seg.session_date,
                        'file_path': str(seg.file_path) if seg.file_path else None,
                    }
                    for seg in self.index.segments
                ],
            }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Index cached to {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get_index(self) -> TranscriptIndex:
        """
        Get the current index (builds if necessary).

        Returns:
            TranscriptIndex instance
        """
        if self.index is None:
            self.build_index()
        return self.index

    def invalidate_cache(self) -> None:
        """
        Invalidate the cache and force rebuild on next access.

        Deletes the cache file and resets the in-memory index.
        Call this after adding new sessions to force a rebuild.
        """
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Cache invalidated")
        self.index = None

    def is_index_stale(self) -> bool:
        """
        Check if the index is stale (new sessions added since last build).

        IMPROVEMENT 3: Detect index staleness to prompt users to rebuild.
        This prevents users from missing recent sessions in search results.

        Returns:
            True if index exists but is older than newest session directory
        """
        if not self.index:
            return True

        if not self.output_dir.exists():
            return False

        # Get index timestamp
        index_time = self.index.indexed_at

        # Find newest session directory
        session_dirs = [
            d
            for d in self.output_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

        if not session_dirs:
            return False

        # Check if any session is newer than index
        for session_dir in session_dirs:
            if session_dir.stat().st_mtime > index_time.timestamp():
                logger.info(
                    f"Index is stale: {session_dir.name} is newer than index"
                )
                return True

        return False
