"""
Session analyzer for extracting and comparing session metrics.

This module provides the SessionAnalyzer class which:
- Loads session data from JSON files
- Extracts comprehensive metrics
- Compares multiple sessions
- Generates timelines and insights
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from functools import lru_cache

from .data_models import (
    SessionMetrics,
    CharacterStats,
    ComparisonResult,
    TimelineData
)

logger = logging.getLogger("DDSessionProcessor.session_analyzer")

# Insight generation thresholds (extracted as constants for maintainability)
DURATION_THRESHOLD_LONG = 1.5  # Sessions >150% of average are considered "notably long"
DURATION_THRESHOLD_SHORT = 0.5  # Sessions <50% of average are considered "notably short"
IC_THRESHOLD_HIGH = 20.0  # IC% deviation above average to trigger "high IC" insight
OOC_THRESHOLD_HIGH = 20.0  # OOC% deviation above average to trigger "high OOC" insight
SPEAKER_COUNT_THRESHOLD = 2.0  # Speaker count deviation above average to trigger insight
IC_VARIANCE_CONSISTENT = 10.0  # Standard deviation below this is "consistent"
IC_VARIANCE_VARYING = 25.0  # Standard deviation above this is "varying significantly"


class SessionAnalyzer:
    """
    Analyzer for extracting and comparing session metrics.

    This class provides methods to:
    - Load session data from output directory
    - Extract comprehensive metrics from session JSON
    - Calculate character statistics
    - Compare multiple sessions
    - Generate timeline data
    - Auto-generate insights

    Example:
        analyzer = SessionAnalyzer(project_root=Path("/path/to/project"))
        sessions = analyzer.load_multiple_sessions(["session1", "session2"])
        comparison = analyzer.compare_sessions(sessions)
        print(comparison.insights)
    """

    def __init__(self, project_root: Path):
        """
        Initialize the session analyzer.

        Args:
            project_root: Root directory of the project (contains output/ directory)
        """
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "output"

        # Validate output directory exists
        if not self.output_dir.exists():
            logger.warning(f"Output directory does not exist: {self.output_dir}")

    def list_available_sessions(self) -> List[str]:
        """
        List all available session IDs from the output directory.

        Returns:
            List of session IDs (directory names in output/)

        Example:
            ['session1', 'session2', '20251117_123456_mysession']
        """
        if not self.output_dir.exists():
            logger.warning(f"Output directory not found: {self.output_dir}")
            return []

        try:
            # Each session has its own timestamped directory
            sessions = []
            for item in self.output_dir.iterdir():
                if item.is_dir():
                    # Check if directory contains a _data.json file
                    json_files = list(item.glob("*_data.json"))
                    if json_files:
                        sessions.append(item.name)

            logger.info(f"Found {len(sessions)} sessions in {self.output_dir}")
            return sorted(sessions)

        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []

    def find_session_data_file(self, session_id: str) -> Optional[Path]:
        """
        Find the data JSON file for a given session.

        Args:
            session_id: Session identifier (directory name)

        Returns:
            Path to *_data.json file, or None if not found
        """
        # Security: Validate session_id to prevent path traversal attacks
        if "/" in session_id or "\\" in session_id or ".." in session_id:
            logger.warning(f"Invalid session_id rejected (path traversal attempt): {session_id}")
            return None

        session_dir = self.output_dir / session_id

        # Security: Verify resolved path is within output_dir
        try:
            if not session_dir.resolve().is_relative_to(self.output_dir.resolve()):
                logger.warning(f"Path traversal attempt detected: {session_id}")
                return None
        except (ValueError, OSError) as e:
            logger.warning(f"Error resolving session path: {e}")
            return None

        if not session_dir.exists() or not session_dir.is_dir():
            logger.warning(f"Session directory not found: {session_dir}")
            return None

        # Find the *_data.json file
        json_files = list(session_dir.glob("*_data.json"))

        if not json_files:
            logger.warning(f"No *_data.json file found in {session_dir}")
            return None

        if len(json_files) > 1:
            logger.warning(f"Multiple *_data.json files found in {session_dir}, using first")

        return json_files[0]

    @lru_cache(maxsize=50)
    def load_session(self, session_id: str) -> Optional[SessionMetrics]:
        """
        Load and extract metrics from a session.

        This method is cached to avoid reloading the same session multiple times.

        Args:
            session_id: Session identifier

        Returns:
            SessionMetrics object, or None if session cannot be loaded

        Raises:
            FileNotFoundError: If session data file is not found
            json.JSONDecodeError: If JSON file is malformed
        """
        logger.info(f"Loading session: {session_id}")

        # Find the data file
        data_file = self.find_session_data_file(session_id)
        if not data_file:
            logger.error(f"Session data file not found for: {session_id}")
            return None

        try:
            # Load JSON data
            with open(data_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Extract metrics
            metrics = self.extract_metrics(session_data, session_id)

            logger.info(
                f"Loaded session {session_id}: "
                f"{metrics.duration_formatted()}, "
                f"{metrics.message_count} messages, "
                f"{metrics.speaker_count} speakers"
            )

            return metrics

        except FileNotFoundError as e:
            logger.error(f"Session data file not found: {data_file}")
            raise

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {data_file}: {e}")
            raise

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
            return None

    def load_multiple_sessions(self, session_ids: List[str]) -> List[SessionMetrics]:
        """
        Load multiple sessions.

        Args:
            session_ids: List of session identifiers

        Returns:
            List of SessionMetrics objects (excludes failed loads)
        """
        logger.info(f"Loading {len(session_ids)} sessions")

        sessions = []
        for session_id in session_ids:
            try:
                session = self.load_session(session_id)
                if session:
                    sessions.append(session)
            except Exception as e:
                logger.warning(f"Failed to load session {session_id}: {e}")
                continue

        logger.info(f"Successfully loaded {len(sessions)}/{len(session_ids)} sessions")
        return sessions

    @staticmethod
    def _get_speaker_name(segment: dict) -> Optional[str]:
        """
        Extract speaker/character name from segment.

        Tries multiple fields in priority order:
        1. speaker_name (primary field)
        2. character (fallback field)

        Args:
            segment: Segment dictionary from session data

        Returns:
            Speaker name or None if not found
        """
        return segment.get("speaker_name") or segment.get("character")

    def extract_metrics(self, session_data: dict, session_id: str) -> SessionMetrics:
        """
        Extract comprehensive metrics from session JSON data.

        Args:
            session_data: Parsed JSON session data
            session_id: Session identifier

        Returns:
            SessionMetrics object with all calculated metrics

        Raises:
            KeyError: If required fields are missing from session data
            ValueError: If data is malformed or invalid
        """
        # Extract metadata
        metadata = session_data.get("metadata", {})
        segments = session_data.get("segments", [])

        if not segments:
            logger.warning(f"Session {session_id} has no segments")

        # Initialize metrics
        session_name = metadata.get("session_id", session_id)
        total_duration = 0.0
        ic_duration = 0.0
        ooc_duration = 0.0
        ic_count = 0
        ooc_count = 0
        speakers = set()

        # Track character statistics
        char_stats_dict: Dict[str, CharacterStats] = {}

        # Process each segment
        for segment in segments:
            # Extract segment data
            start_time = segment.get("start_time", 0.0)
            end_time = segment.get("end_time", 0.0)
            duration = end_time - start_time

            text = segment.get("text", "")
            speaker_id = segment.get("speaker_id", "UNKNOWN")
            speaker_name = self._get_speaker_name(segment)
            classification = segment.get("classification", "OOC").upper()

            # Calculate word count
            word_count = len(text.split()) if text else 0

            # Update total duration
            total_duration = max(total_duration, end_time)

            # Track speakers
            if speaker_name:
                speakers.add(speaker_name)

                # Initialize character stats if needed
                if speaker_name not in char_stats_dict:
                    char_stats_dict[speaker_name] = CharacterStats(
                        character_name=speaker_name,
                        first_appearance=start_time
                    )

                # Update character stats
                char_stat = char_stats_dict[speaker_name]
                char_stat.message_count += 1
                char_stat.word_count += word_count
                char_stat.speaking_duration += duration
                char_stat.last_appearance = end_time

                # Update IC/OOC counts for character
                if classification == "IC":
                    char_stat.ic_messages += 1
                else:
                    char_stat.ooc_messages += 1

            # Update session-wide IC/OOC metrics
            if classification == "IC":
                ic_count += 1
                ic_duration += duration
            else:
                ooc_count += 1
                ooc_duration += duration

        # Calculate average message lengths for each character
        for char_stat in char_stats_dict.values():
            if char_stat.message_count > 0:
                char_stat.avg_message_length = char_stat.word_count / char_stat.message_count

        # Extract timestamp from metadata or filename
        timestamp = None
        if "timestamp" in metadata:
            try:
                timestamp = datetime.fromisoformat(metadata["timestamp"])
            except (ValueError, TypeError):
                pass

        # If no timestamp in metadata, try to parse from session_id
        if not timestamp:
            try:
                # Format: YYYYMMDD_HHMMSS_session_name
                if "_" in session_id:
                    date_part = session_id.split("_")[0]
                    time_part = session_id.split("_")[1]
                    timestamp_str = f"{date_part}_{time_part}"
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            except (ValueError, IndexError):
                pass

        # Create SessionMetrics object
        metrics = SessionMetrics(
            session_id=session_id,
            session_name=session_name,
            duration=total_duration,
            speaker_count=len(speakers),
            message_count=ic_count + ooc_count,
            ic_message_count=ic_count,
            ooc_message_count=ooc_count,
            ic_duration=ic_duration,
            ooc_duration=ooc_duration,
            character_stats=char_stats_dict,
            timestamp=timestamp,
            metadata=metadata
        )

        return metrics

    def calculate_character_stats(self, segments: List[dict]) -> Dict[str, CharacterStats]:
        """
        Calculate character statistics from segments.

        This is a helper method used by extract_metrics.

        Args:
            segments: List of segment dictionaries

        Returns:
            Dictionary mapping character names to CharacterStats
        """
        char_stats: Dict[str, CharacterStats] = {}

        for segment in segments:
            speaker_name = self._get_speaker_name(segment)
            if not speaker_name:
                continue

            # Initialize if needed
            if speaker_name not in char_stats:
                char_stats[speaker_name] = CharacterStats(
                    character_name=speaker_name,
                    first_appearance=segment.get("start_time", 0.0)
                )

            # Update stats
            stat = char_stats[speaker_name]
            stat.message_count += 1
            stat.word_count += len(segment.get("text", "").split())

            # Calculate duration from timestamps (segments don't have duration field)
            duration = segment.get("end_time", 0.0) - segment.get("start_time", 0.0)
            stat.speaking_duration += max(0.0, duration)  # Ensure non-negative
            stat.last_appearance = segment.get("end_time", 0.0)

            # Update IC/OOC
            if segment.get("classification", "").upper() == "IC":
                stat.ic_messages += 1
            else:
                stat.ooc_messages += 1

        # Calculate averages
        for stat in char_stats.values():
            if stat.message_count > 0:
                stat.avg_message_length = stat.word_count / stat.message_count

        return char_stats

    def compare_sessions(self, sessions: List[SessionMetrics]) -> ComparisonResult:
        """
        Compare multiple sessions and generate insights.

        Args:
            sessions: List of SessionMetrics to compare

        Returns:
            ComparisonResult with differences and insights

        Raises:
            ValueError: If sessions list is empty
        """
        if not sessions:
            raise ValueError("Cannot compare empty list of sessions")

        logger.info(f"Comparing {len(sessions)} sessions")

        # Calculate differences
        differences = {
            "duration": [s.duration for s in sessions],
            "message_count": [float(s.message_count) for s in sessions],
            "speaker_count": [float(s.speaker_count) for s in sessions],
            "ic_percentage": [s.ic_percentage() for s in sessions],
            "ooc_percentage": [s.ooc_percentage() for s in sessions],
        }

        # Generate insights
        insights = self.generate_insights(sessions, differences)

        # Create comparison result
        comparison = ComparisonResult(
            sessions=sessions,
            differences=differences,
            insights=insights,
            comparison_date=datetime.now()
        )

        return comparison

    def generate_insights(
        self,
        sessions: List[SessionMetrics],
        differences: Dict[str, List[float]]
    ) -> List[str]:
        """
        Generate auto-insights from session comparison.

        Args:
            sessions: List of sessions being compared
            differences: Dictionary of metric differences

        Returns:
            List of insight strings
        """
        insights = []

        if not sessions:
            return insights

        # Provide a useful summary even when comparing a single session so the
        # UI and tests are guaranteed to surface at least one insight.
        if len(sessions) == 1:
            session = sessions[0]
            summary = (
                f"Session '{session.session_name}' lasted {session.duration_formatted()} "
                f"with {session.message_count} messages "
                f"({session.ic_percentage():.1f}% IC / {session.ooc_percentage():.1f}% OOC)."
            )
            insights.append(summary)

            top_speaker = session.get_top_speakers(1)
            if top_speaker:
                name, stats = top_speaker[0]
                speaker_summary = (
                    f"Top speaker: {name} spoke {stats.message_count} messages "
                    f"over {stats.speaking_duration:.0f}s "
                    f"({stats.ic_percentage():.1f}% IC)."
                )
                insights.append(speaker_summary)

            return insights

        # Duration insights
        durations = differences["duration"]
        avg_duration = sum(durations) / len(durations)
        longest = max(sessions, key=lambda s: s.duration)
        shortest = min(sessions, key=lambda s: s.duration)

        if longest.duration > avg_duration * DURATION_THRESHOLD_LONG:
            insights.append(
                f"Session '{longest.session_name}' was notably long "
                f"({longest.duration_formatted()}), {int((DURATION_THRESHOLD_LONG - 1) * 100)}%+ above average"
            )

        if shortest.duration < avg_duration * DURATION_THRESHOLD_SHORT:
            insights.append(
                f"Session '{shortest.session_name}' was notably short "
                f"({shortest.duration_formatted()}), 50%+ below average"
            )

        # IC/OOC insights
        ic_percentages = differences["ic_percentage"]
        avg_ic = sum(ic_percentages) / len(ic_percentages)

        most_ic = max(sessions, key=lambda s: s.ic_percentage())
        most_ooc = max(sessions, key=lambda s: s.ooc_percentage())

        if most_ic.ic_percentage() > avg_ic + IC_THRESHOLD_HIGH:
            insights.append(
                f"Session '{most_ic.session_name}' had high IC content "
                f"({most_ic.ic_percentage():.1f}%), well above average"
            )

        if most_ooc.ooc_percentage() > (100 - avg_ic) + OOC_THRESHOLD_HIGH:
            insights.append(
                f"Session '{most_ooc.session_name}' had high OOC content "
                f"({most_ooc.ooc_percentage():.1f}%), well above average"
            )

        # Speaker count insights
        speaker_counts = differences["speaker_count"]
        avg_speakers = sum(speaker_counts) / len(speaker_counts)

        most_speakers = max(sessions, key=lambda s: s.speaker_count)
        if most_speakers.speaker_count > avg_speakers + SPEAKER_COUNT_THRESHOLD:
            insights.append(
                f"Session '{most_speakers.session_name}' had {most_speakers.speaker_count} "
                f"speakers, more than typical ({avg_speakers:.1f} average)"
            )

        # Consistency insights
        if len(sessions) >= 3:
            ic_variance = sum((x - avg_ic) ** 2 for x in ic_percentages) / len(ic_percentages)
            ic_std_dev = ic_variance ** 0.5

            if ic_std_dev < IC_VARIANCE_CONSISTENT:
                insights.append(
                    f"Sessions show consistent IC/OOC balance "
                    f"(avg {avg_ic:.1f}% IC, std dev {ic_std_dev:.1f}%)"
                )
            elif ic_std_dev > IC_VARIANCE_VARYING:
                insights.append(
                    f"Sessions vary significantly in IC/OOC balance "
                    f"(std dev {ic_std_dev:.1f}%)"
                )

        # Character participation insights (if multiple sessions)
        if len(sessions) >= 2:
            all_characters = set()
            for session in sessions:
                all_characters.update(session.character_stats.keys())

            # Find characters who appear in all sessions
            consistent_characters = set()
            for char in all_characters:
                appears_in_all = all(
                    char in session.character_stats
                    for session in sessions
                )
                if appears_in_all:
                    consistent_characters.add(char)

            if consistent_characters and len(consistent_characters) == len(all_characters):
                insights.append(
                    f"All {len(consistent_characters)} characters appeared in every session"
                )
            elif consistent_characters:
                insights.append(
                    f"{len(consistent_characters)} characters appeared consistently "
                    f"across all sessions"
                )

        return insights

    def generate_timeline(self, sessions: List[SessionMetrics]) -> TimelineData:
        """
        Generate timeline data from sessions.

        Args:
            sessions: List of sessions to include in timeline

        Returns:
            TimelineData object with chronological progression
        """
        logger.info(f"Generating timeline for {len(sessions)} sessions")

        # Sort sessions chronologically
        sorted_sessions = sorted(
            sessions,
            key=lambda s: s.timestamp or datetime.min
        )

        # Create timeline data
        timeline = TimelineData(sessions=sorted_sessions)

        logger.info(f"Timeline generated with {len(timeline.ic_ooc_ratios)} data points")

        return timeline
